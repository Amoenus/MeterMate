# Service Categorization PRD

> **📋 Document Type**: Implementation Guide
> **🔗 Related**: [Service Base Classes](service-base-classes.md), [Service Module Structure](service-module-structure.md)
> **📅 Last Updated**: 2025-11-06

---

## Overview

This document defines how MeterMate services are categorized into query, mutation, and admin types, with specific registration patterns and permission requirements for each.

**Goal**: Clear categorization of services by their behavior and required permissions.

**Autonomy Level**: 🟡 Collaborative - Implement with human validation at completion

---

## Service Categories

### Three-Category System

MeterMate services fall into three distinct categories:

1. **Query Services** - Read-only operations
2. **Mutation Services** - Data modification operations
3. **Admin Services** - Destructive or bulk operations (require admin)

---

## Query Services (Read-Only)

### Characteristics

- ✅ **Read-only**: Never modify data
- ✅ **Safe**: Can be called repeatedly without side effects
- ✅ **Response support**: Return data to caller
- ✅ **Fast**: Should execute quickly
- ✅ **No permissions required**: Any user can call

### Query Service List

| Service | Purpose | Response |
|---------|---------|----------|
| `get_readings` | Retrieve readings for period | List of readings |
| `validate_reading` | Check if reading is valid | Validation result |

### Query Service Template

```python
"""Query service template."""
from ..base import AbstractMeterMateQueryService
from ..schemas import SERVICE_GET_READINGS_SCHEMA

class GetReadingsService(AbstractMeterMateQueryService):
    """Query service example."""

    @property
    def service(self) -> str:
        return "get_readings"

    @property
    def schema(self):
        return SERVICE_GET_READINGS_SCHEMA

    async def async_handle_service(self, call: ServiceCall) -> dict:
        """Handle query - must return dict."""
        entity_id = call.data["entity_id"]

        # Read data (no modifications)
        readings = await self.data_manager.get_readings(entity_id)

        # Return structured response
        return {
            "readings": [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat(),
                    "value": r.value,
                    "unit": r.unit,
                }
                for r in readings
            ]
        }
```

### Query Service Registration

Query services register with `SupportsResponse.OPTIONAL`:

```python
from homeassistant.core import SupportsResponse

hass.services.async_register(
    domain="metermate",
    service="get_readings",
    service_func=handler,
    schema=schema,
    supports_response=SupportsResponse.OPTIONAL,
)
```

---

## Mutation Services (Data Modification)

### Characteristics

- ⚠️ **Modifies data**: Adds, updates, or deletes records
- ⚠️ **Side effects**: Changes persist to database
- ✅ **Logged**: Operations logged for audit trail
- ✅ **Idempotent**: Safe to retry (when possible)
- ✅ **No admin required**: Regular users can call

### Mutation Service List

| Service | Purpose | Data Changed |
|---------|---------|--------------|
| `add_reading` | Add single reading | Inserts into statistics |
| `update_reading` | Modify existing reading | Updates statistics |
| `delete_reading` | Remove reading | Deletes from statistics |
| `add_meter_reading` | Add meter reading (calculates consumption) | Inserts calculated data |
| `add_consumption_period` | Add consumption for period | Inserts consumption data |
| `update_meter_reading` | Modify meter reading | Updates statistics |
| `update_consumption_period` | Modify consumption period | Updates statistics |

### Mutation Service Template

```python
"""Mutation service template."""
from ..base import AbstractMeterMateMutationService
from ..schemas import SERVICE_ADD_READING_SCHEMA
from ...exceptions import MeterMateDatabaseError
from ...models import Reading

class AddReadingService(AbstractMeterMateMutationService):
    """Mutation service example."""

    @property
    def service(self) -> str:
        return "add_reading"

    @property
    def schema(self):
        return SERVICE_ADD_READING_SCHEMA

    async def _async_execute(self, call: ServiceCall) -> None:
        """Execute mutation - modifies data."""
        entity_id = call.data["entity_id"]

        # Pre-flight checks
        await self._ensure_entity_exists(entity_id)

        # Create and persist reading
        reading = Reading.from_service_call(call.data)
        result = await self.data_manager.add_reading(entity_id, reading)

        if not result.success:
            raise MeterMateDatabaseError(result.message)

        # Mutation completed - logged by base class
```

### Mutation Service Registration

Standard service registration (no response support needed):

```python
hass.services.async_register(
    domain="metermate",
    service="add_reading",
    service_func=handler,
    schema=schema,
)
```

---

## Admin Services (Destructive Operations)

### Characteristics

- 🔴 **Destructive**: May delete or overwrite data
- 🔴 **Bulk operations**: Processes many records at once
- 🔴 **Requires admin**: Only administrators can call
- ⚠️ **Prominent logging**: Logged at WARNING level
- ⚠️ **Safety checks**: Extra validation before execution
- ⚠️ **Long-running**: May take significant time

### Admin Service List

| Service | Purpose | Why Admin Required |
|---------|---------|-------------------|
| `bulk_import` | Import many readings | Bulk data modification |
| `recalculate_statistics` | Rebuild stats from readings | Overwrites existing statistics |
| `rebuild_history` | Complete history rebuild | Destructive operation |
| `import_from_csv` | Import from CSV file | Bulk data import |

### Admin Service Template

```python
"""Admin service template."""
from ..base import AbstractMeterMateAdminService
from ..schemas import SERVICE_REBUILD_HISTORY_SCHEMA
from ...exceptions import MeterMateDatabaseError, MeterMateValidationError

class RebuildHistoryService(AbstractMeterMateAdminService):
    """Admin service example."""

    @property
    def service(self) -> str:
        return "rebuild_history"

    @property
    def schema(self):
        return SERVICE_REBUILD_HISTORY_SCHEMA

    async def _async_execute_admin(self, call: ServiceCall) -> None:
        """Execute admin operation - extra safety checks."""
        entity_id = call.data["entity_id"]
        complete_wipe = call.data.get("complete_wipe", True)

        # Extra safety checks for admin operations
        await self._ensure_entity_exists(entity_id)

        readings = await self.data_manager.get_all_readings(entity_id)
        if not readings:
            raise MeterMateValidationError(
                "Cannot rebuild history: no readings found"
            )

        _LOGGER.warning(
            "Starting DESTRUCTIVE operation: rebuilding %d readings",
            len(readings)
        )

        # Execute potentially destructive operation
        result = await self.data_manager.rebuild_history(
            entity_id,
            complete_wipe=complete_wipe,
        )

        if not result.success:
            raise MeterMateDatabaseError(result.message)

        # Success logged at WARNING level by base class
```

### Admin Service Registration

Uses `async_register_admin_service` for permission enforcement:

```python
from homeassistant.helpers.service import async_register_admin_service

async_register_admin_service(
    hass=hass,
    domain="metermate",
    service="rebuild_history",
    service_func=handler,
    schema=schema,
)
```

---

## Decision Matrix

### Choosing the Right Category

Use this flowchart to categorize a new service:

```
Does it modify data?
├─ NO → Query Service
│   └─ Implement AbstractMeterMateQueryService
│       └─ Return dict response
│
└─ YES → Does it perform bulk/destructive operations?
    ├─ NO → Mutation Service
    │   └─ Implement AbstractMeterMateMutationService
    │       └─ Implement _async_execute
    │
    └─ YES → Admin Service
        └─ Implement AbstractMeterMateAdminService
            └─ Implement _async_execute_admin
```

### Examples by Category

**Query** (read-only):
- Get readings for date range
- Validate input without saving
- Check entity status
- Count readings

**Mutation** (single-record changes):
- Add one reading
- Update one reading
- Delete one reading
- Add meter reading (with calculation)

**Admin** (bulk/destructive):
- Import 1000+ readings
- Rebuild entire history
- Recalculate all statistics
- Delete all readings for entity

---

## Permission Model

### Query Services
- **Permission**: None required
- **Rationale**: Read-only operations are safe
- **User Experience**: Works for all users

### Mutation Services
- **Permission**: None required (standard HA permissions apply)
- **Rationale**: Users should control their own data
- **User Experience**: Authorized users can modify their meters

### Admin Services
- **Permission**: Administrator role required
- **Rationale**: Destructive operations need extra protection
- **User Experience**: Prevents accidental data loss
- **Implementation**: `async_register_admin_service` enforces this

---

## Logging Standards by Category

### Query Services
```python
# INFO level - successful operations
_LOGGER.info("Retrieved %d readings for %s", count, entity_id)

# DEBUG level - detailed information
_LOGGER.debug("Query parameters: start=%s, end=%s", start, end)

# WARNING level - unusual but not error
_LOGGER.warning("No readings found for %s", entity_id)
```

### Mutation Services
```python
# INFO level - all mutations (base class logs start)
_LOGGER.info("Service %s called for entity %s", service_name, entity_id)

# INFO level - successful completion
_LOGGER.info("Successfully added reading: %s", reading_id)

# ERROR level - operation failed
_LOGGER.error("Failed to add reading: %s", error_message)
```

### Admin Services
```python
# WARNING level - operation start (base class logs)
_LOGGER.warning("ADMIN OPERATION: %s called", service_name)

# INFO level - progress updates
_LOGGER.info("Processing reading %d of %d", current, total)

# WARNING level - completion (base class logs)
_LOGGER.warning("ADMIN OPERATION COMPLETED: %s", service_name)

# ERROR level - failure (base class logs)
_LOGGER.error("ADMIN OPERATION FAILED: %s", error_message)
```

---

## Service Registration Orchestration

### File: `services/__init__.py`

```python
"""Service registration with proper categorization."""
from typing import TYPE_CHECKING

from .queries.get_readings import GetReadingsService
from .queries.validate_reading import ValidateReadingService
from .mutations.add_reading import AddReadingService
from .mutations.update_reading import UpdateReadingService
from .mutations.delete_reading import DeleteReadingService
from .admin.bulk_import import BulkImportService
from .admin.rebuild_history import RebuildHistoryService

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from ..data_manager import MeterMateDataManager

# Service registry organized by category
QUERY_SERVICES = [
    GetReadingsService,
    ValidateReadingService,
]

MUTATION_SERVICES = [
    AddReadingService,
    UpdateReadingService,
    DeleteReadingService,
]

ADMIN_SERVICES = [
    BulkImportService,
    RebuildHistoryService,
]

ALL_SERVICES = QUERY_SERVICES + MUTATION_SERVICES + ADMIN_SERVICES


async def async_setup_services(
    hass: HomeAssistant,
    data_manager: MeterMateDataManager
) -> None:
    """Register all services with proper categorization."""
    _LOGGER.info("Registering MeterMate services")

    for service_class in ALL_SERVICES:
        service = service_class(hass, data_manager)
        service.async_register()

        # Determine category for logging
        if isinstance(service, AbstractMeterMateQueryService):
            category = "query"
        elif isinstance(service, AbstractMeterMateAdminService):
            category = "admin"
        else:
            category = "mutation"

        _LOGGER.debug(
            "Registered %s service: %s",
            category,
            service.service,
        )

    _LOGGER.info(
        "Registered %d services: %d queries, %d mutations, %d admin",
        len(ALL_SERVICES),
        len(QUERY_SERVICES),
        len(MUTATION_SERVICES),
        len(ADMIN_SERVICES),
    )
```

---

## Testing by Category

### Query Service Tests

```python
async def test_query_service_returns_data(hass, data_manager, entity):
    """Test that query service returns expected data."""
    service = GetReadingsService(hass, data_manager)
    call = mock_service_call({"entity_id": entity.entity_id})

    result = await service.async_handle_service(call)

    assert "readings" in result
    assert isinstance(result["readings"], list)


async def test_query_service_no_permissions_required(hass, data_manager):
    """Test that query services don't require admin."""
    service = GetReadingsService(hass, data_manager)
    # Verify it's not registered as admin service
    assert not hasattr(service, '_async_execute_admin')
```

### Mutation Service Tests

```python
async def test_mutation_service_modifies_data(hass, data_manager, entity):
    """Test that mutation service persists changes."""
    service = AddReadingService(hass, data_manager)
    call = mock_service_call({
        "entity_id": entity.entity_id,
        "value": 100.0,
    })

    await service.async_handle_service(call)

    # Verify data was persisted
    readings = await data_manager.get_readings(entity.entity_id)
    assert len(readings) > 0


async def test_mutation_service_logs_operation(hass, data_manager, caplog):
    """Test that mutation services log operations."""
    service = AddReadingService(hass, data_manager)

    await service.async_handle_service(mock_call)

    assert any("called for entity" in record.message for record in caplog.records)
```

### Admin Service Tests

```python
async def test_admin_service_requires_permissions(hass):
    """Test that admin services are registered with permissions."""
    service = RebuildHistoryService(hass, Mock())
    service.async_register()

    # Verify admin registration
    # (This is integration test territory - check HA service registry)


async def test_admin_service_logs_prominently(hass, data_manager, caplog):
    """Test that admin operations log at WARNING level."""
    import logging
    caplog.set_level(logging.WARNING)

    service = RebuildHistoryService(hass, data_manager)
    await service.async_handle_service(mock_call)

    assert any("ADMIN OPERATION" in record.message for record in caplog.records)
```

---

## Success Criteria

### Must Have ✅
- [ ] All services correctly categorized
- [ ] Query services use response support
- [ ] Admin services use admin registration
- [ ] Proper logging per category
- [ ] Permission model enforced

### Should Have 🎯
- [ ] Clear documentation per category
- [ ] Decision matrix for new services
- [ ] Category-specific tests
- [ ] Registration orchestration

### Nice to Have ✨
- [ ] Service metadata per category
- [ ] Performance targets per category
- [ ] Rate limiting per category
- [ ] Monitoring per category

---

## Related Documents

- **[Service Base Classes](service-base-classes.md)**: The base classes for each category
- **[Service Module Structure](service-module-structure.md)**: Directory organization by category
- **[Phase 2 Migration Guide](phase-2-migration-guide.md)**: Migration strategy

---

## References

- Home Assistant admin services: https://developers.home-assistant.io/docs/dev_101_services/#admin-only-services
- Service response support: https://developers.home-assistant.io/docs/dev_101_services/#service-responses
- Logging best practices: https://developers.home-assistant.io/docs/development_logging

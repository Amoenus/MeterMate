# Phase 2 PRD: Service Architecture Enhancement

> **🤖 LLM Operator Context**: This PRD follows the **LLM-First Operations Model** (ADR-000). You are expected to implement this modular refactoring autonomously with human validation at migration milestones.

**Status**: � Planned
**Priority**: �🟡 HIGH
**Complexity**: Medium-High
**Impact**: Medium - Improves maintainability and extensibility
**Timeline**: 2-3 weeks
**Dependencies**: Phase 1 completion
**Deciders**: Primary Operator + LLM Co-maintainer
**Last Updated**: 2025-11-05

---

## 🤖 LLM Operator Guidance

### Autonomy Level
🟡 **Collaborative** - Implement migration autonomously with human validation at each week milestone

### Key Tools for This Phase
- `create_file` - Creating new service modules and base classes
- `replace_string_in_file` - Refactoring existing services
- `semantic_search` - Finding all service references
- `grep_search` - Locating service registration points
- `list_code_usages` - Tracking service dependencies
- `runTests` - Validating each migration step

### Migration Checkpoints (Require Human Validation)
1. **Week 1 End**: Base infrastructure created, old services still work
2. **Week 2 End**: All services migrated, dual compatibility maintained
3. **Week 3 End**: Cleanup complete, tests passing, ready for deployment

### Success Indicators
- ✅ Each service module <150 lines, focused on single responsibility
- ✅ All admin services properly registered with permissions
- ✅ 100% backward compatibility during migration
- ✅ Independent test coverage for each service

### Escalation Triggers
- 🔴 Service registration breaks existing automations
- 🔴 Admin service permissions not working correctly
- 🔴 Performance degradation detected during migration
- 🔴 Complex service dependencies discovered

---

## Executive Summary

Phase 2 builds on Phase 1's validation improvements by implementing a **modular service architecture** with proper separation of concerns and admin service patterns. This phase focuses on making MeterMate's services more maintainable, testable, and extensible while maintaining backward compatibility.

### Key Principle: Modular is Maintainable

Industry best practices show:
- ✅ **One service per file** - Easy to find, understand, test
- ✅ **Base classes** - Shared functionality, consistent patterns
- ✅ **Admin services** - Special permissions for destructive operations
- ✅ **Clear separation** - Reading vs writing, query vs mutation

### Goals:
1. 🎯 Implement service base class hierarchy
2. 🎯 Split monolithic `services.py` into focused modules
3. 🎯 Add admin service registration for destructive operations
4. 🎯 Improve service discoverability and documentation
5. 🎯 Enable easier testing and extension

---

## Current State vs Target State

### Current Architecture (Monolithic)

```
custom_components/metermate/
  services.py (800+ lines)
    - MeterMateServices class
    - 12+ service handlers in one class
    - All services treated equally
    - Hard to find specific functionality
    - Difficult to test individually
```

**Problems**:
- 🔴 800+ line file hard to navigate
- 🔴 All services in one class (god object)
- 🔴 No distinction between safe and destructive operations
- 🔴 Hard to add new services without conflicts
- 🔴 Testing requires setting up entire service suite

### Target Architecture (Modular)

```
custom_components/metermate/
  services/
    __init__.py                    # Registration orchestration
    base.py                        # Base classes
    schemas.py                     # All service schemas

    # Read-only services (safe operations)
    queries/
      __init__.py
      get_readings.py              # Query readings
      validate_reading.py          # Validate without saving

    # Write services (data modification)
    mutations/
      __init__.py
      add_reading.py               # Add single reading
      update_reading.py            # Update existing reading
      delete_reading.py            # Delete reading
      add_meter_reading.py         # Add meter reading
      add_consumption_period.py    # Add consumption period

    # Admin services (destructive operations)
    admin/
      __init__.py
      bulk_import.py               # Bulk operations
      recalculate_statistics.py    # Recalculate stats
      rebuild_history.py           # Rebuild from scratch
      import_from_csv.py           # CSV import
```

**Benefits**:
- ✅ Each service ~50-100 lines, easy to understand
- ✅ Clear categorization (queries, mutations, admin)
- ✅ Easy to find and modify specific functionality
- ✅ Can test services individually
- ✅ Easy to add new services without touching existing code

---

## Detailed Implementation Plan

### Task 1: Create Service Base Classes (2 days)

**Goal**: Implement industry-standard base class hierarchy for MeterMate services with proper separation of concerns.

#### File: `services/base.py`

```python
"""Base classes for MeterMate services."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.helpers.service import async_register_admin_service

from ..const import ATTR_INTEGRATION_NAME
from ..exceptions import MeterMateEntityNotFoundError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from ..data_manager import MeterMateDataManager

_LOGGER = logging.getLogger(__name__)


class AbstractMeterMateService(ABC):
    """Abstract base for all MeterMate services."""

    def __init__(
        self,
        hass: HomeAssistant,
        data_manager: MeterMateDataManager
    ) -> None:
        """Initialize the service."""
        self.hass = hass
        self.data_manager = data_manager

    @property
    @abstractmethod
    def domain(self) -> str:
        """Return the domain."""
        return ATTR_INTEGRATION_NAME

    @property
    @abstractmethod
    def service(self) -> str:
        """Return the service name."""

    @property
    @abstractmethod
    def schema(self) -> dict[str, Any] | None:
        """Return the service schema."""

    @abstractmethod
    async def async_handle_service(self, call: ServiceCall) -> Any:
        """Handle the service call."""

    @callback
    def async_register(self) -> None:
        """Register the service."""
        self.hass.services.async_register(
            self.domain,
            self.service,
            self.async_handle_service,
            schema=vol.Schema(self.schema) if self.schema else None,
        )

    # Helper methods available to all services
    def _get_entity(self, entity_id: str):
        """Get entity from hass data."""
        if (
            ATTR_INTEGRATION_NAME not in self.hass.data
            or "entities" not in self.hass.data[ATTR_INTEGRATION_NAME]
        ):
            return None
        return self.hass.data[ATTR_INTEGRATION_NAME]["entities"].get(entity_id)

    async def _ensure_entity_exists(self, entity_id: str) -> None:
        """Ensure entity exists, raise if not."""
        if not self._get_entity(entity_id):
            raise MeterMateEntityNotFoundError(
                f"Entity {entity_id} not found. "
                "Please create the sensor first."
            )


class AbstractMeterMateQueryService(AbstractMeterMateService):
    """Base for read-only query services (supports response)."""

    @callback
    def async_register(self) -> None:
        """Register query service with response support."""
        from homeassistant.core import SupportsResponse

        self.hass.services.async_register(
            self.domain,
            self.service,
            self.async_handle_service,
            schema=vol.Schema(self.schema) if self.schema else None,
            supports_response=SupportsResponse.OPTIONAL,
        )


class AbstractMeterMateMutationService(AbstractMeterMateService):
    """Base for services that modify data (add, update, delete)."""

    async def async_handle_service(self, call: ServiceCall) -> None:
        """Handle mutation service with logging."""
        _LOGGER.info(
            "Service %s called for entity %s",
            self.service,
            call.data.get("entity_id", "N/A"),
        )
        try:
            await self._async_execute(call)
        except Exception as e:
            _LOGGER.exception("Error executing %s", self.service)
            raise

    @abstractmethod
    async def _async_execute(self, call: ServiceCall) -> None:
        """Execute the mutation operation."""


class AbstractMeterMateAdminService(AbstractMeterMateService):
    """Base for admin-only services (destructive operations)."""

    @callback
    def async_register(self) -> None:
        """Register as admin service."""
        async_register_admin_service(
            hass=self.hass,
            domain=self.domain,
            service=self.service,
            service_func=self.async_handle_service,
            schema=vol.Schema(self.schema) if self.schema else None,
        )

    async def async_handle_service(self, call: ServiceCall) -> None:
        """Handle admin service with extra logging and safety checks."""
        _LOGGER.warning(
            "Admin service %s called - this may modify or delete data",
            self.service,
        )
        try:
            await self._async_execute_admin(call)
        except Exception as e:
            _LOGGER.exception("Error executing admin service %s", self.service)
            raise

    @abstractmethod
    async def _async_execute_admin(self, call: ServiceCall) -> None:
        """Execute the admin operation."""
```

#### Usage Pattern

```python
# Example: Simple mutation service
class AddReadingService(AbstractMeterMateMutationService):
    """Service to add a reading."""

    @property
    def service(self) -> str:
        return "add_reading"

    @property
    def schema(self):
        return SERVICE_ADD_READING_SCHEMA  # From schemas.py

    async def _async_execute(self, call: ServiceCall) -> None:
        """Add a reading."""
        entity_id = call.data["entity_id"]
        await self._ensure_entity_exists(entity_id)

        # Business logic here
        reading = Reading(...)
        result = await self.data_manager.add_reading(entity_id, reading)

        if not result.success:
            raise MeterMateDatabaseError(result.message)
```

### Task 2: Service Schema Centralization (1 day)

**Goal**: Move all schemas to a single file for easy reference and reuse.

#### File: `services/schemas.py`

```python
"""Service schemas for MeterMate."""
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from ..const import ATTR_ENTITY_ID, ATTR_NOTES, ATTR_UNIT_OF_MEASUREMENT
from ..validators import (
    metermate_entity_id,
    past_datetime,
    positive_float,
    valid_consumption,
    valid_meter_reading,
)

# Query service schemas
SERVICE_GET_READINGS_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Optional("start_date"): cv.datetime,
    vol.Optional("end_date"): cv.datetime,
}

SERVICE_VALIDATE_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("value"): positive_float,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): cv.string,
}

# Mutation service schemas
SERVICE_ADD_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("value"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): cv.string,
    vol.Optional(ATTR_NOTES): cv.string,
}

SERVICE_UPDATE_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("reading_id"): cv.string,
    vol.Required("meter_reading"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): cv.string,
    vol.Optional(ATTR_NOTES, default=""): cv.string,
}

SERVICE_DELETE_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("reading_id"): cv.string,
}

# Meter-specific service schemas
SERVICE_ADD_METER_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("meter_reading"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): cv.string,
    vol.Optional(ATTR_NOTES, default=""): cv.string,
}

SERVICE_ADD_CONSUMPTION_PERIOD_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("consumption"): valid_consumption,
    vol.Required("period_start"): cv.datetime,
    vol.Required("period_end"): cv.datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): cv.string,
    vol.Optional(ATTR_NOTES, default=""): cv.string,
}

# Admin service schemas
SERVICE_BULK_IMPORT_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("readings"): vol.All(
        cv.ensure_list,
        [
            {
                vol.Required("timestamp"): cv.datetime,
                vol.Required("value"): positive_float,
                vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): cv.string,
                vol.Optional(ATTR_NOTES): cv.string,
            }
        ],
    ),
}

SERVICE_RECALCULATE_STATISTICS_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
}

SERVICE_REBUILD_HISTORY_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Optional("complete_wipe", default=True): cv.boolean,
}

SERVICE_IMPORT_FROM_CSV_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("file_path"): cv.string,
    vol.Optional("delimiter", default=","): cv.string,
    vol.Optional("decimal", default="."): cv.string,
    vol.Optional("timezone"): cv.string,
    vol.Optional("date_format"): cv.string,
    vol.Optional("dry_run", default=False): cv.boolean,
}
```

### Task 3: Implement Individual Service Modules (3-4 days)

**Goal**: Split each service into its own focused module.

#### Example: `services/queries/get_readings.py`

```python
"""Get readings query service."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from ..base import AbstractMeterMateQueryService
from ..schemas import SERVICE_GET_READINGS_SCHEMA
from ...const import ATTR_ENTITY_ID, ATTR_NOTES, ATTR_UNIT_OF_MEASUREMENT
from ...data_manager import TimePeriod

if TYPE_CHECKING:
    from homeassistant.core import ServiceCall

_LOGGER = logging.getLogger(__name__)


class GetReadingsService(AbstractMeterMateQueryService):
    """Service to query readings for an entity."""

    @property
    def service(self) -> str:
        """Return service name."""
        return "get_readings"

    @property
    def schema(self):
        """Return service schema."""
        return SERVICE_GET_READINGS_SCHEMA

    async def async_handle_service(self, call: ServiceCall) -> dict:
        """Handle get_readings service call."""
        entity_id = call.data[ATTR_ENTITY_ID]
        start_date = call.data.get("start_date")
        end_date = call.data.get("end_date")

        _LOGGER.info("Getting readings for %s", entity_id)

        # Ensure dates are timezone-aware
        if start_date is not None:
            start_date = dt_util.as_utc(start_date)
        if end_date is not None:
            end_date = dt_util.as_utc(end_date)

        period = None
        if start_date and end_date:
            period = TimePeriod(start=start_date, end=end_date)

        # Get the readings
        readings = await self.data_manager.get_readings(entity_id, period)

        _LOGGER.info("Retrieved %d readings for %s", len(readings), entity_id)

        # Convert to response format
        readings_data = [
            {
                "id": reading.id,
                "timestamp": reading.timestamp.isoformat(),
                "value": reading.value,
                ATTR_UNIT_OF_MEASUREMENT: reading.unit,
                ATTR_NOTES: reading.notes,
                "period_start": (
                    reading.period_start.isoformat()
                    if reading.period_start else None
                ),
                "period_end": (
                    reading.period_end.isoformat()
                    if reading.period_end else None
                ),
                "consumption": reading.consumption,
            }
            for reading in readings
        ]

        return {"readings": readings_data}
```

#### Example: `services/mutations/add_reading.py`

```python
"""Add reading mutation service."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

from ..base import AbstractMeterMateMutationService
from ..schemas import SERVICE_ADD_READING_SCHEMA
from ...const import ATTR_ENTITY_ID, ATTR_NOTES, ATTR_UNIT_OF_MEASUREMENT
from ...exceptions import MeterMateDatabaseError
from ...models import Reading

if TYPE_CHECKING:
    from homeassistant.core import ServiceCall

_LOGGER = logging.getLogger(__name__)


class AddReadingService(AbstractMeterMateMutationService):
    """Service to add a single reading."""

    @property
    def service(self) -> str:
        """Return service name."""
        return "add_reading"

    @property
    def schema(self):
        """Return service schema."""
        return SERVICE_ADD_READING_SCHEMA

    async def _async_execute(self, call: ServiceCall) -> None:
        """Execute add reading operation."""
        entity_id = call.data[ATTR_ENTITY_ID]
        value = call.data["value"]
        timestamp = call.data.get("timestamp", dt_util.utcnow())
        unit = call.data.get(ATTR_UNIT_OF_MEASUREMENT, "kWh")
        notes = call.data.get(ATTR_NOTES)

        # Ensure entity exists
        await self._ensure_entity_exists(entity_id)

        # Ensure timestamp is timezone-aware
        if timestamp is not None:
            timestamp = dt_util.as_utc(timestamp)

        # Create reading object
        reading = Reading(
            timestamp=timestamp,
            value=value,
            unit=unit,
            notes=notes,
        )

        # Add the reading
        result = await self.data_manager.add_reading(entity_id, reading)

        if not result.success:
            raise MeterMateDatabaseError(result.message)

        _LOGGER.info(
            "Successfully added reading for %s: %s %s at %s",
            entity_id,
            value,
            unit,
            timestamp,
        )
```

#### Example: `services/admin/rebuild_history.py`

```python
"""Rebuild history admin service."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..base import AbstractMeterMateAdminService
from ..schemas import SERVICE_REBUILD_HISTORY_SCHEMA
from ...const import ATTR_ENTITY_ID
from ...exceptions import MeterMateDatabaseError

if TYPE_CHECKING:
    from homeassistant.core import ServiceCall

_LOGGER = logging.getLogger(__name__)


class RebuildHistoryService(AbstractMeterMateAdminService):
    """Admin service to rebuild history from readings."""

    @property
    def service(self) -> str:
        """Return service name."""
        return "rebuild_history"

    @property
    def schema(self):
        """Return service schema."""
        return SERVICE_REBUILD_HISTORY_SCHEMA

    async def _async_execute_admin(self, call: ServiceCall) -> None:
        """Execute rebuild history operation."""
        entity_id = call.data[ATTR_ENTITY_ID]
        complete_wipe = call.data.get("complete_wipe", True)

        # Ensure entity exists
        await self._ensure_entity_exists(entity_id)

        _LOGGER.warning(
            "Starting %s rebuild for %s - this will modify statistics",
            "complete" if complete_wipe else "incremental",
            entity_id,
        )

        # Rebuild history
        result = await self.data_manager.rebuild_history(
            entity_id, complete_wipe=complete_wipe
        )

        if not result.success:
            raise MeterMateDatabaseError(result.message)

        _LOGGER.info(
            "Successfully rebuilt history for %s: %s",
            entity_id,
            result.message,
        )
```

### Task 4: Service Registration Orchestration (1 day)

**Goal**: Create clean registration system that discovers and registers all services.

#### File: `services/__init__.py`

```python
"""MeterMate service registration."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .queries.get_readings import GetReadingsService
from .queries.validate_reading import ValidateReadingService
from .mutations.add_reading import AddReadingService
from .mutations.update_reading import UpdateReadingService
from .mutations.delete_reading import DeleteReadingService
from .mutations.add_meter_reading import AddMeterReadingService
from .mutations.add_consumption_period import AddConsumptionPeriodService
from .mutations.update_meter_reading import UpdateMeterReadingService
from .mutations.update_consumption_period import UpdateConsumptionPeriodService
from .admin.bulk_import import BulkImportService
from .admin.recalculate_statistics import RecalculateStatisticsService
from .admin.rebuild_history import RebuildHistoryService
from .admin.import_from_csv import ImportFromCSVService

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from ..data_manager import MeterMateDataManager

_LOGGER = logging.getLogger(__name__)

# Registry of all service classes
QUERY_SERVICES = [
    GetReadingsService,
    ValidateReadingService,
]

MUTATION_SERVICES = [
    AddReadingService,
    UpdateReadingService,
    DeleteReadingService,
    AddMeterReadingService,
    AddConsumptionPeriodService,
    UpdateMeterReadingService,
    UpdateConsumptionPeriodService,
]

ADMIN_SERVICES = [
    BulkImportService,
    RecalculateStatisticsService,
    RebuildHistoryService,
    ImportFromCSVService,
]

ALL_SERVICES = QUERY_SERVICES + MUTATION_SERVICES + ADMIN_SERVICES


async def async_setup_services(
    hass: HomeAssistant,
    data_manager: MeterMateDataManager
) -> None:
    """Register all MeterMate services."""
    _LOGGER.debug("Registering MeterMate services")

    for service_class in ALL_SERVICES:
        service = service_class(hass, data_manager)
        service.async_register()
        _LOGGER.debug(
            "Registered %s service: %s",
            service.__class__.__base__.__name__,
            service.service,
        )

    _LOGGER.info(
        "Registered %d MeterMate services (%d queries, %d mutations, %d admin)",
        len(ALL_SERVICES),
        len(QUERY_SERVICES),
        len(MUTATION_SERVICES),
        len(ADMIN_SERVICES),
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload all MeterMate services."""
    from ..const import ATTR_INTEGRATION_NAME

    for service_class in ALL_SERVICES:
        # Create temporary instance just to get service name
        temp_instance = service_class(hass, None)  # type: ignore[arg-type]
        hass.services.async_remove(ATTR_INTEGRATION_NAME, temp_instance.service)

    _LOGGER.debug("Unregistered all MeterMate services")
```

### Task 5: Documentation & Discovery (1 day)

**Goal**: Document service architecture and enable easy discovery.

#### File: `services/README.md`

```markdown
# MeterMate Services Architecture

## Overview

MeterMate services are organized into three categories:

### Query Services (Read-Only)
Located in `services/queries/`

Services that retrieve data without modifying anything:
- `get_readings` - Query readings for a period
- `validate_reading` - Validate reading without saving

### Mutation Services (Data Modification)
Located in `services/mutations/`

Services that add, update, or delete individual readings:
- `add_reading` - Add a single reading
- `update_reading` - Update existing reading
- `delete_reading` - Delete a reading
- `add_meter_reading` - Add meter reading (calculates consumption)
- `add_consumption_period` - Add consumption for period
- `update_meter_reading` - Update meter reading
- `update_consumption_period` - Update consumption period

### Admin Services (Destructive Operations)
Located in `services/admin/`

Services that perform bulk or destructive operations (require admin permission):
- `bulk_import` - Import multiple readings at once
- `recalculate_statistics` - Recalculate statistics from readings
- `rebuild_history` - Rebuild entire history from scratch
- `import_from_csv` - Import from CSV file

## Adding a New Service

1. Choose the appropriate category (query, mutation, or admin)
2. Create a new file in the corresponding directory
3. Extend the appropriate base class:
   - `AbstractMeterMateQueryService` for read-only
   - `AbstractMeterMateMutationService` for data modification
   - `AbstractMeterMateAdminService` for destructive operations
4. Implement required properties and methods
5. Add schema to `services/schemas.py`
6. Register in `services/__init__.py`

### Example:

```python
# services/queries/my_new_service.py
from ..base import AbstractMeterMateQueryService
from ..schemas import SERVICE_MY_NEW_SERVICE_SCHEMA

class MyNewService(AbstractMeterMateQueryService):
    @property
    def service(self) -> str:
        return "my_new_service"

    @property
    def schema(self):
        return SERVICE_MY_NEW_SERVICE_SCHEMA

    async def async_handle_service(self, call: ServiceCall) -> dict:
        # Implementation
        return {"result": "data"}
```

## Testing Services

Each service can be tested independently:

```python
# tests/services/queries/test_get_readings.py
async def test_get_readings_service(hass, data_manager):
    service = GetReadingsService(hass, data_manager)
    call = mock_service_call({"entity_id": "sensor.test"})
    result = await service.async_handle_service(call)
    assert "readings" in result
```

## Service Base Classes

### AbstractMeterMateService
Base for all services. Provides:
- Entity existence checking
- Access to data manager
- Common helper methods

### AbstractMeterMateQueryService
For read-only operations. Adds:
- Response support (can return data)
- No transaction management needed

### AbstractMeterMateMutationService
For data modification. Adds:
- Transaction logging
- Operation tracking
- Rollback support (future)

### AbstractMeterMateAdminService
For admin operations. Adds:
- Admin service registration
- Extra safety checks
- Warning logging
```

---

## Migration Strategy

### Phase 2A: Create Infrastructure (Week 1)
1. Create `services/` directory structure
2. Implement base classes in `services/base.py`
3. Create `services/schemas.py` with all schemas
4. Create `services/__init__.py` registration
5. Keep old `services.py` intact

### Phase 2B: Migrate Services (Week 2)
1. Migrate query services first (safest)
2. Migrate mutation services next
3. Migrate admin services last
4. Update imports in `__init__.py` to use new services
5. Keep old `services.py` as compatibility layer

### Phase 2C: Cleanup & Testing (Week 3)
1. Deprecate old `services.py` (keep as re-export)
2. Add comprehensive tests for each service
3. Update documentation
4. Add service discovery helpers

---

## Success Criteria

### Must Have ✅
- [ ] All base classes implemented and tested
- [ ] All existing services migrated to new structure
- [ ] 100% backward compatibility maintained
- [ ] Registration system works for all services
- [ ] Admin services properly registered
- [ ] All services independently testable

### Should Have 🎯
- [ ] Service README documentation
- [ ] Examples for adding new services
- [ ] Migration guide for developers
- [ ] Service discovery helpers
- [ ] Comprehensive test coverage

### Nice to Have ✨
- [ ] Auto-discovery of services (no manual registration)
- [ ] Service metadata for UI generation
- [ ] Performance monitoring per service
- [ ] Service dependency graph

---

## Testing Strategy

### Unit Tests (Per Service)
```python
# Test each service independently
async def test_add_reading_service_success(hass, data_manager, entity):
    service = AddReadingService(hass, data_manager)
    call = mock_service_call({
        "entity_id": entity.entity_id,
        "value": 100.0,
    })
    await service.async_handle_service(call)
    # Assert reading was added

async def test_add_reading_service_invalid_entity(hass, data_manager):
    service = AddReadingService(hass, data_manager)
    call = mock_service_call({
        "entity_id": "sensor.nonexistent",
        "value": 100.0,
    })
    with pytest.raises(MeterMateEntityNotFoundError):
        await service.async_handle_service(call)
```

### Integration Tests (Full Flow)
```python
async def test_service_registration(hass, data_manager):
    """Test all services are registered."""
    await async_setup_services(hass, data_manager)

    # Verify all services registered
    for service_class in ALL_SERVICES:
        service = service_class(hass, data_manager)
        assert hass.services.has_service(ATTR_INTEGRATION_NAME, service.service)

async def test_admin_service_permissions(hass, data_manager):
    """Test admin services require permissions."""
    service = RebuildHistoryService(hass, data_manager)
    # Verify it's registered as admin service
    # Test permission checks work
```

---

## Performance Considerations

### Service Initialization
- Base classes are lightweight (no heavy initialization)
- Services created once during setup
- Shared data_manager instance across all services

### Service Execution
- Each service is focused on one operation
- No cross-service dependencies
- Easy to profile individual services

### Memory Usage
- One instance per service (not per call)
- Schemas defined once, reused
- No state stored in service instances

---

## Future Enhancements (Phase 3+)

### Service Composition
```python
class CompositeService(AbstractMeterMateService):
    """Service that composes multiple services."""

    def __init__(self, hass, data_manager):
        super().__init__(hass, data_manager)
        self.add_reading = AddReadingService(hass, data_manager)
        self.update_sensor = UpdateSensorService(hass, data_manager)

    async def async_handle_service(self, call: ServiceCall):
        # Use composed services
        await self.add_reading.async_handle_service(call)
        await self.update_sensor.async_handle_service(call)
```

### Service Middleware
```python
class LoggingMiddleware:
    """Log all service calls."""

    async def __call__(self, service, call):
        _LOGGER.info("Service %s called", service.service)
        result = await service.async_handle_service(call)
        _LOGGER.info("Service %s completed", service.service)
        return result
```

### Service Metadata
```python
class ServiceMetadata:
    """Metadata for UI generation."""

    description: str
    examples: list[dict]
    response_schema: dict
    permissions: list[str]
```

---

## Dependencies

### Code Dependencies
- Phase 1 completion (validators, exceptions)
- Existing: `homeassistant.helpers.service`
- No new dependencies

### Knowledge Dependencies
- Understanding of modular service architecture patterns
- Familiarity with HA admin service registration
- Python ABC (Abstract Base Classes)
- Service registration patterns in Home Assistant core

---

## Risks & Mitigation

### Risk: Breaking Existing Integrations
**Mitigation**:
- Keep old `services.py` as compatibility layer during migration
- Extensive integration testing
- Gradual rollout with deprecation warnings

### Risk: Over-Engineering
**Mitigation**:
- Keep base classes simple and focused
- Only add functionality when needed
- Resist adding features not in current services

### Risk: Test Coverage Gaps
**Mitigation**:
- Test each service independently
- Integration tests for registration
- Test admin service permissions specifically

---

## Timeline

- **Week 1**: Infrastructure
  - Day 1-2: Base classes and schemas
  - Day 3: Registration system
  - Day 4-5: Documentation and examples

- **Week 2**: Migration
  - Day 1: Migrate query services
  - Day 2-3: Migrate mutation services
  - Day 4: Migrate admin services
  - Day 5: Testing and refinement

- **Week 3**: Polish
  - Day 1-2: Comprehensive testing
  - Day 3: Documentation updates
  - Day 4: Performance testing
  - Day 5: Code review and cleanup

---

## Questions for Implementation

1. Should we support service auto-discovery or explicit registration?
2. How to handle service dependencies (if any)?
3. Should services emit events for monitoring/debugging?
4. What level of logging detail per service?
5. Should we version the service API?

---

## References

### Related Documentation
- **ADR-000**: LLM-First Operations Model - Operational philosophy guiding this refactoring
- **Phase 1 PRD**: Validation patterns that this architecture builds upon
- **LLM Operator's Handbook**: Migration patterns and testing procedures

### External References
- Home Assistant admin services: https://developers.home-assistant.io/docs/dev_101_services
- Python ABC (Abstract Base Classes): https://docs.python.org/3/library/abc.html
- Service best practices: https://developers.home-assistant.io/docs/creating_integration_services
- Home Assistant service registration: https://developers.home-assistant.io/docs/dev_101_services/#registering-your-service

### Implementation Examples
- Home Assistant core service patterns: https://github.com/home-assistant/core/tree/dev/homeassistant/helpers/service.py
- Modular integration examples in HA core: Search for integrations using `async_register_admin_service`

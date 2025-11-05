# Service Module Structure PRD

> **📋 Document Type**: Implementation Guide
> **🔗 Related**: [Service Base Classes](service-base-classes.md), [Service Categorization](service-categorization.md)
> **📅 Last Updated**: 2025-11-06

---

## Overview

This document defines the directory structure and file organization for MeterMate's modular service architecture.

**Goal**: Organize services into focused modules that are easy to navigate, test, and extend.

**Autonomy Level**: 🟡 Collaborative - Implement with human validation at completion

---

## Directory Structure

```
custom_components/metermate/services/
├── __init__.py                    # Service registration orchestration
├── base.py                        # Base classes (all categories)
├── schemas.py                     # Centralized schemas
│
├── queries/                       # Read-only services
│   ├── __init__.py
│   ├── get_readings.py           # Get readings for period
│   └── validate_reading.py       # Validate reading without saving
│
├── mutations/                     # Data modification services
│   ├── __init__.py
│   ├── add_reading.py            # Add single reading
│   ├── update_reading.py         # Update existing reading
│   ├── delete_reading.py         # Delete reading
│   ├── add_meter_reading.py      # Add meter reading (calculates consumption)
│   ├── add_consumption_period.py # Add consumption for period
│   ├── update_meter_reading.py   # Update meter reading
│   └── update_consumption_period.py # Update consumption period
│
└── admin/                         # Admin-only services
    ├── __init__.py
    ├── bulk_import.py            # Bulk import readings
    ├── recalculate_statistics.py # Recalculate statistics
    ├── rebuild_history.py        # Rebuild history
    └── import_from_csv.py        # Import from CSV file
```

---

## File: `services/__init__.py`

```python
"""MeterMate service registration.

This module orchestrates the registration of all MeterMate services,
organizing them by category (query, mutation, admin) and handling
the setup/teardown lifecycle.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# Import all service classes
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

# Service registry organized by category
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
    """Register all MeterMate services.

    Services are registered in order:
    1. Query services (read-only)
    2. Mutation services (data modification)
    3. Admin services (destructive operations)

    Args:
        hass: Home Assistant instance
        data_manager: MeterMate data manager

    Raises:
        Exception: If service registration fails
    """
    _LOGGER.debug("Registering MeterMate services")

    for service_class in ALL_SERVICES:
        try:
            service = service_class(hass, data_manager)
            service.async_register()
            _LOGGER.debug("Registered service: %s", service.service)
        except Exception as e:
            _LOGGER.exception(
                "Failed to register service %s",
                service_class.__name__,
            )
            raise

    _LOGGER.info(
        "Registered %d MeterMate services (%d queries, %d mutations, %d admin)",
        len(ALL_SERVICES),
        len(QUERY_SERVICES),
        len(MUTATION_SERVICES),
        len(ADMIN_SERVICES),
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload all MeterMate services.

    This is called during integration unload to clean up
    registered services.

    Args:
        hass: Home Assistant instance
    """
    from ..const import ATTR_INTEGRATION_NAME

    _LOGGER.debug("Unloading MeterMate services")

    for service_class in ALL_SERVICES:
        # Create temporary instance to get service name
        temp_instance = service_class(hass, None)  # type: ignore[arg-type]
        hass.services.async_remove(ATTR_INTEGRATION_NAME, temp_instance.service)

    _LOGGER.debug("Unloaded all MeterMate services")
```

---

## Category Modules

### File: `services/queries/__init__.py`

```python
"""Query services for MeterMate.

Query services are read-only operations that return data without
modifying anything. They support response data and can be called
frequently without side effects.
"""
from .get_readings import GetReadingsService
from .validate_reading import ValidateReadingService

__all__ = [
    "GetReadingsService",
    "ValidateReadingService",
]
```

### File: `services/mutations/__init__.py`

```python
"""Mutation services for MeterMate.

Mutation services modify data (add, update, delete). They have
side effects and are logged for audit purposes.
"""
from .add_reading import AddReadingService
from .update_reading import UpdateReadingService
from .delete_reading import DeleteReadingService
from .add_meter_reading import AddMeterReadingService
from .add_consumption_period import AddConsumptionPeriodService
from .update_meter_reading import UpdateMeterReadingService
from .update_consumption_period import UpdateConsumptionPeriodService

__all__ = [
    "AddReadingService",
    "UpdateReadingService",
    "DeleteReadingService",
    "AddMeterReadingService",
    "AddConsumptionPeriodService",
    "UpdateMeterReadingService",
    "UpdateConsumptionPeriodService",
]
```

### File: `services/admin/__init__.py`

```python
"""Admin services for MeterMate.

Admin services perform destructive or bulk operations that require
administrator privileges. They log prominently and have extra
safety checks.
"""
from .bulk_import import BulkImportService
from .recalculate_statistics import RecalculateStatisticsService
from .rebuild_history import RebuildHistoryService
from .import_from_csv import ImportFromCSVService

__all__ = [
    "BulkImportService",
    "RecalculateStatisticsService",
    "RebuildHistoryService",
    "ImportFromCSVService",
]
```

---

## Individual Service File Template

### Query Service Example

**File**: `services/queries/get_readings.py`

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
    """Service to query readings for an entity.

    This service retrieves readings for a specified entity, optionally
    filtered by date range. It returns structured JSON data that can
    be used by automations or UI components.

    Response format:
        {
            "readings": [
                {
                    "id": "uuid",
                    "timestamp": "ISO 8601",
                    "value": float,
                    "unit": "kWh",
                    "notes": "string",
                    "consumption": float or null
                },
                ...
            ]
        }
    """

    @property
    def service(self) -> str:
        """Return service name."""
        return "get_readings"

    @property
    def schema(self):
        """Return service schema."""
        return SERVICE_GET_READINGS_SCHEMA

    async def async_handle_service(self, call: ServiceCall) -> dict:
        """Handle get_readings service call.

        Args:
            call: Service call with validated data

        Returns:
            Dictionary with 'readings' key containing list of readings

        Raises:
            MeterMateEntityNotFoundError: If entity doesn't exist
            MeterMateDatabaseError: If database query fails
        """
        entity_id = call.data[ATTR_ENTITY_ID]
        start_date = call.data.get("start_date")
        end_date = call.data.get("end_date")

        _LOGGER.info("Getting readings for %s", entity_id)

        # Ensure entity exists (raises if not)
        await self._ensure_entity_exists(entity_id)

        # Ensure dates are timezone-aware
        if start_date is not None:
            start_date = dt_util.as_utc(start_date)
        if end_date is not None:
            end_date = dt_util.as_utc(end_date)

        # Build period filter if dates provided
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

### Mutation Service Example

**File**: `services/mutations/add_reading.py`

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
    """Service to add a single reading.

    This service adds a new reading to the specified entity. The reading
    is validated, persisted to the database, and added to Home Assistant's
    statistics for the Energy Dashboard.
    """

    @property
    def service(self) -> str:
        """Return service name."""
        return "add_reading"

    @property
    def schema(self):
        """Return service schema."""
        return SERVICE_ADD_READING_SCHEMA

    async def _async_execute(self, call: ServiceCall) -> None:
        """Execute add reading operation.

        Args:
            call: Service call with validated data

        Raises:
            MeterMateEntityNotFoundError: If entity doesn't exist
            MeterMateDatabaseError: If database operation fails
        """
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

### Admin Service Example

**File**: `services/admin/rebuild_history.py`

```python
"""Rebuild history admin service."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..base import AbstractMeterMateAdminService
from ..schemas import SERVICE_REBUILD_HISTORY_SCHEMA
from ...const import ATTR_ENTITY_ID
from ...exceptions import MeterMateDatabaseError, MeterMateValidationError

if TYPE_CHECKING:
    from homeassistant.core import ServiceCall

_LOGGER = logging.getLogger(__name__)


class RebuildHistoryService(AbstractMeterMateAdminService):
    """Admin service to rebuild history from readings.

    This is a destructive operation that recalculates all statistics
    from the stored readings. Use with caution as it may take significant
    time and will overwrite existing statistics.
    """

    @property
    def service(self) -> str:
        """Return service name."""
        return "rebuild_history"

    @property
    def schema(self):
        """Return service schema."""
        return SERVICE_REBUILD_HISTORY_SCHEMA

    async def _async_execute_admin(self, call: ServiceCall) -> None:
        """Execute rebuild history operation.

        Args:
            call: Service call with validated data

        Raises:
            MeterMateEntityNotFoundError: If entity doesn't exist
            MeterMateValidationError: If no readings found
            MeterMateDatabaseError: If rebuild fails
        """
        entity_id = call.data[ATTR_ENTITY_ID]
        complete_wipe = call.data.get("complete_wipe", True)

        # Ensure entity exists
        await self._ensure_entity_exists(entity_id)

        # Safety check: Verify we have readings to rebuild from
        readings = await self.data_manager.get_all_readings(entity_id)
        reading_count = len(readings)

        if reading_count == 0:
            raise MeterMateValidationError(
                f"Cannot rebuild history for {entity_id}: no readings found. "
                "Add readings first."
            )

        _LOGGER.info(
            "Starting history rebuild for %s: %d readings will be processed",
            entity_id,
            reading_count,
        )

        # Execute rebuild
        result = await self.data_manager.rebuild_history(
            entity_id,
            complete_wipe=complete_wipe,
        )

        if not result.success:
            raise MeterMateDatabaseError(
                f"History rebuild failed: {result.message}"
            )

        _LOGGER.warning(
            "History rebuilt for %s: %s",
            entity_id,
            result.message,
        )
```

---

## Service File Naming Conventions

### Naming Rules

1. **File name** = Service name in snake_case
   - Service: `get_readings` → File: `get_readings.py`
   - Service: `add_meter_reading` → File: `add_meter_reading.py`

2. **Class name** = PascalCase + "Service"
   - File: `get_readings.py` → Class: `GetReadingsService`
   - File: `rebuild_history.py` → Class: `RebuildHistoryService`

3. **One service per file**
   - Each file contains exactly one service class
   - Helper functions can be included if service-specific

### Examples

| Service Name | File Path | Class Name |
|--------------|-----------|------------|
| `get_readings` | `queries/get_readings.py` | `GetReadingsService` |
| `add_reading` | `mutations/add_reading.py` | `AddReadingService` |
| `bulk_import` | `admin/bulk_import.py` | `BulkImportService` |

---

## Service Discovery

### Adding a New Service

1. **Choose category**: Query, mutation, or admin
2. **Create file** in appropriate directory
3. **Implement class** extending appropriate base
4. **Add to category `__init__.py`**
5. **Add to main `__init__.py`** registry
6. **Add schema** to `schemas.py`

### Example: Adding New Query Service

```python
# 1. Create services/queries/count_readings.py
class CountReadingsService(AbstractMeterMateQueryService):
    @property
    def service(self) -> str:
        return "count_readings"

    @property
    def schema(self):
        return SERVICE_COUNT_READINGS_SCHEMA

    async def async_handle_service(self, call):
        # Implementation
        return {"count": count}

# 2. Add to services/queries/__init__.py
from .count_readings import CountReadingsService

__all__ = [
    # ... existing services
    "CountReadingsService",
]

# 3. Add to services/__init__.py
from .queries.count_readings import CountReadingsService

QUERY_SERVICES = [
    # ... existing services
    CountReadingsService,
]

# 4. Add to services/schemas.py
SERVICE_COUNT_READINGS_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
}
```

---

## Testing Structure

### Test File Organization

```
tests/services/
├── test_base.py                   # Base class tests
├── queries/
│   ├── test_get_readings.py
│   └── test_validate_reading.py
├── mutations/
│   ├── test_add_reading.py
│   ├── test_update_reading.py
│   └── test_delete_reading.py
└── admin/
    ├── test_bulk_import.py
    ├── test_rebuild_history.py
    └── test_import_from_csv.py
```

### Test File Template

```python
"""Tests for [service_name] service."""
import pytest
from unittest.mock import Mock

from custom_components.metermate.services.queries.get_readings import (
    GetReadingsService
)


async def test_service_name_is_correct():
    """Test service name matches."""
    service = GetReadingsService(Mock(), Mock())
    assert service.service == "get_readings"


async def test_service_has_schema():
    """Test service schema is defined."""
    service = GetReadingsService(Mock(), Mock())
    assert service.schema is not None


async def test_service_execution_success(hass, data_manager, entity):
    """Test service executes successfully."""
    service = GetReadingsService(hass, data_manager)
    call = mock_service_call({"entity_id": entity.entity_id})

    result = await service.async_handle_service(call)

    assert "readings" in result


async def test_service_entity_not_found(hass, data_manager):
    """Test service raises when entity not found."""
    service = GetReadingsService(hass, data_manager)
    call = mock_service_call({"entity_id": "sensor.nonexistent"})

    with pytest.raises(MeterMateEntityNotFoundError):
        await service.async_handle_service(call)
```

---

## Success Criteria

### Must Have ✅
- [ ] Services organized by category (queries/mutations/admin)
- [ ] One service per file
- [ ] Consistent file naming
- [ ] Clear registration in `__init__.py`
- [ ] All services discoverable

### Should Have 🎯
- [ ] Category `__init__.py` files
- [ ] Service discovery documentation
- [ ] Test structure mirrors service structure
- [ ] README in services directory

### Nice to Have ✨
- [ ] Auto-discovery of services
- [ ] Service metadata in files
- [ ] Service generation templates
- [ ] Service validation tool

---

## Related Documents

- **[Service Base Classes](service-base-classes.md)**: The classes these services extend
- **[Service Categorization](service-categorization.md)**: How services are categorized
- **[Service Schema Management](service-schema-management.md)**: Centralized schemas
- **[Phase 2 Migration Guide](phase-2-migration-guide.md)**: Migration strategy

---

## References

- Python package structure: https://docs.python.org/3/tutorial/modules.html#packages
- Home Assistant integration structure: https://developers.home-assistant.io/docs/creating_integration_file_structure

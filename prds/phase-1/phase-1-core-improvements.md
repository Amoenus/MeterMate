# Phase 1 PRD: Core Improvements & Validation Patterns

> **🤖 LLM Operator Context**: This PRD follows the **LLM-First Operations Model** (ADR-000). You are expected to implement these improvements with human validation at key milestones.

**Status**: � Planned
**Priority**: �🔴 CRITICAL
**Complexity**: Medium
**Impact**: High - Improves code quality without breaking functionality
**Timeline**: 1-2 weeks
**Deciders**: Primary Operator + LLM Co-maintainer
**Last Updated**: 2025-11-05

---

## 🤖 LLM Operator Guidance

### Autonomy Level
🟡 **Collaborative** - Implement autonomously with human validation at each task completion

### Key Tools for This Phase
- `replace_string_in_file` - Updating service schemas and handlers
- `create_file` - Creating new validator and exception files
- `read_file` - Understanding existing service patterns
- `semantic_search` - Finding all service registration points
- `grep_search` - Locating all schema definitions
- `runTests` - Validating changes don't break functionality

### Success Indicators
- ✅ All service calls validate input before processing
- ✅ Clear error messages guide users to correct input
- ✅ Zero breaking changes to existing integrations
- ✅ Tests pass with new validation patterns

### Escalation Triggers
- 🔴 Breaking changes detected in integration tests
- 🔴 Performance degradation in service calls
- 🔴 Validation patterns conflict with existing user automations

---

## Executive Summary

Phase 1 focuses on adopting **modern validation patterns** and **service organization best practices** while respecting MeterMate's core mission: **simple manual data entry for Energy Dashboard**. This phase does NOT require entity registry integration (that's optional for Phase 3).

### Key Principle: Don't Break What Works

MeterMate's current approach:
- ✅ **Statistics table management** - This is CORRECT and must stay
- ✅ **Direct database access** - Required for historical data import
- ✅ **Custom data models** - Needed for CRUD operations on readings
- ⚠️ **Metadata in state attributes** - Only problematic if we want UI features

### What We're Improving:
1. 🎯 **Validation patterns** - Industry-standard schema validation with Voluptuous
2. 🎯 **Service organization** - Modular, focused service architecture
3. 🎯 **Error handling** - Clear, actionable user feedback
4. 🎯 **Code quality** - Type safety, comprehensive documentation

### What We're NOT Changing:
- ❌ Statistics table management approach
- ❌ Database access patterns for readings
- ❌ Core data models (Reading, MeterMateDataManager)
- ❌ Existing service functionality

---

## Objectives

### Primary Goals
1. Adopt industry-standard Voluptuous schema validation patterns
2. Improve service error handling and user feedback
3. Add comprehensive input validation before processing
4. Organize services by responsibility with modular architecture
5. Maintain 100% backward compatibility with existing integrations

### Success Metrics
- All service calls validate input before processing
- Clear error messages for invalid input
- Zero breaking changes to existing functionality
- Improved code maintainability and testability

---

## Current State Analysis

### What MeterMate Does (Correctly!)

```python
# MeterMate's approach to statistics - THIS IS CORRECT
class MeterMateDataManager:
    async def add_reading(self, entity_id: str, reading: Reading):
        """Add reading to statistics table."""
        # 1. Get statistics metadata
        metadata = await self._ensure_statistics_meta(entity_id)

        # 2. Insert into statistics table
        await self._insert_statistic(metadata.id, reading)

        # 3. Update sensor state
        await self._update_sensor_state(entity_id, reading.value)
```

**Why this works:**
- ✅ Energy Dashboard reads from `statistics` table
- ✅ Historical data import requires direct table access
- ✅ Custom CRUD operations need our own data layer
- ✅ This is exactly how `homeassistant-statistics` works

### Best Practices to Apply

```python
# Industry-standard patterns to adopt:
# 1. Schema validation with explicit error messages
SERVICE_ADD_READING_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required("value"): vol.All(
        vol.Coerce(float),
        vol.Range(min=0),  # Readings can't be negative
    ),
    vol.Optional("timestamp"): cv.datetime,
    vol.Optional("unit"): vol.In(["kWh", "m³", "gal", "L"]),  # Valid units only
})

# 2. Better error handling
class MeterMateValidationError(HomeAssistantError):
    """Raised when reading validation fails."""

async def async_handle_service(self, call: ServiceCall) -> None:
    """Handle service with proper validation."""
    try:
        # Validation happens in schema
        entity_id = call.data[ATTR_ENTITY_ID]
        value = call.data["value"]

        # Business logic validation
        if not await self._entity_exists(entity_id):
            raise MeterMateValidationError(f"Entity {entity_id} not found")

        # Process the reading
        result = await self.data_manager.add_reading(entity_id, reading)

        if not result.success:
            raise MeterMateValidationError(result.message)

    except MeterMateValidationError as e:
        _LOGGER.error("Validation error: %s", e)
        raise
    except Exception as e:
        _LOGGER.exception("Unexpected error adding reading")
        raise HomeAssistantError(f"Failed to add reading: {e}") from e
```

---

## Detailed Implementation Plan

### Task 1: Enhanced Schema Validation (1-2 days)

**Goal**: Add comprehensive validation to all service schemas using industry-standard Voluptuous patterns.

**Current State**:
```python
# Current schema - basic validation
SERVICE_ADD_READING_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required("value"): vol.Coerce(float),
    vol.Optional("timestamp"): cv.datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): cv.string,
})
```

**Improved Schema**:
```python
# Enhanced schema with comprehensive validation
SERVICE_ADD_READING_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): vol.All(
        cv.entity_id,
        # Validate entity exists and is a MeterMate sensor
        cv.ensure_list,
    ),
    vol.Required("value"): vol.All(
        vol.Coerce(float),
        vol.Range(min=0, msg="Reading value cannot be negative"),
    ),
    vol.Optional("timestamp"): vol.All(
        cv.datetime,
        # Validate timestamp is not in future
        cv.past_datetime,
    ),
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): vol.In(
        ["kWh", "m³", "gal", "L", "ft³"],
        msg="Invalid unit of measurement"
    ),
    vol.Optional(ATTR_NOTES): cv.string,
})
```

**Validation Enhancements**:
1. Range checks (values must be >= 0)
2. Unit validation (only valid units)
3. Timestamp validation (not in future, timezone-aware)
4. Entity existence checks
5. Clear error messages

**Files to Modify**:
- `services.py` - Update all service schemas
- `validation.py` - Add custom validators

### Task 2: Custom Validation Functions (1 day)

**Goal**: Create MeterMate-specific validators following best practices for reusable validation logic.

**New File**: `custom_components/metermate/validators.py`

```python
"""Custom validators for MeterMate."""
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

def metermate_entity_id(value: str) -> str:
    """Validate entity_id belongs to MeterMate integration."""
    entity_id = cv.entity_id(value)
    if not entity_id.startswith("sensor."):
        raise vol.Invalid("MeterMate only supports sensor entities")
    return entity_id

def past_datetime(value):
    """Validate datetime is not in the future."""
    dt = cv.datetime(value)
    if dt > dt_util.utcnow():
        raise vol.Invalid("Timestamp cannot be in the future")
    return dt

def positive_float(value):
    """Validate float is positive."""
    num = vol.Coerce(float)(value)
    if num < 0:
        raise vol.Invalid("Value must be positive")
    return num

def valid_consumption(value):
    """Validate consumption value is reasonable."""
    num = positive_float(value)
    if num > 1000000:  # Arbitrary large number
        raise vol.Invalid("Consumption value seems unreasonably large")
    return num

def valid_meter_reading(value):
    """Validate meter reading is reasonable."""
    num = positive_float(value)
    # Meter readings can be very large (cumulative)
    return num
```

**Usage in Services**:
```python
from .validators import (
    metermate_entity_id,
    past_datetime,
    positive_float,
    valid_consumption,
    valid_meter_reading,
)

SERVICE_ADD_METER_READING_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("meter_reading"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    # ... rest of schema
})
```

### Task 3: Service Error Handling Pattern (1 day)

**Goal**: Standardize error handling across all services using consistent exception hierarchy and messaging patterns.

**New File**: `custom_components/metermate/exceptions.py`

```python
"""MeterMate custom exceptions."""
from homeassistant.exceptions import HomeAssistantError

class MeterMateError(HomeAssistantError):
    """Base exception for MeterMate."""

class MeterMateValidationError(MeterMateError):
    """Raised when validation fails."""

class MeterMateEntityNotFoundError(MeterMateError):
    """Raised when entity is not found."""

class MeterMateReadingNotFoundError(MeterMateError):
    """Raised when reading is not found."""

class MeterMateDatabaseError(MeterMateError):
    """Raised when database operation fails."""

class MeterMateInvalidStateError(MeterMateError):
    """Raised when entity is in invalid state."""
```

**Service Handler Pattern**:
```python
async def _handle_add_reading(self, call: ServiceCall) -> None:
    """Handle add_reading service with proper error handling."""
    entity_id = call.data[ATTR_ENTITY_ID]

    try:
        # 1. Pre-flight checks
        if not await self._entity_exists(entity_id):
            raise MeterMateEntityNotFoundError(
                f"Entity {entity_id} not found. "
                "Please create the sensor first via config flow."
            )

        # 2. Get entity and verify state
        entity = self._get_entity(entity_id)
        if entity is None:
            raise MeterMateInvalidStateError(
                f"Entity {entity_id} is not ready. "
                "Please wait for it to initialize."
            )

        # 3. Create reading object
        reading = Reading(
            timestamp=call.data.get("timestamp", dt_util.utcnow()),
            value=call.data["value"],
            unit=call.data.get("unit", "kWh"),
            notes=call.data.get("notes"),
        )

        # 4. Add reading
        result = await self.data_manager.add_reading(entity_id, reading)

        if not result.success:
            raise MeterMateDatabaseError(result.message)

        _LOGGER.info(
            "Successfully added reading for %s: %s %s at %s",
            entity_id, reading.value, reading.unit, reading.timestamp
        )

    except MeterMateError:
        # Re-raise our errors as-is
        raise
    except Exception as e:
        # Wrap unexpected errors
        _LOGGER.exception("Unexpected error adding reading")
        raise MeterMateDatabaseError(
            f"Failed to add reading due to unexpected error: {e}"
        ) from e
```

### Task 4: Service Organization (2 days)

**Goal**: Organize services by responsibility following modular architecture principles.

**Current Structure**:
```
custom_components/metermate/
  services.py  (500+ lines, all services in one file)
```

**Proposed Structure**:
```
custom_components/metermate/
  services/
    __init__.py              # Service registration
    base.py                  # Base service classes
    reading_services.py      # add_reading, update_reading, delete_reading
    meter_services.py        # add_meter_reading, add_consumption_period
    bulk_services.py         # bulk_import, import_from_csv
    maintenance_services.py  # recalculate_statistics, rebuild_history
    query_services.py        # get_readings, validate_reading
```

**Base Service Classes** (`services/base.py`):
```python
"""Base service classes for MeterMate."""
from abc import ABC, abstractmethod
from homeassistant.core import HomeAssistant, ServiceCall

class MeterMateServiceBase(ABC):
    """Base class for MeterMate services."""

    def __init__(self, hass: HomeAssistant, data_manager) -> None:
        """Initialize service."""
        self.hass = hass
        self.data_manager = data_manager

    @property
    @abstractmethod
    def service_name(self) -> str:
        """Return the service name."""

    @property
    @abstractmethod
    def schema(self):
        """Return the service schema."""

    @abstractmethod
    async def async_handle_service(self, call: ServiceCall) -> None:
        """Handle the service call."""

    def _get_entity(self, entity_id: str):
        """Get entity from registry."""
        if (
            ATTR_INTEGRATION_NAME not in self.hass.data
            or "entities" not in self.hass.data[ATTR_INTEGRATION_NAME]
        ):
            return None
        return self.hass.data[ATTR_INTEGRATION_NAME]["entities"].get(entity_id)

    async def _entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        return self._get_entity(entity_id) is not None
```

**Example Service Implementation** (`services/reading_services.py`):
```python
"""Reading-related services."""
from .base import MeterMateServiceBase
from ..validators import metermate_entity_id, past_datetime, valid_meter_reading
from ..exceptions import MeterMateEntityNotFoundError, MeterMateDatabaseError

class AddReadingService(MeterMateServiceBase):
    """Service to add a reading."""

    @property
    def service_name(self) -> str:
        return "add_reading"

    @property
    def schema(self):
        return vol.Schema({
            vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
            vol.Required("value"): valid_meter_reading,
            vol.Optional("timestamp"): past_datetime,
            vol.Optional("unit", default="kWh"): vol.In(VALID_UNITS),
            vol.Optional("notes"): cv.string,
        })

    async def async_handle_service(self, call: ServiceCall) -> None:
        """Handle add_reading service call."""
        entity_id = call.data[ATTR_ENTITY_ID]

        # Implementation with proper error handling
        # ... (same as Task 3 example)
```

**Service Registration** (`services/__init__.py`):
```python
"""MeterMate service registration."""
from .reading_services import (
    AddReadingService,
    UpdateReadingService,
    DeleteReadingService,
)
from .meter_services import (
    AddMeterReadingService,
    AddConsumptionPeriodService,
)
# ... import other services

async def async_setup_services(
    hass: HomeAssistant,
    data_manager: MeterMateDataManager
) -> None:
    """Register all MeterMate services."""
    services = [
        AddReadingService(hass, data_manager),
        UpdateReadingService(hass, data_manager),
        DeleteReadingService(hass, data_manager),
        AddMeterReadingService(hass, data_manager),
        AddConsumptionPeriodService(hass, data_manager),
        # ... other services
    ]

    for service in services:
        hass.services.async_register(
            ATTR_INTEGRATION_NAME,
            service.service_name,
            service.async_handle_service,
            schema=service.schema,
        )
```

### Task 5: Improve Documentation & Type Safety (1 day)

**Goal**: Add comprehensive docstrings and type hints following Python and Home Assistant standards.

**Enhanced Type Hints**:
```python
from typing import Any, TypedDict

class ServiceCallData(TypedDict, total=False):
    """Type definition for service call data."""
    entity_id: str
    value: float
    timestamp: datetime
    unit: str
    notes: str

class ReadingResponse(TypedDict):
    """Type definition for reading response."""
    id: str
    timestamp: str
    value: float
    unit: str
    notes: str | None
    consumption: float | None

async def _handle_get_readings(self, call: ServiceCall) -> dict[str, list[ReadingResponse]]:
    """Handle get_readings service call.

    Args:
        call: Service call with entity_id, optional start_date, end_date

    Returns:
        Dictionary with 'readings' key containing list of reading objects

    Raises:
        MeterMateEntityNotFoundError: If entity doesn't exist
        MeterMateDatabaseError: If database query fails
    """
```

---

## What We're NOT Doing (And Why)

### ❌ Entity Registry Integration (Optional - Phase 3)

```python
# We are NOT doing this in Phase 1:
entity_registry = er.async_get(hass)
entity_registry.async_update_entity(
    entity_id="sensor.metermate_electricity",
    name="Living Room Meter",  # <-- Not needed for Energy Dashboard
    area_id="living_room",      # <-- Nice to have, not required
)
```

**Why Not**:
- MeterMate's core mission: provide data to Energy Dashboard
- Energy Dashboard reads from `statistics` table (we're doing this correctly)
- Entity registry is for UI features (area assignment, friendly names)
- Users can already rename via UI without registry integration
- Adding this would be scope creep and complexity

**When It Makes Sense** (Phase 3 - Optional):
- IF we want native area assignment UI in config flow
- IF we want integration with HA's device/entity management UI
- IF we want to support device triggers/conditions
- But this is NOT required for core functionality

### ❌ Storage Collection Pattern

```python
# We are NOT doing this:
from homeassistant.helpers.storage import Store

class MeterMateStore:
    """Store meter configurations in .storage/"""
```

**Why Not**:
- MeterMate already uses config entries (correct approach)
- Statistics table is the source of truth for readings
- Adding storage collection would duplicate data
- Current approach works and is proven

### ❌ Replacing Database Access

```python
# We are NOT removing direct database access:
async def add_reading(self, entity_id: str, reading: Reading):
    """Add reading to statistics table."""
    # Direct SQLAlchemy/database access is CORRECT here
    await self._insert_statistic(metadata.id, reading)
```

**Why Not**:
- Historical data import requires direct table access
- This is how `homeassistant-statistics` works (proven approach)
- HA's statistics API is for reading, not writing historical data
- Our use case (manual entry with CRUD) requires our own data layer

---

## Success Criteria

### Must Have ✅
- [ ] All service schemas use Voluptuous validation patterns
- [ ] Custom validators for MeterMate-specific validation
- [ ] Comprehensive error handling with custom exceptions
- [ ] Clear, actionable error messages for users
- [ ] 100% backward compatibility maintained
- [ ] No breaking changes to existing automations/scripts

### Should Have 🎯
- [ ] Services organized into focused modules
- [ ] Base service classes for code reuse
- [ ] Comprehensive docstrings and type hints
- [ ] Unit tests for all validators
- [ ] Integration tests for error cases

### Nice to Have ✨
- [ ] Service response types (for better UI integration)
- [ ] Validation service returns detailed feedback
- [ ] Async validation for complex checks (e.g., duplicate detection)

---

## Testing Strategy

### Unit Tests
```python
# tests/test_validators.py
def test_past_datetime_rejects_future():
    """Test that future datetimes are rejected."""
    future = dt_util.utcnow() + timedelta(days=1)
    with pytest.raises(vol.Invalid):
        past_datetime(future)

def test_valid_meter_reading_accepts_positive():
    """Test that positive readings are accepted."""
    assert valid_meter_reading(123.45) == 123.45

def test_valid_meter_reading_rejects_negative():
    """Test that negative readings are rejected."""
    with pytest.raises(vol.Invalid):
        valid_meter_reading(-10.0)
```

### Integration Tests
```python
# tests/test_services.py
async def test_add_reading_with_invalid_entity(hass, data_manager):
    """Test add_reading with non-existent entity."""
    with pytest.raises(MeterMateEntityNotFoundError):
        await services.add_reading(
            hass, "sensor.nonexistent", 100.0
        )

async def test_add_reading_with_future_timestamp(hass, entity):
    """Test add_reading rejects future timestamps."""
    future = dt_util.utcnow() + timedelta(days=1)
    with pytest.raises(vol.Invalid):
        await services.add_reading(
            hass, entity.entity_id, 100.0, timestamp=future
        )
```

---

## Migration Path

### Phase 1A: Add Validation (Non-Breaking)
1. Create `validators.py` with custom validators
2. Create `exceptions.py` with custom exceptions
3. Update service schemas (still accept old format)
4. Add validation but with warnings (not errors yet)

### Phase 1B: Refactor Services (Non-Breaking)
1. Create `services/` directory structure
2. Create base classes in `services/base.py`
3. Move services to separate files (one by one)
4. Keep old `services.py` as re-export for compatibility
5. Update imports in `__init__.py`

### Phase 1C: Enable Strict Validation
1. Switch from warnings to errors for invalid input
2. Update documentation with new requirements
3. Add migration guide for users
4. Provide validation service for testing

---

## Timeline

- **Week 1**:
  - Day 1-2: Task 1 (Enhanced schemas)
  - Day 3: Task 2 (Custom validators)
  - Day 4: Task 3 (Error handling)
  - Day 5: Testing and documentation

- **Week 2**:
  - Day 1-2: Task 4 (Service organization)
  - Day 3: Task 5 (Documentation & types)
  - Day 4-5: Integration testing and refinement

---

## Dependencies

### Code Dependencies
- Existing: `voluptuous`, `homeassistant.helpers.config_validation`
- No new dependencies required

### Knowledge Dependencies
- Understanding of Voluptuous validation library
- Familiarity with HA service registration patterns
- Knowledge of MeterMate's current service architecture

---

## Risks & Mitigation

### Risk: Breaking Existing Automations
**Mitigation**:
- Maintain backward compatibility
- Gradual rollout with warnings first
- Comprehensive testing with real-world scenarios

### Risk: Over-Engineering
**Mitigation**:
- Keep focus on validation and organization
- Don't add features not needed for core mission
- Resist scope creep (no entity registry yet)

### Risk: Validation Too Strict
**Mitigation**:
- Make validation configurable via service options
- Provide validation service for testing
- Allow bypass for advanced users (with warnings)

---

## Questions for Implementation

1. Should we support validation bypass flag for advanced users?
2. What level of logging detail for validation errors?
3. Should validation service return JSON schema for UI integration?
4. How to handle legacy data that doesn't meet new validation rules?

---

## References

### Related Documentation
- **ADR-000**: LLM-First Operations Model - Operational philosophy guiding this implementation
- **LLM Operator's Handbook**: Tool usage patterns and operational procedures

### External References
- Voluptuous documentation: https://github.com/alecthomas/voluptuous
- Home Assistant service documentation: https://developers.home-assistant.io/docs/dev_101_services
- Home Assistant config validation: `homeassistant.helpers.config_validation`
- Python type hints (PEP 484): https://www.python.org/dev/peps/pep-0484/

### Implementation Examples
- Home Assistant core integrations: https://github.com/home-assistant/core/tree/dev/homeassistant/components
- Validation patterns in HA helpers: `homeassistant/helpers/config_validation.py`

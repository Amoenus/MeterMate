# Validation Patterns PRD

> **📋 Document Type**: Implementation Guide
> **🔗 Related**: [Error Handling Patterns](error-handling-patterns.md), [Phase 1 Migration Guide](phase-1-migration-guide.md)
> **📅 Last Updated**: 2025-11-05

---

## Overview

This document defines the validation patterns and strategies for MeterMate service inputs using industry-standard Voluptuous schema validation.

**Goal**: Add comprehensive input validation to all MeterMate services with clear, actionable error messages.

**Autonomy Level**: 🟡 Collaborative - Implement with human validation at completion

---

## Philosophy

### Why Voluptuous?

MeterMate adopts Voluptuous for validation because:
- ✅ Industry standard in Home Assistant ecosystem
- ✅ Declarative schema definitions
- ✅ Clear error messages out of the box
- ✅ Composable validators
- ✅ Home Assistant's `config_validation` module built on it

### Validation Principles

1. **Fail Fast**: Validate at the service boundary before processing
2. **Clear Messages**: Error messages guide users to correct input
3. **Composable**: Build complex validations from simple validators
4. **Testable**: Each validator is independently testable
5. **Reusable**: Common patterns abstracted into custom validators

---

## Schema Enhancement Patterns

### Basic Schema (Current State)

```python
# Basic validation - what we have now
SERVICE_ADD_READING_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    vol.Required("value"): vol.Coerce(float),
    vol.Optional("timestamp"): cv.datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): cv.string,
})
```

**Problems**:
- No range validation (can submit negative values)
- No unit validation (can use invalid units)
- No timestamp validation (can use future dates)
- Generic error messages

### Enhanced Schema (Target State)

```python
# Enhanced validation - what we're building
SERVICE_ADD_READING_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): vol.All(
        cv.entity_id,
        metermate_entity_id,  # Custom: verifies it's a MeterMate sensor
    ),
    vol.Required("value"): vol.All(
        vol.Coerce(float),
        vol.Range(min=0, msg="Reading value cannot be negative"),
    ),
    vol.Optional("timestamp"): vol.All(
        cv.datetime,
        past_datetime,  # Custom: ensures timestamp not in future
    ),
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): vol.In(
        VALID_UNITS,
        msg="Unit must be one of: kWh, m³, gal, L, ft³"
    ),
    vol.Optional(ATTR_NOTES): cv.string,
})
```

**Improvements**:
- ✅ Range validation with clear message
- ✅ Enum validation for units
- ✅ Timestamp validation (not in future)
- ✅ Entity type validation
- ✅ Helpful error messages

---

## Custom Validators

Create reusable validators specific to MeterMate's domain.

### File: `custom_components/metermate/validators.py`

```python
"""Custom validators for MeterMate."""
from __future__ import annotations

from datetime import datetime
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import VALID_UNITS


def metermate_entity_id(value: str) -> str:
    """Validate entity_id belongs to MeterMate integration.

    Args:
        value: Entity ID string to validate

    Returns:
        Validated entity ID

    Raises:
        vol.Invalid: If entity is not a sensor or not valid format
    """
    entity_id = cv.entity_id(value)
    if not entity_id.startswith("sensor."):
        raise vol.Invalid("MeterMate only supports sensor entities")
    return entity_id


def past_datetime(value: datetime) -> datetime:
    """Validate datetime is not in the future.

    Args:
        value: Datetime object or string to validate

    Returns:
        Validated datetime (timezone-aware UTC)

    Raises:
        vol.Invalid: If datetime is in the future
    """
    # First ensure it's a datetime object
    dt = cv.datetime(value)

    # Ensure timezone-aware
    dt = dt_util.as_utc(dt)

    # Check not in future (with small tolerance for clock differences)
    now = dt_util.utcnow()
    if dt > now:
        raise vol.Invalid(
            f"Timestamp cannot be in the future. "
            f"Received: {dt.isoformat()}, Now: {now.isoformat()}"
        )

    return dt


def positive_float(value: float | int | str) -> float:
    """Validate float is positive (>= 0).

    Args:
        value: Numeric value to validate

    Returns:
        Validated float

    Raises:
        vol.Invalid: If value is negative
    """
    num = vol.Coerce(float)(value)
    if num < 0:
        raise vol.Invalid(f"Value must be positive, got: {num}")
    return num


def valid_consumption(value: float | int | str) -> float:
    """Validate consumption value is reasonable.

    Consumption is the difference between meter readings, so it should
    be positive and not unreasonably large.

    Args:
        value: Consumption value to validate

    Returns:
        Validated consumption value

    Raises:
        vol.Invalid: If value is negative or unreasonably large
    """
    num = positive_float(value)

    # Sanity check: consumption shouldn't be larger than 1,000,000
    # This catches data entry errors (e.g., entering meter reading instead of consumption)
    if num > 1_000_000:
        raise vol.Invalid(
            f"Consumption value seems unreasonably large: {num}. "
            "Did you mean to enter a meter reading instead?"
        )

    return num


def valid_meter_reading(value: float | int | str) -> float:
    """Validate meter reading is reasonable.

    Meter readings are cumulative totals, so they can be large,
    but should still be positive.

    Args:
        value: Meter reading to validate

    Returns:
        Validated meter reading

    Raises:
        vol.Invalid: If value is negative
    """
    return positive_float(value)


def valid_unit(value: str) -> str:
    """Validate unit of measurement is supported.

    Args:
        value: Unit string to validate

    Returns:
        Validated unit string

    Raises:
        vol.Invalid: If unit is not in VALID_UNITS
    """
    if value not in VALID_UNITS:
        raise vol.Invalid(
            f"Invalid unit '{value}'. "
            f"Supported units: {', '.join(VALID_UNITS)}"
        )
    return value


def timezone_aware_datetime(value: datetime) -> datetime:
    """Ensure datetime is timezone-aware (converts to UTC if naive).

    Args:
        value: Datetime object or string

    Returns:
        Timezone-aware datetime in UTC

    Raises:
        vol.Invalid: If datetime cannot be parsed
    """
    dt = cv.datetime(value)
    return dt_util.as_utc(dt)
```

---

## Schema Patterns by Service Type

### Add Reading Service

```python
from .validators import (
    metermate_entity_id,
    past_datetime,
    valid_meter_reading,
    valid_unit,
)

SERVICE_ADD_READING_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("value"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
})
```

### Add Consumption Period Service

```python
SERVICE_ADD_CONSUMPTION_PERIOD_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("consumption"): valid_consumption,
    vol.Required("period_start"): timezone_aware_datetime,
    vol.Required("period_end"): vol.All(
        timezone_aware_datetime,
        # Custom validator: end must be after start
        lambda v: v,  # Validated in service handler with start
    ),
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
})
```

### Get Readings Service (Query)

```python
SERVICE_GET_READINGS_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Optional("start_date"): timezone_aware_datetime,
    vol.Optional("end_date"): timezone_aware_datetime,
    vol.Optional("limit"): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=10000, msg="Limit must be between 1 and 10000"),
    ),
})
```

### Bulk Import Service (Admin)

```python
SERVICE_BULK_IMPORT_SCHEMA = vol.Schema({
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("readings"): vol.All(
        cv.ensure_list,
        vol.Length(min=1, max=10000, msg="Must import 1-10000 readings at once"),
        [
            vol.Schema({
                vol.Required("timestamp"): past_datetime,
                vol.Required("value"): valid_meter_reading,
                vol.Optional(ATTR_UNIT_OF_MEASUREMENT): valid_unit,
                vol.Optional(ATTR_NOTES): cv.string,
            })
        ],
    ),
    vol.Optional("skip_validation", default=False): cv.boolean,
})
```

---

## Complex Validation Scenarios

### Cross-Field Validation

When validation depends on multiple fields:

```python
def validate_period(schema_data: dict) -> dict:
    """Validate that period_end is after period_start.

    Args:
        schema_data: Dictionary with period_start and period_end

    Returns:
        Validated schema data

    Raises:
        vol.Invalid: If period_end <= period_start
    """
    start = schema_data.get("period_start")
    end = schema_data.get("period_end")

    if start and end and end <= start:
        raise vol.Invalid(
            f"period_end ({end.isoformat()}) must be after "
            f"period_start ({start.isoformat()})"
        )

    return schema_data


# Usage in schema
SERVICE_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Required("period_start"): timezone_aware_datetime,
            vol.Required("period_end"): timezone_aware_datetime,
            # ... other fields
        },
        validate_period,  # Apply cross-field validator
    )
)
```

### Conditional Validation

When some fields are required based on others:

```python
def validate_reading_type(schema_data: dict) -> dict:
    """Validate fields based on reading_type.

    If reading_type is 'meter_reading', require 'meter_reading' field.
    If reading_type is 'consumption', require 'consumption' and 'period_*' fields.

    Args:
        schema_data: Dictionary with reading data

    Returns:
        Validated schema data

    Raises:
        vol.Invalid: If required fields for reading_type are missing
    """
    reading_type = schema_data.get("reading_type")

    if reading_type == "meter_reading":
        if "meter_reading" not in schema_data:
            raise vol.Invalid("meter_reading required when reading_type is 'meter_reading'")

    elif reading_type == "consumption":
        required_fields = ["consumption", "period_start", "period_end"]
        missing = [f for f in required_fields if f not in schema_data]
        if missing:
            raise vol.Invalid(
                f"Fields {missing} required when reading_type is 'consumption'"
            )

    return schema_data
```

---

## Validation Testing

### Unit Tests for Validators

```python
"""Tests for custom validators."""
import pytest
from datetime import timedelta
import voluptuous as vol
from homeassistant.util import dt as dt_util

from custom_components.metermate.validators import (
    past_datetime,
    positive_float,
    valid_consumption,
    valid_meter_reading,
    metermate_entity_id,
)


def test_past_datetime_accepts_past():
    """Test that past datetimes are accepted."""
    past = dt_util.utcnow() - timedelta(hours=1)
    result = past_datetime(past)
    assert result == dt_util.as_utc(past)


def test_past_datetime_rejects_future():
    """Test that future datetimes are rejected."""
    future = dt_util.utcnow() + timedelta(hours=1)
    with pytest.raises(vol.Invalid, match="cannot be in the future"):
        past_datetime(future)


def test_positive_float_accepts_positive():
    """Test that positive floats are accepted."""
    assert positive_float(123.45) == 123.45
    assert positive_float(0) == 0.0
    assert positive_float("456.78") == 456.78


def test_positive_float_rejects_negative():
    """Test that negative floats are rejected."""
    with pytest.raises(vol.Invalid, match="must be positive"):
        positive_float(-10.0)


def test_valid_consumption_accepts_reasonable():
    """Test that reasonable consumption values are accepted."""
    assert valid_consumption(100.5) == 100.5
    assert valid_consumption(0) == 0.0


def test_valid_consumption_rejects_large():
    """Test that unreasonably large values are rejected."""
    with pytest.raises(vol.Invalid, match="unreasonably large"):
        valid_consumption(2_000_000)


def test_metermate_entity_id_accepts_sensor():
    """Test that sensor entity IDs are accepted."""
    result = metermate_entity_id("sensor.electricity_meter")
    assert result == "sensor.electricity_meter"


def test_metermate_entity_id_rejects_non_sensor():
    """Test that non-sensor entities are rejected."""
    with pytest.raises(vol.Invalid, match="only supports sensor"):
        metermate_entity_id("light.living_room")
```

### Integration Tests with Schemas

```python
"""Tests for service schemas."""
import pytest
import voluptuous as vol
from homeassistant.util import dt as dt_util

from custom_components.metermate.services.schemas import (
    SERVICE_ADD_READING_SCHEMA,
)


async def test_add_reading_schema_valid():
    """Test that valid data passes schema validation."""
    data = {
        "entity_id": "sensor.electricity_meter",
        "value": 12345.67,
        "timestamp": dt_util.utcnow(),
        "unit_of_measurement": "kWh",
        "notes": "Monthly reading",
    }

    # Should not raise
    validated = SERVICE_ADD_READING_SCHEMA(data)
    assert validated["entity_id"] == data["entity_id"]
    assert validated["value"] == data["value"]


async def test_add_reading_schema_negative_value():
    """Test that negative values are rejected."""
    data = {
        "entity_id": "sensor.electricity_meter",
        "value": -100.0,
    }

    with pytest.raises(vol.Invalid, match="cannot be negative"):
        SERVICE_ADD_READING_SCHEMA(data)


async def test_add_reading_schema_invalid_unit():
    """Test that invalid units are rejected."""
    data = {
        "entity_id": "sensor.electricity_meter",
        "value": 100.0,
        "unit_of_measurement": "invalid_unit",
    }

    with pytest.raises(vol.Invalid, match="Invalid unit"):
        SERVICE_ADD_READING_SCHEMA(data)
```

---

## Error Message Guidelines

### Good Error Messages

✅ **Specific and actionable**:
```python
raise vol.Invalid(
    f"Timestamp cannot be in the future. "
    f"Received: {dt.isoformat()}, Now: {now.isoformat()}"
)
```

✅ **Include valid options**:
```python
raise vol.Invalid(
    f"Invalid unit '{value}'. "
    f"Supported units: {', '.join(VALID_UNITS)}"
)
```

✅ **Suggest fixes**:
```python
raise vol.Invalid(
    f"Consumption value seems unreasonably large: {num}. "
    "Did you mean to enter a meter reading instead?"
)
```

### Poor Error Messages

❌ **Too vague**:
```python
raise vol.Invalid("Invalid input")
```

❌ **No context**:
```python
raise vol.Invalid("Value must be positive")
# Better: "Value must be positive, got: -10.5"
```

❌ **Technical jargon**:
```python
raise vol.Invalid("Datetime must be tz-aware")
# Better: "Timestamp must include timezone information"
```

---

## Constants Definition

### File: `custom_components/metermate/const.py` (additions)

```python
"""Constants for MeterMate validation."""

# Valid units of measurement
VALID_UNITS = [
    "kWh",   # Kilowatt hours (electricity)
    "m³",    # Cubic meters (gas, water)
    "gal",   # Gallons (water)
    "L",     # Liters (water)
    "ft³",   # Cubic feet (gas)
]

# Validation limits
MAX_READING_VALUE = 1_000_000_000  # 1 billion (sanity check)
MAX_CONSUMPTION_VALUE = 1_000_000  # 1 million per period
MAX_BULK_IMPORT_SIZE = 10_000      # Max readings per bulk import
MAX_QUERY_LIMIT = 10_000           # Max readings to return in query

# Validation messages
MSG_NEGATIVE_VALUE = "Reading value cannot be negative"
MSG_FUTURE_TIMESTAMP = "Timestamp cannot be in the future"
MSG_INVALID_UNIT = "Unit must be one of: {units}"
MSG_LARGE_CONSUMPTION = (
    "Consumption value seems unreasonably large: {value}. "
    "Did you mean to enter a meter reading instead?"
)
```

---

## Migration Path

### Phase 1: Add Validators (Non-Breaking)

1. Create `validators.py` with all custom validators
2. Add comprehensive unit tests
3. Document each validator

**No breaking changes** - just infrastructure.

### Phase 2: Update Schemas (Non-Breaking)

1. Update service schemas to use new validators
2. Keep validation lenient initially (log warnings)
3. Test with real-world data

**No breaking changes** - existing calls still work.

### Phase 3: Enable Strict Validation

1. Switch from warnings to errors
2. Update documentation
3. Announce in changelog

**Potential breaking change** - clearly communicate.

---

## Success Criteria

### Must Have ✅
- [ ] All custom validators implemented in `validators.py`
- [ ] All service schemas use appropriate validators
- [ ] Comprehensive unit tests for validators
- [ ] Clear error messages for all validation failures
- [ ] Constants file with all valid values

### Should Have 🎯
- [ ] Integration tests with actual services
- [ ] Documentation of all validators
- [ ] Examples of each validation pattern
- [ ] Migration guide for existing data

### Nice to Have ✨
- [ ] Validation bypass flag for advanced users
- [ ] Validation severity levels (error vs warning)
- [ ] Async validators for database checks

---

## Related Documents

- **[Error Handling Patterns](error-handling-patterns.md)**: Exception hierarchy for validation failures
- **[Service Organization Strategy](service-organization-strategy.md)**: Where schemas are used
- **[Phase 1 Migration Guide](phase-1-migration-guide.md)**: Implementation timeline

---

## References

- Voluptuous documentation: https://github.com/alecthomas/voluptuous
- Home Assistant config_validation: `homeassistant/helpers/config_validation.py`
- HA Service Schemas: https://developers.home-assistant.io/docs/dev_101_services

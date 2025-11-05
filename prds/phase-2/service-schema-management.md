# Service Schema Management PRD

> **📋 Document Type**: Implementation Guide
> **🔗 Related**: [Service Base Classes](service-base-classes.md), [Service Module Structure](service-module-structure.md), [Phase 1: Validation Patterns](../phase-1/validation-patterns.md)
> **📅 Last Updated**: 2025-11-06

---

## Overview

This document defines how service schemas are centralized and managed in MeterMate, providing a single source of truth for all service input validation.

**Goal**: Centralize all service schemas for easy reference, reuse, and maintenance.

**Autonomy Level**: 🟡 Collaborative - Implement with human validation at completion

---

## Philosophy

### Why Centralized Schemas?

- ✅ **Single source of truth**: All schemas in one place
- ✅ **Easy to find**: Navigate to schemas.py to see all services
- ✅ **Reusability**: Common schema patterns defined once
- ✅ **Consistency**: All services use same validation patterns
- ✅ **Documentation**: Schemas document expected inputs

---

## File: `services/schemas.py`

```python
"""Service schemas for MeterMate.

This module contains all service schemas, organized by category.
Each schema defines the input parameters and validation rules for a service.

Schema organization:
    - Query service schemas (read-only operations)
    - Mutation service schemas (data modification)
    - Admin service schemas (destructive operations)
"""
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from ..const import ATTR_ENTITY_ID, ATTR_NOTES, ATTR_UNIT_OF_MEASUREMENT
from ..validators import (
    metermate_entity_id,
    past_datetime,
    positive_float,
    valid_consumption,
    valid_meter_reading,
    valid_unit,
    timezone_aware_datetime,
)

# =============================================================================
# QUERY SERVICE SCHEMAS (Read-only)
# =============================================================================

SERVICE_GET_READINGS_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Optional("start_date"): timezone_aware_datetime,
    vol.Optional("end_date"): timezone_aware_datetime,
    vol.Optional("limit"): vol.All(
        vol.Coerce(int),
        vol.Range(min=1, max=10000, msg="Limit must be between 1 and 10000"),
    ),
}

SERVICE_VALIDATE_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("value"): positive_float,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): valid_unit,
}

# =============================================================================
# MUTATION SERVICE SCHEMAS (Data modification)
# =============================================================================

SERVICE_ADD_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("value"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
}

SERVICE_UPDATE_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("reading_id"): cv.string,
    vol.Required("value"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
}

SERVICE_DELETE_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("reading_id"): cv.string,
}

SERVICE_ADD_METER_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("meter_reading"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
}

SERVICE_ADD_CONSUMPTION_PERIOD_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("consumption"): valid_consumption,
    vol.Required("period_start"): timezone_aware_datetime,
    vol.Required("period_end"): timezone_aware_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
}

SERVICE_UPDATE_METER_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("reading_id"): cv.string,
    vol.Required("meter_reading"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
}

SERVICE_UPDATE_CONSUMPTION_PERIOD_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("reading_id"): cv.string,
    vol.Required("consumption"): valid_consumption,
    vol.Required("period_start"): timezone_aware_datetime,
    vol.Required("period_end"): timezone_aware_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
}

# =============================================================================
# ADMIN SERVICE SCHEMAS (Destructive operations)
# =============================================================================

SERVICE_BULK_IMPORT_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("readings"): vol.All(
        cv.ensure_list,
        vol.Length(min=1, max=10000, msg="Must import 1-10000 readings at once"),
        [
            {
                vol.Required("timestamp"): past_datetime,
                vol.Required("value"): valid_meter_reading,
                vol.Optional(ATTR_UNIT_OF_MEASUREMENT): valid_unit,
                vol.Optional(ATTR_NOTES): cv.string,
            }
        ],
    ),
    vol.Optional("skip_validation", default=False): cv.boolean,
}

SERVICE_RECALCULATE_STATISTICS_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Optional("start_date"): timezone_aware_datetime,
    vol.Optional("end_date"): timezone_aware_datetime,
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

---

## Schema Composition Patterns

### Common Field Patterns

Extract common patterns for reuse:

```python
# Common entity ID requirement
ENTITY_ID_REQUIRED = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
}

# Common timestamp fields
TIMESTAMP_FIELDS = {
    vol.Optional("timestamp"): past_datetime,
}

# Common metadata fields
METADATA_FIELDS = {
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
}

# Compose schemas
SERVICE_ADD_READING_SCHEMA = {
    **ENTITY_ID_REQUIRED,
    vol.Required("value"): valid_meter_reading,
    **TIMESTAMP_FIELDS,
    **METADATA_FIELDS,
}
```

### Schema Inheritance

For services with similar schemas:

```python
# Base reading schema
BASE_READING_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
    vol.Required("value"): valid_meter_reading,
    vol.Optional("timestamp"): past_datetime,
    vol.Optional(ATTR_UNIT_OF_MEASUREMENT, default="kWh"): valid_unit,
    vol.Optional(ATTR_NOTES): cv.string,
}

# Add reading extends base
SERVICE_ADD_READING_SCHEMA = BASE_READING_SCHEMA

# Update reading extends base + reading_id
SERVICE_UPDATE_READING_SCHEMA = {
    **BASE_READING_SCHEMA,
    vol.Required("reading_id"): cv.string,
}
```

---

## Schema Documentation

### Schema Comments

Document complex validation rules:

```python
SERVICE_BULK_IMPORT_SCHEMA = {
    vol.Required(ATTR_ENTITY_ID): metermate_entity_id,

    # Readings array: Must have 1-10000 items
    # Each item must have timestamp and value
    # Optional unit and notes per reading
    vol.Required("readings"): vol.All(
        cv.ensure_list,
        vol.Length(
            min=1,
            max=10000,
            msg="Bulk import supports 1-10000 readings per batch"
        ),
        [
            {
                vol.Required("timestamp"): past_datetime,
                vol.Required("value"): valid_meter_reading,
                vol.Optional(ATTR_UNIT_OF_MEASUREMENT): valid_unit,
                vol.Optional(ATTR_NOTES): cv.string,
            }
        ],
    ),

    # Skip validation: For trusted imports only
    # WARNING: May import invalid data if set to True
    vol.Optional("skip_validation", default=False): cv.boolean,
}
```

---

## Testing Schemas

### Schema Validation Tests

```python
"""Tests for service schemas."""
import pytest
import voluptuous as vol
from homeassistant.util import dt as dt_util

from custom_components.metermate.services.schemas import (
    SERVICE_ADD_READING_SCHEMA,
    SERVICE_BULK_IMPORT_SCHEMA,
)


def test_add_reading_schema_valid():
    """Test valid data passes schema validation."""
    data = {
        "entity_id": "sensor.electricity",
        "value": 12345.67,
        "timestamp": dt_util.utcnow(),
        "unit_of_measurement": "kWh",
        "notes": "Monthly reading",
    }

    schema = vol.Schema(SERVICE_ADD_READING_SCHEMA)
    validated = schema(data)

    assert validated["entity_id"] == data["entity_id"]
    assert validated["value"] == data["value"]


def test_add_reading_schema_defaults():
    """Test schema applies defaults."""
    data = {
        "entity_id": "sensor.electricity",
        "value": 100.0,
    }

    schema = vol.Schema(SERVICE_ADD_READING_SCHEMA)
    validated = schema(data)

    # Default unit should be applied
    assert validated["unit_of_measurement"] == "kWh"


def test_add_reading_schema_negative_value():
    """Test negative values are rejected."""
    data = {
        "entity_id": "sensor.electricity",
        "value": -100.0,
    }

    schema = vol.Schema(SERVICE_ADD_READING_SCHEMA)

    with pytest.raises(vol.Invalid, match="positive"):
        schema(data)
```

---

## Success Criteria

### Must Have ✅
- [ ] All service schemas in `schemas.py`
- [ ] Schemas organized by category
- [ ] Clear comments for complex validation
- [ ] Consistent naming conventions
- [ ] All schemas tested

### Should Have 🎯
- [ ] Common field patterns extracted
- [ ] Schema composition for reuse
- [ ] Documentation for each schema
- [ ] Examples of valid input

### Nice to Have ✨
- [ ] Schema generation from types
- [ ] Schema versioning
- [ ] Schema documentation generator
- [ ] Schema validation tool

---

## Related Documents

- **[Phase 1: Validation Patterns](../phase-1/validation-patterns.md)**: Custom validators used in schemas
- **[Service Base Classes](service-base-classes.md)**: How schemas are used in services
- **[Service Module Structure](service-module-structure.md)**: Where schemas are imported

---

## References

- Voluptuous documentation: https://github.com/alecthomas/voluptuous
- Home Assistant config validation: https://developers.home-assistant.io/docs/development_validation

# Entity Registry Integration PRD

> **📋 Document Type**: Optional Feature Guide
> **🔗 Related**: [Phase 3 Decision Guide](phase-3-decision-guide.md)
> **📅 Last Updated**: 2025-11-06
> **Status**: 📋 Optional - Requires explicit approval

---

## Overview

This document defines entity registry integration for MeterMate sensors, enabling native Home Assistant UI features like area assignment and entity management.

**Goal**: Enable area assignment and entity metadata management through HA's entity registry.

**Autonomy Level**: 🔴 Human Required - Do NOT implement without explicit approval

**Priority**: 🟡 Medium (Nice to have, not required)

---

## Why This Is Optional

### Core Functionality Works Without It
- ✅ Energy Dashboard reads from statistics table (not entity registry)
- ✅ Users can rename entities via UI already
- ✅ Services work without entity registry integration
- ✅ MeterMate's mission accomplished without this feature

### When This Adds Value
- ✓ Users want area-based organization
- ✓ Users want device/area automations
- ✓ Better integration with HA's entity management UI
- ✓ Professional "native" feel

---

## What Entity Registry Provides

### Features Enabled

**Area Assignment**:
```python
# Assign MeterMate sensor to a room/area
entity_registry.async_update_entity(
    entity_id="sensor.electricity_meter",
    area_id="living_room",
)
```

**Custom Icons**:
```python
# Change icon via entity registry (not config)
entity_registry.async_update_entity(
    entity_id="sensor.electricity_meter",
    icon="mdi:flash",
)
```

**Entity Categories**:
```python
# Mark as diagnostic or config entity
entity_registry.async_update_entity(
    entity_id="sensor.electricity_meter",
    entity_category=EntityCategory.DIAGNOSTIC,
)
```

### NOT Provided by Entity Registry
- ❌ Historical statistics (that's statistics table)
- ❌ Energy Dashboard integration (uses statistics)
- ❌ Current state (that's state machine)

---

## Implementation

### 1. Config Flow Enhancement

Add area selection to config flow:

```python
# config_flow.py
from homeassistant.helpers import area_registry as ar

class MeterMateConfigFlow(ConfigFlow):
    """Config flow with area selection."""

    async def async_step_user(self, user_input=None):
        """Handle user step with area selection."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input["name"],
                data=user_input,
            )

        # Get available areas
        area_registry = ar.async_get(self.hass)
        areas = {
            area.id: area.name
            for area in area_registry.async_list_areas()
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("name"): cv.string,
                vol.Required("unit_of_measurement", default="kWh"): vol.In([
                    "kWh", "m³", "gal", "L", "ft³"
                ]),
                vol.Optional("area_id"): vol.In(areas),  # NEW
                vol.Optional("icon"): cv.icon,            # NEW
            }),
        )
```

### 2. Entity Setup with Registry

Update entity setup to set registry metadata:

```python
# sensor.py
from homeassistant.helpers import entity_registry as er

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor with entity registry metadata."""
    sensor = MeterMateSensor(entry)
    async_add_entities([sensor])

    # Set entity registry metadata if provided
    if "area_id" in entry.data or "icon" in entry.data:
        entity_registry = er.async_get(hass)

        # Wait for entity to be registered
        await hass.async_block_till_done()

        # Update entity registry
        entity_registry.async_update_entity(
            entity_id=sensor.entity_id,
            area_id=entry.data.get("area_id"),
            icon=entry.data.get("icon"),
        )
```

### 3. Service for Metadata Updates

Optional service to update entity metadata:

```python
# services/optional/update_entity_metadata.py
from homeassistant.helpers import entity_registry as er
from ..base import AbstractMeterMateMutationService

class UpdateEntityMetadataService(AbstractMeterMateMutationService):
    """Service to update entity metadata (area, icon, etc)."""

    @property
    def service(self) -> str:
        return "update_entity_metadata"

    @property
    def schema(self):
        return {
            vol.Required(ATTR_ENTITY_ID): metermate_entity_id,
            vol.Optional("area_id"): cv.string,
            vol.Optional("icon"): cv.icon,
            vol.Optional("name"): cv.string,
        }

    async def _async_execute(self, call: ServiceCall) -> None:
        """Update entity registry metadata."""
        entity_id = call.data[ATTR_ENTITY_ID]
        await self._ensure_entity_exists(entity_id)

        entity_registry = er.async_get(self.hass)

        # Build update dict
        updates = {}
        if "area_id" in call.data:
            updates["area_id"] = call.data["area_id"]
        if "icon" in call.data:
            updates["icon"] = call.data["icon"]
        if "name" in call.data:
            updates["name"] = call.data["name"]

        entity_registry.async_update_entity(entity_id, **updates)
```

---

## Testing

```python
async def test_entity_registry_area_assignment(hass, entry):
    """Test area assignment via entity registry."""
    entity_registry = er.async_get(hass)

    # Create area
    area_registry = ar.async_get(hass)
    area = area_registry.async_create("Living Room")

    # Assign entity to area
    entity_registry.async_update_entity(
        entity_id="sensor.electricity_meter",
        area_id=area.id,
    )

    # Verify assignment
    entity = entity_registry.async_get("sensor.electricity_meter")
    assert entity.area_id == area.id


async def test_entity_registry_icon_change(hass, entry):
    """Test icon change via entity registry."""
    entity_registry = er.async_get(hass)

    # Change icon
    entity_registry.async_update_entity(
        entity_id="sensor.electricity_meter",
        icon="mdi:lightning-bolt",
    )

    # Verify change
    entity = entity_registry.async_get("sensor.electricity_meter")
    assert entity.icon == "mdi:lightning-bolt"
```

---

## Decision Criteria

### Implement If:
- ✓ Users specifically request area assignment
- ✓ Want "native HA" feel for better UX
- ✓ Have time for polish features
- ✓ Users use area-based automations

### Skip If:
- ✗ Limited development time
- ✗ No user requests for this feature
- ✗ Want to keep integration simple
- ✗ Focus is on core functionality

---

## Estimated Effort

- **Config flow enhancement**: 1 day
- **Entity setup integration**: 1 day
- **Optional service**: 1 day
- **Testing & documentation**: 1 day
- **Total**: 3-4 days

---

## Success Criteria

### Must Have (If Implementing)
- [ ] Area selection in config flow
- [ ] Area persists to entity registry
- [ ] Icon customization works
- [ ] No impact on core functionality

### Nice to Have
- [ ] Service for metadata updates
- [ ] Support for all entity registry fields
- [ ] Bulk metadata updates

---

## Related Documents

- **[Phase 3 Decision Guide](phase-3-decision-guide.md)**: When to implement this feature
- **[Diagnostic Sensors](diagnostic-sensors.md)**: Another optional feature

---

## References

- Entity Registry API: https://developers.home-assistant.io/docs/entity_registry_index
- Area Registry: https://developers.home-assistant.io/docs/area_registry_index

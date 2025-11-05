# Config Flow Enhancements PRD

> **📋 Document Type**: Optional Feature Guide
> **🔗 Related**: [Phase 3 Decision Guide](phase-3-decision-guide.md)
> **📅 Last Updated**: 2025-11-06
> **Status**: 📋 Optional - Requires explicit approval

---

## Overview

Config flow enhancements improve the initial setup experience with better validation, preview, and unit selection.

**Goal**: Improve first-time configuration UX.

**Autonomy Level**: 🔴 Human Required - Do NOT implement without explicit approval

**Priority**: 🟢 Low (Polish, but low cost)

---

## Enhancements

### 1. Unit Selection with Icons

```python
UNIT_OPTIONS = {
    "kWh": {"name": "Kilowatt Hours", "icon": "mdi:flash"},
    "m³": {"name": "Cubic Meters", "icon": "mdi:gas-cylinder"},
    "gal": {"name": "Gallons", "icon": "mdi:water"},
}
```

### 2. Preview Before Creation

Show user what their sensor will look like before creating:

```python
async def async_step_preview(self, config):
    """Show preview of sensor."""
    preview = {
        "entity_id": f"sensor.{slugify(config['name'])}",
        "friendly_name": config['name'],
        "unit": config['unit'],
    }

    return self.async_show_form(
        step_id="preview",
        description_placeholders=preview,
    )
```

### 3. Import from Existing Statistics

Allow creating MeterMate entity from existing statistics in database.

---

## Decision Criteria

### Implement If:
- ✓ Want to improve first-time experience
- ✓ Low development cost acceptable
- ✓ Users struggle with initial setup
- ✓ Have time for polish

### Skip If:
- ✗ Current config flow works fine
- ✗ Focus is on core functionality
- ✗ Limited development time

---

## Estimated Effort

- **Icon selection**: 1 day
- **Preview step**: 1 day
- **Import existing**: 1 day (optional)
- **Total**: 2-3 days

---

## Related Documents

- **[Phase 3 Decision Guide](phase-3-decision-guide.md)**: When to implement

---

## References

- Config flow best practices: https://developers.home-assistant.io/docs/config_entries_config_flow_handler

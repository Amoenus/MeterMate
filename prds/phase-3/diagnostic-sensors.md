# Diagnostic Sensors PRD

> **📋 Document Type**: Optional Feature Guide
> **🔗 Related**: [Phase 3 Decision Guide](phase-3-decision-guide.md)
> **📅 Last Updated**: 2025-11-06
> **Status**: 📋 Optional - Requires explicit approval

---

## Overview

Diagnostic sensors provide visibility into MeterMate's operation and data quality, helping users understand and troubleshoot their meters.

**Goal**: Add observability sensors for reading counts, data quality, and sync status.

**Autonomy Level**: 🔴 Human Required - Do NOT implement without explicit approval

**Priority**: 🟡 Medium (Helpful for troubleshooting)

---

## Diagnostic Sensors

### 1. Reading Count Sensor

```python
class MeterMateReadingCountSensor(SensorEntity):
    """Sensor showing number of readings stored."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:counter"

    async def async_update(self):
        """Update sensor value."""
        readings = await self.data_manager.get_all_readings(self._entity_id)
        self._attr_native_value = len(readings)
```

**Use**: Know how much data you have stored

### 2. Last Reading Timestamp

```python
class MeterMateLastReadingSensor(SensorEntity):
    """Sensor showing timestamp of most recent reading."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check"

    async def async_update(self):
        """Update sensor value."""
        readings = await self.data_manager.get_all_readings(self._entity_id)
        if readings:
            latest = max(readings, key=lambda r: r.timestamp)
            self._attr_native_value = latest.timestamp
```

**Use**: Detect stale data, know when last reading was added

### 3. Data Quality Score

```python
class MeterMateDataQualitySensor(SensorEntity):
    """Sensor showing data quality score (0-100)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:check-circle"
    _attr_unit_of_measurement = "%"

    async def async_update(self):
        """Calculate data quality score."""
        readings = await self.data_manager.get_all_readings(self._entity_id)

        if not readings:
            self._attr_native_value = 0
            return

        score = self._calculate_quality_score(readings)
        self._attr_native_value = score

    def _calculate_quality_score(self, readings) -> int:
        """Calculate quality 0-100 based on gaps, consistency."""
        score = 100

        # Deduct points for large gaps
        gaps = self._find_gaps(readings)
        score -= min(len(gaps) * 5, 30)

        # Deduct points for inconsistent intervals
        if not self._check_consistency(readings):
            score -= 20

        return max(score, 0)
```

**Use**: Identify data quality issues at a glance

---

## Configuration

Enable via options flow:

```python
class MeterMateOptionsFlow(OptionsFlow):
    """Options flow for diagnostic sensors."""

    async def async_step_init(self, user_input=None):
        """Manage diagnostic sensor options."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("enable_diagnostics", default=False): cv.boolean,
                vol.Optional("diagnostic_update_interval", default=3600): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=60, max=86400),
                ),
            }),
        )
```

---

## Decision Criteria

### Implement If:
- ✓ Users report data issues frequently
- ✓ Want visibility into MeterMate's operation
- ✓ Troubleshooting would benefit from metrics
- ✓ Power users request observability

### Skip If:
- ✗ Users don't report issues
- ✗ Core functionality is priority
- ✗ Want minimal sensor count
- ✗ Limited development time

---

## Estimated Effort

- **Diagnostic sensor implementation**: 2 days
- **Data quality calculation**: 1 day
- **Options flow integration**: 1 day
- **Testing**: 1 day
- **Total**: 4-5 days

---

## Success Criteria

### Must Have (If Implementing)
- [ ] Reading count sensor working
- [ ] Last reading timestamp accurate
- [ ] Data quality score meaningful
- [ ] Can be disabled via options

### Nice to Have
- [ ] More quality metrics
- [ ] Historical quality tracking
- [ ] Quality trend analysis

---

## References

- Diagnostic entities: https://developers.home-assistant.io/docs/core/entity#generic-properties
- Entity categories: https://developers.home-assistant.io/docs/core/entity#entity-category

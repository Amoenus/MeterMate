# Phase 3 PRD: Optional Advanced Features

> **🤖 LLM Operator Context**: This PRD follows the **LLM-First Operations Model** (ADR-000). These are optional enhancements - implement only with explicit human approval and prioritization.

**Status**: 📋 Planned (Optional)
**Priority**: 🟢 MEDIUM/LOW (Optional Enhancements)
**Complexity**: Medium-High
**Impact**: Medium - Improves UX but not required for core functionality
**Timeline**: 3-4 weeks (if implemented)
**Dependencies**: Phase 1 & 2 completion
**Deciders**: Primary Operator + LLM Co-maintainer
**Last Updated**: 2025-11-05

---

## 🤖 LLM Operator Guidance

### Autonomy Level
🔴 **Human Required** - Do NOT implement without explicit human approval for specific features

### Decision Points
Each feature in Phase 3 requires separate approval:
1. Present feature benefits and implementation cost
2. Wait for human decision to proceed
3. Only implement approved features
4. Validate each feature independently

### Key Tools for This Phase
- `get_vscode_api` - Understanding HA entity registry patterns
- `semantic_search` - Finding existing entity registry usage
- `create_file` - Adding new diagnostic sensors and repair flows
- `replace_string_in_file` - Enhancing config flow
- `runTests` - Validating optional features don't break core

### Success Indicators
- ✅ Core functionality remains unchanged
- ✅ Optional features can be disabled
- ✅ No performance impact on base operations
- ✅ Clear user benefit for each feature

### Escalation Triggers
- 🔴 Optional feature affects core Energy Dashboard functionality
- 🔴 Performance degradation detected
- 🔴 Complex dependencies introduced
- 🔴 User requests to disable features

---

## Executive Summary

Phase 3 implements **optional enhancements** that improve user experience and integration with Home Assistant's ecosystem. **These features are NOT required for MeterMate's core mission** (manual data entry for Energy Dashboard) but provide valuable quality-of-life improvements.

### Key Principle: Optional But Delightful

These features enhance MeterMate without compromising its simplicity:
- ✅ **Entity Registry Integration** - Better UI integration (area assignment)
- ✅ **Diagnostic Sensors** - Visibility into MeterMate's operation
- ✅ **Repair Detection** - Proactive issue identification
- ✅ **Enhanced UI** - Better config flow and panel features

### Critical Understanding:
- ❌ NOT required for Energy Dashboard functionality
- ✅ Improves integration with HA's UI and tools
- ✅ Makes MeterMate feel more "native" to Home Assistant
- ✅ Helps users manage and troubleshoot their meters

---

## Feature Breakdown

### Feature 1: Entity Registry Integration (Optional UI Enhancement)

**Goal**: Enable native Home Assistant UI features for MeterMate sensors.

**Priority**: 🟡 Medium (Nice to have, not required)

#### What It Enables

```python
# Users can assign MeterMate sensors to areas via UI
# This doesn't affect Energy Dashboard, but makes organization better

entity_registry = er.async_get(hass)
entity_registry.async_update_entity(
    entity_id="sensor.metermate_electricity",
    area_id="living_room",  # Assign to room
    icon="mdi:flash",       # Custom icon
    # Note: Energy Dashboard doesn't use this metadata
)
```

**User Benefits**:
- ✅ Assign sensors to areas (rooms) via UI
- ✅ Change icons without editing YAML
- ✅ Enable/disable sensors from UI
- ✅ Better integration with area-based automations
- ✅ Cleaner entity management

**Implementation Approach**:

1. **Config Flow Enhancement** (1-2 days)
```python
# Add area selection to config flow
class MeterMateConfigFlow(ConfigFlow):
    """Enhanced config flow with area selection."""

    async def async_step_user(self, user_input=None):
        """Handle user step with area selection."""
        # ... existing code ...

        # Add area selector
        area_registry = ar.async_get(self.hass)
        areas = {area.id: area.name for area in area_registry.async_list_areas()}

        schema = vol.Schema({
            # ... existing fields ...
            vol.Optional("area_id"): vol.In(areas),
            vol.Optional("icon"): cv.icon,
        })
```

2. **Entity Setup Enhancement** (1 day)
```python
# In sensor.py - set initial entity registry metadata
async def async_setup_entry(hass, entry, async_add_entities):
    """Set up sensor with entity registry metadata."""
    sensor = MeterMateSensor(entry)
    async_add_entities([sensor])

    # Set entity registry metadata if provided in config
    if "area_id" in entry.data or "icon" in entry.data:
        entity_registry = er.async_get(hass)
        entity_registry.async_update_entity(
            entity_id=sensor.entity_id,
            area_id=entry.data.get("area_id"),
            icon=entry.data.get("icon"),
        )
```

3. **Optional Service** (1 day)
```python
# Add optional service for updating entity metadata
# services/optional/update_entity_metadata.py
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
            vol.Optional("entity_category"): cv.string,
        }

    async def _async_execute(self, call: ServiceCall) -> None:
        """Update entity registry metadata."""
        entity_id = call.data[ATTR_ENTITY_ID]
        await self._ensure_entity_exists(entity_id)

        entity_registry = er.async_get(self.hass)

        # Update only provided fields
        update_data = {}
        if "area_id" in call.data:
            update_data["area_id"] = call.data["area_id"]
        if "icon" in call.data:
            update_data["icon"] = call.data["icon"]
        if "entity_category" in call.data:
            update_data["entity_category"] = call.data["entity_category"]

        entity_registry.async_update_entity(entity_id, **update_data)

        _LOGGER.info("Updated metadata for %s: %s", entity_id, update_data)
```

**When to Use**: If users request better organization features or area-based automations.

---

### Feature 2: Diagnostic Sensors (Observability)

**Goal**: Provide visibility into MeterMate's operation and data status.

**Priority**: 🟡 Medium (Helpful for troubleshooting)

#### Diagnostic Sensors to Add

```python
# Diagnostic sensors that help users understand their data
class MeterMateDiagnosticSensors:
    """Diagnostic sensors for MeterMate."""

    # 1. Reading Count Sensor
    sensor.metermate_electricity_reading_count
    # Value: Total number of readings stored
    # Useful for: Knowing how much data you have

    # 2. Last Reading Timestamp
    sensor.metermate_electricity_last_reading
    # Value: Datetime of most recent reading
    # Useful for: Detecting stale data

    # 3. Data Quality Score
    sensor.metermate_electricity_data_quality
    # Value: 0-100 score based on gaps, consistency
    # Useful for: Identifying data quality issues

    # 4. Statistics Sync Status
    sensor.metermate_electricity_sync_status
    # Value: "synced" | "pending" | "error"
    # Useful for: Knowing if stats are up to date
```

**Implementation**:

```python
# custom_components/metermate/diagnostics.py
"""Diagnostic sensors for MeterMate."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory

class MeterMateReadingCountSensor(SensorEntity):
    """Sensor showing number of readings."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:counter"

    def __init__(self, entry, meter_entity_id):
        """Initialize diagnostic sensor."""
        self._meter_entity_id = meter_entity_id
        self._attr_unique_id = f"{entry.entry_id}_reading_count"
        self._attr_name = f"{entry.data['name']} Reading Count"

    async def async_update(self):
        """Update sensor value."""
        data_manager = self.hass.data[ATTR_INTEGRATION_NAME]["data_manager"]
        readings = await data_manager.get_all_readings(self._meter_entity_id)
        self._attr_native_value = len(readings)

class MeterMateLastReadingSensor(SensorEntity):
    """Sensor showing timestamp of last reading."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check"

    async def async_update(self):
        """Update sensor value."""
        data_manager = self.hass.data[ATTR_INTEGRATION_NAME]["data_manager"]
        readings = await data_manager.get_all_readings(self._meter_entity_id)
        if readings:
            latest = max(readings, key=lambda r: r.timestamp)
            self._attr_native_value = latest.timestamp

class MeterMateDataQualitySensor(SensorEntity):
    """Sensor showing data quality score."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:check-circle"
    _attr_unit_of_measurement = "%"

    async def async_update(self):
        """Calculate data quality score."""
        data_manager = self.hass.data[ATTR_INTEGRATION_NAME]["data_manager"]
        readings = await data_manager.get_all_readings(self._meter_entity_id)

        if not readings:
            self._attr_native_value = 0
            return

        # Calculate quality score based on:
        # - Number of readings (more is better)
        # - Gaps between readings (fewer is better)
        # - Consistency of intervals (more consistent is better)
        score = self._calculate_quality_score(readings)
        self._attr_native_value = score

    def _calculate_quality_score(self, readings) -> int:
        """Calculate quality score 0-100."""
        # Implementation details...
        # - Check for large gaps
        # - Check for reasonable intervals
        # - Check for duplicate timestamps
        # - Check for negative consumption (impossible)
        return score
```

**Configuration Option**:
```python
# In config flow, add option to enable diagnostics
class MeterMateOptionsFlow(OptionsFlow):
    """Handle options flow."""

    async def async_step_init(self, user_input=None):
        """Manage options."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    "enable_diagnostics",
                    default=False,
                ): cv.boolean,
                vol.Optional(
                    "diagnostic_update_interval",
                    default=3600,  # 1 hour
                ): cv.positive_int,
            }),
        )
```

**When to Use**: If users report issues or want visibility into their data status.

---

### Feature 3: Repair Detection (Proactive Issue Management)

**Goal**: Automatically detect and report common issues to users.

**Priority**: 🟡 Medium (Helpful for maintenance)

#### Repairs to Detect

```python
# Industry-standard repair detection patterns
class MeterMateRepairs:
    """Repair detections for MeterMate."""

    # 1. Orphaned Statistics
    # - Statistics exist but no MeterMate entity
    # - Offer to clean up or recreate entity

    # 2. Data Gaps
    # - Large gaps between readings (>30 days)
    # - Suggest adding missing data

    # 3. Inconsistent Units
    # - Unit changed over time in statistics
    # - Offer to standardize

    # 4. Negative Consumption
    # - Meter reading decreased (impossible for cumulative)
    # - Flag for review

    # 5. Stale Data
    # - No readings in last 90 days
    # - Suggest archiving or adding data
```

**Implementation**:

```python
# custom_components/metermate/repairs.py
"""Repair detection for MeterMate."""
from homeassistant.helpers import issue_registry as ir

class MeterMateRepairDetector:
    """Detect and report issues."""

    async def async_detect_repairs(self, hass: HomeAssistant) -> None:
        """Run all repair detections."""
        await self._detect_orphaned_statistics(hass)
        await self._detect_data_gaps(hass)
        await self._detect_inconsistent_units(hass)
        await self._detect_negative_consumption(hass)
        await self._detect_stale_data(hass)

    async def _detect_orphaned_statistics(self, hass: HomeAssistant) -> None:
        """Detect statistics without entities."""
        # Query statistics_meta for metermate entries
        # Check if corresponding entities exist
        # Create repair issue if orphaned

        issue_registry = ir.async_get(hass)

        for orphaned_stat in orphaned_statistics:
            issue_registry.async_create_issue(
                domain=ATTR_INTEGRATION_NAME,
                issue_id=f"orphaned_statistic_{orphaned_stat.statistic_id}",
                is_fixable=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="orphaned_statistic",
                translation_placeholders={
                    "statistic_id": orphaned_stat.statistic_id,
                    "name": orphaned_stat.name,
                },
            )

    async def _detect_data_gaps(self, hass: HomeAssistant) -> None:
        """Detect large gaps in reading data."""
        data_manager = hass.data[ATTR_INTEGRATION_NAME]["data_manager"]

        for entity_id in self._get_all_metermate_entities(hass):
            readings = await data_manager.get_all_readings(entity_id)
            gaps = self._find_large_gaps(readings, threshold_days=30)

            if gaps:
                issue_registry = ir.async_get(hass)
                issue_registry.async_create_issue(
                    domain=ATTR_INTEGRATION_NAME,
                    issue_id=f"data_gap_{entity_id}",
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="data_gap",
                    translation_placeholders={
                        "entity_id": entity_id,
                        "gap_count": str(len(gaps)),
                        "largest_gap_days": str(max(gaps)),
                    },
                )
```

**Repair Fixes**:

```python
# custom_components/metermate/repairs_flow.py
"""Handle repair fix flows."""
from homeassistant import data_entry_flow
from homeassistant.helpers import issue_registry as ir

class MeterMateRepairFlow(data_entry_flow.FlowHandler):
    """Handler for repair flows."""

    async def async_step_orphaned_statistic(self, user_input=None):
        """Handle orphaned statistic repair."""
        if user_input is not None:
            action = user_input["action"]

            if action == "cleanup":
                # Remove orphaned statistics
                await self._cleanup_orphaned_statistic()
            elif action == "recreate":
                # Recreate entity from statistics
                await self._recreate_entity_from_statistics()

            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="orphaned_statistic",
            data_schema=vol.Schema({
                vol.Required("action"): vol.In({
                    "cleanup": "Remove statistics",
                    "recreate": "Recreate entity",
                    "ignore": "Keep as-is",
                }),
            }),
        )
```

**When to Use**: If users struggle with data quality or maintenance.

---

### Feature 4: Enhanced Config Flow (Better UX)

**Goal**: Improve config flow with better validation and options.

**Priority**: 🟢 Low (Polish)

#### Enhancements

```python
# 1. Unit Selection with Icons
UNIT_OPTIONS = {
    "kWh": {"name": "Kilowatt Hours", "icon": "mdi:flash", "device_class": "energy"},
    "m³": {"name": "Cubic Meters", "icon": "mdi:gas-cylinder", "device_class": "gas"},
    "gal": {"name": "Gallons", "icon": "mdi:water", "device_class": "water"},
    "L": {"name": "Liters", "icon": "mdi:water", "device_class": "water"},
}

# 2. Validation Preview
# Show user what their sensor will look like
async def async_step_user(self, user_input=None):
    """Step with preview."""
    if user_input is not None:
        # Show preview before confirmation
        return await self.async_step_preview(user_input)

    return self.async_show_form(...)

async def async_step_preview(self, config):
    """Show preview of sensor before creation."""
    preview_data = {
        "entity_id": f"sensor.{config['name'].lower().replace(' ', '_')}",
        "friendly_name": config['name'],
        "unit": config['unit_of_measurement'],
        "device_class": config['device_class'],
        "initial_value": config.get('initial_reading', 0),
    }

    return self.async_show_form(
        step_id="preview",
        description_placeholders=preview_data,
        data_schema=vol.Schema({
            vol.Required("confirm", default=True): cv.boolean,
        }),
    )

# 3. Import from Existing Statistics
# Allow creating MeterMate entity from existing statistics
async def async_step_import_existing(self, user_input=None):
    """Import from existing statistics."""
    # List all statistics_meta entries
    # User selects one
    # Create MeterMate entity pointing to it
```

---

### Feature 5: Panel Enhancements (Better Management UI)

**Goal**: Improve the frontend panel with better features.

**Priority**: 🟢 Low (Polish)

#### Enhancements

```python
# 1. Data Quality Dashboard
# Show quality metrics for all meters
{
  "meters": [
    {
      "entity_id": "sensor.electricity",
      "name": "Electricity",
      "reading_count": 245,
      "last_reading": "2025-01-01T10:00:00Z",
      "data_quality_score": 92,
      "issues": ["Gap: 2024-12-20 to 2024-12-25"]
    }
  ]
}

# 2. Bulk Operations UI
# Select multiple readings for bulk edit/delete
# Visual timeline of readings
# Gap detection visualization

# 3. Import/Export UI
# Better CSV import with preview
# Export readings to CSV
# Template download for CSV format

# 4. Statistics Viewer
# Show how readings map to statistics
# Visualize consumption over time
# Compare with Energy Dashboard view
```

---

## Implementation Priority (Within Phase 3)

### High Priority (If Implementing Phase 3)
1. 🎯 **Entity Registry Integration** - Most requested feature
2. 🎯 **Diagnostic Sensors** - Helps with troubleshooting

### Medium Priority
3. 🔧 **Repair Detection** - Proactive issue management
4. 🔧 **Enhanced Config Flow** - Better first-time experience

### Low Priority
5. ✨ **Panel Enhancements** - Polish and convenience

---

## Success Criteria

### Must Have ✅ (If Implementing)
- [ ] Entity registry integration works correctly
- [ ] Area assignment functional via UI
- [ ] Diagnostic sensors provide accurate data
- [ ] No performance impact on core functionality
- [ ] All features are optional and non-breaking

### Should Have 🎯
- [ ] Repair detection identifies common issues
- [ ] Config flow preview works
- [ ] Diagnostic sensors update efficiently
- [ ] Documentation for all new features

### Nice to Have ✨
- [ ] Panel enhancements implemented
- [ ] Bulk operations UI
- [ ] Data quality dashboard
- [ ] Import/export improvements

---

## Testing Strategy

### Entity Registry Tests
```python
async def test_entity_registry_integration(hass, entry):
    """Test area assignment works."""
    entity_registry = er.async_get(hass)

    # Update area
    entity_registry.async_update_entity(
        entity_id="sensor.metermate_test",
        area_id="living_room",
    )

    # Verify area assigned
    entity = entity_registry.async_get("sensor.metermate_test")
    assert entity.area_id == "living_room"

async def test_area_assignment_persists(hass, entry):
    """Test area survives reload."""
    # Assign area
    # Reload integration
    # Verify area still assigned
```

### Diagnostic Sensor Tests
```python
async def test_reading_count_sensor(hass, data_manager, entity):
    """Test reading count sensor updates."""
    # Add readings
    # Check diagnostic sensor value
    # Add more readings
    # Verify count increased

async def test_data_quality_calculation(hass, data_manager, entity):
    """Test quality score calculation."""
    # Add good data -> high score
    # Add data with gaps -> lower score
    # Add inconsistent data -> low score
```

### Repair Detection Tests
```python
async def test_orphaned_statistic_detection(hass, data_manager):
    """Test orphaned statistics are detected."""
    # Create statistics without entity
    # Run repair detection
    # Verify issue created

async def test_data_gap_detection(hass, data_manager, entity):
    """Test large gaps are detected."""
    # Add readings with large gap
    # Run repair detection
    # Verify issue created
```

---

## Migration Strategy

Phase 3 is entirely optional and non-breaking:

### Step 1: Entity Registry (Optional)
- Add to config flow as optional
- Existing entities continue working
- Users can opt-in via reconfiguration

### Step 2: Diagnostic Sensors (Optional)
- Add as separate entities
- Disabled by default
- Enable via options flow

### Step 3: Repair Detection (Passive)
- Runs in background
- Only creates issues when problems found
- Users can dismiss issues

### Step 4: UI Enhancements (Progressive)
- Add features incrementally
- Maintain backward compatibility
- Old panel continues working

---

## Performance Considerations

### Entity Registry
- ✅ Minimal overhead (one-time update)
- ✅ No impact on statistics writing
- ✅ Standard HA pattern

### Diagnostic Sensors
- ⚠️ Need efficient update mechanism
- ⚠️ Don't query on every state change
- ✅ Update on configurable interval (default: 1 hour)
- ✅ Can be disabled entirely

### Repair Detection
- ⚠️ Can be expensive if checking all data
- ✅ Run on background schedule (default: daily)
- ✅ Can be disabled via config
- ✅ Cache results to avoid repeat checks

---

## Timeline

**Total: 3-4 weeks (if implementing all features)**

- **Week 1**: Entity Registry Integration
  - Day 1-2: Config flow enhancement
  - Day 3: Entity setup integration
  - Day 4: Service for metadata updates
  - Day 5: Testing

- **Week 2**: Diagnostic Sensors
  - Day 1-2: Implement sensors
  - Day 3: Data quality calculation
  - Day 4: Options flow integration
  - Day 5: Testing

- **Week 3**: Repair Detection
  - Day 1-2: Detection logic
  - Day 3: Issue creation/management
  - Day 4: Repair flows
  - Day 5: Testing

- **Week 4**: Polish & Enhancements
  - Day 1-2: Config flow improvements
  - Day 3-4: Panel enhancements
  - Day 5: Documentation and final testing

---

## Cost-Benefit Analysis

### Entity Registry Integration
**Cost**: 3-4 days development
**Benefit**: Native HA UI integration, better organization
**Verdict**: 🟡 Valuable if users request area features

### Diagnostic Sensors
**Cost**: 3-4 days development
**Benefit**: Better observability, easier troubleshooting
**Verdict**: 🟢 Useful for support and power users

### Repair Detection
**Cost**: 4-5 days development
**Benefit**: Proactive issue identification
**Verdict**: 🟡 Nice to have, but not critical

### Enhanced Config Flow
**Cost**: 2-3 days development
**Benefit**: Better first-time experience
**Verdict**: 🟢 Low cost, good improvement

### Panel Enhancements
**Cost**: 5-6 days development
**Benefit**: Better management UX
**Verdict**: 🔴 High cost, optional benefit

---

## Dependencies

### Code Dependencies
- Phase 1 & 2 completion
- Entity registry: `homeassistant.helpers.entity_registry`
- Area registry: `homeassistant.helpers.area_registry`
- Issue registry: `homeassistant.helpers.issue_registry`
- No new external dependencies

### Knowledge Dependencies
- HA entity registry patterns
- Issue/repair system
- Data entry flow system
- Frontend panel development

---

## Risks & Mitigation

### Risk: Feature Creep
**Mitigation**:
- All features are optional
- Can skip entirely if not needed
- Implement incrementally
- Get user feedback before continuing

### Risk: Performance Impact
**Mitigation**:
- Diagnostic sensors update on schedule, not real-time
- Repair detection runs in background
- All features can be disabled
- Monitor performance with each addition

### Risk: Maintenance Burden
**Mitigation**:
- Keep features simple
- Good test coverage
- Clear documentation
- Can deprecate unused features later

---

## When to Skip Phase 3

Skip or defer Phase 3 if:

- ✅ Core functionality (Phases 1 & 2) is solid and users are happy
- ✅ No user requests for these features
- ✅ Limited development time/resources
- ✅ Want to keep integration minimal
- ✅ Users prefer simplicity over features

**Remember**: Phase 3 is entirely optional. MeterMate works perfectly without these features!

---

## References

### Related Documentation
- **ADR-000**: LLM-First Operations Model - Decision framework for optional features
- **Phase 1 & 2 PRDs**: Foundation that these enhancements build upon
- **LLM Operator's Handbook**: Feature implementation and validation procedures

### External References
- Home Assistant issue registry: https://developers.home-assistant.io/docs/creating_integration_repairs
- Entity registry integration: https://developers.home-assistant.io/docs/entity_registry_index
- Diagnostic entities: https://developers.home-assistant.io/docs/core/entity#generic-properties
- Config flow best practices: https://developers.home-assistant.io/docs/config_entries_config_flow_handler
- Area registry: https://developers.home-assistant.io/docs/area_registry_index

### Implementation Examples
- Repair flows in HA core: Search for `async_create_issue` in core integrations
- Diagnostic entities: Look for `entity_category=EntityCategory.DIAGNOSTIC` in core
- Entity registry usage: Examples in popular integrations like `zha`, `mqtt`

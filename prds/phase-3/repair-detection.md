# Repair Detection PRD

> **📋 Document Type**: Optional Feature Guide
> **🔗 Related**: [Phase 3 Decision Guide](phase-3-decision-guide.md), [Diagnostic Sensors](diagnostic-sensors.md)
> **📅 Last Updated**: 2025-11-06
> **Status**: 📋 Optional - Requires explicit approval

---

## Overview

Repair detection automatically identifies common data issues and offers fixes through Home Assistant's repair system.

**Goal**: Proactively detect and help users fix data quality issues.

**Autonomy Level**: 🔴 Human Required - Do NOT implement without explicit approval

**Priority**: 🟡 Medium (Optional maintenance feature)

---

## Detectable Issues

### 1. Orphaned Statistics
- Statistics exist but no MeterMate entity
- **Fix**: Offer to clean up or recreate entity

### 2. Large Data Gaps
- Missing readings for 30+ days
- **Fix**: Suggest adding missing data

### 3. Inconsistent Units
- Unit changed over time
- **Fix**: Offer to standardize units

### 4. Negative Consumption
- Meter reading decreased (impossible)
- **Fix**: Flag for manual review

### 5. Stale Data
- No readings in last 90 days
- **Fix**: Suggest archiving or adding data

---

## Implementation

Uses Home Assistant's issue registry:

```python
from homeassistant.helpers import issue_registry as ir

class MeterMateRepairDetector:
    """Detect and report issues."""

    async def async_detect_repairs(self, hass):
        """Run all repair detections."""
        await self._detect_orphaned_statistics(hass)
        await self._detect_data_gaps(hass)
        # ... other detections

    async def _detect_orphaned_statistics(self, hass):
        """Detect statistics without entities."""
        issue_registry = ir.async_get(hass)

        for orphaned in self._find_orphaned():
            issue_registry.async_create_issue(
                domain=DOMAIN,
                issue_id=f"orphaned_{orphaned.id}",
                is_fixable=True,
                severity=ir.IssueSeverity.WARNING,
                translation_key="orphaned_statistic",
            )
```

---

## Decision Criteria

### Implement If:
- ✓ Users frequently have data quality issues
- ✓ Support burden from bad data is high
- ✓ Want proactive issue detection
- ✓ Have development time available

### Skip If:
- ✗ Users don't report data issues
- ✗ Support burden is low
- ✗ Limited development time
- ✗ Prefer reactive troubleshooting

---

## Estimated Effort

- **Detection logic**: 2-3 days
- **Issue creation/management**: 1-2 days
- **Repair flows**: 2 days
- **Testing**: 1 day
- **Total**: 5-6 days

---

## Related Documents

- **[Diagnostic Sensors](diagnostic-sensors.md)**: Complementary observability
- **[Phase 3 Decision Guide](phase-3-decision-guide.md)**: When to implement

---

## References

- Repair system: https://developers.home-assistant.io/docs/creating_integration_repairs
- Issue registry: https://developers.home-assistant.io/docs/issue_registry_index

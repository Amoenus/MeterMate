# Product Requirements Document: MeterMate Improvements

**Document Version:** 1.0
**Date:** November 5, 2025
**Status:** Draft - Ready for Implementation
**Priority:** High

---

## Executive Summary

This PRD outlines improvements to MeterMate that will enhance reliability, user experience, and compatibility with Home Assistant's Energy Dashboard. These improvements focus on adopting proven patterns while maintaining MeterMate's unique value proposition as a live CRUD management system for manual utility readings.

**Key Improvements:**
1. External Statistics Architecture for historical data
2. Comprehensive validation framework
3. Enhanced error handling with solutions
4. CSV/File import capabilities
5. Improved timezone handling

---

## 1. Strategic Architecture Decision: External Statistics

### 1.1 Problem Statement

Our current approach uses internal statistics (`sensor.metermate_xyz`) which creates challenges:
- Complex state injection into Home Assistant's recorder
- Conflicts with HA's state management
- Difficult to manage historical data retroactively
- Potential data inconsistencies

### 1.2 Proposed Solution: Hybrid Architecture

**Implement a two-tier system:**

```
┌─────────────────────────────────────────────────┐
│ User Interface Layer                            │
├─────────────────────────────────────────────────┤
│ sensor.metermate_electricity                    │
│ - Current state (latest meter reading)         │
│ - Visible in HA dashboard                      │
│ - Used in automations                          │
│ - State class: total_increasing                │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│ Historical Data Layer                           │
├─────────────────────────────────────────────────┤
│ metermate:electricity                           │
│ - All historical readings                      │
│ - External statistics format                   │
│ - Energy Dashboard compatible                  │
│ - No state management conflicts                │
└─────────────────────────────────────────────────┘
```

### 1.3 Benefits

✅ **Separation of Concerns:** Current state vs. historical data
✅ **Reliability:** No conflicts with HA's recorder
✅ **Flexibility:** Easy to add/modify historical data
✅ **Performance:** Efficient statistics queries
✅ **Compatibility:** Works seamlessly with Energy Dashboard

### 1.4 Implementation Requirements

**Phase 1: Parallel Implementation (Weeks 1-2)**
- Add external statistics alongside current internal statistics
- Implement `_create_external_statistics()` method
- Test Energy Dashboard integration

**Phase 2: Migration Path (Week 3)**
- Provide migration script for existing users
- Document transition process
- Add service to rebuild statistics in new format

**Phase 3: Deprecation (Week 4+)**
- Mark internal statistics as deprecated
- Provide backward compatibility
- Plan eventual removal

### 1.5 Success Criteria

- [ ] External statistics appear in Energy Dashboard
- [ ] Historical data import works correctly
- [ ] No performance degradation
- [ ] Existing users can migrate seamlessly
- [ ] Documentation updated with examples

---

## 2. Validation Framework Enhancement

### 2.1 Problem Statement

Current validation is basic:
- Limited error messages
- No timestamp boundary checks
- Missing consumption validation
- No timezone validation

### 2.2 Proposed Solution

Create comprehensive validation module.

### 2.3 Requirements

**New File:** `custom_components/metermate/validation.py`

```python
"""
Validation utilities for MeterMate.

"""

class ValidationError(Exception):
    """Base validation error with solution guidance."""

class TimestampValidator:
    """Validate timestamps for statistics compatibility."""

    @staticmethod
    def validate_hour_boundary(timestamp: datetime) -> None:
        """Ensure timestamp is on hour boundary."""

    @staticmethod
    def validate_not_future(timestamp: datetime) -> None:
        """Ensure timestamp is not in the future."""

    @staticmethod
    def validate_timezone_aware(timestamp: datetime) -> datetime:
        """Ensure timestamp has timezone info."""

class ValueValidator:
    """Validate reading values."""

    @staticmethod
    def validate_numeric(value: any) -> float:
        """Convert and validate numeric value."""

    @staticmethod
    def validate_positive(value: float, allow_zero: bool = True) -> None:
        """Ensure value is positive."""

    @staticmethod
    def validate_consumption(
        previous: float,
        current: float,
        allow_rollover: bool = False
    ) -> float:
        """Validate meter readings and calculate consumption."""

class ReadingValidator:
    """Complete reading validation."""

    @staticmethod
    def validate_reading(reading: Reading) -> ValidationResult:
        """Comprehensive validation of a reading."""
```

### 2.4 Integration Points

- Update `data_manager.py` to use new validators
- Update service handlers to use new validators
- Add validation to all CRUD operations

### 2.5 Success Criteria

- [ ] All timestamp validation uses hour boundaries
- [ ] Timezone validation on all inputs
- [ ] Consumption calculations validated
- [ ] Comprehensive test coverage (>90%)
- [ ] Clear error messages with solutions

---

## 3. Solution-Oriented Error Messages

### 3.1 Problem Statement

Current errors are technical:
```python
raise HomeAssistantError("Validation failed: Timestamp cannot be in the future")
```

Users don't know how to fix it.

### 3.2 Proposed Solution

Implement error hierarchy with solutions.

### 3.3 Requirements

**New File:** `custom_components/metermate/exceptions.py`

```python
"""
Custom exceptions with solution guidance.

"""

class MeterMateError(HomeAssistantError):
    """Base error with solution guidance."""

    def __init__(self, error: str, solution: str, details: dict = None):
        self.solution = solution
        self.details = details or {}
        super().__init__(self._format_message(error))

    def _format_message(self, error: str) -> str:
        msg = f"{error}\n\n💡 Solution: {self.solution}"
        if self.details:
            msg += f"\n\nℹ️  Details: {self.details}"
        return msg

class ReadingExistsError(MeterMateError):
    """Reading already exists."""

    def __init__(self, timestamp: datetime, existing_value: float):
        super().__init__(
            error=f"Reading already exists for {timestamp.strftime('%Y-%m-%d %H:%M')}",
            solution="Use 'metermate.update_reading' to modify, or 'metermate.delete_reading' to remove first",
            details={"existing_value": existing_value, "timestamp": timestamp.isoformat()}
        )

class InvalidTimestampError(MeterMateError):
    """Timestamp validation failed."""
    pass

class InvalidValueError(MeterMateError):
    """Value validation failed."""
    pass

class ConsumptionError(MeterMateError):
    """Consumption calculation error."""
    pass
```

### 3.4 Error Message Standards

All errors must include:
1. **What** went wrong (clear description)
2. **Why** it's a problem (context)
3. **How** to fix it (actionable solution)
4. **Details** for debugging (optional)

### 3.5 Example Error Messages

```
❌ Current:
"Timestamp cannot be in the future"

✅ Improved:
"Timestamp 2025-12-01 10:00:00 is in the future

💡 Solution: Use a past timestamp, or omit timestamp to use current time

ℹ️  Details:
  - Provided: 2025-12-01 10:00:00
  - Current time: 2025-11-05 10:00:00
  - Difference: 26 days in the future"
```

### 3.6 Success Criteria

- [ ] All exceptions inherit from MeterMateError
- [ ] Every error has a solution
- [ ] Error messages tested with non-technical users
- [ ] Documentation includes common errors and solutions

---

## 4. CSV/File Import Capability

### 4.1 Problem Statement

Users often have historical data in spreadsheets:
- Monthly bills in Excel
- Meter reading logs in CSV
- Data from previous systems

Currently no way to bulk import this data efficiently.

### 4.2 Proposed Solution

Add CSV import service using pandas.

### 4.3 Requirements

**New Service:** `metermate.import_from_csv`

```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "/config/meter_readings.csv"
  delimiter: ","
  decimal: "."
  timezone: "America/Los_Angeles"
  date_format: "%Y-%m-%d %H:%M"
```

**CSV Format:**
```csv
timestamp,value,unit,notes
2024-01-01 00:00,15432.5,kWh,January reading
2024-02-01 00:00,15650.2,kWh,February reading
2024-03-01 00:00,15890.1,kWh,March reading
```

### 4.4 Features

1. **Flexible Format Support**
   - CSV, TSV support
   - Configurable delimiter
   - Configurable decimal separator (. or ,)
   - Custom date/time formats

2. **Validation**
   - Check for required columns
   - Validate all timestamps
   - Validate all values
   - Report errors with line numbers

3. **Efficiency**
   - Use pandas for large files
   - Batch processing
   - Progress reporting

4. **Safety**
   - Dry-run mode
   - Duplicate detection
   - Rollback capability

### 4.5 Implementation

**New File:** `custom_components/metermate/import_helper.py`

```python
"""
Bulk import utilities.
"""

class CSVImporter:
    """Import readings from CSV files."""

    async def import_from_csv(
        self,
        entity_id: str,
        file_path: str,
        delimiter: str = ",",
        decimal: str = ".",
        timezone: str = "UTC",
        date_format: str = "%Y-%m-%d %H:%M",
        dry_run: bool = False
    ) -> ImportResult:
        """Import readings from CSV file."""
```

### 4.6 User Interface

Add to service descriptions in `services.yaml`:

```yaml
import_from_csv:
  name: Import from CSV
  description: Import multiple readings from a CSV file
  fields:
    entity_id:
      name: Entity
      description: The meter entity to import readings for
      required: true
      selector:
        entity:
          domain: sensor
    file_path:
      name: File Path
      description: Path to CSV file (relative to /config)
      required: true
      example: "meter_readings.csv"
    delimiter:
      name: Delimiter
      description: Column separator
      default: ","
      selector:
        select:
          options:
            - label: "Comma (,)"
              value: ","
            - label: "Semicolon (;)"
              value: ";"
            - label: "Tab"
              value: "\t"
    # ... other fields
```

### 4.7 Success Criteria

- [ ] Can import 1000+ readings efficiently
- [ ] Clear error messages for invalid CSV
- [ ] Duplicate detection works correctly
- [ ] Progress reporting for large imports
- [ ] Documentation with example CSV files
- [ ] Video tutorial created

---

## 5. Enhanced Timezone Handling

### 5.1 Problem Statement

Current timezone handling is implicit:
- Users may not understand UTC vs. local time
- Errors when timezone-naive timestamps provided
- Confusion about when readings occur

### 5.2 Proposed Solution

Explicit timezone handling with validation and conversion.

### 5.3 Requirements

1. **Always Store UTC**
   - Convert all inputs to UTC
   - Store in UTC in database
   - Display in user's timezone

2. **Timezone Configuration**
   - Per-entity timezone setting
   - Default to HA's configured timezone
   - Allow override in service calls

3. **Validation**
   - Reject timezone-naive timestamps with helpful error
   - Validate timezone strings against IANA database
   - Provide timezone picker in UI

4. **Display**
   - Show timezone in entity attributes
   - Convert to local time in UI
   - Include timezone in all logs

### 5.4 Implementation Changes

**Update `Reading` model:**
```python
@dataclass
class Reading:
    """Reading with explicit timezone handling."""
    timestamp: datetime  # Always UTC in storage
    timezone: str = "UTC"  # Original timezone for reference

    def to_local_time(self, target_tz: str = None) -> datetime:
        """Convert to local time."""

    @classmethod
    def from_local_time(cls, timestamp: datetime, timezone: str) -> "Reading":
        """Create reading from local time."""
```

**Update services:**
```yaml
add_reading:
  fields:
    timestamp:
      description: "Timestamp (will be converted to UTC)"
    timezone:
      name: Timezone
      description: "Timezone of the timestamp (defaults to HA timezone)"
      default: "UTC"
      example: "America/Los_Angeles"
      selector:
        text:
```

### 5.5 User Experience

**Clear Communication:**
```
✅ Reading added successfully
   - Your time: 2025-01-15 10:00:00 PST
   - Stored as: 2025-01-15 18:00:00 UTC
   - Timezone: America/Los_Angeles
```

### 5.6 Success Criteria

- [ ] All timestamps stored in UTC
- [ ] Timezone validation on all inputs
- [ ] Clear error messages for timezone issues
- [ ] Documentation with timezone examples
- [ ] UI shows local and UTC times

---

## 6. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)
**Priority: High**

- [ ] Create `validation.py` module
- [ ] Create `exceptions.py` module
- [ ] Implement hour boundary validation
- [ ] Implement timezone validation
- [ ] Update existing code to use new validators
- [ ] Add comprehensive tests

**Deliverables:**
- Validation framework implemented
- All tests passing
- Error messages improved

### Phase 2: External Statistics (Weeks 3-4)
**Priority: High**

- [ ] Implement external statistics creation
- [ ] Add parallel statistics tracking
- [ ] Test Energy Dashboard integration
- [ ] Create migration script
- [ ] Update documentation

**Deliverables:**
- External statistics working
- Migration path documented
- Energy Dashboard verified

### Phase 3: CSV Import (Weeks 5-6)
**Priority: Medium**

- [ ] Implement `import_helper.py`
- [ ] Add CSV import service
- [ ] Create example CSV files
- [ ] Add service to `services.yaml`
- [ ] Write import documentation
- [ ] Create video tutorial

**Deliverables:**
- CSV import service functional
- Example files provided
- Documentation complete

### Phase 4: Polish & Documentation (Week 7)
**Priority: Medium**

- [ ] Update all documentation
- [ ] Create upgrade guide
- [ ] Add troubleshooting section
- [ ] Update examples
- [ ] Create comparison table (old vs new)

**Deliverables:**
- Complete documentation
- User migration guide
- Troubleshooting guide

---

## 7. Technical Specifications

### 7.1 New Dependencies

Add to `manifest.json`:
```json
{
  "requirements": [
    "pandas>=2.0.0",
    "pytz>=2023.3"
  ]
}
```

### 7.2 New Files

```
custom_components/metermate/
├── validation.py          # NEW: Validation framework
├── exceptions.py          # NEW: Custom exceptions
├── import_helper.py       # NEW: CSV import utilities
├── timezone_helper.py     # NEW: Timezone utilities
└── migrations/            # NEW: Migration scripts
    └── to_external_stats.py
```

### 7.3 Modified Files

```
custom_components/metermate/
├── __init__.py            # MODIFY: Add new services
├── data_manager.py        # MODIFY: Use new validators, external stats
├── services.py            # MODIFY: Use new exceptions
├── sensor.py              # MODIFY: Update state management
└── services.yaml          # MODIFY: Add new services
```

### 7.4 API Changes

**Breaking Changes:** None (backward compatible)

**New Services:**
- `metermate.import_from_csv` - Import readings from CSV
- `metermate.migrate_to_external_stats` - Migrate to new architecture
- `metermate.validate_reading` - Validate reading without adding

**Modified Services:**
- All services now return more detailed error messages
- All services validate timezone explicitly

### 7.5 Database Schema

**No database schema changes** - Uses Home Assistant's existing statistics tables via external statistics API.

---

## 8. Testing Requirements

### 8.1 Unit Tests

- [ ] Validation module (>95% coverage)
- [ ] Exception hierarchy (100% coverage)
- [ ] CSV import (>90% coverage)
- [ ] Timezone handling (>95% coverage)

### 8.2 Integration Tests

- [ ] External statistics creation
- [ ] Energy Dashboard integration
- [ ] CSV import end-to-end
- [ ] Migration script

### 8.3 User Acceptance Testing

- [ ] Non-technical user can import CSV
- [ ] Error messages are clear and actionable
- [ ] Energy Dashboard shows correct data
- [ ] Migration completes successfully

### 8.4 Performance Tests

- [ ] Import 10,000 readings < 30 seconds
- [ ] External statistics query < 1 second
- [ ] No memory leaks during bulk import

---

## 9. Documentation Requirements

### 9.1 User Documentation

1. **Getting Started Guide** (Update)
   - Add CSV import section
   - Add timezone configuration
   - Add troubleshooting

2. **Service Reference** (Update)
   - Document all new services
   - Add CSV format examples
   - Add timezone examples

3. **Migration Guide** (New)
   - How to migrate to external statistics
   - What changes for users
   - How to verify migration

4. **Troubleshooting Guide** (New)
   - Common errors and solutions
   - Timezone issues
   - CSV import issues

### 9.2 Developer Documentation

1. **Architecture Decision Record** (New)
   - Why external statistics
   - Trade-offs considered
   - Future considerations

2. **Code Patterns** (New)
   - Validation patterns
   - Error handling patterns
   - Testing patterns

3. **Contributing Guide** (Update)
   - How to add validators
   - How to add error types
   - Testing requirements

---

## 10. Success Metrics

### 10.1 Technical Metrics

- [ ] Test coverage > 90%
- [ ] No critical bugs for 2 weeks
- [ ] Import performance < 30s for 10k readings
- [ ] Zero data loss during migration

### 10.2 User Metrics

- [ ] 90% of users successfully migrate
- [ ] <5% support requests about errors
- [ ] Positive feedback on error messages
- [ ] CSV import used by >50% of users

### 10.3 Quality Metrics

- [ ] All validation documented
- [ ] All errors have solutions
- [ ] Example CSV files provided
- [ ] Video tutorials created

---

## 11. Risks and Mitigations

### 11.1 Migration Risk

**Risk:** Users lose data during migration to external statistics

**Mitigation:**
- Implement parallel tracking (both systems work)
- Create comprehensive migration script
- Add rollback capability
- Test with real user data
- Provide data backup instructions

### 11.2 Performance Risk

**Risk:** pandas dependency increases startup time

**Mitigation:**
- Import pandas only when needed (lazy import)
- Make CSV import optional
- Profile and optimize import code
- Consider alternative to pandas if needed

### 11.3 Compatibility Risk

**Risk:** External statistics don't work with Energy Dashboard

**Mitigation:**
- Test thoroughly before release
- Have fallback to internal statistics
- Document limitations clearly
- Get community feedback early

### 11.4 Complexity Risk

**Risk:** Added features make integration too complex

**Mitigation:**
- Keep core functionality simple
- Make advanced features optional
- Maintain clear documentation
- Provide migration path
- Get user feedback

---

## 12. Open Questions

1. **Pandas Dependency**
   - Is pandas size acceptable? (~50MB)
   - Alternative: Use csv module (slower but smaller)
   - Decision: TBD based on user feedback

2. **Migration Timeline**
   - How long to maintain internal statistics?
   - When to deprecate old approach?
   - Decision: Keep both for at least 6 months

3. **CSV Import Location**
   - Service-based or UI-based?
   - File picker in frontend?
   - Decision: Start with service, add UI later

4. **Timezone UI**
   - Add timezone picker to config flow?
   - Or just use HA's default?
   - Decision: Use HA default, allow override

---

## 13. Attribution and Licensing

### 13.1 Code Attribution

All adapted code must include attribution:

```python
"""
Module description.

Adaptations and modifications by MeterMate contributors.
"""
```

### 13.2 License Compatibility

- [ ] Ensure compatibility with MeterMate license
- [ ] Document any restrictions
- [ ] Add to ATTRIBUTION.md file

---

## 14. Future Considerations

### 14.1 Phase 2 Features (Future PRD)

- Export to CSV functionality
- Automatic bill parsing (OCR)
- Multi-tariff support
- Cost calculation
- Comparison reports

### 14.2 Integration Opportunities

- Work with Energy Dashboard team
- Collaborate with utility_meter integration
- Share patterns with HA community

### 14.3 Long-term Vision

MeterMate becomes the **reference implementation** for manual data entry in Home Assistant:
- Other integrations adopt our patterns
- Core HA adopts our validation framework
- Become part of default HA installation

---

## Appendix A: Code Examples

### Example 1: Using New Validation

```python
from custom_components.metermate.validation import (
    TimestampValidator,
    ValueValidator,
    ValidationError
)

async def add_reading(self, entity_id: str, reading: Reading):
    """Add reading with comprehensive validation."""
    try:
        # Validate timestamp
        TimestampValidator.validate_timezone_aware(reading.timestamp)
        TimestampValidator.validate_hour_boundary(reading.timestamp)
        TimestampValidator.validate_not_future(reading.timestamp)

        # Validate value
        reading.value = ValueValidator.validate_numeric(reading.value)
        ValueValidator.validate_positive(reading.value)

        # If we have previous reading, validate consumption
        if previous := await self.get_latest_reading(entity_id):
            consumption = ValueValidator.validate_consumption(
                previous.value,
                reading.value
            )
            reading.consumption = consumption

        # Add the reading
        await self._store_reading(entity_id, reading)

    except ValidationError as e:
        # Error already has solution
        raise
```

### Example 2: Using External Statistics

```python
async def _create_external_statistics(self, entity_id: str):
    """Create external statistics for historical data."""
    readings = await self.get_all_readings(entity_id)

    # External statistics format: domain:identifier
    stat_id = f"metermate:{entity_id.replace('sensor.', '')}"

    metadata = StatisticMetaData(
        has_mean=False,
        has_sum=True,
        name=entity_id.replace("sensor.", "").replace("_", " ").title(),
        source="metermate",  # Our integration name
        statistic_id=stat_id,  # External format
        unit_of_measurement=readings[0].unit if readings else "kWh",
    )

    statistics = []
    for reading in readings:
        # Align to hour boundary
        hour_ts = reading.timestamp.replace(minute=0, second=0, microsecond=0)

        statistics.append(
            StatisticData(
                start=hour_ts,
                state=reading.value,  # Current reading
                sum=reading.value,    # Cumulative total
            )
        )

    # Use Home Assistant's external statistics API
    async_add_external_statistics(self.hass, metadata, statistics)
```

### Example 3: CSV Import

```python
# User's CSV file: meter_readings.csv
"""
timestamp,value,unit,notes
2024-01-01 00:00,15432.5,kWh,January reading
2024-02-01 00:00,15650.2,kWh,February reading
2024-03-01 00:00,15890.1,kWh,March reading
"""

# Service call
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "meter_readings.csv"
  timezone: "America/Los_Angeles"

# Result
✅ Import completed successfully
   - Processed: 3 readings
   - Added: 3 new readings
   - Skipped: 0 duplicates
   - Errors: 0
   - Time taken: 0.3 seconds
```

---

## Appendix B: Error Message Examples

### Before and After Comparison

**Scenario: Duplicate Reading**

```
❌ BEFORE:
HomeAssistantError: Reading already exists for timestamp 2024-01-01 00:00:00

✅ AFTER:
ReadingExistsError: Reading already exists for 2024-01-01 00:00

💡 Solution: Use 'metermate.update_reading' to modify the existing reading,
or 'metermate.delete_reading' to remove it first, then add the new reading.

ℹ️  Details:
  - Existing value: 15432.5 kWh
  - Attempted value: 15450.0 kWh
  - Difference: +17.5 kWh
  - Reading ID: abc123-def456
```

**Scenario: Future Timestamp**

```
❌ BEFORE:
HomeAssistantError: Timestamp cannot be in the future

✅ AFTER:
InvalidTimestampError: Timestamp is in the future

💡 Solution: Use a past timestamp, or omit the timestamp parameter
to use the current time.

ℹ️  Details:
  - Provided: 2025-12-01 10:00:00
  - Current time: 2025-11-05 10:00:00
  - Difference: 26 days in the future
  - Suggestion: Did you mean 2024-12-01?
```

**Scenario: Invalid CSV**

```
❌ BEFORE:
HomeAssistantError: Invalid CSV format

✅ AFTER:
CSVImportError: Missing required column 'value' in CSV file

💡 Solution: Add a 'value' column to your CSV file. The file must contain
at least these columns: timestamp, value

ℹ️  Details:
  - File: meter_readings.csv
  - Found columns: date, reading, unit
  - Missing columns: timestamp, value
  - Suggestion: Rename 'date' to 'timestamp' and 'reading' to 'value'

Example correct format:
  timestamp,value,unit
  2024-01-01 00:00,15432.5,kWh
```

---

## Appendix C: Testing Scenarios

### Critical Test Cases

1. **Hour Boundary Validation**
   - ✅ Accept: 2024-01-01 10:00:00
   - ❌ Reject: 2024-01-01 10:30:00
   - ❌ Reject: 2024-01-01 10:00:01

2. **Timezone Handling**
   - ✅ Convert PST to UTC correctly
   - ✅ Handle DST transitions
   - ❌ Reject timezone-naive timestamps

3. **Consumption Calculation**
   - ✅ Normal: current > previous
   - ❌ Reject: current < previous (without rollover flag)
   - ✅ Handle: Meter rollover with flag

4. **CSV Import**
   - ✅ Import 10,000 readings
   - ✅ Handle duplicate timestamps
   - ✅ Handle mixed units
   - ❌ Reject invalid CSV format

5. **External Statistics**
   - ✅ Appear in Energy Dashboard
   - ✅ Historical data is correct
   - ✅ Statistics align to hour boundaries

---

## Approval and Sign-off

**Product Owner:** _____________________ Date: _______

**Technical Lead:** _____________________ Date: _______

**QA Lead:** _____________________ Date: _______

---

**End of Document**

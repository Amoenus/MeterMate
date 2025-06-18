# MeterMate Service Call Examples

This document demonstrates how users interact with the CRUD interface for manual utility data entry.

## Overview

MeterMate provides comprehensive service calls for managing your utility readings:

✅ Add cumulative meter readings (from physical meters)
✅ Add periodic consumption data (from utility bills)
✅ Bulk import multiple readings at once
✅ Update existing readings (corrections)
✅ Delete incorrect readings
✅ Query readings for specific time periods
✅ Recalculate statistics after changes

## Value Proposition

- **Full CRUD capability** for manual utility data
- **Seamless Energy Dashboard integration**
- **No complex template sensors needed**
- **User-friendly service interface**
- **Comprehensive data management**

## Integration with Home Assistant

- Works with automations and scripts
- Compatible with dashboard cards
- Supports notifications and reminders
- Maintains data integrity and audit trail

## Service Call Examples

### Example 1: Add a Cumulative Meter Reading

```yaml
service: metermate.add_reading
target:
  entity_id: sensor.electricity_meter
data:
  value: 15432.5
  timestamp: "2025-06-01T10:00:00"
  reading_type: "cumulative"
  unit: "kWh"
  notes: "Monthly meter reading"
```

### Example 2: Add a Periodic Utility Bill Reading

```yaml
service: metermate.add_reading
target:
  entity_id: sensor.gas_meter
data:
  value: 125.3
  timestamp: "2025-05-31T23:59:59"
  reading_type: "periodic"
  unit: "m³"
  notes: "May utility bill - 125.3 m³ consumed"
```

### Example 3: Bulk Import Multiple Readings

```yaml
service: metermate.bulk_import
target:
  entity_id: sensor.water_meter
data:
  readings:
    - timestamp: "2025-01-31T23:59:59"
      value: 234.1
      reading_type: "periodic"
      unit: "gal"
      notes: "January bill"
    - timestamp: "2025-02-28T23:59:59"
      value: 198.7
      reading_type: "periodic"
      unit: "gal"
      notes: "February bill"
    - timestamp: "2025-03-31T23:59:59"
      value: 276.4
      reading_type: "periodic"
      unit: "gal"
      notes: "March bill"
```

### Example 4: Update an Existing Meter Reading

```yaml
service: metermate.update_meter_reading
target:
  entity_id: sensor.electricity_meter
data:
  reading_id: "abc123-def456-ghi789"  # From previous add_reading response
  meter_reading: 15434.7  # Corrected meter reading value
  timestamp: "2025-06-01T10:00:00"
  unit: "kWh"
  notes: "Corrected monthly meter reading"
```

### Example 4b: Update an Existing Consumption Period

```yaml
service: metermate.update_consumption_period
target:
  entity_id: sensor.electricity_meter
data:
  reading_id: "def456-ghi789-jkl012"  # From previous add_consumption response
  consumption: 280.5  # Corrected consumption amount
  period_start: "2025-05-01T00:00:00"
  period_end: "2025-05-31T23:59:59"
  unit: "kWh"
  notes: "Corrected electricity bill for May 2025"
```

### Example 4c: Legacy Update Reading Service

```yaml
service: metermate.update_reading
target:
  entity_id: sensor.electricity_meter
data:
  reading_id: "abc123-def456-ghi789"  # From previous add_reading response
  meter_reading: 15434.7  # Corrected meter reading value
  timestamp: "2025-06-01T10:00:00"
  unit: "kWh"
  notes: "Corrected monthly meter reading"
```

### Example 5: Delete an Incorrect Reading

```yaml
service: metermate.delete_reading
target:
  entity_id: sensor.electricity_meter
data:
  reading_id: "abc123-def456-ghi789"
```

### Example 6: Get Readings for a Specific Period

```yaml
service: metermate.get_readings
target:
  entity_id: sensor.electricity_meter
data:
  start_date: "2025-01-01T00:00:00"
  end_date: "2025-06-30T23:59:59"
```

### Example 7: Recalculate Statistics

```yaml
service: metermate.recalculate_statistics
target:
  entity_id: sensor.electricity_meter
```

## Home Assistant Integration Examples

### Automation: Monthly Meter Reading Reminder

```yaml
automation:
  - alias: "Monthly Meter Reading Reminder"
    trigger:
      platform: time
      at: "09:00:00"
    condition:
      condition: template
      value_template: "{{ now().day == 1 }}"  # First day of month
    action:
      - service: notify.mobile_app
        data:
          title: "📊 Meter Reading Due"
          message: "Time for your monthly meter reading! Current reading: {{ states('sensor.electricity_meter') }}"
```

### Script: Quick Meter Reading Entry

```yaml
script:
  add_meter_reading:
    alias: "Add Meter Reading"
    fields:
      meter_value:
        description: "Current meter reading"
        example: "15432.5"
      reading_notes:
        description: "Optional notes"
        example: "End of month reading"
    sequence:
      - service: metermate.add_reading
        target:
          entity_id: sensor.electricity_meter
        data:
          value: "{{ meter_value }}"
          reading_type: "cumulative"
          unit: "kWh"
          notes: "{{ reading_notes | default('Manual reading') }}"
```

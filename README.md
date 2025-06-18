# MeterMate

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

# MeterMate

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

**A comprehensive data source for manual utility readings with full CRUD capabilities**

MeterMate is a Home Assistant custom integration that transforms manual utility data entry into a powerful, user-friendly experience. It provides full Create, Read, Update, Delete (CRUD) capabilities for managing utility meter readings and seamlessly integrates with Home Assistant's Energy Dashboard.

## 🎯 Value Proposition

MeterMate adds significant value by:

- **Full CRUD Interface**: Complete data management for all your utility readings
- **Dedicated Data Source**: Acts as a standalone data source specifically for manual utility data
- **Energy Dashboard Integration**: Seamlessly exposes data as if it were from smart meters
- **User-Friendly Management**: Intuitive service interface for all data operations
- **Data Integrity**: Maintains consistency and provides validation for all entries

## ✨ Features

### Core Capabilities
- **Complete Data Management**: Full CRUD operations (Create, Read, Update, Delete)
- **Multiple Data Entry Methods**: Cumulative meter readings and periodic consumption data
- **Bulk Operations**: Import multiple readings at once from spreadsheets or bills
- **Data Validation**: Comprehensive validation with helpful error messages
- **Audit Trail**: Track all changes with operation IDs and timestamps

### Integration Features
- **Energy Dashboard Ready**: Works directly with Home Assistant's Energy Dashboard
- **Service Interface**: Rich set of services for automation and scripting
- **Multiple Utilities**: Electricity, gas, water, and custom utility types
- **Flexible Units**: Support for kWh, m³, gallons, and custom units

## Installation

### HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Go to HACS > Integrations
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/Amoenus/metermate`
5. Select "Integration" as the category
6. Click "Add"
7. Find "MeterMate" in the list and click "Install"
8. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/Amoenus/metermate/releases)
2. Extract the files to your `custom_components` directory
3. The final directory structure should be: `custom_components/metermate/`
4. Restart Home Assistant

## Configuration

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "MeterMate"
4. Follow the configuration steps:
   - **Name**: Give your meter a friendly name (e.g., "Main Electricity Meter")
   - **Unit of Measurement**: Select the appropriate unit (kWh, m³, gal, etc.)
   - **Device Class**: Choose the device class (energy, gas, water, volume)
   - **Initial Reading** (optional): Enter your meter's current reading to start tracking from zero

## Usage

Once configured, MeterMate creates a sensor entity that you can use with the Energy Dashboard. To add readings, use the `metermate.add_reading` service:

### Service: `metermate.add_reading`

#### Parameters:
- `entity_id`: The MeterMate sensor entity
- `value`: The numeric value to add
- `mode`: Either "cumulative" (default) or "periodic"
- `timestamp` (optional): When the reading was taken (defaults to now)
- `start_date`/`end_date` (optional): Date range for periodic readings

### Examples

#### Adding a Cumulative Reading
```yaml
service: metermate.add_reading
data:
  entity_id: sensor.main_electricity_meter
  value: 15650  # Current meter reading
  mode: cumulative
```

#### Adding Periodic Consumption
```yaml
service: metermate.add_reading
data:
  entity_id: sensor.gas_meter
  value: 45.2  # Consumption for the period
  mode: periodic
  start_date: "2023-05-01"
  end_date: "2023-05-31"
```

## 🚀 Usage Examples

MeterMate provides a comprehensive set of services for managing your utility data:

### Add a Meter Reading

```yaml
# Add a cumulative meter reading (from physical meter)
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

### Add Utility Bill Data

```yaml
# Add periodic consumption data (from utility bill)
service: metermate.add_reading
target:
  entity_id: sensor.gas_meter
data:
  value: 125.3
  reading_type: "periodic"
  unit: "m³"
  notes: "May utility bill - 125.3 m³ consumed"
```

### Bulk Import Multiple Readings

```yaml
# Import multiple readings at once
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
```

### Update an Existing Reading

```yaml
# Update a meter reading
service: metermate.update_meter_reading
target:
  entity_id: sensor.electricity_meter
data:
  reading_id: "abc123-def456-ghi789"  # From add_reading response
  meter_reading: 15434.7  # Corrected meter reading value
  notes: "Corrected monthly meter reading"
```

```yaml
# Update a consumption period
service: metermate.update_consumption_period
target:
  entity_id: sensor.electricity_meter
data:
  reading_id: "def456-ghi789-jkl012"  # From add_consumption response
  consumption: 280.5  # Corrected consumption amount
  period_start: "2025-05-01T00:00:00"
  period_end: "2025-05-31T23:59:59"
  notes: "Corrected electricity bill for May 2025"
```

```yaml
# Legacy update (still supported)
service: metermate.update_reading
target:
  entity_id: sensor.electricity_meter
data:
  reading_id: "abc123-def456-ghi789"  # From add_reading response
  meter_reading: 15434.7  # Corrected meter reading value
  notes: "Corrected monthly meter reading"
```

### Delete an Incorrect Reading

```yaml
# Remove an incorrect reading
service: metermate.delete_reading
target:
  entity_id: sensor.electricity_meter
data:
  reading_id: "abc123-def456-ghi789"
```

### Query Your Data

```yaml
# Get readings for a specific period
service: metermate.get_readings
target:
  entity_id: sensor.electricity_meter
data:
  start_date: "2025-01-01T00:00:00"
  end_date: "2025-06-30T23:59:59"
```

### Automation Examples

```yaml
# Remind yourself to take monthly readings
automation:
  - alias: "Monthly Meter Reading Reminder"
    trigger:
      platform: time
      at: "09:00:00"
    condition:
      condition: template
      value_template: "{{ now().day == 1 }}"
    action:
      - service: notify.mobile_app
        data:
          title: "📊 Meter Reading Due"
          message: "Time for your monthly meter reading!"

# Script for quick meter reading entry
script:
  add_meter_reading:
    alias: "Add Meter Reading"
    fields:
      meter_value:
        description: "Current meter reading"
        example: "15432.5"
    sequence:
      - service: metermate.add_reading
        target:
          entity_id: sensor.electricity_meter
        data:
          value: "{{ meter_value }}"
          reading_type: "cumulative"
          unit: "kWh"
```

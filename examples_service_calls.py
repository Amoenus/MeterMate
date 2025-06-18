"""
Example service calls for MeterMate integration.

This demonstrates how users interact with the CRUD interface for manual utility data entry.
"""

# Example 1: Add a cumulative meter reading
service_call_add_cumulative = {
    "service": "metermate.add_reading",
    "target": {"entity_id": "sensor.electricity_meter"},
    "data": {
        "value": 15432.5,
        "timestamp": "2025-06-01T10:00:00",
        "reading_type": "cumulative",
        "unit": "kWh",
        "notes": "Monthly meter reading",
    },
}

# Example 2: Add a periodic utility bill reading
service_call_add_periodic = {
    "service": "metermate.add_reading",
    "target": {"entity_id": "sensor.gas_meter"},
    "data": {
        "value": 125.3,
        "timestamp": "2025-05-31T23:59:59",
        "reading_type": "periodic",
        "unit": "m³",
        "notes": "May utility bill - 125.3 m³ consumed",
    },
}

# Example 3: Bulk import multiple readings (from CSV or manual entry)
service_call_bulk_import = {
    "service": "metermate.bulk_import",
    "target": {"entity_id": "sensor.water_meter"},
    "data": {
        "readings": [
            {
                "timestamp": "2025-01-31T23:59:59",
                "value": 234.1,
                "reading_type": "periodic",
                "unit": "gal",
                "notes": "January bill",
            },
            {
                "timestamp": "2025-02-28T23:59:59",
                "value": 198.7,
                "reading_type": "periodic",
                "unit": "gal",
                "notes": "February bill",
            },
            {
                "timestamp": "2025-03-31T23:59:59",
                "value": 276.4,
                "reading_type": "periodic",
                "unit": "gal",
                "notes": "March bill",
            },
        ]
    },
}

# Example 4: Update an existing meter reading (fix typo or correction)
service_call_update_meter = {
    "service": "metermate.update_meter_reading",
    "target": {"entity_id": "sensor.electricity_meter"},
    "data": {
        "reading_id": "abc123-def456-ghi789",  # From previous add_reading response
        "meter_reading": 15434.7,  # Corrected meter reading value
        "timestamp": "2025-06-01T10:00:00",
        "unit": "kWh",
        "notes": "Corrected monthly meter reading",
    },
}

# Example 4b: Update an existing consumption period
service_call_update_consumption = {
    "service": "metermate.update_consumption_period",
    "target": {"entity_id": "sensor.electricity_meter"},
    "data": {
        "reading_id": "def456-ghi789-jkl012",  # From previous add_consumption response
        "consumption": 280.5,  # Corrected consumption amount
        "period_start": "2025-05-01T00:00:00",
        "period_end": "2025-05-31T23:59:59",
        "unit": "kWh",
        "notes": "Corrected electricity bill for May 2025",
    },
}

# Example 4c: Legacy update_reading service (still supported)
service_call_update_legacy = {
    "service": "metermate.update_reading",
    "target": {"entity_id": "sensor.electricity_meter"},
    "data": {
        "reading_id": "abc123-def456-ghi789",  # From previous add_reading response
        "meter_reading": 15434.7,  # Corrected meter reading value
        "timestamp": "2025-06-01T10:00:00",
        "unit": "kWh",
        "notes": "Corrected monthly meter reading",
    },
}

# Example 5: Delete an incorrect reading
service_call_delete = {
    "service": "metermate.delete_reading",
    "target": {"entity_id": "sensor.electricity_meter"},
    "data": {"reading_id": "abc123-def456-ghi789"},
}

# Example 6: Get readings for a specific period (for verification)
service_call_get_readings = {
    "service": "metermate.get_readings",
    "target": {"entity_id": "sensor.electricity_meter"},
    "data": {"start_date": "2025-01-01T00:00:00", "end_date": "2025-06-30T23:59:59"},
}

# Example 7: Recalculate statistics (after bulk changes)
service_call_recalculate = {
    "service": "metermate.recalculate_statistics",
    "target": {"entity_id": "sensor.electricity_meter"},
}

# Example YAML configuration for Home Assistant automations
yaml_automation_example = """
# Automation to remind user to take monthly meter reading
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

# Script to quickly add a meter reading via dashboard
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
"""

if __name__ == "__main__":
    print("📋 MeterMate Service Call Examples")
    print("=" * 50)
    print()
    print("These examples show how users interact with MeterMate's CRUD interface:")
    print()
    print("✅ Add cumulative meter readings (from physical meters)")
    print("✅ Add periodic consumption data (from utility bills)")
    print("✅ Bulk import multiple readings at once")
    print("✅ Update existing readings (corrections)")
    print("✅ Delete incorrect readings")
    print("✅ Query readings for specific time periods")
    print("✅ Recalculate statistics after changes")
    print()
    print("🎯 Value Proposition:")
    print("   • Full CRUD capability for manual utility data")
    print("   • Seamless Energy Dashboard integration")
    print("   • No complex template sensors needed")
    print("   • User-friendly service interface")
    print("   • Comprehensive data management")
    print()
    print("🏠 Integration with Home Assistant:")
    print("   • Works with automations and scripts")
    print("   • Compatible with dashboard cards")
    print("   • Supports notifications and reminders")
    print("   • Maintains data integrity and audit trail")

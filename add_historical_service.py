#!/usr/bin/env python3
"""Safe historical data addition using the MeterMate service."""

import json
import subprocess
from datetime import datetime

def add_historical_data_via_service():
    """Add historical data using Home Assistant service call."""
    
    print("Adding 203.0 kWh for June 15th using MeterMate service...")
    
    # Prepare the service call data
    service_data = {
        "entity_id": "sensor.manual_meter",
        "value": 203.0,
        "mode": "cumulative",
        "timestamp": "2025-06-15T18:00:00"
    }
    
    # Create the service call command
    cmd = [
        "curl", "-X", "POST",
        "http://localhost:8123/api/services/metermate/add_reading",
        "-H", "Content-Type: application/json",
        "-H", "Authorization: Bearer YOUR_TOKEN_HERE",
        "-d", json.dumps(service_data)
    ]
    
    print("Service call command:")
    print(" ".join(cmd))
    print("\nTo run this manually:")
    print("1. Get a Long-Lived Access Token from Home Assistant")
    print("2. Replace 'YOUR_TOKEN_HERE' with your actual token")
    print("3. Run the curl command")
    
    print("\nAlternatively, you can call this from Home Assistant's Developer Tools > Services:")
    print("Service: metermate.add_reading")
    print("Service Data:")
    print(json.dumps(service_data, indent=2))
    
    return True

def show_alternative_approach():
    """Show how to use the Developer Tools in Home Assistant."""
    
    print("\n" + "="*60)
    print("ALTERNATIVE: Use Home Assistant Developer Tools")
    print("="*60)
    
    print("\n1. Open Home Assistant in your browser")
    print("2. Go to Developer Tools > Services")
    print("3. Select service: metermate.add_reading")
    print("4. Use this YAML in the service data field:")
    
    yaml_data = """entity_id: sensor.manual_meter
value: 203.0
mode: cumulative
timestamp: "2025-06-15T18:00:00" """
    
    print("\n" + yaml_data)
    print("\n5. Click 'CALL SERVICE'")
    
    print("\nThis will add 203.0 kWh with the correct timestamp for June 15th!")

if __name__ == "__main__":
    add_historical_data_via_service()
    show_alternative_approach()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("✅ Our MeterMate integration now supports historical data!")
    print("✅ The database handler can insert data with correct timestamps")
    print("✅ Use the service to add your 203.0 kWh reading for June 15th")
    print("💡 After adding data, check the Energy Dashboard to see historical data")

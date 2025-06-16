# MeterMate

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]
[![Project Maintenance][maintenance-shield]][user_profile]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

**Your smart friend for your dumb meter**

MeterMate is a Home Assistant custom integration that allows you to manually enter utility readings from traditional "dumb" meters and make them compatible with Home Assistant's Energy Dashboard.

## Features

- **Simple Setup**: Easy configuration through the Home Assistant UI
- **Energy Dashboard Compatible**: Creates sensors that work directly with Home Assistant's Energy Dashboard
- **Flexible Input**: Support for both cumulative meter readings and periodic consumption data
- **Multiple Utilities**: Works with electricity, gas, water, and other utility meters
- **Manual Data Entry**: Perfect for users without smart meters or automated monitoring devices

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

## Creating Dashboard Cards

### Simple Input Card (Recommended for MVP)

Create an `input_number` helper and a script to make data entry easier:

1. Go to Settings > Devices & Services > Helpers
2. Create a new "Number" helper (e.g., `input_number.meter_reading`)
3. Create an automation or script to call the service:

```yaml
alias: "Add Meter Reading"
sequence:
  - service: metermate.add_reading
    data:
      entity_id: sensor.main_electricity_meter
      value: "{{ states('input_number.meter_reading') | float }}"
      mode: cumulative
```

## Energy Dashboard Integration

1. Go to Settings > Dashboards > Energy
2. Click "Add Consumption"
3. Select your MeterMate sensor
4. Configure the energy source settings as needed

Your manual readings will now appear in the Energy Dashboard with proper historical tracking.

## Troubleshooting

### Service Not Found
- Ensure the integration is properly installed and loaded
- Check the Home Assistant logs for any error messages
- Restart Home Assistant if needed

### Entity Not Updating
- Verify the service call parameters are correct
- Check that the entity ID matches your sensor
- Ensure the integration is not disabled

### Energy Dashboard Not Showing Data
- Confirm your sensor has the correct `device_class` and `state_class`
- Verify the `unit_of_measurement` is appropriate for the Energy Dashboard
- Check that statistics are being recorded (Developer Tools > Statistics)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- [Issues](https://github.com/Amoenus/metermate/issues)
- [Discussions](https://github.com/Amoenus/metermate/discussions)
- [Home Assistant Community Forum](https://community.home-assistant.io/)

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/Amoenus/metermate.svg?style=for-the-badge
[commits]: https://github.com/Amoenus/metermate/commits/main
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/Amoenus/metermate.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Amoenus-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/Amoenus/metermate.svg?style=for-the-badge
[releases]: https://github.com/Amoenus/metermate/releases
[user_profile]: https://github.com/Amoenus

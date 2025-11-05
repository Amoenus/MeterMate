# CSV Import Guide for MeterMate

## Overview

MeterMate now supports bulk importing of historical meter readings from CSV files. This feature is perfect for:

- Importing historical data from spreadsheets
- Migrating from other systems
- Loading monthly/yearly utility bills
- Bulk data entry

## CSV File Format

### Required Columns

Your CSV file **must** include these columns:

- `timestamp` - Date and time of the reading (ISO format recommended)
- `value` - The meter reading or consumption value

### Optional Columns

- `unit` - Unit of measurement (defaults to kWh)
- `notes` - Notes about the reading

### Example CSV File

```csv
timestamp,value,unit,notes
2024-01-01 00:00,15432.5,kWh,January reading
2024-02-01 00:00,15650.2,kWh,February reading
2024-03-01 00:00,15890.1,kWh,March reading
2024-04-01 00:00,16120.8,kWh,April reading
```

## Using the Import Service

### Basic Import

```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "meter_readings.csv"
```

### Advanced Import with Options

```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "/config/data/meter_readings.csv"
  delimiter: ","
  decimal: "."
  timezone: "America/Los_Angeles"
  date_format: "%Y-%m-%d %H:%M"
  dry_run: false
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `entity_id` | Yes | - | The meter sensor to import for |
| `file_path` | Yes | - | Path to CSV file (relative to /config or absolute) |
| `delimiter` | No | `,` | Column separator (`,`, `;`, or `\t`) |
| `decimal` | No | `.` | Decimal separator (`.` or `,`) |
| `timezone` | No | HA timezone | Timezone for timestamps |
| `date_format` | No | ISO format | strptime format string |
| `dry_run` | No | `false` | Validate without importing |

## File Path Options

The `file_path` parameter supports:

### Relative Paths (relative to /config directory)

```yaml
file_path: "meter_readings.csv"           # /config/meter_readings.csv
file_path: "data/meters.csv"              # /config/data/meters.csv
file_path: "backups/2024/january.csv"     # /config/backups/2024/january.csv
```

### Absolute Paths

```yaml
file_path: "/config/meter_readings.csv"
file_path: "/media/usb/data.csv"
```

## Date Format Examples

The `date_format` parameter uses Python's strptime format codes.

### Common Date Formats

| Format | Example | date_format Value |
|--------|---------|------------------|
| ISO 8601 | `2024-01-15 10:00:00` | (default) |
| US Format | `01/15/2024 10:00` | `%m/%d/%Y %H:%M` |
| European | `15.01.2024 10:00` | `%d.%m.%Y %H:%M` |
| Date only | `2024-01-15` | `%Y-%m-%d` |

### Format Code Reference

| Code | Meaning | Example |
|------|---------|---------|
| `%Y` | 4-digit year | 2024 |
| `%m` | Month (01-12) | 01 |
| `%d` | Day (01-31) | 15 |
| `%H` | Hour (00-23) | 10 |
| `%M` | Minute (00-59) | 30 |
| `%S` | Second (00-59) | 45 |

## Regional Formats

### European Format (semicolon delimiter, comma decimal)

```csv
timestamp;value;unit;notes
2024-01-01 00:00;15432,5;kWh;January
2024-02-01 00:00;15650,2;kWh;February
```

Import with:

```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "meter_readings.csv"
  delimiter: ";"
  decimal: ","
```

## Dry Run Mode

Use `dry_run: true` to validate your CSV without actually importing:

```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "meter_readings.csv"
  dry_run: true
```

This will:
- ✅ Validate CSV format
- ✅ Check for required columns
- ✅ Validate all timestamps and values
- ✅ Check for duplicates
- ❌ **NOT** actually import the data

Perfect for testing before a large import!

## Import Results

After import, check the Home Assistant logs for detailed results:

```
CSV import completed: 100 processed, 98 added, 2 skipped, 0 errors
```

- **Processed** - Total rows read from CSV
- **Added** - Successfully imported readings
- **Skipped** - Duplicate timestamps (already exist)
- **Errors** - Validation or import failures

## Troubleshooting

### Error: "File not found"

**Problem:** CSV file cannot be located

**Solution:**
- Check file path is correct
- Use relative path from /config: `"meter_readings.csv"`
- Or absolute path: `"/config/meter_readings.csv"`
- Verify file exists in File Editor or SSH

### Error: "Missing required columns"

**Problem:** CSV doesn't have `timestamp` and `value` columns

**Solution:**
- Add column headers as first row
- Ensure columns are named exactly: `timestamp` and `value`
- Check delimiter matches your file (comma vs semicolon)

### Error: "Too many parsing errors"

**Problem:** CSV format doesn't match settings

**Solution:**
- Check delimiter setting (`,`, `;`, or tab)
- Check decimal separator (`.` or `,`)
- Verify date format matches timestamps
- Try with `dry_run: true` first

### Error: "Timestamp must be on hour boundary"

**Problem:** Timestamps include minutes/seconds

**Solution:**
Home Assistant statistics require hourly boundaries. Round timestamps:

❌ Wrong:
```csv
2024-01-01 10:30:15,15432.5
```

✅ Correct:
```csv
2024-01-01 10:00:00,15432.5
```

### Warning: "Skipped duplicate"

**Info:** Reading already exists for that timestamp

This is normal and safe - MeterMate won't overwrite existing data. If you need to update a reading, use the update service instead.

## Best Practices

### 1. Start with Dry Run

Always test with `dry_run: true` first:

```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "test.csv"
  dry_run: true
```

### 2. Use Hour Boundaries

Round all timestamps to the hour (00 minutes, 00 seconds):

```csv
2024-01-01 00:00:00,15432.5  ✅
2024-01-01 10:30:15,15650.2  ❌
```

### 3. Sort by Timestamp

Sort your CSV by timestamp ascending (oldest first):

```csv
2024-01-01 00:00,15432.5
2024-02-01 00:00,15650.2
2024-03-01 00:00,15890.1
```

### 4. Validate Units

Ensure all readings use the same unit as your meter:

```yaml
entity_id: sensor.metermate_electricity  # Unit: kWh
# CSV should use kWh, not Wh or MWh
```

### 5. Add Notes

Use the notes column for context:

```csv
timestamp,value,unit,notes
2024-01-01 00:00,15432.5,kWh,Bill #123456 - January 2024
2024-02-01 00:00,15650.2,kWh,Bill #123789 - February 2024
```

### 6. Backup First

Before large imports, backup your data:

1. Use `metermate.get_readings` to export current data
2. Save the response
3. Perform import
4. Verify results

### 7. Import in Batches

For very large files (1000+ readings), consider splitting into smaller batches:

- `readings_2020.csv`
- `readings_2021.csv`
- `readings_2022.csv`

## Example Workflows

### Workflow 1: Monthly Bill Entry

You have 12 months of electricity bills.

**Step 1:** Create CSV from bills

```csv
timestamp,value,unit,notes
2024-01-01 00:00,15432.5,kWh,Bill Jan - $145.20
2024-02-01 00:00,15650.2,kWh,Bill Feb - $162.80
2024-03-01 00:00,15890.1,kWh,Bill Mar - $178.50
```

**Step 2:** Test with dry run

```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "2024_bills.csv"
  dry_run: true
```

**Step 3:** Import for real

```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "2024_bills.csv"
  dry_run: false
```

### Workflow 2: Migrating from Spreadsheet

You have years of data in Excel.

**Step 1:** Export from Excel
- File → Save As → CSV (Comma delimited)
- Ensure UTF-8 encoding

**Step 2:** Add headers if missing
```csv
timestamp,value,unit
2020-01-01 00:00,14200.5,kWh
2020-02-01 00:00,14380.2,kWh
...
```

**Step 3:** Import with timezone
```yaml
service: metermate.import_from_csv
data:
  entity_id: sensor.metermate_electricity
  file_path: "historical_data.csv"
  timezone: "America/New_York"
```

## Advanced: Creating CSV from Other Sources

### From Google Sheets

1. In Google Sheets: File → Download → Comma Separated Values (.csv)
2. Upload to Home Assistant via File Editor or SSH
3. Import using service call

### From Excel

1. In Excel: Save As → CSV (Comma delimited) (*.csv)
2. Ensure "Save as type" is CSV UTF-8
3. Upload and import

### From Smart Meter API

Many smart meters provide CSV exports. Common formats:

```python
import requests
import csv

# Fetch from API
response = requests.get("https://api.utility.com/readings")
data = response.json()

# Convert to MeterMate format
with open('readings.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['timestamp', 'value', 'unit', 'notes'])

    for reading in data['readings']:
        writer.writerow([
            reading['timestamp'],
            reading['value'],
            'kWh',
            f"Import from API - {reading['id']}"
        ])
```

## Support

If you encounter issues:

1. Check Home Assistant logs (Settings → System → Logs)
2. Try with `dry_run: true` for validation
3. Verify CSV format matches examples
4. Open an issue on GitHub with:
   - CSV sample (first few lines)
   - Service call configuration
   - Error messages from logs

## Example CSV Files

### Electricity Meter (Monthly Bills)

```csv
timestamp,value,unit,notes
2024-01-01 00:00,15432.5,kWh,January bill - $145.20
2024-02-01 00:00,15650.2,kWh,February bill - $162.80
2024-03-01 00:00,15890.1,kWh,March bill - $178.50
2024-04-01 00:00,16120.8,kWh,April bill - $185.90
2024-05-01 00:00,16380.5,kWh,May bill - $198.30
```

### Water Meter (Quarterly Readings)

```csv
timestamp,value,unit,notes
2024-01-01 00:00,1250.5,m³,Q1 2024
2024-04-01 00:00,1312.8,m³,Q2 2024
2024-07-01 00:00,1398.2,m³,Q3 2024
2024-10-01 00:00,1445.9,m³,Q4 2024
```

### Gas Meter (European Format)

```csv
timestamp;value;unit;notes
2024-01-01 00:00;2450,5;m³;January
2024-02-01 00:00;2498,3;m³;February
2024-03-01 00:00;2532,1;m³;March
```

---

**Next Steps:**
- [Validation Guide](VALIDATION.md) - Understanding validation rules
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Service Reference](SERVICES.md) - Complete service documentation

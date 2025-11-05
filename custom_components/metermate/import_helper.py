"""
Bulk import utilities for MeterMate.

Supports importing historical meter readings from CSV files with comprehensive
validation and error reporting.
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, UnitOfEnergy
from homeassistant.util import dt as dt_util

from .const import ATTR_NOTES
from .exceptions import CSVImportError, ValidationSummaryError
from .models import Reading
from .validation import ReadingValidator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data_manager import MeterMateDataManager

_LOGGER = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of a CSV import operation."""

    success: bool
    processed_count: int
    added_count: int
    skipped_count: int
    error_count: int
    errors: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    time_taken: float = 0.0

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "processed": self.processed_count,
            "added": self.added_count,
            "skipped": self.skipped_count,
            "errors": self.error_count,
            "error_details": self.errors,
            "warnings": self.warnings,
            "time_taken_seconds": round(self.time_taken, 2),
        }


class CSVImporter:
    """Import readings from CSV files."""

    # Required CSV columns
    REQUIRED_COLUMNS = {"timestamp", "value"}

    # Optional CSV columns
    OPTIONAL_COLUMNS = {"unit", "notes"}

    # All valid columns
    ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS

    def __init__(self, hass: HomeAssistant, data_manager: MeterMateDataManager) -> None:
        """Initialize CSV importer."""
        self.hass = hass
        self.data_manager = data_manager

    async def import_from_csv(
        self,
        entity_id: str,
        file_path: str,
        *,
        delimiter: str = ",",
        decimal: str = ".",
        timezone: str | None = None,
        date_format: str | None = None,
        dry_run: bool = False,
    ) -> ImportResult:
        """
        Import readings from a CSV file.

        Args:
            entity_id: The meter entity to import readings for
            file_path: Path to CSV file (relative to /config or absolute)
            delimiter: Column separator (default: comma)
            decimal: Decimal separator (default: period)
            timezone: Timezone for timestamps (default: HA timezone)
            date_format: strptime format for dates (default: ISO format)
            dry_run: If True, validate but don't import

        Returns:
            ImportResult with detailed import statistics

        Raises:
            CSVImportError: If file cannot be read or format is invalid

        """
        import time

        start_time = time.time()

        # Resolve file path
        full_path = self._resolve_file_path(file_path)

        # Validate file exists
        if not full_path.exists():
            raise CSVImportError(
                reason=f"File not found: {file_path}",
                details={
                    "provided_path": file_path,
                    "resolved_path": str(full_path),
                    "config_dir": str(self.hass.config.config_dir),
                },
            )

        # Use HA timezone if not specified
        if timezone is None:
            timezone = str(self.hass.config.time_zone)

        _LOGGER.info(
            "Starting CSV import for %s from %s (dry_run=%s)",
            entity_id,
            full_path,
            dry_run,
        )

        try:
            # Read and validate CSV
            readings = await self._read_csv(
                full_path,
                delimiter=delimiter,
                decimal=decimal,
                timezone=timezone,
                date_format=date_format,
            )

            # Import readings
            result = await self._import_readings(entity_id, readings, dry_run=dry_run)

            result.time_taken = time.time() - start_time

            _LOGGER.info(
                "CSV import completed: %d processed, %d added, %d skipped, %d errors",
                result.processed_count,
                result.added_count,
                result.skipped_count,
                result.error_count,
            )

            return result

        except CSVImportError:
            raise
        except Exception as e:
            _LOGGER.exception("Unexpected error during CSV import")
            raise CSVImportError(
                reason=f"Import failed: {e}",
                details={"error_type": type(e).__name__, "file": str(full_path)},
            ) from e

    def _resolve_file_path(self, file_path: str) -> Path:
        """Resolve file path relative to config directory."""
        path = Path(file_path)

        # If absolute path, use as-is
        if path.is_absolute():
            return path

        # Otherwise, resolve relative to config directory
        config_dir = Path(self.hass.config.config_dir)
        return config_dir / path

    async def _read_csv(
        self,
        file_path: Path,
        *,
        delimiter: str,
        decimal: str,
        timezone: str,
        date_format: str | None,
    ) -> list[Reading]:
        """
        Read and parse CSV file into Reading objects.

        Args:
            file_path: Path to CSV file
            delimiter: Column separator
            decimal: Decimal separator
            timezone: Timezone for timestamps
            date_format: Date format string

        Returns:
            List of Reading objects

        Raises:
            CSVImportError: If CSV format is invalid

        """
        readings = []
        errors = []

        try:
            with file_path.open(encoding="utf-8") as csvfile:
                # Detect dialect
                sample = csvfile.read(1024)
                csvfile.seek(0)

                # Try to detect delimiter if standard comma doesn't work
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=delimiter)
                except csv.Error:
                    dialect = csv.excel()
                    dialect.delimiter = delimiter

                reader = csv.DictReader(csvfile, dialect=dialect)

                # Validate headers
                if reader.fieldnames is None:
                    raise CSVImportError(
                        reason="CSV file has no headers",
                        details={
                            "file": str(file_path),
                            "expected_columns": list(self.REQUIRED_COLUMNS),
                        },
                    )

                headers = set(reader.fieldnames)
                missing_columns = self.REQUIRED_COLUMNS - headers

                if missing_columns:
                    raise CSVImportError(
                        reason=f"Missing required columns: {', '.join(missing_columns)}",
                        details={
                            "file": str(file_path),
                            "found_columns": list(headers),
                            "missing_columns": list(missing_columns),
                            "required_columns": list(self.REQUIRED_COLUMNS),
                        },
                    )

                # Parse rows
                for line_num, row in enumerate(
                    reader, start=2
                ):  # Start at 2 (header=1)
                    try:
                        reading = self._parse_row(
                            row,
                            timezone=timezone,
                            decimal=decimal,
                            date_format=date_format,
                        )
                        readings.append(reading)

                    except Exception as e:
                        errors.append(
                            {
                                "line": line_num,
                                "row": str(row),
                                "error": str(e),
                            }
                        )

                if errors:
                    # If more than 50% errors, likely format issue
                    if len(errors) > len(readings):
                        error_list = "\n".join(
                            f"  Line {e['line']}: {e['error']}" for e in errors[:5]
                        )
                        raise CSVImportError(
                            reason="Too many parsing errors. Check CSV format.",
                            details={
                                "file": str(file_path),
                                "total_rows": len(readings) + len(errors),
                                "error_count": len(errors),
                                "sample_errors": error_list,
                            },
                        )

                _LOGGER.info(
                    "Parsed %d readings from CSV (%d errors)",
                    len(readings),
                    len(errors),
                )

                return readings

        except CSVImportError:
            raise
        except UnicodeDecodeError as e:
            raise CSVImportError(
                reason="File encoding error. CSV must be UTF-8 encoded.",
                details={
                    "file": str(file_path),
                    "error": str(e),
                    "suggestion": "Save your CSV file as UTF-8 encoding",
                },
            ) from e
        except Exception as e:
            raise CSVImportError(
                reason=f"Failed to read CSV file: {e}",
                details={"file": str(file_path), "error_type": type(e).__name__},
            ) from e

    def _parse_row(
        self,
        row: dict[str, str],
        *,
        timezone: str,
        decimal: str,
        date_format: str | None,
    ) -> Reading:
        """
        Parse a CSV row into a Reading object.

        Args:
            row: CSV row as dictionary
            timezone: Timezone for timestamp
            decimal: Decimal separator
            date_format: Date format string

        Returns:
            Reading object

        Raises:
            ValueError: If row data is invalid

        """
        # Parse timestamp
        timestamp_str = row["timestamp"].strip()

        if date_format:
            # Use custom format
            timestamp = datetime.strptime(timestamp_str, date_format)
        else:
            # Try ISO format
            timestamp = datetime.fromisoformat(timestamp_str)

        # Make timezone-aware
        if timestamp.tzinfo is None:
            import zoneinfo

            tz = zoneinfo.ZoneInfo(timezone)
            timestamp = timestamp.replace(tzinfo=tz)

        # Convert to UTC
        timestamp = dt_util.as_utc(timestamp)

        # Parse value (handle decimal separator)
        value_str = row["value"].strip()
        if decimal != ".":
            value_str = value_str.replace(decimal, ".")

        value = float(value_str)

        # Get optional fields
        unit = row.get(ATTR_UNIT_OF_MEASUREMENT, UnitOfEnergy.KILO_WATT_HOUR).strip()
        notes = row.get(ATTR_NOTES, "").strip() or None

        # Create reading
        return Reading(
            timestamp=timestamp,
            value=value,
            unit=unit,
            notes=notes,
        )

    async def _import_readings(
        self, entity_id: str, readings: list[Reading], *, dry_run: bool
    ) -> ImportResult:
        """
        Import readings into the data manager.

        Args:
            entity_id: Entity to import for
            readings: List of readings to import
            dry_run: If True, only validate

        Returns:
            ImportResult with statistics

        """
        result = ImportResult(
            success=True,
            processed_count=0,
            added_count=0,
            skipped_count=0,
            error_count=0,
        )

        # Sort readings by timestamp
        readings.sort(key=lambda r: r.timestamp)

        # Get existing readings to check for duplicates
        existing_readings = await self.data_manager.get_all_readings(entity_id)
        existing_timestamps = {r.timestamp for r in existing_readings}

        validation_errors = []

        for reading in readings:
            result.processed_count += 1

            try:
                # Validate reading
                ReadingValidator.validate_reading(reading)

                # Check for duplicate
                if reading.timestamp in existing_timestamps:
                    result.skipped_count += 1
                    result.warnings.append(
                        f"Skipped duplicate: {reading.timestamp.isoformat()}"
                    )
                    continue

                # Import reading (if not dry run)
                if not dry_run:
                    import_result = await self.data_manager.add_reading(
                        entity_id, reading
                    )

                    if import_result.success:
                        result.added_count += 1
                        existing_timestamps.add(reading.timestamp)
                    else:
                        result.error_count += 1
                        result.errors.append(
                            {
                                "timestamp": reading.timestamp.isoformat(),
                                "error": import_result.message,
                            }
                        )
                else:
                    # Dry run - just count as added
                    result.added_count += 1

            except Exception as e:
                result.error_count += 1
                validation_errors.append(f"{reading.timestamp.isoformat()}: {e}")
                result.errors.append(
                    {
                        "timestamp": reading.timestamp.isoformat(),
                        "error": str(e),
                    }
                )

        # If too many errors, report as failed
        if result.error_count > result.added_count:
            result.success = False
            if validation_errors:
                raise ValidationSummaryError(errors=validation_errors[:10])

        return result


async def async_import_csv(
    hass: HomeAssistant,
    data_manager: MeterMateDataManager,
    entity_id: str,
    file_path: str,
    **options,
) -> ImportResult:
    """
    Convenience function for CSV import.

    Args:
        hass: Home Assistant instance
        data_manager: Data manager instance
        entity_id: Entity to import for
        file_path: Path to CSV file
        **options: Additional import options

    Returns:
        ImportResult

    """
    importer = CSVImporter(hass, data_manager)
    return await importer.import_from_csv(entity_id, file_path, **options)

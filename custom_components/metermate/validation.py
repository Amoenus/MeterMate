"""
Validation utilities for MeterMate.

These validation patterns ensure data consistency and compatibility with
Home Assistant's statistics system, particularly for Energy Dashboard integration.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.util import dt as dt_util

if TYPE_CHECKING:
    from .models import Reading

_LOGGER = logging.getLogger(__name__)


class ValidationError(Exception):
    """Base validation error with solution guidance."""

    def __init__(self, error: str, solution: str, details: dict | None = None) -> None:
        """Initialize validation error with solution."""
        self.error = error
        self.solution = solution
        self.details = details or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with solution."""
        msg = f"{self.error}\n\n💡 Solution: {self.solution}"
        if self.details:
            msg += "\n\n[i] Details:\n"
            for key, value in self.details.items():
                msg += f"  - {key}: {value}\n"
        return msg


class TimestampValidator:
    """Validate timestamps for statistics compatibility."""

    @staticmethod
    def validate_hour_boundary(timestamp: datetime) -> None:
        """
        Ensure timestamp is on hour boundary.

        Home Assistant's statistics system works with hourly data.
        All timestamps must be aligned to the hour (00 minutes, 00 seconds).

        Args:
            timestamp: The timestamp to validate

        Raises:
            ValidationError: If timestamp is not on hour boundary

        """
        if timestamp.minute != 0 or timestamp.second != 0 or timestamp.microsecond != 0:
            actual_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            expected_time = timestamp.replace(
                minute=0, second=0, microsecond=0
            ).strftime("%Y-%m-%d %H:00:00")

            raise ValidationError(
                error="Timestamp must be on hour boundary (00:00 minutes/seconds)",
                solution=(
                    "Round your timestamp to the nearest hour. "
                    "For example, use 10:00:00 instead of 10:30:15"
                ),
                details={
                    "provided": actual_time,
                    "expected_format": expected_time,
                    "minutes": timestamp.minute,
                    "seconds": timestamp.second,
                },
            )

    @staticmethod
    def validate_not_future(timestamp: datetime) -> None:
        """
        Ensure timestamp is not in the future.

        Historical data cannot be timestamped in the future.

        Args:
            timestamp: The timestamp to validate

        Raises:
            ValidationError: If timestamp is in the future

        """
        now_utc = dt_util.utcnow()
        timestamp_utc = dt_util.as_utc(timestamp)

        if timestamp_utc > now_utc:
            time_diff = timestamp_utc - now_utc
            days = time_diff.days
            hours = time_diff.seconds // 3600

            # Provide helpful suggestion for common mistake
            suggestion = "Check if you have the correct year. "
            if days > 365:
                past_year = timestamp.year - 1
                suggestion += f"Did you mean {past_year} instead of {timestamp.year}?"
            else:
                suggestion += "Omit the timestamp parameter to use the current time."

            raise ValidationError(
                error="Timestamp is in the future",
                solution=f"Use a past timestamp, or {suggestion}",
                details={
                    "provided": timestamp_utc.strftime("%Y-%m-%d %H:%M:%S %Z"),
                    "current_time": now_utc.strftime("%Y-%m-%d %H:%M:%S %Z"),
                    "difference": f"{days} days, {hours} hours in the future",
                },
            )

    @staticmethod
    def validate_timezone_aware(timestamp: datetime) -> datetime:
        """
        Ensure timestamp has timezone info.

        All timestamps must be timezone-aware for consistent storage
        and comparison across different locales.

        Args:
            timestamp: The timestamp to validate

        Returns:
            Timezone-aware timestamp (converted to UTC if needed)

        Raises:
            ValidationError: If timestamp is timezone-naive

        """
        if timestamp.tzinfo is None:
            raise ValidationError(
                error="Timestamp must include timezone information",
                solution=(
                    "Add timezone to your timestamp. If you're using Python, "
                    "use datetime.now(timezone.utc) or dt_util.utcnow(). "
                    "In YAML, use format: '2024-01-01 10:00:00+00:00'"
                ),
                details={
                    "provided": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "example_correct": "2024-01-01 10:00:00+00:00",
                },
            )

        # Convert to UTC for consistent storage
        return dt_util.as_utc(timestamp)

    @staticmethod
    def validate_timestamp(
        timestamp: datetime, *, allow_future: bool = False
    ) -> datetime:
        """
        Comprehensive timestamp validation.

        Validates timezone awareness, hour boundary alignment, and future dates.

        Args:
            timestamp: The timestamp to validate
            allow_future: If True, allows future timestamps (default: False)

        Returns:
            Validated and normalized timestamp in UTC

        Raises:
            ValidationError: If any validation fails

        """
        # 1. Ensure timezone-aware
        timestamp = TimestampValidator.validate_timezone_aware(timestamp)

        # 2. Check not in future (unless explicitly allowed)
        if not allow_future:
            TimestampValidator.validate_not_future(timestamp)

        # 3. Ensure hour boundary for statistics compatibility
        TimestampValidator.validate_hour_boundary(timestamp)

        return timestamp


class ValueValidator:
    """Validate reading values."""

    @staticmethod
    def validate_numeric(value: float | str) -> float:
        """
        Convert and validate numeric value.

        Args:
            value: The value to validate

        Returns:
            Float representation of the value

        Raises:
            ValidationError: If value cannot be converted to number

        """
        try:
            return float(value)
        except (ValueError, TypeError) as e:
            raise ValidationError(
                error=f"Value must be numeric, got: {type(value).__name__}",
                solution=(
                    "Provide a numeric value. For example: 15432.5, not '15432.5 kWh'"
                ),
                details={
                    "provided": str(value),
                    "type": type(value).__name__,
                },
            ) from e

    @staticmethod
    def validate_positive(value: float, *, allow_zero: bool = True) -> None:
        """
        Ensure value is positive.

        Args:
            value: The value to validate
            allow_zero: If True, allows zero values (default: True)

        Raises:
            ValidationError: If value is negative or zero (when not allowed)

        """
        if value < 0:
            raise ValidationError(
                error="Value cannot be negative",
                solution=(
                    "Provide a positive value. "
                    "Meter readings should always increase or stay the same."
                ),
                details={
                    "provided": value,
                },
            )

        if not allow_zero and value == 0:
            raise ValidationError(
                error="Value cannot be zero",
                solution="Provide a positive value greater than zero",
                details={
                    "provided": value,
                },
            )

    @staticmethod
    def validate_consumption(
        previous: float,
        current: float,
        *,
        allow_rollover: bool = False,
        meter_max: float | None = None,
    ) -> float:
        """
        Validate meter readings and calculate consumption.

        Ensures current reading is greater than or equal to previous reading,
        unless rollover is allowed.

        Args:
            previous: Previous meter reading
            current: Current meter reading
            allow_rollover: Allow meter rollover (e.g., 9999 -> 0001)
            meter_max: Maximum meter value before rollover (required if allow_rollover)

        Returns:
            Calculated consumption

        Raises:
            ValidationError: If consumption calculation fails validation

        """
        if current < previous:
            if allow_rollover and meter_max is not None:
                # Calculate consumption with rollover
                # e.g., previous=9999, current=10, max=10000
                # consumption = (10000 - 9999) + 10 = 11
                consumption = (meter_max - previous) + current
                _LOGGER.info(
                    "Meter rollover detected: %s -> %s (max: %s), consumption: %s",
                    previous,
                    current,
                    meter_max,
                    consumption,
                )
                return consumption
            # This is an error - meter should not go backwards
            raise ValidationError(
                error="Current reading is less than previous reading",
                solution=(
                    "Check your reading values. Meter readings should always increase. "
                    "If your meter rolled over (e.g., 9999 -> 0001), "
                    "use the allow_rollover parameter with meter_max value."
                ),
                details={
                    "previous": previous,
                    "current": current,
                    "difference": current - previous,
                },
            )

        return current - previous


class ReadingValidator:
    """Complete reading validation."""

    @staticmethod
    def validate_reading(reading: Reading, *, allow_future: bool = False) -> None:
        """
        Comprehensive validation of a reading.

        Validates all aspects of a reading: timestamp, value, and unit.

        Args:
            reading: The reading to validate
            allow_future: If True, allows future timestamps (default: False)

        Raises:
            ValidationError: If any validation fails

        """
        # Validate timestamp
        reading.timestamp = TimestampValidator.validate_timestamp(
            reading.timestamp, allow_future=allow_future
        )

        # Validate value
        reading.value = ValueValidator.validate_numeric(reading.value)
        ValueValidator.validate_positive(reading.value, allow_zero=True)

        # Validate unit (basic check - ensure it's not empty)
        if not reading.unit or not isinstance(reading.unit, str):
            raise ValidationError(
                error="Unit of measurement is required",
                solution=(
                    "Provide a valid unit. "
                    "Common units: kWh (electricity), m³ (gas/water), gal (gallons)"
                ),
                details={
                    "provided": reading.unit,
                },
            )

    @staticmethod
    def validate_reading_with_previous(
        reading: Reading,
        previous_reading: Reading | None,
        *,
        allow_future: bool = False,
        allow_rollover: bool = False,
        meter_max: float | None = None,
    ) -> float | None:
        """
        Validate reading in context of previous reading.

        Performs full validation and calculates consumption if previous reading exists.

        Args:
            reading: The reading to validate
            previous_reading: The previous reading (if any)
            allow_future: If True, allows future timestamps
            allow_rollover: Allow meter rollover
            meter_max: Maximum meter value before rollover

        Returns:
            Calculated consumption if previous reading exists, None otherwise

        Raises:
            ValidationError: If any validation fails

        """
        # Basic validation
        ReadingValidator.validate_reading(reading, allow_future=allow_future)

        # If we have a previous reading, validate consumption
        if previous_reading is not None:
            # Validate units match
            if reading.unit != previous_reading.unit:
                raise ValidationError(
                    error="Unit mismatch between readings",
                    solution=(
                        "Ensure all readings for the same meter use the same unit. "
                        "Convert values to match the meter's configured unit."
                    ),
                    details={
                        "previous_unit": previous_reading.unit,
                        "current_unit": reading.unit,
                    },
                )

            # Validate and calculate consumption
            consumption = ValueValidator.validate_consumption(
                previous_reading.value,
                reading.value,
                allow_rollover=allow_rollover,
                meter_max=meter_max,
            )

            return consumption

        return None

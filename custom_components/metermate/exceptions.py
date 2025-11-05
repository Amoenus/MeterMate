"""
Custom exceptions with solution guidance for MeterMate.

All errors provide actionable solutions to help users quickly resolve issues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import HomeAssistantError

if TYPE_CHECKING:
    from datetime import datetime


class MeterMateError(HomeAssistantError):
    """Base error with solution guidance."""

    def __init__(
        self, error: str, solution: str, details: dict[str, Any] | None = None
    ) -> None:
        """Initialize error with solution guidance."""
        self.error_message = error
        self.solution = solution
        self.details = details or {}
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format error message with solution and details."""
        msg = f"{self.error_message}\n\n💡 Solution: {self.solution}"

        if self.details:
            msg += "\n\n[i] Details:"
            for key, value in self.details.items():
                msg += f"\n  - {key}: {value}"

        return msg


class ReadingExistsError(MeterMateError):
    """Reading already exists for the given timestamp."""

    def __init__(
        self, timestamp: datetime, existing_value: float, attempted_value: float
    ) -> None:
        """Initialize reading exists error."""
        time_str = timestamp.strftime("%Y-%m-%d %H:%M")
        difference = attempted_value - existing_value

        super().__init__(
            error=f"Reading already exists for {time_str}",
            solution=(
                "Use 'metermate.update_reading' to modify the existing reading, "
                "or 'metermate.delete_reading' to remove it first"
            ),
            details={
                "timestamp": timestamp.isoformat(),
                "existing_value": f"{existing_value}",
                "attempted_value": f"{attempted_value}",
                "difference": f"{difference:+.2f}",
            },
        )


class ReadingNotFoundError(MeterMateError):
    """Reading with given ID was not found."""

    def __init__(self, reading_id: str, entity_id: str) -> None:
        """Initialize reading not found error."""
        super().__init__(
            error=f"Reading '{reading_id}' not found for entity '{entity_id}'",
            solution=(
                "Verify the reading ID is correct. "
                "Use 'metermate.get_readings' to list all available readings."
            ),
            details={
                "reading_id": reading_id,
                "entity_id": entity_id,
            },
        )


class InvalidTimestampError(MeterMateError):
    """Timestamp validation failed."""

    def __init__(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Initialize invalid timestamp error."""
        solution = "Ensure your timestamp is properly formatted and valid"

        if "future" in reason.lower():
            solution = (
                "Use a past timestamp, or omit the timestamp parameter "
                "to use the current time"
            )
        elif "hour" in reason.lower() or "boundary" in reason.lower():
            solution = (
                "Round your timestamp to the nearest hour "
                "(e.g., use 10:00:00 instead of 10:30:15)"
            )
        elif "timezone" in reason.lower():
            solution = (
                "Add timezone information to your timestamp. "
                "Format: '2024-01-01 10:00:00+00:00'"
            )

        super().__init__(error=reason, solution=solution, details=details)


class InvalidValueError(MeterMateError):
    """Value validation failed."""

    def __init__(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Initialize invalid value error."""
        solution = "Provide a valid numeric value"

        if "negative" in reason.lower():
            solution = (
                "Meter readings must be positive. "
                "Check if you entered the value correctly."
            )
        elif "zero" in reason.lower():
            solution = "Provide a value greater than zero"

        super().__init__(error=reason, solution=solution, details=details)


class ConsumptionError(MeterMateError):
    """Consumption calculation or validation error."""

    def __init__(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Initialize consumption error."""
        solution = "Verify your meter reading values are correct"

        if "less than" in reason.lower() or "backwards" in reason.lower():
            solution = (
                "Current reading must be greater than or equal to previous reading. "
                "Meter values should increase over time. "
                "If your meter rolled over (9999 -> 0001), "
                "contact support for rollover handling."
            )

        super().__init__(error=reason, solution=solution, details=details)


class UnitMismatchError(MeterMateError):
    """Unit of measurement mismatch between readings."""

    def __init__(self, previous_unit: str, current_unit: str, entity_id: str) -> None:
        """Initialize unit mismatch error."""
        super().__init__(
            error="Unit of measurement mismatch",
            solution=(
                f"All readings for '{entity_id}' must use the same unit. "
                f"Convert your reading to '{previous_unit}' or reconfigure the meter."
            ),
            details={
                "entity_id": entity_id,
                "previous_unit": previous_unit,
                "current_unit": current_unit,
            },
        )


class CSVImportError(MeterMateError):
    """CSV import operation failed."""

    def __init__(self, reason: str, details: dict[str, Any] | None = None) -> None:
        """Initialize CSV import error."""
        solution = "Check your CSV file format and try again"

        if "column" in reason.lower():
            solution = (
                "Ensure your CSV has these columns: timestamp, value. "
                "Optional columns: unit, notes"
            )
        elif "format" in reason.lower():
            solution = (
                "Use standard CSV format with comma-separated values. "
                "Example:\n"
                "timestamp,value,unit\n"
                "2024-01-01 00:00,15432.5,kWh"
            )

        super().__init__(error=reason, solution=solution, details=details)


class DatabaseError(MeterMateError):
    """Database operation failed."""

    def __init__(self, operation: str, details: dict[str, Any] | None = None) -> None:
        """Initialize database error."""
        super().__init__(
            error=f"Database operation failed: {operation}",
            solution=(
                "Check Home Assistant logs for more details. "
                "Ensure the recorder integration is working properly."
            ),
            details=details,
        )


class ValidationSummaryError(MeterMateError):
    """Multiple validation errors occurred."""

    def __init__(self, errors: list[str]) -> None:
        """Initialize validation summary error."""
        error_count = len(errors)
        error_list = "\n  • ".join(errors)

        super().__init__(
            error=f"{error_count} validation error(s) found",
            solution="Fix the following issues and try again",
            details={"errors": f"\n  • {error_list}"},
        )

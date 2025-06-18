"""Data models for MeterMate integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from homeassistant.util import dt as dt_util


@dataclass
class Reading:
    """Represents a utility meter reading."""

    timestamp: datetime
    value: float
    unit: str = "kWh"
    notes: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=dt_util.utcnow)
    updated_at: datetime | None = None
    # New fields for period support
    period_start: datetime | None = None
    period_end: datetime | None = None
    consumption: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert reading to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "unit": self.unit,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "period_start": (
                self.period_start.isoformat() if self.period_start else None
            ),
            "period_end": (self.period_end.isoformat() if self.period_end else None),
            "consumption": self.consumption,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Reading:
        """Create reading from dictionary."""
        return cls(
            id=data["id"],
            timestamp=dt_util.as_utc(datetime.fromisoformat(data["timestamp"])),
            value=data["value"],
            unit=data.get("unit", "kWh"),
            notes=data.get("notes"),
            created_at=dt_util.as_utc(datetime.fromisoformat(data["created_at"])),
            updated_at=(
                dt_util.as_utc(datetime.fromisoformat(data["updated_at"]))
                if data.get("updated_at")
                else None
            ),
            period_start=(
                dt_util.as_utc(datetime.fromisoformat(data["period_start"]))
                if data.get("period_start")
                else None
            ),
            period_end=(
                dt_util.as_utc(datetime.fromisoformat(data["period_end"]))
                if data.get("period_end")
                else None
            ),
            consumption=data.get("consumption"),
        )


@dataclass
class OperationResult:
    """Result of a data operation."""

    success: bool
    message: str
    operation_id: str = field(default_factory=lambda: str(uuid4()))
    data: dict[str, Any] | None = None


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class BulkOperationResult:
    """Result of a bulk operation."""

    success_count: int
    error_count: int
    errors: list[dict[str, Any]] = field(default_factory=list)
    operation_id: str = field(default_factory=lambda: str(uuid4()))
    reading_ids: list[str] = field(default_factory=list)

"""Data models for MeterMate integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from homeassistant.util import dt as dt_util


# Dataclass models for business logic
class ReadingType(Enum):
    """Type of meter reading."""

    CUMULATIVE = "cumulative"
    PERIODIC = "periodic"


@dataclass
class Reading:
    """Represents a utility meter reading."""

    timestamp: datetime
    value: float
    reading_type: ReadingType = ReadingType.CUMULATIVE
    unit: str = "kWh"
    notes: str | None = None
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=dt_util.utcnow)
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert reading to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "reading_type": self.reading_type.value,
            "unit": self.unit,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Reading:
        """Create reading from dictionary."""
        return cls(
            id=data["id"],
            timestamp=dt_util.as_utc(datetime.fromisoformat(data["timestamp"])),
            value=data["value"],
            reading_type=ReadingType(data["reading_type"]),
            unit=data.get("unit", "kWh"),
            notes=data.get("notes"),
            created_at=dt_util.as_utc(datetime.fromisoformat(data["created_at"])),
            updated_at=(
                dt_util.as_utc(datetime.fromisoformat(data["updated_at"]))
                if data.get("updated_at")
                else None
            ),
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

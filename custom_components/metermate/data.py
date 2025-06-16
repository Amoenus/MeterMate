"""Custom types for MeterMate."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry


type MeterMateConfigEntry = ConfigEntry[None]

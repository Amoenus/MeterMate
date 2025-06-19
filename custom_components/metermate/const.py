"""Constants for MeterMate."""

from __future__ import annotations

from logging import Logger, getLogger
from typing import Final

LOGGER: Final[Logger] = getLogger(__package__)

ATTR_INTEGRATION_NAME: Final[str] = "metermate"

# Service parameters (alphabetical order)
ATTR_END_DATE: Final[str] = "end_date"
ATTR_ENTITY_ID: Final[str] = "entity_id"
ATTR_MODE: Final[str] = "mode"
ATTR_START_DATE: Final[str] = "start_date"
ATTR_TIMESTAMP: Final[str] = "timestamp"
ATTR_VALUE: Final[str] = "value"
ATTR_NOTES: Final[str] = "notes"

# Configuration (alphabetical order)
CONF_INITIAL_READING: Final[str] = "initial_reading"

# Default values
DEFAULT_NAME: Final[str] = "Manual Meter"

# Reading modes (alphabetical order)
MODE_CUMULATIVE: Final[str] = "cumulative"
MODE_PERIODIC: Final[str] = "periodic"

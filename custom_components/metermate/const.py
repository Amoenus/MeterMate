"""Constants for MeterMate."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "metermate"

# Service parameters (alphabetical order)
ATTR_END_DATE = "end_date"
ATTR_ENTITY_ID = "entity_id"
ATTR_MODE = "mode"
ATTR_START_DATE = "start_date"
ATTR_TIMESTAMP = "timestamp"
ATTR_VALUE = "value"

# Configuration (alphabetical order)
CONF_DEVICE_CLASS = "device_class"
CONF_INITIAL_READING = "initial_reading"

# Default values
DEFAULT_NAME = "Manual Meter"

# Reading modes (alphabetical order)
MODE_CUMULATIVE = "cumulative"
MODE_PERIODIC = "periodic"

# Service names
SERVICE_ADD_READING = "add_reading"

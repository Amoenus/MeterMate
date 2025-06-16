"""Constants for MeterMate."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "metermate"

# Configuration
CONF_INITIAL_READING = "initial_reading"
CONF_DEVICE_CLASS = "device_class"

# Service names
SERVICE_ADD_READING = "add_reading"

# Service parameters
ATTR_ENTITY_ID = "entity_id"
ATTR_VALUE = "value"
ATTR_MODE = "mode"
ATTR_TIMESTAMP = "timestamp"
ATTR_START_DATE = "start_date"
ATTR_END_DATE = "end_date"

# Reading modes
MODE_CUMULATIVE = "cumulative"
MODE_PERIODIC = "periodic"

# Default values
DEFAULT_NAME = "Manual Meter"

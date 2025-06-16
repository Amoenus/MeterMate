"""Database operations for MeterMate integration."""

from __future__ import annotations

import sqlite3
import time
from typing import TYPE_CHECKING

from homeassistant.helpers.recorder import get_instance
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from datetime import datetime

    from homeassistant.core import HomeAssistant

# Constants
SHORT_TERM_STATISTICS_DAYS = 10


class HistoricalDataHandler:
    """Handle historical data insertion into Home Assistant database."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the handler."""
        self.hass = hass
        self.recorder = get_instance(hass)

    def _get_database_path(self) -> str | None:
        """Get the path to the Home Assistant database."""
        if not self.recorder or not self.recorder.db_url:
            LOGGER.error("Cannot access recorder database")
            return None

        # Extract SQLite database path from URL
        if self.recorder.db_url.startswith("sqlite:///"):
            return self.recorder.db_url[10:]  # Remove 'sqlite:///' prefix

        LOGGER.error("Only SQLite databases are supported for historical data import")
        return None

    def _get_or_create_metadata_id(
        self, conn: sqlite3.Connection, statistic_id: str, unit: str, name: str
    ) -> int | None:
        """Get or create metadata entry and return its ID."""
        try:
            # Check if metadata exists
            cursor = conn.execute(
                "SELECT id FROM statistics_meta WHERE statistic_id = ?",
                (statistic_id,),
            )
            result = cursor.fetchone()

            if result:
                return result[0]

            # Create new metadata entry
            cursor = conn.execute(
                """INSERT INTO statistics_meta
                   (statistic_id, source, unit_of_measurement,
                    has_mean, has_sum, name)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (statistic_id, DOMAIN, unit, False, True, name),
            )
            return cursor.lastrowid  # noqa: TRY300

        except sqlite3.Error as e:
            LOGGER.error("Error managing statistics metadata: %s", e)
            return None

    def _timestamp_exists(
        self, conn: sqlite3.Connection, metadata_id: int, timestamp: float
    ) -> bool:
        """Check if a statistic already exists for the given timestamp."""
        try:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM statistics "
                "WHERE metadata_id = ? AND start_ts = ?",
                (metadata_id, timestamp),
            )
            return cursor.fetchone()[0] > 0
        except sqlite3.Error as e:
            LOGGER.error("Error checking timestamp existence: %s", e)
            return True  # Assume exists to prevent duplicates

    def add_historical_statistic(
        self,
        entity_id: str,
        timestamp: datetime,
        value: float,
        unit: str,
        name: str,
    ) -> bool:
        """Add a historical statistic directly to the database."""
        db_path = self._get_database_path()
        if not db_path:
            return False

        # Convert timestamp to Unix epoch
        unix_timestamp = timestamp.timestamp()

        # Create statistic_id from entity_id
        statistic_id = entity_id.replace("sensor.", f"{DOMAIN}:")

        conn = None
        try:
            # Connect to database
            conn = sqlite3.connect(db_path)
            conn.execute("BEGIN TRANSACTION")

            # Get or create metadata
            metadata_id = self._get_or_create_metadata_id(
                conn, statistic_id, unit, name
            )

            if not metadata_id:
                conn.rollback()
                return False

            # Check if data already exists for this timestamp
            if self._timestamp_exists(conn, metadata_id, unix_timestamp):
                LOGGER.warning(
                    "Statistic already exists for %s at %s, skipping",
                    entity_id,
                    timestamp,
                )
                conn.rollback()
                return False

            # Insert the statistic
            current_ts = time.time()
            conn.execute(
                """INSERT INTO statistics
                   (metadata_id, start_ts, state, sum, created_ts)
                   VALUES (?, ?, ?, ?, ?)""",
                (metadata_id, unix_timestamp, value, value, current_ts),
            )

            # Also insert into short-term statistics if recent
            days_ago = (dt_util.now().timestamp() - unix_timestamp) / (24 * 3600)
            if days_ago <= SHORT_TERM_STATISTICS_DAYS:
                # Check if statistics_short_term table exists
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='statistics_short_term'"
                )
                if cursor.fetchone():
                    conn.execute(
                        """INSERT OR IGNORE INTO statistics_short_term
                           (metadata_id, start_ts, state, sum, created_ts)
                           VALUES (?, ?, ?, ?, ?)""",
                        (metadata_id, unix_timestamp, value, value, current_ts),
                    )

            conn.commit()

            LOGGER.info(
                "Successfully added historical statistic for %s: %s at %s",
                entity_id,
                value,
                timestamp,
            )
            return True

        except sqlite3.Error as e:
            LOGGER.error(
                "Database error adding historical statistic for %s: %s", entity_id, e
            )
            if conn:
                conn.rollback()
            return False

        except (ValueError, TypeError, AttributeError) as e:
            LOGGER.error(
                "Data error adding historical statistic for %s: %s", entity_id, e
            )
            if conn:
                conn.rollback()
            return False

        finally:
            if conn:
                conn.close()

    def get_latest_statistic(self, entity_id: str) -> tuple[datetime, float] | None:
        """Get the latest statistic for an entity."""
        db_path = self._get_database_path()
        if not db_path:
            return None

        statistic_id = entity_id.replace("sensor.", f"{DOMAIN}:")

        try:
            conn = sqlite3.connect(db_path)

            cursor = conn.execute(
                """SELECT s.start_ts, s.sum
                   FROM statistics s
                   JOIN statistics_meta m ON s.metadata_id = m.id
                   WHERE m.statistic_id = ?
                   ORDER BY s.start_ts DESC
                   LIMIT 1""",
                (statistic_id,),
            )

            result = cursor.fetchone()
            conn.close()

            if result:
                timestamp = dt_util.utc_from_timestamp(result[0])
                return timestamp, result[1]

            return None

        except sqlite3.Error as e:
            LOGGER.error("Error getting latest statistic for %s: %s", entity_id, e)
            return None

    def validate_database_access(self) -> bool:
        """Validate that we can access the database."""
        db_path = self._get_database_path()
        if not db_path:
            return False

        try:
            conn = sqlite3.connect(db_path)

            # Check for required tables
            required_tables = ["statistics_meta", "statistics"]
            for table in required_tables:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                if not cursor.fetchone():
                    LOGGER.error("Required table %s not found in database", table)
                    conn.close()
                    return False

            conn.close()
            LOGGER.info("Database access validation successful")
            return True

        except sqlite3.Error as e:
            LOGGER.error("Database validation failed: %s", e)
            return False

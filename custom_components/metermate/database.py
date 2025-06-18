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
# Threshold for considering values as "same" (0.001)
VALUE_DIFFERENCE_THRESHOLD = 0.001
# Time threshold for considering readings as too close (1 hour in seconds)
TIME_DIFFERENCE_THRESHOLD = 3600


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
        self,
        conn: sqlite3.Connection,
        statistic_id: str,
        unit: str,
        name: str,
        source: str = DOMAIN,
    ) -> int | None:
        """Get or create metadata entry and return its ID."""
        try:
            # Check if metadata exists
            cursor = conn.execute(
                "SELECT id FROM statistics_meta WHERE statistic_id = ? AND source = ?",
                (statistic_id, source),
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
                (statistic_id, source, unit, False, True, name),
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

        # For historical data, use the original entity_id to integrate
        # with Home Assistant's recorder statistics
        # This ensures historical data appears in the Energy Dashboard
        statistic_id = entity_id

        conn = None
        try:
            # Connect to database
            conn = sqlite3.connect(db_path)
            conn.execute("BEGIN TRANSACTION")

            # Get or create metadata - use 'recorder' as source
            # to match Home Assistant's native statistics
            metadata_id = self._get_or_create_metadata_id(
                conn, statistic_id, unit, name, source="recorder"
            )

            if not metadata_id:
                conn.rollback()
                return False

            # Check if data already exists for this timestamp
            exists = self._timestamp_exists(conn, metadata_id, unix_timestamp)
            if exists:
                LOGGER.info(
                    "Statistic already exists for %s at %s, updating with new value %s",
                    entity_id,
                    timestamp,
                    value,
                )
                # Update existing statistic
                current_ts = time.time()
                conn.execute(
                    """UPDATE statistics
                       SET state = ?, sum = ?, created_ts = ?
                       WHERE metadata_id = ? AND start_ts = ?""",
                    (value, value, current_ts, metadata_id, unix_timestamp),
                )
            else:
                # Insert new statistic
                current_ts = time.time()
                conn.execute(
                    """INSERT INTO statistics
                       (metadata_id, start_ts, state, sum, created_ts)
                       VALUES (?, ?, ?, ?, ?)""",
                    (metadata_id, unix_timestamp, value, value, current_ts),
                )

            # Also insert/update short-term statistics if recent
            days_ago = (dt_util.now().timestamp() - unix_timestamp) / (24 * 3600)
            if days_ago <= SHORT_TERM_STATISTICS_DAYS:
                # Check if statistics_short_term table exists
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='statistics_short_term'"
                )
                if cursor.fetchone():
                    # Use INSERT OR REPLACE for short-term statistics
                    conn.execute(
                        """INSERT OR REPLACE INTO statistics_short_term
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

    def add_historical_state(
        self,
        entity_id: str,
        timestamp: datetime,
        value: float,
        unit: str,
        attributes: dict | None = None,
        *,
        force_add: bool = False,
    ) -> bool:
        """Add a historical state, but only if it represents a significant change."""
        db_path = self._get_database_path()
        if not db_path:
            return False

        # Convert timestamp to Unix epoch
        unix_timestamp = timestamp.timestamp()

        # Prepare attributes
        if attributes is None:
            attributes = {
                "unit_of_measurement": unit,
                "device_class": "energy",
                "state_class": "total_increasing",
            }

        try:
            with sqlite3.connect(db_path) as conn:
                # Check if we should add this state (avoid duplicates/noise)
                if not force_add:
                    # Get the most recent state value
                    cursor = conn.execute(
                        """SELECT state, last_changed_ts FROM states
                           WHERE entity_id = ?
                           ORDER BY last_changed_ts DESC
                           LIMIT 1""",
                        (entity_id,),
                    )
                    recent_state = cursor.fetchone()

                    if recent_state:
                        try:
                            recent_value = float(recent_state[0])
                            recent_timestamp = recent_state[1]

                            # Skip if same value and within 1 hour
                            value_diff = abs(recent_value - value)
                            time_diff = abs(unix_timestamp - recent_timestamp)
                            if (
                                value_diff < VALUE_DIFFERENCE_THRESHOLD
                                and time_diff < TIME_DIFFERENCE_THRESHOLD
                            ):
                                return True  # Skip, but not an error

                        except (ValueError, TypeError):
                            pass  # Previous state wasn't numeric, proceed

                # Check if state exists for this exact timestamp
                cursor = conn.execute(
                    """SELECT state_id FROM states
                       WHERE entity_id = ?
                       AND ABS(last_changed_ts - ?) < 1.0
                       LIMIT 1""",
                    (entity_id, unix_timestamp),
                )
                existing_state = cursor.fetchone()

                current_ts = time.time()
                attrs_json = str(attributes).replace("'", '"')

                if existing_state:
                    # Update existing state
                    conn.execute(
                        """UPDATE states
                           SET state = ?, attributes = ?,
                               last_changed_ts = ?, last_updated_ts = ?
                           WHERE state_id = ?""",
                        (
                            str(value),
                            attrs_json,
                            unix_timestamp,
                            current_ts,
                            existing_state[0],
                        ),
                    )
                else:
                    # Insert new state
                    conn.execute(
                        """INSERT INTO states
                           (entity_id, state, attributes, last_changed_ts,
                            last_updated_ts)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            entity_id,
                            str(value),
                            attrs_json,
                            unix_timestamp,
                            current_ts,
                        ),
                    )

                LOGGER.debug(
                    "Added historical state for %s: %s at %s",
                    entity_id,
                    value,
                    timestamp,
                )
                return True

        except sqlite3.Error as e:
            LOGGER.error(
                "Database error adding historical state for %s: %s", entity_id, e
            )
            return False
            return False

        # Convert timestamp to Unix epoch
        unix_timestamp = timestamp.timestamp()

        # Prepare attributes
        if attributes is None:
            attributes = {
                "unit_of_measurement": unit,
                "device_class": "energy",
                "state_class": "total_increasing",
            }

        conn = None
        try:
            # Connect to database
            conn = sqlite3.connect(db_path)
            conn.execute("BEGIN TRANSACTION")

            # Check if state exists for this timestamp (within 1 second)
            cursor = conn.execute(
                """SELECT state_id FROM states
                   WHERE entity_id = ?
                   AND ABS(last_changed_ts - ?) < 1.0
                   LIMIT 1""",
                (entity_id, unix_timestamp),
            )
            existing_state = cursor.fetchone()

            current_ts = time.time()
            attrs_json = str(attributes).replace("'", '"')

            if existing_state:
                # Update existing state
                conn.execute(
                    """UPDATE states
                       SET state = ?, attributes = ?,
                           last_changed_ts = ?, last_updated_ts = ?
                       WHERE state_id = ?""",
                    (
                        str(value),
                        attrs_json,
                        unix_timestamp,
                        current_ts,
                        existing_state[0],
                    ),
                )
                LOGGER.debug(
                    "Updated existing state for %s at %s", entity_id, timestamp
                )
            else:
                # Insert new state
                conn.execute(
                    """INSERT INTO states
                       (entity_id, state, attributes, last_changed_ts,
                        last_updated_ts)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        entity_id,
                        str(value),
                        attrs_json,
                        unix_timestamp,
                        current_ts,
                    ),
                )
                LOGGER.debug(
                    "Added new historical state for %s at %s", entity_id, timestamp
                )

            conn.commit()
            return True

        except sqlite3.Error as e:
            LOGGER.error(
                "Database error adding historical state for %s: %s", entity_id, e
            )
            if conn:
                conn.rollback()
            return False

        except (ValueError, TypeError, AttributeError) as e:
            LOGGER.error("Data error adding historical state for %s: %s", entity_id, e)
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

    def clear_statistics_for_entity(self, entity_id: str) -> bool:
        """Clear all statistics data for an entity."""
        db_path = self._get_database_path()
        if not db_path:
            return False

        try:
            with sqlite3.connect(
                db_path, timeout=10.0, check_same_thread=False
            ) as conn:
                # Get metadata ID for the entity
                cursor = conn.execute(
                    "SELECT id FROM statistics_meta WHERE statistic_id = ?",
                    (entity_id,),
                )
                result = cursor.fetchone()

                if not result:
                    LOGGER.debug("No statistics metadata found for %s", entity_id)
                    return True

                metadata_id = result[0]

                # Delete statistics entries
                cursor = conn.execute(
                    "DELETE FROM statistics WHERE metadata_id = ?",
                    (metadata_id,),
                )
                deleted_count = cursor.rowcount

                # Delete short-term statistics entries (if table exists)
                try:
                    cursor = conn.execute(
                        "DELETE FROM statistics_short_term WHERE metadata_id = ?",
                        (metadata_id,),
                    )
                    deleted_short_term = cursor.rowcount
                except sqlite3.OperationalError:
                    # Table might not exist in older HA versions
                    deleted_short_term = 0

                conn.commit()

                LOGGER.info(
                    "Cleared statistics for %s: %d long-term, %d short-term",
                    entity_id,
                    deleted_count,
                    deleted_short_term,
                )
                return True

        except sqlite3.Error as e:
            LOGGER.error("Error clearing statistics for %s: %s", entity_id, e)
            return False

    def cleanup_invalid_states(self, entity_id: str) -> bool:
        """Clean up invalid, duplicate, and inconsistent states for an entity."""
        db_path = self._get_database_path()
        if not db_path:
            return False

        try:
            with sqlite3.connect(db_path) as conn:
                # Get metadata_id for the entity
                cursor = conn.execute(
                    "SELECT metadata_id FROM states_meta WHERE entity_id = ?",
                    (entity_id,),
                )
                result = cursor.fetchone()
                if not result:
                    LOGGER.warning("Entity %s not found in states_meta", entity_id)
                    return False

                metadata_id = result[0]

                # Remove invalid states (empty, unavailable, non-numeric)
                cursor = conn.execute(
                    """DELETE FROM states
                       WHERE metadata_id = ?
                       AND (state = '' OR state = 'unavailable'
                            OR state = 'unknown' OR state IS NULL)""",
                    (metadata_id,),
                )
                invalid_deleted = cursor.rowcount

                # Remove duplicate states (same state value within 5 minutes)
                cursor = conn.execute(
                    """DELETE FROM states
                       WHERE metadata_id = ?
                       AND state_id NOT IN (
                           SELECT MAX(state_id)
                           FROM states
                           WHERE metadata_id = ?
                           GROUP BY
                               state,
                               CAST((COALESCE(
                                   last_changed_ts,
                                   last_updated_ts,
                                   last_reported_ts
                               ) / 300) AS INTEGER)
                       )""",
                    (metadata_id, metadata_id),
                )
                duplicate_deleted = cursor.rowcount

                # Remove states with impossible values (negative for energy)
                cursor = conn.execute(
                    """DELETE FROM states
                       WHERE metadata_id = ?
                       AND CAST(state AS REAL) < 0""",
                    (metadata_id,),
                )
                negative_deleted = cursor.rowcount

                LOGGER.info(
                    "Cleaned up states for %s: %d invalid, %d duplicates, %d negative",
                    entity_id,
                    invalid_deleted,
                    duplicate_deleted,
                    negative_deleted,
                )
                return True

        except sqlite3.Error as e:
            LOGGER.error("Error cleaning up states for %s: %s", entity_id, e)
            return False

    def clear_states_for_entity(
        self, entity_id: str, *, keep_latest: bool = True
    ) -> bool:
        """Clear state history for an entity, optionally keeping latest state."""
        db_path = self._get_database_path()
        if not db_path:
            return False

        try:
            with sqlite3.connect(
                db_path, timeout=10.0, check_same_thread=False
            ) as conn:
                if keep_latest:
                    # Keep only the most recent state
                    cursor = conn.execute(
                        """DELETE FROM states
                           WHERE entity_id = ?
                           AND state_id NOT IN (
                               SELECT state_id FROM states
                               WHERE entity_id = ?
                               ORDER BY last_changed_ts DESC
                               LIMIT 1
                           )""",
                        (entity_id, entity_id),
                    )
                else:
                    # Delete all states
                    cursor = conn.execute(
                        "DELETE FROM states WHERE entity_id = ?",
                        (entity_id,),
                    )

                deleted_count = cursor.rowcount
                conn.commit()

                LOGGER.info(
                    "Cleared %d state entries for %s (keep_latest=%s)",
                    deleted_count,
                    entity_id,
                    keep_latest,
                )
                return True

        except sqlite3.Error as e:
            LOGGER.error("Error clearing states for %s: %s", entity_id, e)
            return False

    def complete_clear_entity_data(self, entity_id: str) -> bool:
        """
        Completely clear ALL data associated with an entity from all tables.

        This is a comprehensive reset that removes:
        - All states (current and historical)
        - All statistics (long-term)
        - All short-term statistics
        - Orphaned state attributes
        - Related context data

        Used for complete rebuilds to ensure no residual test/invalid data remains.
        """
        db_path = self._get_database_path()
        if not db_path:
            return False

        try:
            with sqlite3.connect(db_path, timeout=30.0) as conn:
                conn.execute("BEGIN TRANSACTION")

                total_deleted = 0

                # Step 1: Get metadata_id for states
                cursor = conn.execute(
                    "SELECT metadata_id FROM states_meta WHERE entity_id = ?",
                    (entity_id,),
                )
                state_metadata = cursor.fetchone()

                if state_metadata:
                    metadata_id = state_metadata[0]

                    # Clear all states
                    cursor = conn.execute(
                        "DELETE FROM states WHERE metadata_id = ?",
                        (metadata_id,),
                    )
                    states_deleted = cursor.rowcount
                    total_deleted += states_deleted
                    LOGGER.debug("Deleted %d states for %s", states_deleted, entity_id)

                # Step 2: Get metadata_ids for statistics
                # (both sensor and metermate formats)
                statistics_patterns = [
                    entity_id,  # sensor.manual_meter
                    f"{DOMAIN}:{entity_id.replace('sensor.', '')}",
                ]

                stats_metadata_ids = []
                for pattern in statistics_patterns:
                    cursor = conn.execute(
                        "SELECT id FROM statistics_meta WHERE statistic_id = ?",
                        (pattern,),
                    )
                    result = cursor.fetchone()
                    if result:
                        stats_metadata_ids.append((pattern, result[0]))

                # Clear statistics for all found metadata_ids
                for stat_id, metadata_id in stats_metadata_ids:
                    # Clear long-term statistics
                    cursor = conn.execute(
                        "DELETE FROM statistics WHERE metadata_id = ?",
                        (metadata_id,),
                    )
                    stats_deleted = cursor.rowcount
                    total_deleted += stats_deleted

                    # Clear short-term statistics
                    cursor = conn.execute(
                        "DELETE FROM statistics_short_term WHERE metadata_id = ?",
                        (metadata_id,),
                    )
                    short_stats_deleted = cursor.rowcount
                    total_deleted += short_stats_deleted

                    LOGGER.debug(
                        "Deleted %d statistics and %d short-term statistics for %s",
                        stats_deleted,
                        short_stats_deleted,
                        stat_id,
                    )

                # Step 3: Clean up orphaned state attributes
                cursor = conn.execute(
                    """DELETE FROM state_attributes
                       WHERE attributes_id NOT IN (
                           SELECT DISTINCT attributes_id FROM states
                           WHERE attributes_id IS NOT NULL
                       )"""
                )
                orphaned_attrs = cursor.rowcount
                total_deleted += orphaned_attrs

                if orphaned_attrs > 0:
                    LOGGER.debug("Deleted %d orphaned state attributes", orphaned_attrs)

                # Step 4: Clean up old recorder runs if needed
                cursor = conn.execute(
                    "DELETE FROM recorder_runs "
                    "WHERE start < datetime('now', '-30 days')"
                )
                old_runs = cursor.rowcount
                if old_runs > 0:
                    LOGGER.debug("Deleted %d old recorder runs", old_runs)

                conn.commit()

                LOGGER.info(
                    "Complete data clear for %s: %d total entries deleted",
                    entity_id,
                    total_deleted,
                )
                return True

        except sqlite3.Error as e:
            LOGGER.error("Error in complete clear for %s: %s", entity_id, e)
            return False

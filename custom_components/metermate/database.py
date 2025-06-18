"""SQLAlchemy-based database operations for MeterMate integration."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.exc import SQLAlchemyError

from homeassistant.components.recorder.db_schema import (
    States,
    StatesMeta,
    Statistics,
    StatisticsMeta,
    StatisticsShortTerm,
)
from homeassistant.helpers.recorder import get_instance, session_scope
from homeassistant.util import dt as dt_util

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from homeassistant.core import HomeAssistant

# Constants
SHORT_TERM_STATISTICS_DAYS = 10
VALUE_DIFFERENCE_THRESHOLD = 0.001
TIME_DIFFERENCE_THRESHOLD = 3600


class HistoricalDataHandler:
    """Handle historical data insertion using Home Assistant's SQLAlchemy models."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the handler."""
        self.hass = hass
        self.recorder = get_instance(hass)

    def _validate_recorder_available(self) -> bool:
        """Validate that recorder is available."""
        if not self.recorder:
            LOGGER.error("Recorder instance not available")
            return False
        return True

    def _get_or_create_statistics_metadata(
        self,
        session: Session,
        statistic_id: str,
        unit: str,
        name: str,
        source: str = DOMAIN,
    ) -> StatisticsMeta | None:
        """Get or create statistics metadata using SQLAlchemy."""
        try:
            # Try to find existing metadata
            stmt = select(StatisticsMeta).where(
                and_(
                    StatisticsMeta.statistic_id == statistic_id,
                    StatisticsMeta.source == source,
                )
            )
            metadata = session.execute(stmt).scalar_one_or_none()

            if metadata:
                return metadata

            # Create new metadata
            metadata = StatisticsMeta(
                statistic_id=statistic_id,
                source=source,
                unit_of_measurement=unit,
                has_mean=False,
                has_sum=True,
                name=name,
            )
            session.add(metadata)
            session.flush()  # Get the ID
            return metadata

        except SQLAlchemyError as e:
            LOGGER.error("Error managing statistics metadata: %s", e)
            return None

    def _get_or_create_states_metadata(
        self,
        session: Session,
        entity_id: str,
    ) -> StatesMeta | None:
        """Get or create states metadata using SQLAlchemy."""
        try:
            # Try to find existing metadata
            stmt = select(StatesMeta).where(StatesMeta.entity_id == entity_id)
            metadata = session.execute(stmt).scalar_one_or_none()

            if metadata:
                return metadata

            # Create new metadata
            metadata = StatesMeta(entity_id=entity_id)
            session.add(metadata)
            session.flush()  # Get the ID
            return metadata

        except SQLAlchemyError as e:
            LOGGER.error("Error managing states metadata: %s", e)
            return None

    async def add_historical_statistic(
        self,
        entity_id: str,
        timestamp: datetime,
        value: float,
        unit: str,
        name: str,
    ) -> bool:
        """Add a historical statistic using SQLAlchemy."""
        if not self._validate_recorder_available():
            return False

        def _add_statistic_sync() -> bool:
            unix_timestamp = timestamp.timestamp()
            statistic_id = entity_id

            try:
                with session_scope(hass=self.hass) as session:
                    # Get or create metadata
                    metadata = self._get_or_create_statistics_metadata(
                        session, statistic_id, unit, name
                    )
                    if not metadata:
                        return False

                    current_ts = time.time()

                    # Check if statistic already exists
                    existing_stmt = select(Statistics).where(
                        and_(
                            Statistics.metadata_id == metadata.id,
                            Statistics.start_ts == unix_timestamp,
                        )
                    )
                    existing = session.execute(existing_stmt).scalar_one_or_none()

                    if existing:
                        # Update existing statistic
                        existing.state = value
                        existing.sum = value
                        existing.created_ts = current_ts
                        LOGGER.info(
                            "Updated existing statistic for %s at %s with value %s",
                            entity_id,
                            timestamp,
                            value,
                        )
                    else:
                        # Create new statistic
                        statistic = Statistics(
                            metadata_id=metadata.id,
                            start_ts=unix_timestamp,
                            state=value,
                            sum=value,
                            created_ts=current_ts,
                        )
                        session.add(statistic)
                        LOGGER.info(
                            "Added new historical statistic for %s: %s at %s",
                            entity_id,
                            value,
                            timestamp,
                        )

                    # Handle short-term statistics if recent enough
                    days_ago = (dt_util.now().timestamp() - unix_timestamp) / (
                        24 * 3600
                    )
                    if days_ago <= SHORT_TERM_STATISTICS_DAYS:
                        self._add_short_term_statistic(
                            session, metadata.id, unix_timestamp, value, current_ts
                        )

                    return True

            except SQLAlchemyError as e:
                LOGGER.error(
                    "SQLAlchemy error adding historical statistic for %s: %s",
                    entity_id,
                    e,
                )
                return False
            except (ValueError, TypeError, AttributeError) as e:
                LOGGER.error(
                    "Data error adding historical statistic for %s: %s", entity_id, e
                )
                return False

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(_add_statistic_sync)

    def _add_short_term_statistic(
        self,
        session: Session,
        metadata_id: int,
        timestamp: float,
        value: float,
        created_ts: float,
    ) -> None:
        """Add short-term statistic if table exists."""
        try:
            # Check if record exists
            existing_stmt = select(StatisticsShortTerm).where(
                and_(
                    StatisticsShortTerm.metadata_id == metadata_id,
                    StatisticsShortTerm.start_ts == timestamp,
                )
            )
            existing = session.execute(existing_stmt).scalar_one_or_none()

            if existing:
                # Update existing
                existing.state = value
                existing.sum = value
                existing.created_ts = created_ts
            else:
                # Create new
                short_term = StatisticsShortTerm(
                    metadata_id=metadata_id,
                    start_ts=timestamp,
                    state=value,
                    sum=value,
                    created_ts=created_ts,
                )
                session.add(short_term)

        except SQLAlchemyError as e:
            LOGGER.warning("Could not add short-term statistic: %s", e)

    async def add_historical_state(
        self,
        entity_id: str,
        timestamp: datetime,
        value: float,
        unit: str,
        attributes: dict | None = None,
        *,
        force_add: bool = False,
    ) -> bool:
        """Add a historical state using SQLAlchemy."""
        if not self._validate_recorder_available():
            return False

        def _add_historical_state_sync(
            attrs: dict | None,
        ) -> bool:
            unix_timestamp = timestamp.timestamp()

            # Prepare attributes
            if attrs is None:
                attrs = {
                    "unit_of_measurement": unit,
                    "device_class": "energy",
                    "state_class": "total_increasing",
                }

            try:
                with session_scope(hass=self.hass) as session:
                    # Get or create states metadata
                    states_metadata = self._get_or_create_states_metadata(
                        session, entity_id
                    )
                    if not states_metadata:
                        return False

                    # Check if we should add this state (avoid duplicates/noise)
                    if not force_add:
                        recent_stmt = (
                            select(States)
                            .where(States.metadata_id == states_metadata.metadata_id)
                            .order_by(desc(States.last_changed_ts))
                            .limit(1)
                        )
                        recent_state = session.execute(recent_stmt).scalar_one_or_none()

                        if recent_state and self._should_skip_state(
                            recent_state, value, unix_timestamp
                        ):
                            return True  # Skip, but not an error

                    current_ts = time.time()
                    attrs_json = str(attrs).replace("'", '"')

                    # Check if state exists for this exact timestamp
                    existing_stmt = select(States).where(
                        and_(
                            States.metadata_id == states_metadata.metadata_id,
                            func.abs(States.last_changed_ts - unix_timestamp) < 1.0,
                        )
                    )
                    existing_state = session.execute(existing_stmt).scalar_one_or_none()

                    if existing_state:
                        # Update existing state
                        existing_state.state = str(value)
                        existing_state.attributes = attrs_json
                        existing_state.last_changed_ts = unix_timestamp
                        existing_state.last_updated_ts = current_ts
                        LOGGER.debug(
                            "Updated existing state for %s at %s", entity_id, timestamp
                        )
                    else:
                        # Create new state
                        state = States(
                            metadata_id=states_metadata.metadata_id,
                            entity_id=entity_id,
                            state=str(value),
                            attributes=attrs_json,
                            last_changed_ts=unix_timestamp,
                            last_updated_ts=current_ts,
                        )
                        session.add(state)
                        LOGGER.debug(
                            "Added new historical state for %s at %s",
                            entity_id,
                            timestamp,
                        )

                    return True

            except SQLAlchemyError as e:
                LOGGER.error(
                    "SQLAlchemy error adding historical state for %s: %s", entity_id, e
                )
                return False

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(
            _add_historical_state_sync, attributes
        )

    def _should_skip_state(
        self, recent_state: States, new_value: float, new_timestamp: float
    ) -> bool:
        """Determine if we should skip adding a state due to similarity."""
        try:
            if recent_state.state is None or recent_state.last_changed_ts is None:
                return False

            recent_value = float(recent_state.state)
            value_diff = abs(recent_value - new_value)
            time_diff = abs(new_timestamp - recent_state.last_changed_ts)

            return (
                value_diff < VALUE_DIFFERENCE_THRESHOLD
                and time_diff < TIME_DIFFERENCE_THRESHOLD
            )
        except (ValueError, TypeError):
            return False  # Previous state wasn't numeric, proceed

    async def get_latest_statistic(
        self, entity_id: str
    ) -> tuple[datetime, float] | None:
        """Get the latest statistic for an entity using SQLAlchemy."""
        if not self._validate_recorder_available():
            return None

        def _get_latest_statistic_sync() -> tuple[datetime, float] | None:
            statistic_id = entity_id

            try:
                with session_scope(hass=self.hass) as session:
                    stmt = (
                        select(Statistics.start_ts, Statistics.sum)
                        .join(
                            StatisticsMeta, Statistics.metadata_id == StatisticsMeta.id
                        )
                        .where(StatisticsMeta.statistic_id == statistic_id)
                        .order_by(desc(Statistics.start_ts))
                        .limit(1)
                    )

                    result = session.execute(stmt).first()

                    if result:
                        timestamp = dt_util.utc_from_timestamp(result[0])
                        return timestamp, result[1]

                    return None

            except SQLAlchemyError as e:
                LOGGER.error("Error getting latest statistic for %s: %s", entity_id, e)
                return None

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(_get_latest_statistic_sync)

    async def clear_statistics_for_entity(self, entity_id: str) -> bool:
        """Clear all statistics data for an entity using SQLAlchemy."""
        if not self._validate_recorder_available():
            return False

        def _clear_statistics_sync() -> bool:
            try:
                with session_scope(hass=self.hass) as session:
                    # Find metadata for the entity
                    metadata_stmt = select(StatisticsMeta).where(
                        StatisticsMeta.statistic_id == entity_id
                    )
                    metadata = session.execute(metadata_stmt).scalar_one_or_none()

                    if not metadata:
                        LOGGER.debug("No statistics metadata found for %s", entity_id)
                        return True

                    # Delete statistics entries
                    stats_delete = delete(Statistics).where(
                        Statistics.metadata_id == metadata.id
                    )
                    result = session.execute(stats_delete)
                    deleted_count = result.rowcount

                    # Delete short-term statistics entries
                    short_term_delete = delete(StatisticsShortTerm).where(
                        StatisticsShortTerm.metadata_id == metadata.id
                    )
                    short_result = session.execute(short_term_delete)
                    deleted_short_term = short_result.rowcount

                    LOGGER.info(
                        "Cleared statistics for %s: %d long-term, %d short-term",
                        entity_id,
                        deleted_count,
                        deleted_short_term,
                    )
                    return True

            except SQLAlchemyError as e:
                LOGGER.error("Error clearing statistics for %s: %s", entity_id, e)
                return False

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(_clear_statistics_sync)

    async def clear_states_for_entity(
        self, entity_id: str, *, keep_latest: bool = True
    ) -> bool:
        """Clear state history for an entity using SQLAlchemy."""
        if not self._validate_recorder_available():
            return False

        def _clear_states_sync() -> bool:
            try:
                with session_scope(hass=self.hass) as session:
                    # Find states metadata
                    metadata_stmt = select(StatesMeta).where(
                        StatesMeta.entity_id == entity_id
                    )
                    metadata = session.execute(metadata_stmt).scalar_one_or_none()

                    if not metadata:
                        LOGGER.debug("No states metadata found for %s", entity_id)
                        return True

                    if keep_latest:
                        # Keep only the most recent state
                        latest_stmt = (
                            select(States.state_id)
                            .where(States.metadata_id == metadata.metadata_id)
                            .order_by(desc(States.last_changed_ts))
                            .limit(1)
                        )
                        latest_result = session.execute(
                            latest_stmt
                        ).scalar_one_or_none()

                        if latest_result:
                            # Delete all except the latest
                            delete_stmt = delete(States).where(
                                and_(
                                    States.metadata_id == metadata.metadata_id,
                                    States.state_id != latest_result,
                                )
                            )
                        else:
                            # No states found, nothing to delete
                            return True
                    else:
                        # Delete all states
                        delete_stmt = delete(States).where(
                            States.metadata_id == metadata.metadata_id
                        )

                    result = session.execute(delete_stmt)
                    deleted_count = result.rowcount

                    LOGGER.info(
                        "Cleared %d state entries for %s (keep_latest=%s)",
                        deleted_count,
                        entity_id,
                        keep_latest,
                    )
                    return True

            except SQLAlchemyError as e:
                LOGGER.error("Error clearing states for %s: %s", entity_id, e)
                return False

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(_clear_states_sync)

    async def validate_database_access(self) -> bool:
        """Validate that we can access the database using SQLAlchemy."""
        if not self._validate_recorder_available():
            return False

        def _sync_validate() -> bool:
            try:
                with session_scope(hass=self.hass) as session:
                    # Simple query to test access
                    stmt = select(func.count()).select_from(StatisticsMeta)
                    session.execute(stmt).scalar()
                    LOGGER.info("SQLAlchemy database access validation successful")
                    return True
            except SQLAlchemyError as e:
                LOGGER.error("SQLAlchemy database validation failed: %s", e)
                return False

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(_sync_validate)

    async def clear_all_metermate_statistics(self) -> bool:
        """Clear all statistics created by MeterMate integration."""
        if not self._validate_recorder_available():
            return False

        def _clear_all_statistics_sync() -> bool:
            try:
                with session_scope(hass=self.hass) as session:
                    # Find all MeterMate metadata entries
                    metadata_stmt = select(StatisticsMeta).where(
                        StatisticsMeta.source == DOMAIN
                    )
                    metadata_results = session.execute(metadata_stmt).scalars().all()

                    if not metadata_results:
                        LOGGER.debug("No MeterMate statistics metadata found")
                        return True

                    total_deleted = 0
                    total_short_term_deleted = 0

                    for metadata in metadata_results:
                        # Delete statistics entries
                        stats_delete = delete(Statistics).where(
                            Statistics.metadata_id == metadata.id
                        )
                        result = session.execute(stats_delete)
                        deleted_count = result.rowcount
                        total_deleted += deleted_count

                        # Delete short-term statistics entries
                        short_term_delete = delete(StatisticsShortTerm).where(
                            StatisticsShortTerm.metadata_id == metadata.id
                        )
                        short_result = session.execute(short_term_delete)
                        deleted_short_term = short_result.rowcount
                        total_short_term_deleted += deleted_short_term

                        LOGGER.debug(
                            "Cleared statistics for %s: %d long-term, %d short-term",
                            metadata.statistic_id,
                            deleted_count,
                            deleted_short_term,
                        )

                    LOGGER.info(
                        "Cleared all MeterMate statistics: %d long-term, "
                        "%d short-term entries from %d entities",
                        total_deleted,
                        total_short_term_deleted,
                        len(metadata_results),
                    )
                    return True

            except SQLAlchemyError as e:
                LOGGER.error("Error clearing all MeterMate statistics: %s", e)
                return False

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(_clear_all_statistics_sync)

    async def get_metermate_entities(self) -> list[str]:
        """Get list of all entity IDs that have MeterMate statistics."""
        if not self._validate_recorder_available():
            return []

        def _get_entities_sync() -> list[str]:
            try:
                with session_scope(hass=self.hass) as session:
                    stmt = select(StatisticsMeta.statistic_id).where(
                        StatisticsMeta.source == DOMAIN
                    )
                    results = session.execute(stmt).scalars().all()
                    # Filter out None values (shouldn't happen but type safety)
                    return [r for r in results if r is not None]

            except SQLAlchemyError as e:
                LOGGER.error("Error getting MeterMate entities: %s", e)
                return []

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(_get_entities_sync)

    async def complete_clear_entity_data(self, entity_id: str) -> bool:
        """Completely clear all data (states and statistics) for an entity."""
        if not self._validate_recorder_available():
            return False

        LOGGER.info("Performing complete data clear for %s", entity_id)

        # Clear statistics
        stats_success = await self.clear_statistics_for_entity(entity_id)

        # Clear states (without keeping latest since this is a complete clear)
        states_success = await self.clear_states_for_entity(
            entity_id, keep_latest=False
        )

        success = stats_success and states_success

        if success:
            LOGGER.info("Successfully completed full data clear for %s", entity_id)
        else:
            LOGGER.error("Failed to complete full data clear for %s", entity_id)

        return success

    async def cleanup_invalid_states(self, entity_id: str) -> bool:
        """Clean up invalid or problematic states for an entity."""
        if not self._validate_recorder_available():
            return False

        def _cleanup_invalid_states_sync() -> bool:
            try:
                with session_scope(hass=self.hass) as session:
                    # Find states metadata
                    metadata_stmt = select(StatesMeta).where(
                        StatesMeta.entity_id == entity_id
                    )
                    metadata = session.execute(metadata_stmt).scalar_one_or_none()

                    if not metadata:
                        LOGGER.debug("No states metadata found for %s", entity_id)
                        return True

                    # Find and delete states with invalid values
                    # (non-numeric, negative for totals, etc.)
                    invalid_conditions = [
                        # States with null values
                        States.state.is_(None),
                        # States with empty string values
                        States.state == "",
                        # Add more conditions as needed for invalid states
                    ]

                    delete_stmt = delete(States).where(
                        and_(
                            States.metadata_id == metadata.metadata_id,
                            # At least one invalid condition must be true
                            or_(*invalid_conditions),
                        )
                    )

                    result = session.execute(delete_stmt)
                    deleted_count = result.rowcount

                    if deleted_count > 0:
                        LOGGER.info(
                            "Cleaned up %d invalid states for %s",
                            deleted_count,
                            entity_id,
                        )
                    else:
                        LOGGER.debug("No invalid states found for %s", entity_id)

                    return True

            except SQLAlchemyError as e:
                LOGGER.error(
                    "Error cleaning up invalid states for %s: %s", entity_id, e
                )
                return False

        # Run in executor to avoid blocking the event loop
        return await self.hass.async_add_executor_job(_cleanup_invalid_states_sync)

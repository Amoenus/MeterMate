# Error Handling Patterns PRD

> **📋 Document Type**: Implementation Guide
> **🔗 Related**: [Validation Patterns](validation-patterns.md), [Service Organization Strategy](service-organization-strategy.md)
> **📅 Last Updated**: 2025-11-05

---

## Overview

This document defines the error handling patterns and exception hierarchy for MeterMate services, focusing on clear user feedback and maintainable error management.

**Goal**: Standardize error handling across all services with consistent exception types and informative messages.

**Autonomy Level**: 🟡 Collaborative - Implement with human validation at completion

---

## Philosophy

### Why Custom Exceptions?

MeterMate uses custom exceptions to:
- ✅ Distinguish MeterMate errors from HA framework errors
- ✅ Enable specific error handling based on error type
- ✅ Provide context-specific error messages
- ✅ Support troubleshooting and debugging
- ✅ Allow granular error recovery strategies

### Error Handling Principles

1. **Fail Explicitly**: Never silently swallow errors
2. **Fail Informatively**: Include context in error messages
3. **Fail Appropriately**: Use the right exception type
4. **Fail Gracefully**: Clean up resources on error
5. **Fail Visibly**: Log errors at appropriate levels

---

## Exception Hierarchy

### File: `custom_components/metermate/exceptions.py`

```python
"""Custom exceptions for MeterMate.

Exception Hierarchy:
    MeterMateError (base)
    ├── MeterMateValidationError (user input errors)
    ├── MeterMateEntityNotFoundError (missing entities)
    ├── MeterMateReadingNotFoundError (missing readings)
    ├── MeterMateDatabaseError (database operation failures)
    ├── MeterMateInvalidStateError (entity state issues)
    └── MeterMateConfigError (configuration errors)
"""
from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class MeterMateError(HomeAssistantError):
    """Base exception for all MeterMate errors.

    All MeterMate-specific exceptions should inherit from this class.
    This allows catching all MeterMate errors with a single except block.
    """


class MeterMateValidationError(MeterMateError):
    """Raised when input validation fails.

    Use this for:
    - Invalid service call parameters (after schema validation)
    - Business logic validation failures
    - Data consistency checks

    Examples:
        - Negative consumption values
        - Period end before period start
        - Duplicate timestamps
    """


class MeterMateEntityNotFoundError(MeterMateError):
    """Raised when a MeterMate entity is not found.

    Use this for:
    - Entity ID references that don't exist
    - Entity not yet initialized
    - Entity removed but still referenced

    This is a specialized error that can be caught separately
    to provide helpful "did you create the sensor?" messages.
    """


class MeterMateReadingNotFoundError(MeterMateError):
    """Raised when a specific reading is not found.

    Use this for:
    - Reading ID doesn't exist
    - Reading was deleted
    - Reading query returned no results (when expected)
    """


class MeterMateDatabaseError(MeterMateError):
    """Raised when database operations fail.

    Use this for:
    - Statistics table write failures
    - Database connection errors
    - Transaction failures
    - Data integrity violations

    This indicates a system-level problem, not user error.
    """


class MeterMateInvalidStateError(MeterMateError):
    """Raised when entity or system is in invalid state.

    Use this for:
    - Entity not ready/initialized
    - Integration not fully loaded
    - Concurrent modification conflicts
    - State machine violations
    """


class MeterMateConfigError(MeterMateError):
    """Raised when configuration is invalid.

    Use this for:
    - Config entry data invalid
    - Missing required configuration
    - Configuration migration failures

    This is typically raised during setup, not during normal operation.
    """
```

---

## Service Error Handling Pattern

### Standard Service Handler Template

```python
"""Standard error handling pattern for service handlers."""
import logging
from typing import Any

from homeassistant.core import ServiceCall
from homeassistant.util import dt as dt_util

from ..exceptions import (
    MeterMateError,
    MeterMateEntityNotFoundError,
    MeterMateValidationError,
    MeterMateDatabaseError,
    MeterMateInvalidStateError,
)
from ..models import Reading

_LOGGER = logging.getLogger(__name__)


async def async_handle_add_reading(self, call: ServiceCall) -> None:
    """Handle add_reading service with proper error handling.

    This demonstrates the standard error handling pattern:
    1. Extract and validate parameters
    2. Pre-flight checks (entity exists, state valid)
    3. Execute operation with detailed error context
    4. Handle specific exception types appropriately
    5. Log and re-raise with context

    Args:
        call: Service call with validated data

    Raises:
        MeterMateEntityNotFoundError: Entity doesn't exist
        MeterMateValidationError: Input validation failed
        MeterMateDatabaseError: Database operation failed
        MeterMateInvalidStateError: Entity not ready
    """
    entity_id = call.data[ATTR_ENTITY_ID]
    value = call.data["value"]
    timestamp = call.data.get("timestamp", dt_util.utcnow())

    try:
        # Pre-flight check: Entity exists
        if not await self._entity_exists(entity_id):
            raise MeterMateEntityNotFoundError(
                f"Entity {entity_id} not found. "
                "Please create the sensor first via Configuration > Integrations."
            )

        # Pre-flight check: Entity state
        entity = self._get_entity(entity_id)
        if entity is None or not entity.available:
            raise MeterMateInvalidStateError(
                f"Entity {entity_id} is not ready. "
                "Please wait for it to initialize or check if it's unavailable."
            )

        # Business logic validation
        # (Schema validation already happened, this is business rules)
        if await self._reading_exists(entity_id, timestamp):
            raise MeterMateValidationError(
                f"A reading already exists for {entity_id} at {timestamp.isoformat()}. "
                "Use update_reading service to modify existing readings."
            )

        # Create reading object
        reading = Reading(
            timestamp=dt_util.as_utc(timestamp),
            value=value,
            unit=call.data.get("unit", "kWh"),
            notes=call.data.get("notes"),
        )

        # Execute database operation
        result = await self.data_manager.add_reading(entity_id, reading)

        if not result.success:
            raise MeterMateDatabaseError(
                f"Failed to add reading: {result.message}"
            )

        # Success logging
        _LOGGER.info(
            "Successfully added reading for %s: %s %s at %s",
            entity_id,
            value,
            reading.unit,
            timestamp.isoformat(),
        )

    except MeterMateError:
        # Re-raise our exceptions as-is (already have good messages)
        # These will be shown to the user in the HA UI
        raise

    except Exception as e:
        # Catch any unexpected errors and wrap them
        # This prevents leaking internal errors to users
        _LOGGER.exception(
            "Unexpected error adding reading for %s",
            entity_id,
        )
        raise MeterMateDatabaseError(
            f"Unexpected error adding reading: {str(e)}"
        ) from e
```

---

## Error Handling by Service Type

### Query Services (Read-Only)

Query services should handle errors gracefully and return empty results when appropriate:

```python
async def async_handle_get_readings(self, call: ServiceCall) -> dict:
    """Get readings with graceful error handling."""
    entity_id = call.data[ATTR_ENTITY_ID]

    try:
        # Verify entity exists
        if not await self._entity_exists(entity_id):
            # For queries, we can return empty instead of erroring
            _LOGGER.warning("Entity %s not found", entity_id)
            return {"readings": []}

        # Get readings
        readings = await self.data_manager.get_readings(
            entity_id,
            start_date=call.data.get("start_date"),
            end_date=call.data.get("end_date"),
        )

        return {"readings": [r.to_dict() for r in readings]}

    except MeterMateDatabaseError:
        # Database errors should still be raised
        raise

    except Exception as e:
        _LOGGER.exception("Error getting readings for %s", entity_id)
        # Return empty rather than crash
        return {"readings": []}
```

### Mutation Services (Data Modification)

Mutation services should fail explicitly and cleanly:

```python
async def async_handle_delete_reading(self, call: ServiceCall) -> None:
    """Delete reading with strict error handling."""
    entity_id = call.data[ATTR_ENTITY_ID]
    reading_id = call.data["reading_id"]

    try:
        # Must verify entity exists (strict)
        await self._ensure_entity_exists(entity_id)

        # Must verify reading exists before deleting
        reading = await self.data_manager.get_reading(entity_id, reading_id)
        if reading is None:
            raise MeterMateReadingNotFoundError(
                f"Reading {reading_id} not found for entity {entity_id}. "
                "It may have already been deleted."
            )

        # Perform deletion
        result = await self.data_manager.delete_reading(entity_id, reading_id)

        if not result.success:
            raise MeterMateDatabaseError(
                f"Failed to delete reading: {result.message}"
            )

        _LOGGER.info(
            "Deleted reading %s for %s (value: %s at %s)",
            reading_id,
            entity_id,
            reading.value,
            reading.timestamp.isoformat(),
        )

    except MeterMateError:
        raise
    except Exception as e:
        _LOGGER.exception("Error deleting reading %s", reading_id)
        raise MeterMateDatabaseError(
            f"Unexpected error deleting reading: {str(e)}"
        ) from e
```

### Admin Services (Destructive Operations)

Admin services need extra safety checks and detailed logging:

```python
async def async_handle_rebuild_history(self, call: ServiceCall) -> None:
    """Rebuild history with extensive safety checks and logging."""
    entity_id = call.data[ATTR_ENTITY_ID]
    complete_wipe = call.data.get("complete_wipe", True)

    # Log admin operation prominently
    _LOGGER.warning(
        "ADMIN OPERATION: rebuild_history called for %s (complete_wipe=%s)",
        entity_id,
        complete_wipe,
    )

    try:
        # Verify entity exists
        await self._ensure_entity_exists(entity_id)

        # Safety check: Get reading count
        readings = await self.data_manager.get_all_readings(entity_id)
        reading_count = len(readings)

        if reading_count == 0:
            raise MeterMateValidationError(
                f"Cannot rebuild history for {entity_id}: no readings found. "
                "Add readings first."
            )

        _LOGGER.info(
            "Starting history rebuild for %s: %d readings will be processed",
            entity_id,
            reading_count,
        )

        # Execute rebuild
        result = await self.data_manager.rebuild_history(
            entity_id,
            complete_wipe=complete_wipe,
        )

        if not result.success:
            raise MeterMateDatabaseError(
                f"History rebuild failed: {result.message}"
            )

        _LOGGER.warning(
            "ADMIN OPERATION COMPLETED: History rebuilt for %s: %s",
            entity_id,
            result.message,
        )

    except MeterMateError:
        _LOGGER.error("History rebuild failed for %s", entity_id)
        raise
    except Exception as e:
        _LOGGER.exception("Unexpected error rebuilding history for %s", entity_id)
        raise MeterMateDatabaseError(
            f"Unexpected error during history rebuild: {str(e)}"
        ) from e
```

---

## Logging Guidelines

### Log Levels

**ERROR** - Something failed and user action is required:
```python
_LOGGER.error(
    "Failed to add reading for %s: %s",
    entity_id,
    error_message,
)
```

**WARNING** - Something unusual but not necessarily broken:
```python
_LOGGER.warning(
    "Entity %s not found, returning empty results",
    entity_id,
)
```

**INFO** - Normal operations that are noteworthy:
```python
_LOGGER.info(
    "Successfully added reading for %s: %s %s",
    entity_id,
    value,
    unit,
)
```

**DEBUG** - Detailed information for troubleshooting:
```python
_LOGGER.debug(
    "Retrieved %d readings for %s between %s and %s",
    len(readings),
    entity_id,
    start_date,
    end_date,
)
```

### Admin Operation Logging

Admin operations should use WARNING level for start/completion:

```python
# Start of operation
_LOGGER.warning(
    "ADMIN OPERATION: %s called for %s with parameters: %s",
    service_name,
    entity_id,
    parameters,
)

# Completion
_LOGGER.warning(
    "ADMIN OPERATION COMPLETED: %s for %s: %s",
    service_name,
    entity_id,
    result_summary,
)
```

---

## Error Message Guidelines

### User-Facing Error Messages

Error messages shown to users should be:

1. **Clear**: Avoid technical jargon
2. **Actionable**: Tell user how to fix it
3. **Contextual**: Include relevant details
4. **Consistent**: Use similar phrasing for similar errors

### Examples

✅ **Good Messages**:

```python
# Clear and actionable
raise MeterMateEntityNotFoundError(
    f"Entity {entity_id} not found. "
    "Please create the sensor first via Configuration > Integrations."
)

# Includes context
raise MeterMateValidationError(
    f"A reading already exists for {entity_id} at {timestamp.isoformat()}. "
    "Use update_reading service to modify existing readings."
)

# Suggests alternatives
raise MeterMateValidationError(
    f"Consumption value seems unreasonably large: {value}. "
    "Did you mean to enter a meter reading instead?"
)
```

❌ **Poor Messages**:

```python
# Too vague
raise MeterMateError("Operation failed")

# Too technical
raise MeterMateError("SQLAlchemy session.commit() raised IntegrityError")

# No guidance
raise MeterMateError("Invalid input")
```

---

## Error Recovery Strategies

### Transient Errors

For transient errors (database locks, network issues), implement retry logic:

```python
from asyncio import sleep

async def _add_reading_with_retry(
    self,
    entity_id: str,
    reading: Reading,
    max_retries: int = 3,
) -> Result:
    """Add reading with retry logic for transient errors."""
    for attempt in range(max_retries):
        try:
            return await self.data_manager.add_reading(entity_id, reading)

        except MeterMateDatabaseError as e:
            if "locked" in str(e).lower() and attempt < max_retries - 1:
                # Database locked, retry after brief delay
                wait_time = 2 ** attempt  # Exponential backoff
                _LOGGER.warning(
                    "Database locked, retrying in %ds (attempt %d/%d)",
                    wait_time,
                    attempt + 1,
                    max_retries,
                )
                await sleep(wait_time)
            else:
                # Not a transient error or out of retries
                raise

    raise MeterMateDatabaseError(
        f"Failed to add reading after {max_retries} attempts"
    )
```

### Partial Success Handling

For batch operations, track partial success:

```python
async def async_handle_bulk_import(self, call: ServiceCall) -> None:
    """Import multiple readings with partial success tracking."""
    entity_id = call.data[ATTR_ENTITY_ID]
    readings = call.data["readings"]

    success_count = 0
    errors = []

    for i, reading_data in enumerate(readings):
        try:
            reading = Reading.from_dict(reading_data)
            result = await self.data_manager.add_reading(entity_id, reading)

            if result.success:
                success_count += 1
            else:
                errors.append(f"Reading {i}: {result.message}")

        except Exception as e:
            errors.append(f"Reading {i}: {str(e)}")

    # Report results
    if errors:
        error_summary = "\n".join(errors[:5])  # First 5 errors
        if len(errors) > 5:
            error_summary += f"\n... and {len(errors) - 5} more errors"

        if success_count == 0:
            # Complete failure
            raise MeterMateDatabaseError(
                f"Bulk import failed: No readings imported.\n{error_summary}"
            )
        else:
            # Partial success
            _LOGGER.warning(
                "Bulk import partially completed: %d/%d succeeded.\nErrors:\n%s",
                success_count,
                len(readings),
                error_summary,
            )
    else:
        # Complete success
        _LOGGER.info(
            "Bulk import completed successfully: %d readings imported",
            success_count,
        )
```

---

## Testing Error Handling

### Unit Tests for Exceptions

```python
"""Tests for exception hierarchy."""
import pytest

from custom_components.metermate.exceptions import (
    MeterMateError,
    MeterMateValidationError,
    MeterMateEntityNotFoundError,
)


def test_exception_hierarchy():
    """Test that exceptions inherit correctly."""
    # All MeterMate exceptions should inherit from MeterMateError
    assert issubclass(MeterMateValidationError, MeterMateError)
    assert issubclass(MeterMateEntityNotFoundError, MeterMateError)

    # MeterMateError should inherit from HomeAssistantError
    from homeassistant.exceptions import HomeAssistantError
    assert issubclass(MeterMateError, HomeAssistantError)


def test_exception_can_catch_base():
    """Test that catching base exception catches derived."""
    try:
        raise MeterMateValidationError("Test error")
    except MeterMateError as e:
        assert "Test error" in str(e)
        # Successfully caught derived exception with base


def test_exception_messages():
    """Test that exception messages are preserved."""
    msg = "Entity sensor.test not found"
    exc = MeterMateEntityNotFoundError(msg)
    assert str(exc) == msg
```

### Integration Tests for Error Handling

```python
"""Tests for service error handling."""
import pytest

from custom_components.metermate.exceptions import (
    MeterMateEntityNotFoundError,
    MeterMateValidationError,
    MeterMateDatabaseError,
)


async def test_add_reading_entity_not_found(hass, data_manager):
    """Test that entity not found raises appropriate error."""
    service = AddReadingService(hass, data_manager)

    call = mock_service_call({
        "entity_id": "sensor.nonexistent",
        "value": 100.0,
    })

    with pytest.raises(MeterMateEntityNotFoundError) as exc_info:
        await service.async_handle_service(call)

    assert "not found" in str(exc_info.value).lower()
    assert "sensor.nonexistent" in str(exc_info.value)


async def test_add_reading_duplicate_timestamp(hass, data_manager, entity):
    """Test that duplicate timestamps raise validation error."""
    service = AddReadingService(hass, data_manager)

    timestamp = dt_util.utcnow()

    # Add first reading
    await service.async_handle_service(mock_service_call({
        "entity_id": entity.entity_id,
        "value": 100.0,
        "timestamp": timestamp,
    }))

    # Try to add duplicate
    with pytest.raises(MeterMateValidationError) as exc_info:
        await service.async_handle_service(mock_service_call({
            "entity_id": entity.entity_id,
            "value": 200.0,
            "timestamp": timestamp,
        }))

    assert "already exists" in str(exc_info.value).lower()


async def test_error_logged_correctly(hass, data_manager, caplog):
    """Test that errors are logged at correct levels."""
    import logging
    caplog.set_level(logging.INFO)

    service = AddReadingService(hass, data_manager)

    with pytest.raises(MeterMateEntityNotFoundError):
        await service.async_handle_service(mock_service_call({
            "entity_id": "sensor.nonexistent",
            "value": 100.0,
        }))

    # Verify error was logged
    assert any("not found" in record.message.lower() for record in caplog.records)
```

---

## Success Criteria

### Must Have ✅
- [ ] Complete exception hierarchy in `exceptions.py`
- [ ] All services use appropriate exception types
- [ ] Error messages are clear and actionable
- [ ] Comprehensive error logging
- [ ] All exceptions tested

### Should Have 🎯
- [ ] Error recovery strategies for transient failures
- [ ] Partial success handling for batch operations
- [ ] Admin operation audit logging
- [ ] Error message consistency across services

### Nice to Have ✨
- [ ] Error rate monitoring/metrics
- [ ] Automatic error reporting/telemetry
- [ ] Error message localization
- [ ] Retry policies per error type

---

## Related Documents

- **[Validation Patterns](validation-patterns.md)**: Input validation that triggers these exceptions
- **[Service Organization Strategy](service-organization-strategy.md)**: How services use error handling
- **[Phase 1 Migration Guide](phase-1-migration-guide.md)**: Implementation timeline

---

## References

- Home Assistant exception handling: https://developers.home-assistant.io/docs/dev_101_services#exceptions
- Python exception best practices: https://docs.python.org/3/tutorial/errors.html
- Logging best practices: https://docs.python.org/3/howto/logging.html

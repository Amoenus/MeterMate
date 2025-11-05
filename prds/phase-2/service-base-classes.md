# Service Base Classes PRD

> **📋 Document Type**: Implementation Guide
> **🔗 Related**: [Service Categorization](service-categorization.md), [Service Module Structure](service-module-structure.md)
> **📅 Last Updated**: 2025-11-06

---

## Overview

This document defines the base class hierarchy for MeterMate services, providing a foundation for consistent service implementation with proper separation of concerns.

**Goal**: Create reusable base classes that encapsulate common service functionality and enforce consistent patterns.

**Autonomy Level**: 🟡 Collaborative - Implement with human validation at completion

---

## Philosophy

### Why Base Classes?

Base classes provide:
- ✅ **Code Reuse**: Common functionality in one place
- ✅ **Consistency**: All services follow same patterns
- ✅ **Type Safety**: Abstract methods enforce implementation
- ✅ **Extensibility**: Easy to add new service types
- ✅ **Maintainability**: Changes propagate to all services

### Design Principles

1. **Single Responsibility**: Each base class serves one purpose
2. **Open/Closed**: Open for extension, closed for modification
3. **Liskov Substitution**: Derived classes are substitutable
4. **Interface Segregation**: Minimal required methods
5. **Dependency Inversion**: Depend on abstractions

---

## Base Class Hierarchy

```
AbstractMeterMateService (abstract base)
├── AbstractMeterMateQueryService (read-only, supports response)
├── AbstractMeterMateMutationService (data modification)
└── AbstractMeterMateAdminService (destructive operations, requires admin)
```

---

## File: `services/base.py`

### Abstract Base Service

```python
"""Base classes for MeterMate services.

This module provides the foundational service classes that all MeterMate
services inherit from. The hierarchy enforces consistent patterns while
allowing flexibility for different service types.

Hierarchy:
    AbstractMeterMateService (base)
    ├── AbstractMeterMateQueryService (queries)
    ├── AbstractMeterMateMutationService (mutations)
    └── AbstractMeterMateAdminService (admin operations)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import voluptuous as vol

from homeassistant.core import callback
from homeassistant.helpers.service import async_register_admin_service

from ..const import ATTR_INTEGRATION_NAME
from ..exceptions import MeterMateEntityNotFoundError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant, ServiceCall
    from ..data_manager import MeterMateDataManager

_LOGGER = logging.getLogger(__name__)


class AbstractMeterMateService(ABC):
    """Abstract base for all MeterMate services.

    This class provides the foundation for all services, including:
    - Access to Home Assistant and data manager
    - Entity existence checking
    - Common helper methods
    - Service registration

    All MeterMate services must inherit from this or a derived class.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        data_manager: MeterMateDataManager
    ) -> None:
        """Initialize the service.

        Args:
            hass: Home Assistant instance
            data_manager: MeterMate data manager for database operations
        """
        self.hass = hass
        self.data_manager = data_manager

    @property
    @abstractmethod
    def domain(self) -> str:
        """Return the domain.

        Returns:
            Domain name (typically ATTR_INTEGRATION_NAME)
        """
        return ATTR_INTEGRATION_NAME

    @property
    @abstractmethod
    def service(self) -> str:
        """Return the service name.

        This should be a snake_case name matching the service definition.

        Returns:
            Service name (e.g., "add_reading", "get_readings")
        """

    @property
    @abstractmethod
    def schema(self) -> dict[str, Any] | None:
        """Return the service schema.

        Returns:
            Dictionary defining the service schema, or None if no schema
        """

    @abstractmethod
    async def async_handle_service(self, call: ServiceCall) -> Any:
        """Handle the service call.

        This is the main entry point for service execution. The call data
        has already been validated against the schema.

        Args:
            call: Service call with validated data

        Returns:
            Service response data (for query services) or None

        Raises:
            MeterMateError: For expected error conditions
            Exception: For unexpected errors (will be wrapped)
        """

    @callback
    def async_register(self) -> None:
        """Register the service with Home Assistant.

        This default implementation registers a standard service.
        Override in derived classes for specialized registration
        (e.g., admin services, services with response support).
        """
        self.hass.services.async_register(
            self.domain,
            self.service,
            self.async_handle_service,
            schema=vol.Schema(self.schema) if self.schema else None,
        )

    # Helper methods available to all services

    def _get_entity(self, entity_id: str):
        """Get entity from hass data.

        Args:
            entity_id: Entity ID to retrieve

        Returns:
            Entity object or None if not found
        """
        if (
            ATTR_INTEGRATION_NAME not in self.hass.data
            or "entities" not in self.hass.data[ATTR_INTEGRATION_NAME]
        ):
            return None
        return self.hass.data[ATTR_INTEGRATION_NAME]["entities"].get(entity_id)

    async def _ensure_entity_exists(self, entity_id: str) -> None:
        """Ensure entity exists, raise if not.

        This is a convenience method for services that require an entity
        to exist. It provides a consistent error message.

        Args:
            entity_id: Entity ID to check

        Raises:
            MeterMateEntityNotFoundError: If entity doesn't exist
        """
        if not self._get_entity(entity_id):
            raise MeterMateEntityNotFoundError(
                f"Entity {entity_id} not found. "
                "Please create the sensor first via Configuration > Integrations."
            )

    async def _entity_exists(self, entity_id: str) -> bool:
        """Check if entity exists.

        Args:
            entity_id: Entity ID to check

        Returns:
            True if entity exists, False otherwise
        """
        return self._get_entity(entity_id) is not None
```

---

## Query Service Base Class

```python
class AbstractMeterMateQueryService(AbstractMeterMateService):
    """Base for read-only query services.

    Query services:
    - Read data without modification
    - Support returning response data
    - Can be called frequently without side effects
    - Typically return JSON-serializable data

    Examples: get_readings, validate_reading
    """

    @callback
    def async_register(self) -> None:
        """Register query service with response support.

        Query services can return data to the caller, which is useful
        for integrations and automations.
        """
        from homeassistant.core import SupportsResponse

        self.hass.services.async_register(
            self.domain,
            self.service,
            self.async_handle_service,
            schema=vol.Schema(self.schema) if self.schema else None,
            supports_response=SupportsResponse.OPTIONAL,
        )

    @abstractmethod
    async def async_handle_service(self, call: ServiceCall) -> dict[str, Any]:
        """Handle query service call.

        Query services should return dictionaries that can be serialized
        to JSON. The response should be structured and documented.

        Args:
            call: Service call with validated data

        Returns:
            Dictionary with query results (JSON-serializable)

        Raises:
            MeterMateError: For expected error conditions
        """
```

---

## Mutation Service Base Class

```python
class AbstractMeterMateMutationService(AbstractMeterMateService):
    """Base for services that modify data.

    Mutation services:
    - Add, update, or delete data
    - Have side effects
    - Should be idempotent when possible
    - Log operations for audit trail

    Examples: add_reading, update_reading, delete_reading
    """

    async def async_handle_service(self, call: ServiceCall) -> None:
        """Handle mutation service with logging.

        This wrapper adds consistent logging for all mutation operations.
        Derived classes implement _async_execute for the actual operation.

        Args:
            call: Service call with validated data

        Raises:
            MeterMateError: For expected error conditions
            Exception: For unexpected errors (logged and re-raised)
        """
        entity_id = call.data.get("entity_id", "N/A")
        _LOGGER.info(
            "Service %s called for entity %s",
            self.service,
            entity_id,
        )

        try:
            await self._async_execute(call)
            _LOGGER.debug("Service %s completed successfully", self.service)
        except Exception as e:
            _LOGGER.exception("Error executing %s", self.service)
            raise

    @abstractmethod
    async def _async_execute(self, call: ServiceCall) -> None:
        """Execute the mutation operation.

        This is where the actual business logic goes. The call data
        has been validated and operation has been logged.

        Args:
            call: Service call with validated data

        Raises:
            MeterMateError: For expected error conditions
        """
```

---

## Admin Service Base Class

```python
class AbstractMeterMateAdminService(AbstractMeterMateService):
    """Base for admin-only services (destructive operations).

    Admin services:
    - Require administrator privileges
    - Perform destructive or bulk operations
    - Should have extra safety checks
    - Log prominently for audit trail

    Examples: rebuild_history, bulk_import, recalculate_statistics
    """

    @callback
    def async_register(self) -> None:
        """Register as admin service.

        Admin services use Home Assistant's admin service registration,
        which enforces permission checks before execution.
        """
        async_register_admin_service(
            hass=self.hass,
            domain=self.domain,
            service=self.service,
            service_func=self.async_handle_service,
            schema=vol.Schema(self.schema) if self.schema else None,
        )

    async def async_handle_service(self, call: ServiceCall) -> None:
        """Handle admin service with extra logging and safety checks.

        Admin operations are logged at WARNING level to ensure they
        appear in logs even with default log levels.

        Args:
            call: Service call with validated data

        Raises:
            MeterMateError: For expected error conditions
            Exception: For unexpected errors (logged and re-raised)
        """
        entity_id = call.data.get("entity_id", "N/A")
        _LOGGER.warning(
            "ADMIN OPERATION: %s called for entity %s",
            self.service,
            entity_id,
        )

        try:
            await self._async_execute_admin(call)
            _LOGGER.warning(
                "ADMIN OPERATION COMPLETED: %s for %s",
                self.service,
                entity_id,
            )
        except Exception as e:
            _LOGGER.error(
                "ADMIN OPERATION FAILED: %s for %s: %s",
                self.service,
                entity_id,
                str(e),
            )
            raise

    @abstractmethod
    async def _async_execute_admin(self, call: ServiceCall) -> None:
        """Execute the admin operation.

        This is where the actual admin logic goes. Extra safety checks
        should be implemented here.

        Args:
            call: Service call with validated data

        Raises:
            MeterMateError: For expected error conditions
        """
```

---

## Usage Examples

### Simple Query Service

```python
from .base import AbstractMeterMateQueryService
from .schemas import SERVICE_GET_READINGS_SCHEMA

class GetReadingsService(AbstractMeterMateQueryService):
    """Service to query readings for an entity."""

    @property
    def service(self) -> str:
        return "get_readings"

    @property
    def schema(self):
        return SERVICE_GET_READINGS_SCHEMA

    async def async_handle_service(self, call: ServiceCall) -> dict:
        """Handle get_readings service call."""
        entity_id = call.data["entity_id"]

        # Get readings from data manager
        readings = await self.data_manager.get_readings(entity_id)

        # Return formatted response
        return {
            "readings": [r.to_dict() for r in readings]
        }
```

### Simple Mutation Service

```python
from .base import AbstractMeterMateMutationService
from .schemas import SERVICE_ADD_READING_SCHEMA
from ..models import Reading

class AddReadingService(AbstractMeterMateMutationService):
    """Service to add a single reading."""

    @property
    def service(self) -> str:
        return "add_reading"

    @property
    def schema(self):
        return SERVICE_ADD_READING_SCHEMA

    async def _async_execute(self, call: ServiceCall) -> None:
        """Execute add reading operation."""
        entity_id = call.data["entity_id"]

        # Ensure entity exists
        await self._ensure_entity_exists(entity_id)

        # Create and add reading
        reading = Reading.from_service_call(call.data)
        result = await self.data_manager.add_reading(entity_id, reading)

        if not result.success:
            raise MeterMateDatabaseError(result.message)
```

### Admin Service

```python
from .base import AbstractMeterMateAdminService
from .schemas import SERVICE_REBUILD_HISTORY_SCHEMA

class RebuildHistoryService(AbstractMeterMateAdminService):
    """Admin service to rebuild history from readings."""

    @property
    def service(self) -> str:
        return "rebuild_history"

    @property
    def schema(self):
        return SERVICE_REBUILD_HISTORY_SCHEMA

    async def _async_execute_admin(self, call: ServiceCall) -> None:
        """Execute rebuild history operation."""
        entity_id = call.data["entity_id"]
        complete_wipe = call.data.get("complete_wipe", True)

        # Safety check
        await self._ensure_entity_exists(entity_id)

        # Get reading count for logging
        readings = await self.data_manager.get_all_readings(entity_id)
        _LOGGER.info("Rebuilding history: %d readings", len(readings))

        # Execute rebuild
        result = await self.data_manager.rebuild_history(
            entity_id,
            complete_wipe=complete_wipe
        )

        if not result.success:
            raise MeterMateDatabaseError(result.message)
```

---

## Testing Base Classes

### Base Class Tests

```python
"""Tests for service base classes."""
import pytest
from unittest.mock import Mock, AsyncMock

from custom_components.metermate.services.base import (
    AbstractMeterMateService,
    AbstractMeterMateQueryService,
    AbstractMeterMateMutationService,
    AbstractMeterMateAdminService,
)


def test_cannot_instantiate_abstract_base():
    """Test that abstract base cannot be instantiated."""
    with pytest.raises(TypeError):
        AbstractMeterMateService(Mock(), Mock())


def test_derived_class_must_implement_abstract_methods():
    """Test that derived classes must implement required methods."""
    class IncompleteService(AbstractMeterMateService):
        @property
        def service(self):
            return "test"

    with pytest.raises(TypeError):
        IncompleteService(Mock(), Mock())


async def test_query_service_registers_with_response_support(hass):
    """Test that query services register with response support."""
    class TestQueryService(AbstractMeterMateQueryService):
        @property
        def service(self):
            return "test_query"

        @property
        def schema(self):
            return {}

        async def async_handle_service(self, call):
            return {"result": "data"}

    service = TestQueryService(hass, Mock())
    service.async_register()

    # Verify service is registered
    assert hass.services.has_service("metermate", "test_query")


async def test_mutation_service_logs_operations(hass, caplog):
    """Test that mutation services log operations."""
    import logging
    caplog.set_level(logging.INFO)

    class TestMutationService(AbstractMeterMateMutationService):
        @property
        def service(self):
            return "test_mutation"

        @property
        def schema(self):
            return {}

        async def _async_execute(self, call):
            pass

    service = TestMutationService(hass, Mock())
    await service.async_handle_service(Mock(data={"entity_id": "sensor.test"}))

    # Verify logging
    assert any("test_mutation called" in record.message for record in caplog.records)
```

---

## Design Decisions

### Why Abstract Base Classes?

**Rationale**: Python's ABC module provides compile-time checking that derived classes implement required methods, catching errors early.

**Alternatives Considered**:
- Duck typing (rejected: no validation)
- Interfaces (rejected: not Pythonic)
- Mixins (considered for future enhancements)

### Why Separate Query/Mutation/Admin?

**Rationale**: Different service types have different requirements:
- Queries need response support
- Mutations need operation logging
- Admin services need permission checks

**Benefits**:
- Clear categorization
- Appropriate registration for each type
- Consistent patterns within categories

### Why Helper Methods in Base?

**Rationale**: Entity existence checking is common to nearly all services, so centralizing it reduces code duplication.

**Trade-off**: Base class is slightly more complex, but derived classes are much simpler.

---

## Success Criteria

### Must Have ✅
- [ ] All base classes implemented in `services/base.py`
- [ ] Abstract methods clearly defined
- [ ] Helper methods well-documented
- [ ] Registration methods for each service type
- [ ] Comprehensive docstrings

### Should Have 🎯
- [ ] Unit tests for base classes
- [ ] Usage examples for each type
- [ ] Type hints throughout
- [ ] Integration with existing services

### Nice to Have ✨
- [ ] Mixins for additional functionality
- [ ] Service metadata support
- [ ] Performance monitoring hooks
- [ ] Service dependency injection

---

## Related Documents

- **[Service Categorization](service-categorization.md)**: How services are categorized
- **[Service Module Structure](service-module-structure.md)**: Where these classes are used
- **[Phase 2 Migration Guide](phase-2-migration-guide.md)**: Implementation timeline

---

## References

- Python ABC documentation: https://docs.python.org/3/library/abc.html
- Home Assistant service registration: https://developers.home-assistant.io/docs/dev_101_services
- Admin services: https://developers.home-assistant.io/docs/dev_101_services/#admin-only-services

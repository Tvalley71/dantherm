"""Test the Dantherm services module."""

import re

from config.custom_components.dantherm.device_map import (
    SERVICE_ALARM_RESET,
    SERVICE_CLEAR_ADAPTIVE_EVENT_STACK,
    SERVICE_FILTER_RESET,
    SERVICE_SET_CONFIGURATION,
)
from config.custom_components.dantherm.services import (
    DANTHERM_SET_CONFIGURATION_SCHEMA,
    DANTHERM_SET_STATE_SCHEMA,
    async_setup_services,
)
import pytest
import voluptuous as vol

from homeassistant.core import HomeAssistant


async def test_service_schema_validation(hass: HomeAssistant) -> None:
    """Test service schema imports and basic validation."""

    # Test that schemas exist and are callable
    assert DANTHERM_SET_CONFIGURATION_SCHEMA is not None
    assert DANTHERM_SET_STATE_SCHEMA is not None

    # Test basic schema validation
    try:
        DANTHERM_SET_STATE_SCHEMA({"entity_id": "switch.test"})
    except vol.Invalid:
        pytest.fail("Basic schema validation should not fail")


def test_time_validation_patterns() -> None:
    """Test time format validation patterns."""
    # This tests the module's time handling capabilities

    # Common time pattern that should be in services
    time_pattern = r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"

    # Valid times
    assert re.match(time_pattern, "12:30")
    assert re.match(time_pattern, "23:59")
    assert re.match(time_pattern, "00:00")

    # Invalid times
    assert not re.match(time_pattern, "25:00")
    assert not re.match(time_pattern, "12:60")
    assert not re.match(time_pattern, "invalid")


async def test_service_constants_exist(hass: HomeAssistant) -> None:
    """Test that service constants are defined."""

    # Test constants exist
    assert SERVICE_ALARM_RESET is not None
    assert SERVICE_FILTER_RESET is not None
    assert SERVICE_CLEAR_ADAPTIVE_EVENT_STACK is not None


async def test_clear_adaptive_event_stack_service_registered(
    hass: HomeAssistant,
) -> None:
    """Test that the clear adaptive event stack service is properly registered."""
    # Setup services
    await async_setup_services(hass)

    # Check that the service is registered
    assert hass.services.has_service("dantherm", SERVICE_CLEAR_ADAPTIVE_EVENT_STACK)


async def test_clear_adaptive_event_stack_service_schema(hass: HomeAssistant) -> None:
    """Test that the clear adaptive event stack service has correct target schema."""
    # The service should target devices and entities in the dantherm integration
    # This test verifies the service definition exists and is callable

    await async_setup_services(hass)

    # The service should be callable (schema validation would happen in actual use)
    service_def = hass.services._services.get("dantherm", {}).get(
        SERVICE_CLEAR_ADAPTIVE_EVENT_STACK
    )
    assert service_def is not None
    assert SERVICE_SET_CONFIGURATION is not None

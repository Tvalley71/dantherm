"""Platform integration tests for Dantherm components."""

from unittest.mock import AsyncMock

from config.custom_components.dantherm.button import (
    async_setup_entry as async_setup_button,
)
from config.custom_components.dantherm.const import DOMAIN
from config.custom_components.dantherm.sensor import (
    async_setup_entry as async_setup_sensor,
)
import pytest


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
class TestPlatformIntegration:
    """Test platform setup and integration without full integration loading."""

    async def test_sensor_platform_setup(
        self,
        hass,
        mock_device_with_all_capabilities,
        mock_platform_setup,
    ) -> None:
        """Test sensor platform can be set up successfully."""
        # Mock hass.data for sensor platform
        hass.data = {DOMAIN: {"test_entry": {"device": mock_device_with_all_capabilities}}}

        mock_config_entry = AsyncMock()
        mock_config_entry.entry_id = "test_entry"

        result = await async_setup_sensor(
            hass, mock_config_entry, mock_platform_setup["add_entities"]
        )
        assert result is True

    async def test_button_platform_setup(
        self,
        hass,
        mock_device_with_all_capabilities,
        mock_platform_setup,
    ) -> None:
        """Test button platform can be set up successfully."""
        # Mock hass.data for button platform
        hass.data = {DOMAIN: {"test_entry": {"device": mock_device_with_all_capabilities}}}

        mock_config_entry = AsyncMock()
        mock_config_entry.entry_id = "test_entry"

        result = await async_setup_button(
            hass, mock_config_entry, mock_platform_setup["add_entities"]
        )
        assert result is True

    async def test_platform_setup_no_device(self, hass) -> None:
        """Test platform setup fails gracefully when device is missing."""
        # Mock hass.data with no device
        hass.data = {DOMAIN: {"test_entry": None}}

        mock_config_entry = AsyncMock()
        mock_config_entry.entry_id = "test_entry"

        result = await async_setup_sensor(hass, mock_config_entry, AsyncMock())
        assert result is False

    async def test_platform_setup_missing_entry(self, hass) -> None:
        """Test platform setup fails gracefully when entry is missing."""
        # Mock hass.data with missing entry
        hass.data = {DOMAIN: {}}

        mock_config_entry = AsyncMock()
        mock_config_entry.entry_id = "missing_entry"

        result = await async_setup_sensor(hass, mock_config_entry, AsyncMock())
        assert result is False

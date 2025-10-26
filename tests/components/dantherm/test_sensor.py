"""Test the Dantherm sensor platform."""

from unittest.mock import AsyncMock

from config.custom_components.dantherm.const import DOMAIN
from config.custom_components.dantherm.sensor import async_setup_entry

from homeassistant.core import HomeAssistant


async def test_sensor_setup_no_device(hass: HomeAssistant) -> None:
    """Test sensor setup when device is None."""
    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "test_entry"

    # Mock hass.data to return None for device
    hass.data = {DOMAIN: {"test_entry": None}}

    result = await async_setup_entry(hass, mock_config_entry, AsyncMock())
    assert result is False


async def test_sensor_setup_missing_device_object(hass: HomeAssistant) -> None:
    """Test sensor setup when device object is missing."""
    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "test_entry"

    # Mock hass.data to return entry without device
    hass.data = {DOMAIN: {"test_entry": {"something": "else"}}}

    result = await async_setup_entry(hass, mock_config_entry, AsyncMock())
    assert result is False


async def test_sensor_setup_success(hass: HomeAssistant) -> None:
    """Test successful sensor setup."""
    mock_device = AsyncMock()
    mock_device.async_install_entity.return_value = False  # No entities to install

    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "test_entry"

    # Mock hass.data to return valid device
    hass.data = {DOMAIN: {"test_entry": {"device": mock_device}}}

    mock_add_entities = AsyncMock()

    result = await async_setup_entry(hass, mock_config_entry, mock_add_entities)
    assert result is True
    # Should call with empty list since no entities are installed
    mock_add_entities.assert_called_once_with([], update_before_add=True)

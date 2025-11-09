"""Test the Dantherm button platform."""

from unittest.mock import AsyncMock

from config.custom_components.dantherm.button import DanthermButton, async_setup_entry
from config.custom_components.dantherm.const import DOMAIN

from homeassistant.core import HomeAssistant


async def test_button_setup_no_device(hass: HomeAssistant) -> None:
    """Test button setup when device is None."""
    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "test_entry"

    # Mock hass.data to return None for device
    hass.data = {DOMAIN: {"test_entry": None}}

    result = await async_setup_entry(hass, mock_config_entry, AsyncMock())
    assert result is False


async def test_button_setup_missing_device_object(hass: HomeAssistant) -> None:
    """Test button setup when device object is missing."""
    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "test_entry"

    # Mock hass.data to return entry without device
    hass.data = {DOMAIN: {"test_entry": {"something": "else"}}}

    result = await async_setup_entry(hass, mock_config_entry, AsyncMock())
    assert result is False


async def test_button_setup_success(hass: HomeAssistant) -> None:
    """Test successful button setup."""
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


async def test_button_press_action(hass: HomeAssistant) -> None:
    """Test button press calls coordinator method."""
    mock_device = AsyncMock()
    mock_description = AsyncMock()

    # Create button entity
    button = DanthermButton(mock_device, mock_description)

    # Mock the coordinator that the button will use
    mock_coordinator = AsyncMock()
    button.coordinator = mock_coordinator

    # Test press calls coordinator
    await button.async_press()
    mock_coordinator.async_set_entity_state.assert_called_once_with(button, None)

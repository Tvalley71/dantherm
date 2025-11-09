"""Test the Dantherm text platform."""

from unittest.mock import AsyncMock

from config.custom_components.dantherm.const import DOMAIN
from config.custom_components.dantherm.text import async_setup_entry

from homeassistant.core import HomeAssistant


async def test_text_setup_no_device(hass: HomeAssistant) -> None:
    """Test text setup when device is None."""
    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "test_entry"

    # Mock hass.data to return None for device
    hass.data = {DOMAIN: {"test_entry": None}}

    result = await async_setup_entry(hass, mock_config_entry, AsyncMock())
    assert result is False


async def test_text_setup_missing_device_object(hass: HomeAssistant) -> None:
    """Test text setup when device object is missing."""
    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "test_entry"

    # Mock hass.data to return entry without device
    hass.data = {DOMAIN: {"test_entry": {"something": "else"}}}

    result = await async_setup_entry(hass, mock_config_entry, AsyncMock())
    assert result is False


async def test_text_setup_success(hass: HomeAssistant) -> None:
    """Test successful text setup."""
    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "test_entry"

    # Mock device
    mock_device = AsyncMock()
    mock_device.async_install_entity = AsyncMock(return_value=True)

    # Mock hass.data with device
    hass.data = {DOMAIN: {"test_entry": {"device": mock_device}}}

    mock_add_entities = AsyncMock()

    result = await async_setup_entry(hass, mock_config_entry, mock_add_entities)
    assert result is True


async def test_text_setup_missing_entry(hass: HomeAssistant) -> None:
    """Test text setup when entry is missing from hass.data."""
    mock_config_entry = AsyncMock()
    mock_config_entry.entry_id = "missing_entry"

    # Mock hass.data without the entry
    hass.data = {DOMAIN: {}}

    result = await async_setup_entry(hass, mock_config_entry, AsyncMock())
    assert result is False

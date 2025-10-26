"""Test notification when filter_remain reaches zero."""

from unittest.mock import AsyncMock, MagicMock, patch

from config.custom_components.dantherm.device import DanthermDevice
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_filter_remain_notification(hass: HomeAssistant) -> None:
    """Test that a notification is sent when filter_remain is zero."""

    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="dantherm",
        title="Test",
        data={},
        options={},
        entry_id="test123",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    device = DanthermDevice(hass, "TestDevice", "localhost", 1, 1, 5, config_entry)
    device._options = {}  # Ensure notifications are not disabled

    # Mock coordinator with is_entity_installed returning True
    device.coordinator = MagicMock()
    device.coordinator.is_entity_installed.return_value = True

    # Patch the modbus read to return 0 for filter_remain and intercept helper
    with (
        patch.object(device, "_read_holding_uint32", return_value=0),
        patch(
            "config.custom_components.dantherm.device.async_create_key_value_notification",
            new=AsyncMock(),
        ) as mock_notify,
    ):
        await device.async_get_filter_remain()
        mock_notify.assert_awaited_once()
        args, _ = mock_notify.await_args
        assert args[0] is hass
        assert args[1] == "TestDevice"
        assert args[2] == "sensor"
        assert args[3] == "filter_remain"
        assert args[4] == 0

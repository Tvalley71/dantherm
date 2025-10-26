"""Test notification when alarm is triggered."""

from unittest.mock import AsyncMock, patch

from config.custom_components.dantherm.device import DanthermDevice
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_alarm_notification(hass: HomeAssistant) -> None:
    """Test that a notification is sent when alarm is triggered."""

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
    device._alarm = 0  # Simulate previous alarm state

    # Patch the modbus read to return 5 for alarm and intercept notification helper
    with (
        patch.object(device, "_read_holding_uint32", return_value=5),
        patch(
            "config.custom_components.dantherm.device.async_create_key_value_notification",
            new=AsyncMock(),
        ) as mock_notify,
    ):
        await device.async_get_alarm()
        # Verify the helper was called with expected arguments
        mock_notify.assert_awaited_once()
        args, _ = mock_notify.await_args
        assert args[0] is hass
        assert args[1] == "TestDevice"
        assert args[2] == "sensor"
        assert args[3] == "alarm"
        assert args[4] == 5

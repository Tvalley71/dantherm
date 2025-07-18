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

    # Patch the modbus read to return 5 for alarm
    with (
        patch.object(device, "_read_holding_uint32", return_value=5),
        patch.object(device, "_create_notification", new=AsyncMock()) as mock_notify,
    ):
        await device.async_get_alarm()
        mock_notify.assert_awaited_once_with("sensor", "alarm", 5)

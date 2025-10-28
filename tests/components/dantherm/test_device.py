"""Tests for Dantherm device functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

from config.custom_components.dantherm.device import DanthermDevice
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.mark.asyncio
async def test_set_alarm_reset_dismisses_notification(hass: HomeAssistant) -> None:
    """set_alarm_reset should dismiss the persistent notification and write reset value."""

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="dantherm",
        title="Test",
        data={},
        options={},
        entry_id="abc123",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    device = DanthermDevice(hass, "Dev", "localhost", 1, 1, 5, entry)
    device._alarm = 7

    with (
        patch(
            "config.custom_components.dantherm.device.async_dismiss_notification",
            new=AsyncMock(),
        ) as mock_dismiss,
        patch.object(device, "_write_holding_uint32", new=AsyncMock()) as mock_write,
    ):
        await device.set_alarm_reset()

        mock_dismiss.assert_awaited_once()
        # Validate the value written equals current alarm value
        assert mock_write.await_count == 1
        # args: (register, value)
        _, value = mock_write.await_args.args
        assert value == 7


@pytest.mark.asyncio
async def test_set_filter_reset_dismisses_notification(hass: HomeAssistant) -> None:
    """set_filter_reset should dismiss the filter notification and write default reset value 1."""

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="dantherm",
        title="Test",
        data={},
        options={},
        entry_id="def456",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    device = DanthermDevice(hass, "Dev", "localhost", 1, 1, 5, entry)

    with (
        patch(
            "config.custom_components.dantherm.device.async_dismiss_notification",
            new=AsyncMock(),
        ) as mock_dismiss,
        patch.object(device, "_write_holding_uint32", new=AsyncMock()) as mock_write,
    ):
        await device.set_filter_reset()

        mock_dismiss.assert_awaited_once()
        assert mock_write.await_count == 1
        _, value = mock_write.await_args.args
        assert value == 1


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


@pytest.mark.asyncio
async def test_set_night_mode_start_time_valid(hass: HomeAssistant) -> None:
    """Valid time should write hour and minute values to registers in order."""

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="dantherm",
        title="Test",
        data={},
        options={},
        entry_id="ghi789",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    device = DanthermDevice(hass, "Dev", "localhost", 1, 1, 5, entry)

    with patch.object(device, "_write_holding_uint32", new=AsyncMock()) as mock_write:
        await device.set_night_mode_start_time("22:15")

        assert mock_write.await_count == 2
        # Validate the order of written values: hours then minutes
        values = [call.args[1] for call in mock_write.await_args_list]
        assert values == [22, 15]


@pytest.mark.asyncio
async def test_set_night_mode_start_time_invalid(hass: HomeAssistant) -> None:
    """Invalid time should not perform any register writes."""

    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="dantherm",
        title="Test",
        data={},
        options={},
        entry_id="jkl012",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    device = DanthermDevice(hass, "Dev", "localhost", 1, 1, 5, entry)

    with patch.object(device, "_write_holding_uint32", new=AsyncMock()) as mock_write:
        await device.set_night_mode_start_time("99:99")
        mock_write.assert_not_awaited()

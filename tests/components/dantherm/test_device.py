"""Tests for notification dismissal helpers in Dantherm device actions."""

from unittest.mock import AsyncMock, patch

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

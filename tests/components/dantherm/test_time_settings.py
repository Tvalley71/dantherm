"""Tests for night mode time setters in Dantherm device."""

from unittest.mock import AsyncMock, patch

from config.custom_components.dantherm.device import DanthermDevice
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


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

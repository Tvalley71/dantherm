"""Tests for Dantherm device functionality."""

from time import monotonic
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.dantherm.device import DanthermDevice
from custom_components.dantherm.device_map import (
    ATTR_AFTER_HEATER_EXTRACT_SETPOINT,
    ATTR_AFTER_HEATER_ROOM_SETPOINT,
    ATTR_AFTER_HEATER_SUPPLY_SETPOINT,
    ATTR_ALARM_EVENT,
    ATTR_EXTRACT_TEMPERATURE,
    ATTR_ROOM_TEMPERATURE,
    ATTR_SUPPLY_TEMPERATURE,
    ComponentClass,
    DanthermEventEntityDescription,
)
from custom_components.dantherm.entity import DanthermEntity
from custom_components.dantherm.event import DanthermEvent
from custom_components.dantherm.modbus import Hac1ComponentClass
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.mark.asyncio
async def test_carbon_dioxide_sensor_filtering(hass: HomeAssistant) -> None:
    """Test that carbon dioxide readings use the sensor filter when enabled."""

    device = DanthermDevice(
        hass,
        "TestDevice",
        "localhost",
        1,
        1,
        5,
        MockConfigEntry(domain="dantherm"),
    )
    device._sensor_filtering = True

    with patch.object(
        device,
        "_read_holding_uint32",
        side_effect=[800, 800, 800, 800, 800, 1000],
    ):
        for _ in range(5):
            assert await device.async_get_carbon_dioxide() == 800

        assert await device.async_get_carbon_dioxide() == 800


@pytest.mark.asyncio
async def test_carbon_dioxide_sensor_filtering_disabled(
    hass: HomeAssistant,
) -> None:
    """Test that carbon dioxide readings are not filtered when disabled."""

    device = DanthermDevice(
        hass,
        "TestDevice",
        "localhost",
        1,
        1,
        5,
        MockConfigEntry(domain="dantherm"),
    )

    with patch.object(device, "_read_holding_uint32", return_value=1000):
        assert await device.async_get_carbon_dioxide() == 1000


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
            "custom_components.dantherm.device.async_dismiss_notification",
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
            "custom_components.dantherm.device.async_dismiss_notification",
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
    device._alarm_test_cycle_started_at = monotonic() - 61

    # Patch the modbus read to return 5 for alarm and intercept notification helper
    with (
        patch.object(device, "_read_holding_uint32", return_value=5),
        patch(
            "custom_components.dantherm.device.async_create_key_value_notification",
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
        assert args[4] == "5"


async def test_event_entity_uses_base_lifecycle_and_registers_device(
    hass: HomeAssistant,
) -> None:
    """Event entities should use the base coordinator lifecycle once and register with device."""

    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain="dantherm",
        title="Test",
        data={},
        options={},
        entry_id="event123",
        source="user",
        unique_id=None,
        discovery_keys={},
        subentries_data={},
    )
    device = DanthermDevice(hass, "TestDevice", "localhost", 1, 1, 5, config_entry)
    device.coordinator = MagicMock()
    device.coordinator.async_add_entity = AsyncMock()
    device.coordinator.async_remove_entity = AsyncMock()

    entity = DanthermEvent(
        device,
        DanthermEventEntityDescription(
            key=ATTR_ALARM_EVENT,
            icon="mdi:alert-circle",
            event_types=["alarm_supply_air"],
        ),
    )

    with patch.object(
        DanthermEntity,
        "async_added_to_hass",
        wraps=DanthermEntity.async_added_to_hass,
    ) as mock_added:
        await entity.async_added_to_hass()

    mock_added.assert_awaited_once()
    device.coordinator.async_add_entity.assert_awaited_once_with(entity)
    assert device._event_entities[ATTR_ALARM_EVENT] is entity

    with patch.object(
        DanthermEntity,
        "async_will_remove_from_hass",
        wraps=DanthermEntity.async_will_remove_from_hass,
    ) as mock_removed:
        await entity.async_will_remove_from_hass()

    mock_removed.assert_awaited_once()
    device.coordinator.async_remove_entity.assert_awaited_once_with(entity)
    assert ATTR_ALARM_EVENT not in device._event_entities


@pytest.mark.asyncio
async def test_alarm_event_includes_alarm_code_and_alarm_text(
    hass: HomeAssistant,
) -> None:
    """Test that alarm events include alarm code and alarm text in attributes."""

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
    device._options = {}
    device._alarm = 0
    device._alarm_test_cycle_started_at = monotonic() - 61

    with (
        patch.object(device, "_read_holding_uint32", return_value=5),
        patch(
            "custom_components.dantherm.device.async_create_key_value_notification",
            new=AsyncMock(),
        ),
        patch(
            "custom_components.dantherm.device.async_get_translated_state_text",
            new=AsyncMock(return_value="HCC 2 ALU"),
        ),
        patch.object(device, "fire_event") as mock_fire_event,
    ):
        await device.async_get_alarm()

    mock_fire_event.assert_called_once_with(
        ATTR_ALARM_EVENT,
        "alarm_supply_air",
        {"alarm_code": 5, "alarm_text": "HCC 2 ALU"},
    )


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

    # Patch reads so filter remain level computes to 3 and triggers a notification
    with (
        patch.object(device, "_read_holding_uint32", side_effect=[30, 0]),
        patch(
            "custom_components.dantherm.device.async_create_key_value_notification",
            new=AsyncMock(),
        ) as mock_notify,
    ):
        await device.async_get_filter_state()
        mock_notify.assert_awaited_once()
        args, _ = mock_notify.await_args
        assert args[0] is hass
        assert args[1] == "TestDevice"
        assert args[2] == "sensor"
        assert args[3] == "filter_remain"
        assert args[4] == "0"


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


async def test_after_heater_disabled_setpoints_return_false(
    hass: HomeAssistant, standard_config_entry: MockConfigEntry
) -> None:
    """Zero setpoints should be ignored when HRC2 is not installed."""
    device = DanthermDevice(
        hass, "TestDevice", "localhost", 502, 1, 5, standard_config_entry
    )
    entity_states = {
        ATTR_SUPPLY_TEMPERATURE: None,
        ATTR_AFTER_HEATER_SUPPLY_SETPOINT: 0,
        ATTR_EXTRACT_TEMPERATURE: None,
        ATTR_AFTER_HEATER_EXTRACT_SETPOINT: 0,
    }

    device.hac1_active_components = Hac1ComponentClass.AfterHeater
    with (
        patch.object(
            device,
            "async_get_entity_state",
            new=AsyncMock(side_effect=entity_states.get),
        ),
    ):
        assert await device.async_get_after_heater_active() is False


async def test_after_heater_missing_temperature_returns_none(
    hass: HomeAssistant, standard_config_entry: MockConfigEntry
) -> None:
    """An enabled setpoint with no corresponding reading should be unknown."""
    device = DanthermDevice(
        hass, "TestDevice", "localhost", 502, 1, 5, standard_config_entry
    )
    entity_states = {
        ATTR_SUPPLY_TEMPERATURE: None,
        ATTR_AFTER_HEATER_SUPPLY_SETPOINT: 20,
        ATTR_EXTRACT_TEMPERATURE: 18,
        ATTR_AFTER_HEATER_EXTRACT_SETPOINT: 0,
    }

    device.hac1_active_components = Hac1ComponentClass.AfterHeater
    with (
        patch.object(
            device,
            "async_get_entity_state",
            new=AsyncMock(side_effect=entity_states.get),
        ),
    ):
        assert await device.async_get_after_heater_active() is None


async def test_after_heater_checks_room_setpoint_with_hrc2(
    hass: HomeAssistant, standard_config_entry: MockConfigEntry
) -> None:
    """The room setpoint should be checked when HRC2 is installed."""
    device = DanthermDevice(
        hass, "TestDevice", "localhost", 502, 1, 5, standard_config_entry
    )
    device.installed_components = ComponentClass.HRC2
    device.hac1_active_components = Hac1ComponentClass.AfterHeater
    entity_states = {
        ATTR_SUPPLY_TEMPERATURE: None,
        ATTR_AFTER_HEATER_SUPPLY_SETPOINT: 0,
        ATTR_EXTRACT_TEMPERATURE: None,
        ATTR_AFTER_HEATER_EXTRACT_SETPOINT: 0,
        ATTR_ROOM_TEMPERATURE: 18,
        ATTR_AFTER_HEATER_ROOM_SETPOINT: 20,
    }

    with (
        patch.object(
            device,
            "async_get_entity_state",
            new=AsyncMock(side_effect=entity_states.get),
        ),
    ):
        assert await device.async_get_after_heater_active() is True


async def test_after_heater_missing_hrc2_setpoint_returns_none(
    hass: HomeAssistant, standard_config_entry: MockConfigEntry
) -> None:
    """A missing room setpoint should make the HRC2-dependent result unavailable."""
    device = DanthermDevice(
        hass, "TestDevice", "localhost", 502, 1, 5, standard_config_entry
    )
    device.installed_components = ComponentClass.HRC2
    device.hac1_active_components = Hac1ComponentClass.AfterHeater
    entity_states = {
        ATTR_SUPPLY_TEMPERATURE: None,
        ATTR_AFTER_HEATER_SUPPLY_SETPOINT: 0,
        ATTR_EXTRACT_TEMPERATURE: None,
        ATTR_AFTER_HEATER_EXTRACT_SETPOINT: 0,
        ATTR_AFTER_HEATER_ROOM_SETPOINT: None,
    }

    with patch.object(
        device,
        "async_get_entity_state",
        new=AsyncMock(side_effect=entity_states.get),
    ):
        assert await device.async_get_after_heater_active() is None

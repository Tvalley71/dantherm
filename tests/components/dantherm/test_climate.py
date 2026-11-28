"""Tests for the Dantherm climate platform."""

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.dantherm.climate import DanthermClimate, async_setup_entry
from custom_components.dantherm.const import DOMAIN
from custom_components.dantherm.device import DanthermDevice
from custom_components.dantherm.device_map import CLIMATES
from custom_components.dantherm.entity import DanthermEntity
import pytest

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.const import PRECISION_TENTHS
from homeassistant.core import HomeAssistant


def create_climate() -> tuple[DanthermClimate, MagicMock]:
    """Create a climate entity with a mocked coordinator."""
    device = MagicMock()
    device._config_entry.entry_id = "test_entry"
    device.coordinator = MagicMock()
    device.coordinator.async_set_entity_state = AsyncMock()
    return DanthermClimate(device, CLIMATES[0]), device.coordinator


async def test_climate_setup_success() -> None:
    """Test successful climate platform setup."""
    hass = MagicMock(spec=HomeAssistant)
    config_entry = MagicMock(entry_id="test_entry")
    device = MagicMock()
    device.async_install_entity = AsyncMock(return_value=True)
    hass.data = {DOMAIN: {"test_entry": {"device": device}}}
    add_entities = MagicMock()

    assert await async_setup_entry(hass, config_entry, add_entities) is True
    assert [entity.key for entity in add_entities.call_args.args[0]] == [
        description.key for description in CLIMATES
    ]


async def test_climate_setup_without_device() -> None:
    """Test climate platform setup without a device."""
    hass = MagicMock(spec=HomeAssistant)
    config_entry = MagicMock(entry_id="test_entry")
    hass.data = {DOMAIN: {"test_entry": {}}}

    assert await async_setup_entry(hass, config_entry, AsyncMock()) is False


def test_climate_updates_state_from_coordinator() -> None:
    """Test current, target, mode, and action updates."""
    climate, _ = create_climate()

    with patch.object(DanthermEntity, "_coordinator_update"):
        climate._attr_changed = True
        climate._attr_new_state = {
            "current_temperature": 18.5,
            "target_temperature": 21,
            "heating": True,
        }
        climate._coordinator_update()

    assert climate.current_temperature == 18.5
    assert climate.precision == PRECISION_TENTHS
    assert climate.target_temperature == 21
    assert climate.hvac_mode == HVACMode.HEAT
    assert climate.hvac_action == HVACAction.HEATING


async def test_climate_turns_off_and_restores_target() -> None:
    """Test that turn off uses zero and turn on restores the target."""
    climate, coordinator = create_climate()

    await climate.async_set_temperature(temperature=24)
    await climate.async_set_hvac_mode(HVACMode.OFF)
    await climate.async_set_hvac_mode(HVACMode.HEAT)

    assert coordinator.async_set_entity_state.await_args_list[0].args[1] == 24
    assert coordinator.async_set_entity_state.await_args_list[1].args[1] == 0
    assert coordinator.async_set_entity_state.await_args_list[2].args[1] == 24
    assert climate.target_temperature == 24


def test_climate_off_state_keeps_last_positive_target() -> None:
    """Test that an off state remains restorable."""
    climate, _ = create_climate()

    with patch.object(DanthermEntity, "_coordinator_update"):
        climate._attr_changed = True
        climate._attr_new_state = {
            "current_temperature": 19,
            "target_temperature": 0,
            "heating": False,
        }
        climate._coordinator_update()

    assert climate.hvac_mode == HVACMode.OFF
    assert climate.hvac_action == HVACAction.OFF
    assert climate.target_temperature == 20


@pytest.mark.parametrize(
    ("method", "register"),
    [
        ("set_after_heater_supply_setpoint", 344),
        ("set_after_heater_extract_setpoint", 346),
        ("set_after_heater_room_setpoint", 348),
        ("set_carbon_dioxide_low_threshold", 568),
        ("set_carbon_dioxide_middle_threshold", 570),
        ("set_carbon_dioxide_high_threshold", 572),
    ],
)
async def test_set_hac_value(method: str, register: int) -> None:
    """Test writing each HAC value."""
    device = object.__new__(DanthermDevice)
    device._write_holding_uint32 = AsyncMock()

    await getattr(device, method)(21.8)

    device._write_holding_uint32.assert_awaited_once_with(register, 21)

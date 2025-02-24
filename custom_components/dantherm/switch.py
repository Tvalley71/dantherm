"""Switch implementation."""

from datetime import datetime
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .device import DanthermEntity, Device
from .device_map import SWITCHES, DanthermSwitchEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device_entry = hass.data[DOMAIN][config_entry.entry_id]
    if device_entry is None:
        _LOGGER.error("Device entry not found for %s", config_entry.entry_id)
        return False

    device = device_entry.get("device")
    if device is None:
        _LOGGER.error("Device object is missing in entry %s", config_entry.entry_id)
        return False

    entities = []
    for description in SWITCHES:
        if await device.async_install_entity(description):
            switch = DanthermSwitch(device, description)
            entities.append(switch)

    async_add_entities(entities, update_before_add=False)  # True
    return True


class DanthermSwitch(SwitchEntity, DanthermEntity):
    """Dantherm switch."""

    def __init__(
        self,
        device: Device,
        description: DanthermSwitchEntityDescription,
    ) -> None:
        """Init Number."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermSwitchEntityDescription = description

    @property
    def icon(self) -> str | None:
        """Switch icon."""

        if self._attr_is_on:
            return self.entity_description.icon_on
        return self.entity_description.icon_off

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""

        if self.entity_description.state_suspend_for:
            self.suspend_refresh(self.entity_description.state_suspend_for)

        self._attr_is_on = False
        state = self.entity_description.state_setoff
        if state is None:
            state = self.entity_description.state_off

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(state)
        elif self.entity_description.data_store:
            await self._device.set_entity_state(self.key, state)
        else:
            await self._device.write_holding_registers(
                description=self.entity_description, value=state
            )

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""

        if self.entity_description.state_suspend_for:
            self.suspend_refresh(self.entity_description.state_suspend_for)

        self._attr_is_on = True
        state = self.entity_description.state_seton
        if state is None:
            state = self.entity_description.state_on

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(state)
        elif self.entity_description.data_store:
            await self._device.set_entity_state(self.key, state)
        else:
            await self._device.write_holding_registers(
                description=self.entity_description, value=state
            )

    async def async_update(self) -> None:
        """Update the state of the switch."""

        if self.attr_suspend_refresh:
            if self.attr_suspend_refresh > datetime.now():
                _LOGGER.debug("Skipping suspened entity=%s", self.name)
                return

        if self.entity_description.data_getinternal:
            if hasattr(
                self._device, f"async_{self.entity_description.data_getinternal}"
            ):
                func = getattr(
                    self._device, f"async_{self.entity_description.data_getinternal}"
                )
                result = await func()
            else:
                result = getattr(self._device, self.entity_description.data_getinternal)
        elif self.entity_description.data_store:
            result = self._device.get_entity_state(
                self.key, self.entity_description.data_default
            )
        else:
            result = await self._device.read_holding_registers(
                description=self.entity_description
            )

        if result is None:
            self._attr_available = False
            self._device.data[self.key] = None
        else:
            self._attr_available = True
            if isinstance(result, bool):
                self._attr_is_on = result
            elif (
                result & self.entity_description.state_on
            ) == self.entity_description.state_on:
                self._attr_is_on = True
            else:
                self._attr_is_on = False

            self._device.data[self.key] = self._attr_is_on

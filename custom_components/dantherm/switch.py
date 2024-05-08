"""."""

from datetime import datetime
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SWITCH_TYPES, DanthermSwitchEntityDescription
from .device import DanthermEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for entity_description in SWITCH_TYPES.values():
        if await device.async_install_entity(entity_description):
            switch = DanthermSwitch(device, entity_description)
            entities.append(switch)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermSwitch(SwitchEntity, DanthermEntity):
    """Dantherm switch."""

    def __init__(
        self,
        device,
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
        else:
            await self._device.write_holding_registers(
                description=self.entity_description, value=state
            )

    async def async_update(self) -> None:
        """Read holding register."""

        if self.attr_suspend_refresh:
            if self.attr_suspend_refresh > datetime.now():
                _LOGGER.debug("Skipping suspened entity=%s", self.name)
                return

        if self.entity_description.data_getinternal:
            result = getattr(self._device, self.entity_description.data_getinternal)
        elif self.entity_description.data_entity:
            result = self._device.data.get(self.entity_description.data_entity, None)
        else:
            result = await self._device.read_holding_registers(
                description=self.entity_description
            )

        if result is None:
            self._attr_available = False
        else:
            self._attr_available = True
            if (
                result & self.entity_description.state_on
            ) == self.entity_description.state_on:
                self._attr_is_on = True
            else:
                self._attr_is_on = False

"""."""

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant

from . import DanthermEntity
from .const import DOMAIN, SWITCH_TYPES, DanthermSwitchEntityDescription

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

    # async def async_added_to_hass(self):
    #     """Register entity for ."""
    #     self._device.async_add_refresh_entity(self)

    # async def async_will_remove_from_hass(self) -> None:
    #     """Unregister callbacks."""
    #     self._device.async_remove_refresh_entity(self)

    @property
    def unique_id(self) -> str | None:
        """Return the unique id."""
        return f"dantherm_{self._key}"

    @property
    def _key(self) -> str:
        """Return the key name."""
        return self.entity_description.key

    @property
    def translation_key(self) -> str:
        """Return the translation key name."""
        return self._key

    @property
    def icon(self) -> str | None:
        """Select icon."""
        if self._attr_is_on:
            return self.entity_description.icon_on
        return self.entity_description.icon_off

    async def async_turn_off(self, **kwargs):
        """Turn the entity off."""

        await self._device.write_holding_registers(
            description=self.entity_description, value=self.entity_description.state_off
        )
        self._attr_is_on = False

        if self.entity_description.data_entity:
            await self._device.async_refresh_entity(
                name=self.entity_description.data_entity
            )

    async def async_turn_on(self, **kwargs):
        """Turn the entity on."""

        await self._device.write_holding_registers(
            description=self.entity_description, value=self.entity_description.state_on
        )
        self._attr_is_on = True

        if self.entity_description.data_entity:
            await self._device.async_refresh_entity(
                name=self.entity_description.data_entity
            )

    async def async_update(self) -> None:
        """Read holding register."""

        if self.entity_description.data_entity:
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

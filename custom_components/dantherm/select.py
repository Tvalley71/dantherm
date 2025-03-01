"""Select implementation."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .device import DanthermEntity, Device
from .device_map import SELECTS, DanthermSelectEntityDescription

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
    for description in SELECTS:
        if await device.async_install_entity(description):
            select = DanthermSelect(device, description)
            entities.append(select)

    async_add_entities(entities, update_before_add=False)  # True
    return True


class DanthermSelect(SelectEntity, DanthermEntity):
    """Dantherm select."""

    def __init__(
        self,
        device: Device,
        description: DanthermSelectEntityDescription,
    ) -> None:
        """Init select."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermSelectEntityDescription = description

    @property
    def icon(self) -> str | None:
        """Return an icon."""

        result = super().icon
        if hasattr(self._device, f"get_{self.key}_icon"):
            result = getattr(self._device, f"get_{self.key}_icon")
        return result

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""

        if self.entity_description.data_setinternal:
            await getattr(self._device, self.entity_description.data_setinternal)(
                option
            )
        elif self.entity_description.data_store:
            await self._device.set_entity_state(self, self.key, option)
        elif option.isdigit():
            await self._device.write_holding_registers(
                description=self.entity_description, value=int(option)
            )

    async def async_update(self) -> None:
        """Update state of the select."""

        # Get the entity state
        result = await self._device.async_get_entity_state(self.entity_description)

        if result is None:
            self._attr_available = False
            self._attr_current_option = None
        else:
            self._attr_available = True
            if self.entity_description.data_bitwise_and:
                result &= self.entity_description.data_bitwise_and

            self._attr_current_option = str(result)

        self._device.data[self.key] = result

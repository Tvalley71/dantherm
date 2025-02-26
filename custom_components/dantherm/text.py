"""Text implementation."""

import logging
import re

from homeassistant.components.sensor import HomeAssistantError
from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import DanthermEntity, Device
from .device_map import TIMETEXTS, DanthermTimeTextEntityDescription

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for description in TIMETEXTS:
        if await device.async_install_entity(description):
            text = DanthermTimeText(device, description)
            entities.append(text)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermTimeText(TextEntity, DanthermEntity):
    """Dantherm time text."""

    def __init__(
        self,
        device: Device,
        description: DanthermTimeTextEntityDescription,
    ) -> None:
        """Init time text."""
        super().__init__(device)
        self._device = device
        self._attr_has_entity_name = True
        self.entity_description: DanthermTimeTextEntityDescription = description

    @property
    def native_value(self):
        """Return the state."""

        return self._device.data.get(self.key, None)

    async def async_update(self) -> None:
        """Update the state of the sensor."""

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

        if result is None:
            self._attr_available = False
        else:
            self._attr_available = True
            self._device.data[self.key] = result

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""

        if re.match(r"^([01]\d|2[0-3]):([0-5]\d)$", value):  # Validates HH:MM format
            if self.entity_description.data_setinternal:
                await getattr(self._device, self.entity_description.data_setinternal)(
                    value
                )
        else:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="invalid_timeformat"
            )

"""Sensor implementation."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant

from .__init__ import DanthermEntity
from .const import DOMAIN, SENSOR_TYPES, DanthermSensorEntityDescription
from .device import Device

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    """."""
    device = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for entity_description in SENSOR_TYPES.values():
        if await device.async_install_entity(entity_description):
            sensor = DanthermSensor(device, entity_description)
            entities.append(sensor)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermSensor(SensorEntity, DanthermEntity):
    """Dantherm sensor."""

    def __init__(
        self,
        device: Device,
        description: DanthermSensorEntityDescription,
    ) -> None:
        """Init sensor."""
        super().__init__(device)
        self._device = device
        self.has_entity_name = True
        self.entity_description: DanthermSensorEntityDescription = description

    async def async_added_to_hass(self):
        """Register entity for ."""
        self._device.async_add_refresh_entity(self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks."""
        self._device.async_remove_refresh_entity(self)

    @property
    def unique_id(self) -> str | None:
        """Return the unique id."""
        return f"dantherm_{self._key}"

    @property
    def native_value(self):
        """Return the state."""
        return self._device.data.get(self._key, None)

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
        """Return an icon."""
        if self.entity_description.data_icon_zero and not self._attr_state:
            return self.entity_description.data_icon_zero
        return super().icon

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
            self._device.data[self._key] = self._attr_state = result

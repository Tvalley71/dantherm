"""Sensor implementation."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SENSOR_TYPES, DanthermSensorEntityDescription
from .device import DanthermEntity, Device

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

    @property
    def native_value(self):
        """Return the state."""
        return self._device.data.get(self.key, None)

    @property
    def icon(self) -> str | None:
        """Return an icon."""

        result = super().icon
        if self.entity_description.data_zero_icon and not self._attr_state:
            result = self.entity_description.data_zero_icon
        elif self.entity_description.icon_internal:
            result = getattr(self._device, self.entity_description.icon_internal)

        return result

    async def async_update(self) -> None:
        """Read holding register."""

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
            self._device.data[self.key] = self._attr_state = result

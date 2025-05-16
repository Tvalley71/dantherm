"""Sensor implementation."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import DanthermDevice
from .device_map import SENSORS, DanthermSensorEntityDescription
from .entity import DanthermEntity

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
    for description in SENSORS:
        if await device.async_install_entity(description):
            sensor = DanthermSensor(device, description)
            entities.append(sensor)

    async_add_entities(entities, update_before_add=True)
    return True


class DanthermSensor(SensorEntity, DanthermEntity):
    """Dantherm sensor."""

    def __init__(
        self,
        device: DanthermDevice,
        description: DanthermSensorEntityDescription,
    ) -> None:
        """Init sensor."""
        super().__init__(device, description)
        self._attr_has_entity_name = True
        self._attr_icon = description.icon_zero or description.icon
        self.entity_description: DanthermSensorEntityDescription = description

    def _coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        super()._coordinator_update()

        if self._attr_changed:
            self._attr_native_value = self._attr_new_state

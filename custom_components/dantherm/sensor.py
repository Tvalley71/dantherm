"""Sensor implementation."""

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .device import DanthermEntity, Device
from .device_map import SENSORS, DanthermSensorEntityDescription

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

    async_add_entities(entities, update_before_add=False)  # True
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
        self._attr_has_entity_name = True
        self.entity_description: DanthermSensorEntityDescription = description

    @property
    def native_value(self):
        """Return the state."""

        return self._device.data.get(self.key, None)

    @property
    def icon(self) -> str | None:
        """Return an icon."""

        result = super().icon
        if hasattr(self._device, f"get_{self.key}_icon"):
            result = getattr(self._device, f"get_{self.key}_icon")
        elif self.entity_description.icon_zero and not self.native_value:
            result = self.entity_description.icon_zero

        return result

    async def async_update(self) -> None:
        """Update the state of the sensor."""

        if hasattr(self._device, f"async_get_{self.key}_attrs"):
            func = getattr(self._device, f"async_get_{self.key}_attrs")
            self._attr_extra_state_attributes = await func()
        elif hasattr(self._device, f"get_{self.key}_attrs"):
            self._attr_extra_state_attributes = getattr(
                self._device, f"get_{self.key}_attrs"
            )

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
        else:
            result = await self._device.read_holding_registers(
                description=self.entity_description
            )

        if result is None:
            self._attr_available = False
        else:
            self._attr_available = True
            self._device.data[self.key] = result

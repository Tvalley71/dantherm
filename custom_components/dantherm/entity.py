"""Entity implementation."""

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEFAULT_NAME, DOMAIN
from .device_map import DanthermEntityDescription


class DanthermEntity(CoordinatorEntity):
    """Dantherm Entity."""

    def __init__(self, device, description: DanthermEntityDescription) -> None:
        """Initialize the instance."""
        super().__init__(device.coordinator)
        self._device = device
        self._attr_unique_id = f"{self._device.get_device_name}_{description.key}"
        self._attr_should_poll = False
        self._attr_add_to_coordinator = True
        self._attr_available = False
        self._attr_changed = False
        self._attr_new_state = None
        self._attr_icon = description.icon
        self._attr_extra_state_attributes = None
        self._added_to_coordinator = False
        self.entity_description: DanthermEntityDescription = description

    async def async_added_to_hass(self):
        """Register entity in coordinator."""
        await super().async_added_to_hass()
        await self.coordinator.async_add_entity(self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister entity in coordinator."""
        await self.coordinator.async_remove_entity(self)

    @property
    def key(self) -> str:
        """Return the key name."""
        return self.entity_description.key

    @property
    def translation_key(self) -> str:
        """Return the translation key name."""
        return self.key

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self._device.available:
            return False
        return self._attr_available

    @property
    def device_info(self):
        """Device Info."""
        unique_id = self._device.get_device_name

        return {
            "identifiers": {
                (DOMAIN, unique_id),
            },
            "name": self._device.get_device_name,
            "manufacturer": DEFAULT_NAME,
            "model": self._device.get_device_type,
            "sw_version": self._device.get_device_fw_version,
            "serial_number": self._device.get_device_serial_number,
        }

    def _coordinator_update(self) -> None:
        """Update data from the coordinator."""

        if self._attr_available != self._device.available:
            self._attr_available = self._device.available
            self._attr_changed = True

        states = self.coordinator.data.get(self.key, None)
        if states:
            self._attr_changed = False
            new_state = states.get("state", None)
            if new_state is None:
                if self._attr_available:
                    self._attr_changed = True
                self._attr_available = False
            else:
                if not self._attr_available:
                    self._attr_changed = True
                self._attr_available = True

                if self._attr_new_state != new_state:
                    self._attr_changed = True
                    self._attr_new_state = new_state

            new_icon = states.get("icon", None)
            if new_icon is not None and new_icon != self._attr_icon:
                self._attr_changed = True
                self._attr_icon = new_icon

            new_attrs = states.get("attrs", None)
            if new_attrs is not None and new_attrs != self._attr_extra_state_attributes:
                self._attr_changed = True
                self._attr_extra_state_attributes = new_attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update from the coordinator."""

        self._coordinator_update()
        if self._attr_changed:
            self.async_write_ha_state()

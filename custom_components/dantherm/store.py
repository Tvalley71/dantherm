"""Store implementation."""

from homeassistant.components.http.auth import Store
from homeassistant.core import HomeAssistant


class DanthermStore:
    """Dantherm Store."""

    def __init__(
        self,
        hass: HomeAssistant,
        name,
    ) -> None:
        """Init store."""
        self._hass = hass
        self._entity_store = Store(hass, version=1, key=f"{name}_entities")
        self._stored_entities = {"entities": {}}

    async def async_load_entities(self):
        """Load stored entities."""
        store = await self._entity_store.async_load()
        if store is None:
            store = {"entities": {}}
        self._stored_entities = store

    async def async_save_entities(self):
        """Save entities to store."""
        await self._entity_store.async_save(self._stored_entities)

    async def async_store_entity_state(self, entity_key, value):
        """Store entity state."""
        self._stored_entities["entities"][entity_key] = value
        await self.async_save_entities()

    def get_stored_entity_state(self, entity_key, default=None):
        """Get stored entity state."""
        return self._stored_entities["entities"].get(entity_key, default)

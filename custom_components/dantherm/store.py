"""Store implementation."""

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store


class DanthermStore:
    """Dantherm Store."""

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
    ) -> None:
        """Init store."""
        self._hass = hass
        self._entity_store: Store[dict[str, Any]] = Store(
            hass, version=1, key=f"{name}_entities"
        )
        self._stored_entities: dict[str, Any] = {"entities": {}}

    async def async_load_entities(self) -> None:
        """Load stored entities."""
        store = await self._entity_store.async_load()
        if store is None:
            store = {"entities": {}}
        self._stored_entities = store

    async def async_save_entities(self) -> None:
        """Save entities to store."""
        await self._entity_store.async_save(self._stored_entities)

    async def async_store_entity_state(self, entity_key: str, value: Any) -> None:
        """Store entity state."""
        self._stored_entities["entities"][entity_key] = value
        await self.async_save_entities()

    def get_stored_entity_state(self, entity_key: str, default: Any = None) -> Any:
        """Get stored entity state."""
        return self._stored_entities["entities"].get(entity_key, default)

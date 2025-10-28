"""Test the Dantherm store functionality."""

from unittest.mock import patch

from config.custom_components.dantherm.store import DanthermStore

from homeassistant.core import HomeAssistant


class TestDanthermStore:
    """Test DanthermStore class."""

    def test_store_initialization(self, hass: HomeAssistant) -> None:
        """Test store initialization."""
        store = DanthermStore(hass, "TestDevice")

        assert store._hass is hass
        assert store._stored_entities == {"entities": {}}

    async def test_async_load_entities_new_store(self, hass: HomeAssistant) -> None:
        """Test loading entities from new store (no existing data)."""
        with patch("homeassistant.helpers.storage.Store.async_load") as mock_load:
            mock_load.return_value = None

            store = DanthermStore(hass, "TestDevice")
            await store.async_load_entities()

            assert store._stored_entities == {"entities": {}}
            mock_load.assert_called_once()

    async def test_async_load_entities_existing_store(
        self, hass: HomeAssistant
    ) -> None:
        """Test loading entities from existing store."""
        existing_data = {
            "entities": {
                "sensor_1": {"state": "on", "last_updated": "2023-10-27"},
                "sensor_2": {"state": "off", "last_updated": "2023-10-26"},
            }
        }

        with patch("homeassistant.helpers.storage.Store.async_load") as mock_load:
            mock_load.return_value = existing_data

            store = DanthermStore(hass, "TestDevice")
            await store.async_load_entities()

            assert store._stored_entities == existing_data
            mock_load.assert_called_once()

    async def test_async_save_entities(self, hass: HomeAssistant) -> None:
        """Test saving entities to store."""
        with patch("homeassistant.helpers.storage.Store.async_save") as mock_save:
            store = DanthermStore(hass, "TestDevice")
            store._stored_entities = {"entities": {"test": "data"}}

            await store.async_save_entities()

            mock_save.assert_called_once_with({"entities": {"test": "data"}})

    async def test_async_store_entity_state(self, hass: HomeAssistant) -> None:
        """Test storing individual entity state."""
        with patch("homeassistant.helpers.storage.Store.async_save") as mock_save:
            store = DanthermStore(hass, "TestDevice")

            await store.async_store_entity_state("sensor_1", {"state": "active"})

            assert store._stored_entities["entities"]["sensor_1"] == {"state": "active"}
            mock_save.assert_called_once()

    def test_get_stored_entity_state_existing(self, hass: HomeAssistant) -> None:
        """Test getting stored entity state that exists."""
        store = DanthermStore(hass, "TestDevice")
        store._stored_entities = {
            "entities": {
                "sensor_1": {"state": "on", "value": 42},
                "sensor_2": {"state": "off", "value": 0},
            }
        }

        result = store.get_stored_entity_state("sensor_1")
        assert result == {"state": "on", "value": 42}

    def test_get_stored_entity_state_missing_with_default(
        self, hass: HomeAssistant
    ) -> None:
        """Test getting stored entity state that doesn't exist with default."""
        store = DanthermStore(hass, "TestDevice")

        result = store.get_stored_entity_state("nonexistent", "default_value")
        assert result == "default_value"

    def test_get_stored_entity_state_missing_no_default(
        self, hass: HomeAssistant
    ) -> None:
        """Test getting stored entity state that doesn't exist without default."""
        store = DanthermStore(hass, "TestDevice")

        result = store.get_stored_entity_state("nonexistent")
        assert result is None

    async def test_store_workflow_integration(self, hass: HomeAssistant) -> None:
        """Test complete store workflow."""
        store = DanthermStore(hass, "TestDevice")

        # Load empty store
        await store.async_load_entities()
        assert store._stored_entities == {"entities": {}}

        # Store some data
        await store.async_store_entity_state("temp_sensor", {"value": 23.5})
        await store.async_store_entity_state("humidity_sensor", {"value": 65})

        # Verify data is stored
        assert store.get_stored_entity_state("temp_sensor") == {"value": 23.5}
        assert store.get_stored_entity_state("humidity_sensor") == {"value": 65}

        # Data should be persisted (using real Home Assistant storage in test environment)

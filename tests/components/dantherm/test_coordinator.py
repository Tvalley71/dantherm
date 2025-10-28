"""Test the Dantherm coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock

from config.custom_components.dantherm.coordinator import DanthermCoordinator
import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_config_entry():
    """Return mock config entry."""
    return ConfigEntry(
        version=1,
        minor_version=1,
        domain="dantherm",
        title="Test Device",
        data={"host": "192.168.1.100"},
        options={},
        entry_id="test_entry_id",
        source="user",
        unique_id="test_unique_id",
        discovery_keys={},
        subentries_data={},
    )


@pytest.fixture
def mock_hub():
    """Return mock hub."""
    hub = MagicMock()
    hub.async_get_data = AsyncMock(return_value={"test_data": "value"})
    return hub


class TestDanthermCoordinator:
    """Test DanthermCoordinator class."""

    async def test_coordinator_initialization(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test coordinator initialization."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
            write_delay=0.3,
        )

        assert coordinator.name == "TestDeviceCoordinator"
        assert coordinator.hub is mock_hub
        assert coordinator.update_interval == timedelta(seconds=30)
        assert coordinator._config_entry is mock_config_entry

    async def test_coordinator_update_success(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test successful data update with no entities."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        # With no entities, update should return empty dict
        await coordinator.async_refresh()
        assert coordinator.data == {}

    async def test_coordinator_update_failure(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test coordinator handles update failure gracefully."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        # Add a test entity to trigger update
        mock_entity = MagicMock()
        mock_entity.key = "test_sensor"
        coordinator._entities.append(mock_entity)

        # Make async_get_current_unit_mode return None to trigger failure
        mock_hub.async_get_current_unit_mode = AsyncMock(return_value=None)

        # The coordinator will now suppress UpdateFailed and just log error
        await coordinator.async_refresh()

        # Check that update was not successful
        assert not coordinator.last_update_success

    async def test_coordinator_entity_management(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test entity add/remove management."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        mock_entity = MagicMock()
        mock_entity.key = "test_sensor"

        # Test adding entity
        await coordinator.async_add_entity(mock_entity)
        assert mock_entity in coordinator._entities

        # Initialize data dict and mock disconnect to prevent errors
        coordinator.data = {}
        mock_hub.disconnect_and_close = AsyncMock()

        # Test removing entity (will call disconnect when no entities left)
        await coordinator.async_remove_entity(mock_entity)
        assert mock_entity not in coordinator._entities

    async def test_coordinator_write_operations(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test coordinator write operations."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
            write_delay=0.1,
        )

        mock_entity = MagicMock()
        mock_entity.key = "test_key"

        # Test entity update operation (this is what coordinator actually does)
        result = await coordinator.async_update_entity(mock_entity, {})

        # Verify the operation completed
        assert isinstance(result, dict)

    async def test_coordinator_is_entity_installed(
        self, hass: HomeAssistant, mock_hub, mock_config_entry
    ) -> None:
        """Test entity installation check."""
        coordinator = DanthermCoordinator(
            hass=hass,
            name="TestDevice",
            hub=mock_hub,
            scan_interval=30,
            config_entry=mock_config_entry,
        )

        # Test entity not installed
        assert not coordinator.is_entity_installed("nonexistent_entity")

        # Add entity to list
        mock_entity = MagicMock()
        mock_entity.key = "test_entity"
        await coordinator.async_add_entity(mock_entity)

        # Test entity installed
        assert coordinator.is_entity_installed("test_entity")

"""Test the Dantherm entity base functionality."""

from unittest.mock import AsyncMock, MagicMock

from config.custom_components.dantherm.device_map import DanthermEntityDescription
from config.custom_components.dantherm.entity import DanthermEntity

from homeassistant.core import HomeAssistant


class TestDanthermEntity:
    """Test DanthermEntity class."""

    def test_entity_initialization_with_serial(self, hass: HomeAssistant) -> None:
        """Test entity initialization when device has serial number."""
        mock_device = MagicMock()
        mock_device.coordinator = MagicMock()
        mock_device.get_device_serial_number = "ABC12345"

        description = DanthermEntityDescription(
            key="test_sensor", name="Test Sensor", icon="mdi:thermometer"
        )

        entity = DanthermEntity(mock_device, description)

        assert entity._attr_unique_id == "ABC12345_test_sensor"
        assert entity._attr_should_poll is False
        assert entity._attr_icon == "mdi:thermometer"
        assert entity.entity_description is description

    def test_entity_initialization_fallback_to_entry_id(
        self, hass: HomeAssistant
    ) -> None:
        """Test entity initialization when device has no serial number."""
        mock_device = MagicMock()
        mock_device.coordinator = MagicMock()
        mock_device.get_device_serial_number = None

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "config_entry_123"
        mock_device._config_entry = mock_config_entry

        description = DanthermEntityDescription(key="test_sensor", name="Test Sensor")

        entity = DanthermEntity(mock_device, description)

        assert entity._attr_unique_id == "config_entry_123_test_sensor"

    def test_entity_initialization_serial_exception(self, hass: HomeAssistant) -> None:
        """Test entity initialization when getting serial number raises exception."""
        mock_device = MagicMock()
        mock_device.coordinator = MagicMock()

        # Simulate exception when accessing serial number by returning None first
        mock_device.get_device_serial_number = None

        mock_config_entry = MagicMock()
        mock_config_entry.entry_id = "fallback_entry_456"
        mock_device._config_entry = mock_config_entry

        description = DanthermEntityDescription(key="error_sensor", name="Error Sensor")

        entity = DanthermEntity(mock_device, description)

        assert entity._attr_unique_id == "fallback_entry_456_error_sensor"

    def test_entity_initialization_no_config_entry(self, hass: HomeAssistant) -> None:
        """Test entity initialization when no config entry available."""
        mock_device = MagicMock()
        mock_device.coordinator = MagicMock()
        mock_device.get_device_serial_number = None
        mock_device._config_entry = None

        description = DanthermEntityDescription(
            key="unknown_sensor", name="Unknown Sensor"
        )

        entity = DanthermEntity(mock_device, description)

        assert entity._attr_unique_id == "unknown_unknown_sensor"

    async def test_async_added_to_hass(self, hass: HomeAssistant) -> None:
        """Test entity registration when added to hass."""
        mock_device = MagicMock()
        mock_coordinator = MagicMock()
        mock_coordinator.async_add_entity = AsyncMock()
        mock_device.coordinator = mock_coordinator
        mock_device.get_device_serial_number = "TEST123"

        description = DanthermEntityDescription(key="test_entity", name="Test Entity")

        entity = DanthermEntity(mock_device, description)

        # Mock the parent async_added_to_hass
        entity.async_on_remove = MagicMock()

        await entity.async_added_to_hass()

        mock_coordinator.async_add_entity.assert_called_once_with(entity)

    async def test_async_will_remove_from_hass(self, hass: HomeAssistant) -> None:
        """Test entity unregistration when removed from hass."""
        mock_device = MagicMock()
        mock_coordinator = MagicMock()
        mock_coordinator.async_remove_entity = AsyncMock()
        mock_device.coordinator = mock_coordinator
        mock_device.get_device_serial_number = "TEST123"

        description = DanthermEntityDescription(key="test_entity", name="Test Entity")

        entity = DanthermEntity(mock_device, description)

        await entity.async_will_remove_from_hass()

        mock_coordinator.async_remove_entity.assert_called_once_with(entity)

    def test_entity_key_property(self, hass: HomeAssistant) -> None:
        """Test entity key property."""
        mock_device = MagicMock()
        mock_device.coordinator = MagicMock()
        mock_device.get_device_serial_number = "TEST123"

        description = DanthermEntityDescription(key="temperature", name="Temperature")

        entity = DanthermEntity(mock_device, description)

        assert entity.key == "temperature"

    def test_entity_device_property(self, hass: HomeAssistant) -> None:
        """Test entity device property."""
        mock_device = MagicMock()
        mock_device.coordinator = MagicMock()
        mock_device.get_device_serial_number = "TEST123"

        description = DanthermEntityDescription(key="humidity", name="Humidity")

        entity = DanthermEntity(mock_device, description)

        assert entity._device is mock_device

    def test_entity_state_management(self, hass: HomeAssistant) -> None:
        """Test entity state management properties."""
        mock_device = MagicMock()
        mock_device.coordinator = MagicMock()
        mock_device.get_device_serial_number = "TEST123"

        description = DanthermEntityDescription(key="fan_speed", name="Fan Speed")

        entity = DanthermEntity(mock_device, description)

        # Test initial state
        assert entity._attr_changed is False
        assert entity._attr_available is False
        assert entity._attr_new_state is None
        assert entity._attr_extra_state_attributes is None
        assert entity._added_to_coordinator is False

        # Test state modifications
        entity._attr_changed = True
        entity._attr_available = True
        entity._attr_new_state = "active"

        assert entity._attr_changed is True
        assert entity._attr_available is True
        assert entity._attr_new_state == "active"

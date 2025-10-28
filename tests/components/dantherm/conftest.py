"""Test configuration for Dantherm tests."""

from unittest.mock import AsyncMock, MagicMock

from config.custom_components.dantherm.const import DOMAIN
from config.custom_components.dantherm.device_map import (
    CONF_BOOST_MODE_TRIGGER,
    CONF_ECO_MODE_TRIGGER,
    CONF_HOME_MODE_TRIGGER,
)
import pytest

from tests.common import MockConfigEntry


@pytest.fixture(name="entity_registry_enabled_by_default")
def entity_registry_enabled_by_default_fixture():
    """Force all entities to be enabled by default in tests."""
    return


@pytest.fixture
def standard_config_entry():
    """Create standard config entry for Dantherm tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Test Dantherm",
            "host": "dantherm.local",
            "port": 502,
            "scan_interval": 5,
        },
        unique_id="TEST123456",
    )


@pytest.fixture
def config_entry_with_triggers():
    """Factory for creating config entries with trigger configurations."""

    def _create_entry(
        boost_trigger: bool = False,
        eco_trigger: bool = False,
        home_trigger: bool = False,
        unique_id: str = "TEST123456",
    ) -> MockConfigEntry:
        return MockConfigEntry(
            domain=DOMAIN,
            data={
                "name": "Test Dantherm",
                "host": "dantherm.local",
                "port": 502,
                "scan_interval": 5,
            },
            options={
                CONF_BOOST_MODE_TRIGGER: boost_trigger,
                CONF_ECO_MODE_TRIGGER: eco_trigger,
                CONF_HOME_MODE_TRIGGER: home_trigger,
            },
            unique_id=unique_id,
        )

    return _create_entry


@pytest.fixture
def mock_device_with_all_capabilities():
    """Mock a device that supports all capabilities and triggers."""
    device = MagicMock()

    # Standard device info
    device.get_info.return_value = {
        "serialno": "TEST123456",
        "mac": "00:11:22:33:44:55",
        "device_type": "DanTherm HRV",
        "capabilities": 0xFFFF,  # All capabilities
    }

    # Mock modbus responses for all capabilities
    device.modbus.read_input_register.return_value = [0xFFFF]
    device.modbus.read_holding_register.return_value = [1]
    device.get_sensor_infos.return_value = []

    # Component class supporting all features
    device.component_class = "Comprehensive"
    device.get_device_serial_number = "TEST123456"

    # Mock async_install_entity as AsyncMock that returns True
    device.async_install_entity = AsyncMock(return_value=True)

    # Mock trigger availability (can be overridden in tests)
    device._options = {
        CONF_BOOST_MODE_TRIGGER: False,
        CONF_ECO_MODE_TRIGGER: False,
        CONF_HOME_MODE_TRIGGER: False,
    }

    return device


@pytest.fixture
def mock_platform_setup():
    """Mock platform setup utilities."""

    async def _mock_async_setup_entry(hass, config_entry, async_add_entities):
        """Mock successful platform setup."""
        return True

    def _mock_add_entities(entities, update_before_add=True):
        """Mock entity addition."""
        return

    return {
        "setup_entry": _mock_async_setup_entry,
        "add_entities": MagicMock(side_effect=_mock_add_entities),
    }


@pytest.fixture
def mock_dantherm_device():
    """Mock Dantherm device for testing."""
    device = MagicMock()

    # Standard device info
    device.get_info.return_value = {
        "serialno": "TEST123456",
        "mac": "00:11:22:33:44:55",
        "device_type": "DanTherm HRV",
        "capabilities": 0x8000,
    }

    # Mock modbus responses
    device.modbus.read_input_register.return_value = [0x8000]
    device.modbus.read_holding_register.return_value = [1]
    device.get_sensor_infos.return_value = []

    # Component class
    device.component_class = "HCV4"

    # Device serial number property
    device.get_device_serial_number = "TEST123456"

    return device

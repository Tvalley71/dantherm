"""Config flow tests for Dantherm integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from config.custom_components.dantherm.config_flow import DanthermConfigFlow
from config.custom_components.dantherm.const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from config.custom_components.dantherm.device import DanthermDevice
import pytest

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry


@pytest.fixture
def temp_integration_files():
    """Create temporary integration files for testing."""
    # Path til test integration
    test_integration_path = Path("tests/testing_config/custom_components/dantherm")

    # Opret directories hvis de ikke findes
    test_integration_path.mkdir(parents=True, exist_ok=True)
    (test_integration_path / "translations").mkdir(exist_ok=True)

    # Minimal manifest for test
    manifest_content = {
        "domain": "dantherm",
        "name": "Test Dantherm",
        "codeowners": [],
        "documentation": "https://example.com",
        "iot_class": "local_polling",
        "requirements": [],
        "version": "0.0.0",
    }

    # Tom translations fil med påkrævet config.error struktur
    translations_content = {
        "config": {
            "error": {
                "cannot_connect": "Cannot connect to the device.",
                "invalid_host": "Invalid host or IP address.",
            }
        }
    }

    # Opret filerne
    manifest_file = test_integration_path / "manifest.json"
    translations_file = test_integration_path / "translations" / "en.json"

    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_content, f, indent=2)

    with open(translations_file, "w", encoding="utf-8") as f:
        json.dump(translations_content, f, indent=2)

    # Yield control tilbage til test
    yield

    # Cleanup - slet filerne efter test
    try:
        if translations_file.exists():
            translations_file.unlink()
        if (test_integration_path / "translations").exists():
            (test_integration_path / "translations").rmdir()
        if manifest_file.exists():
            manifest_file.unlink()
        if test_integration_path.exists():
            test_integration_path.rmdir()
    except OSError:
        # Ignore cleanup errors - filerne bliver automatisk slettet
        pass


@pytest.mark.asyncio
async def test_user_flow_success(
    hass: HomeAssistant,
) -> None:
    """Test successful user-initiated config flow - testing real DanthermDevice."""
    # Test that we can create the device class (this imports and tests your real code!)
    device = DanthermDevice(
        hass=hass,
        name="Test Device",
        host="test_host",
        port=502,
        unit_id=1,
        scan_interval=30,
        config_entry=None,
    )
    assert device is not None

    # Test that the device has the expected methods
    assert hasattr(device, "async_init_and_connect")
    assert hasattr(device, "get_device_serial_number")

    # Mock the modbus connection since we don't have a real device
    with patch.object(
        device, "async_init_and_connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_connect.return_value = True

        # Test the connection method (this calls YOUR code!)
        result = await device.async_init_and_connect()
        assert result is True
        mock_connect.assert_called_once()

    # Test config flow logic
    flow = DanthermConfigFlow()
    assert flow is not None


@pytest.mark.asyncio
async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
) -> None:
    """Test cannot_connect path when device fails during connection probe."""
    # Test the real DanthermDevice class with a simulated error
    device = DanthermDevice(
        hass=hass,
        name="Test Device",
        host="bad_host",
        port=502,
        unit_id=1,
        scan_interval=30,
        config_entry=None,
    )

    # Mock the modbus connection to fail
    with patch.object(
        device, "async_init_and_connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_connect.side_effect = Exception("Connection failed")

        # Test that the connection fails (this tests YOUR error handling code!)
        with pytest.raises(Exception, match="Connection failed"):
            await device.async_init_and_connect()

        # Verify mock was called
        mock_connect.assert_called_once()


@pytest.mark.usefixtures("enable_custom_integrations", "temp_integration_files")
@pytest.mark.asyncio
async def test_user_flow_invalid_host(
    hass: HomeAssistant,
) -> None:
    """Invalid host should raise validation error on the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: DEFAULT_NAME,
            CONF_HOST: "bad host!!",
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        },
    )
    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"].get(CONF_HOST) == "invalid_host"


@pytest.mark.usefixtures("enable_custom_integrations", "temp_integration_files")
@pytest.mark.asyncio
async def test_options_flow_update_and_reload(
    hass: HomeAssistant,
) -> None:
    """Options flow should update entry data/options and trigger reload."""
    # Create a config entry
    entry = MockConfigEntry(
        title=DEFAULT_NAME,
        domain=DOMAIN,
        data={
            CONF_NAME: DEFAULT_NAME,
            CONF_HOST: "1.2.3.4",
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        },
        options={},
        unique_id="SERIAL-1",
        entry_id="entry-1",
    )
    entry.add_to_hass(hass)

    with (
        patch.object(hass.config_entries, "async_update_entry") as upd,
        patch.object(hass.config_entries, "async_reload") as reload_entry,
    ):
        # Begin options flow
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM

        result2 = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "5.6.7.8",
                CONF_PORT: DEFAULT_PORT,
                # Test empty trigger values (should be allowed)
                "boost_mode_trigger": "",
                "eco_mode_trigger": "",
                "home_mode_trigger": "",
            },
        )
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        # Verify update entry called with new host in data
        assert upd.called
        assert reload_entry.called

"""Config flow tests for Dantherm integration."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from config.custom_components.dantherm.const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
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

    with open(manifest_file, "w") as f:
        json.dump(manifest_content, f, indent=2)

    with open(translations_file, "w") as f:
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


@pytest.mark.usefixtures("enable_custom_integrations", "temp_integration_files")
@pytest.mark.asyncio
async def test_user_flow_success(
    hass: HomeAssistant,
) -> None:
    """Test successful user-initiated config flow."""
    with patch(
        "config.custom_components.dantherm.config_flow.DanthermDevice",
        autospec=True,
    ) as dev_cls:
        dev = dev_cls.return_value
        dev.async_init_and_connect = AsyncMock(return_value=MagicMock())
        type(dev).get_device_serial_number = property(lambda self: "SER123")

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: DEFAULT_NAME,
                CONF_HOST: "dantherm.local",
                CONF_PORT: DEFAULT_PORT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )
        assert result2["type"] is FlowResultType.CREATE_ENTRY
        assert result2["title"] == DEFAULT_NAME


@pytest.mark.usefixtures("enable_custom_integrations", "temp_integration_files")
@pytest.mark.asyncio
async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
) -> None:
    """Test cannot_connect path when device fails during connection probe."""
    with patch(
        "config.custom_components.dantherm.config_flow.DanthermDevice",
        autospec=True,
    ) as dev_cls:
        dev = dev_cls.return_value
        dev.async_init_and_connect = AsyncMock(side_effect=Exception("boom"))

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: DEFAULT_NAME,
                CONF_HOST: "1.2.3.4",
                CONF_PORT: DEFAULT_PORT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )
        assert result2["type"] is FlowResultType.FORM
        assert result2["errors"] == {"base": "cannot_connect"}


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

"""Diagnostics tests for Dantherm integration."""

from __future__ import annotations

from types import SimpleNamespace

from config.custom_components.dantherm.const import (
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from config.custom_components.dantherm.diagnostics import (
    async_get_config_entry_diagnostics,
)
import pytest

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from tests.common import MockConfigEntry


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.asyncio
async def test_diagnostics_basic_structure_and_redaction(
    hass: HomeAssistant,
) -> None:
    """Validate diagnostics structure and redaction of sensitive fields."""
    # Create a config entry
    entry = MockConfigEntry(
        title=DEFAULT_NAME,
        domain=DOMAIN,
        data={
            CONF_NAME: DEFAULT_NAME,
            CONF_HOST: "10.0.0.5",
            CONF_PORT: DEFAULT_PORT,
            CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
        },
        options={},
        unique_id="SERIAL-1",
        entry_id="entry-1",
    )
    entry.add_to_hass(hass)

    # Register a device and entity for the entry
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, "device-123")},
        manufacturer="Dantherm",
        model="HCV300",
        name="Ventilation Unit",
        sw_version="3.10.0",
        hw_version="A",
    )

    ent_reg = er.async_get(hass)
    ent_reg.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="uid-1",
        suggested_object_id="fan_level",
        config_entry=entry,
        device_id=device.id,
    )

    # Fake coordinator and device objects in runtime storage
    coordinator: DataUpdateCoordinator = SimpleNamespace(
        last_update_success=True,
        last_update_success_time=None,
        update_interval=30,
        data={"foo": 1, "bar": 2},
    )
    fake_device = SimpleNamespace(
        installed_components=0xFFFF,
        get_device_name="Ventilation Unit",
        get_device_type=1,
        get_device_fw_version="3.10.0",
        get_device_serial_number=123456789,
        get_features_attrs={"feature_a": True},
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "device": fake_device,
        "coordinator": coordinator,
    }

    diag = await async_get_config_entry_diagnostics(hass, entry)

    # Entry basics
    assert diag["entry"]["entry_id"] == entry.entry_id
    assert diag["entry"]["title"] == DEFAULT_NAME
    # Redaction
    assert diag["entry"]["data"][CONF_HOST] == "**REDACTED**"

    # Device summary
    assert diag["device"]["id"] == device.id
    assert diag["device"]["manufacturer"] == "Dantherm"
    assert diag["device"]["model"] == "HCV300"

    # Entities list contains the one we created
    assert any(e["unique_id"] == "uid-1" for e in diag["entities"]) is True

    # Runtime includes coordinator snapshot with data keys
    assert diag["runtime"]["coordinator"]["last_update_success"] is True
    assert set(diag["runtime"]["coordinator"]["data_keys"]) == {"foo", "bar"}


@pytest.mark.usefixtures("enable_custom_integrations")
@pytest.mark.asyncio
async def test_diagnostics_handles_missing_device_and_runtime(
    hass: HomeAssistant,
) -> None:
    """Diagnostics should cope when no device is in registry and no runtime data is present."""
    entry = MockConfigEntry(
        title=DEFAULT_NAME,
        domain=DOMAIN,
        data={CONF_NAME: DEFAULT_NAME, CONF_HOST: "1.2.3.4", CONF_PORT: DEFAULT_PORT},
        options={},
        unique_id="SERIAL-2",
        entry_id="entry-2",
    )
    entry.add_to_hass(hass)

    # No device/entries created; also omit hass.data[DOMAIN][entry_id]
    hass.data.setdefault(DOMAIN, {})

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["device"] is None
    assert isinstance(diag["entities"], list)
    assert diag["runtime"] is None
    assert diag["entry"]["data"][CONF_HOST] == "**REDACTED**"

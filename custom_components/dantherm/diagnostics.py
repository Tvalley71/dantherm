"""Diagnostics implementation."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_registry import EntityRegistry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN

TO_REDACT: set[str] = {CONF_HOST}


async def _gather_device_info(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any] | None:
    """Return basic device info for the config entry device."""
    dev_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    if not devices:
        return None
    # Only one device is expected
    device: DeviceEntry = devices[0]
    return {
        "id": device.id,
        "name": device.name,
        "manufacturer": device.manufacturer,
        "model": device.model,
        # Serial numbers may be sensitive; include but mark as redacted-like
        "serial_number_present": device.serial_number is not None,
        "sw_version": device.sw_version,
        "hw_version": device.hw_version,
        "connections": list(device.connections),
        "identifiers": list(device.identifiers),
    }


async def _gather_entities(
    hass: HomeAssistant, entry: ConfigEntry
) -> list[dict[str, Any]]:
    """Return a summary of entities registered for this config entry."""
    ent_reg: EntityRegistry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    return [
        {
            "entity_id": e.entity_id,
            "unique_id": e.unique_id,
            "platform": e.platform,
            "device_id": e.device_id,
            "disabled_by": e.disabled_by,
            "original_name": e.original_name,
            "original_device_class": e.original_device_class,
        }
        for e in entities
    ]


async def _gather_runtime(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any] | None:
    """Return a snapshot of coordinator data and relevant runtime details."""
    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(entry.entry_id)
    if not isinstance(entry_data, dict):
        return None
    coordinator: DataUpdateCoordinator | None = entry_data.get("coordinator")
    device = entry_data.get("device")

    runtime: dict[str, Any] = {}
    if coordinator:
        runtime["coordinator"] = {
            "last_update_success": coordinator.last_update_success,
            "last_update_success_time": getattr(
                coordinator, "last_update_success_time", None
            ),
            "update_interval": getattr(coordinator, "update_interval", None),
            "data_keys": list((coordinator.data or {}).keys()),
        }
    if device:
        # Avoid calling I/O in diagnostics; use readily available attributes only
        installed_components = getattr(device, "installed_components", None)
        features_map = getattr(device, "get_features_attrs", None)
        runtime["device"] = {
            "name": getattr(device, "get_device_name", None),
            "type": getattr(device, "get_device_type", None),
            "fw_version": getattr(device, "get_device_fw_version", None),
            # Do not include serial directly
            "serial_present": getattr(device, "get_device_serial_number", None)
            is not None,
            # Raw feature bitmask and expanded features (booleans per capability)
            "features_bitmask": (
                hex(installed_components)
                if isinstance(installed_components, int)
                else installed_components
            ),
            "features": features_map,
        }
    return runtime


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    redacted_data = async_redact_data(dict(entry.data), TO_REDACT)
    redacted_options = async_redact_data(dict(entry.options), TO_REDACT)

    device_info = await _gather_device_info(hass, entry)
    entities = await _gather_entities(hass, entry)
    runtime = await _gather_runtime(hass, entry)

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": redacted_data,
            "options": redacted_options,
            "state": entry.state.value,
            "disabled_by": entry.disabled_by,
        },
        "device": device_info,
        "entities": entities,
        "runtime": runtime,
        "version": {
            "domain": DOMAIN,
        },
    }

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
from .device_map import ATTR_CALENDAR
from .translations import async_get_adaptive_state_from_summary

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
        # Get adaptive manager and event stack if available
        event_stack_data = None
        if hasattr(device, "events") and device.events:
            try:
                event_stack_data = device.events.to_list()
            except (AttributeError, TypeError):
                event_stack_data = "Error retrieving event stack"

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
            "adaptive_event_stack": event_stack_data,
        }
    return runtime


def _extract_adaptive_state_from_summary(summary: str) -> str:
    """Extract adaptive state from summary text, return key format if found."""
    # This function is now a sync wrapper - the async work happens in _gather_calendar_data
    if not summary:
        return "**REDACTED**"
    return summary  # Will be processed async in _gather_calendar_data


async def _extract_adaptive_state_async(hass: HomeAssistant, summary: str) -> str:
    """Extract adaptive state from summary text using translations, return key format if found."""
    if not summary:
        return "**REDACTED**"

    # Use the existing translation function to find adaptive state
    state_key = await async_get_adaptive_state_from_summary(hass, summary)

    # If a state was found, return the key, otherwise redact
    return state_key if state_key else "**REDACTED**"


async def _gather_calendar_data(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any] | None:
    """Return calendar data with intelligent anonymization of adaptive states."""
    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(entry.entry_id)
    if not isinstance(entry_data, dict):
        return None

    calendar = entry_data.get(ATTR_CALENDAR)
    if not calendar:
        return None

    # Sammel basis kalender info
    calendar_info = {
        "entity_id": getattr(calendar, "entity_id", None),
        "unique_id": getattr(calendar, "unique_id", None),
        "storage_version": getattr(calendar, "_storage_version", None),
        "event_count": len(getattr(calendar, "_events", [])),
    }

    # Analyser events med intelligent anonymisering
    events = getattr(calendar, "_events", [])
    if events:
        event_stats = {
            "total_events": len(events),
            "recurring_events": sum(1 for e in events if getattr(e, "rrule", None)),
            "all_day_events": sum(1 for e in events if getattr(e, "all_day", False)),
            "events_with_description": sum(
                1 for e in events if getattr(e, "description", "")
            ),
            "events_with_exdate": sum(1 for e in events if getattr(e, "exdate", [])),
        }

        # Sammel event samples med intelligent anonymisering
        event_samples = []
        for i, event in enumerate(events):
            try:
                original_summary = getattr(event, "summary", "")
                # Use async function to extract adaptive state
                redacted_summary = await _extract_adaptive_state_async(
                    hass, original_summary
                )

                # Anonymiser sensitive data
                sample = {
                    "index": i,
                    "has_uid": bool(getattr(event, "uid", None)),
                    "summary_redacted": redacted_summary,
                    "description": "**REDACTED**",  # Altid redact beskrivelser
                    "has_rrule": bool(getattr(event, "rrule", None)),
                    "has_recurrence_id": bool(getattr(event, "recurrence_id", None)),
                    "exdate_count": len(getattr(event, "exdate", [])),
                    "all_day": getattr(event, "all_day", None),
                    "event_type": type(event).__name__,
                }

                # Tilføj tidsstempel info (anonymiseret)
                start = getattr(event, "start", None)
                end = getattr(event, "end", None)
                if start and end:
                    sample.update(
                        {
                            "start_type": type(start).__name__,
                            "end_type": type(end).__name__,
                            "has_timezone": hasattr(start, "tzinfo")
                            and start.tzinfo is not None
                            if hasattr(start, "tzinfo")
                            else False,
                        }
                    )

                event_samples.append(sample)
            except (AttributeError, TypeError, ValueError) as ex:
                event_samples.append(
                    {
                        "index": i,
                        "error": f"Failed to analyze event: {type(ex).__name__}",
                    }
                )

        calendar_info.update(
            {
                "statistics": event_stats,
                "event_samples": event_samples,
            }
        )

    return calendar_info


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    redacted_data = async_redact_data(dict(entry.data), TO_REDACT)
    redacted_options = async_redact_data(dict(entry.options), TO_REDACT)

    device_info = await _gather_device_info(hass, entry)
    entities = await _gather_entities(hass, entry)
    runtime = await _gather_runtime(hass, entry)
    calendar_data = await _gather_calendar_data(hass, entry)

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
        "calendar": calendar_data,
        "version": {
            "domain": DOMAIN,
        },
    }

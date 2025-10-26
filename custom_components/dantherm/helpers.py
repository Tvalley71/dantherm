"""Helper functions for the Dantherm integration."""

from datetime import UTC, date, datetime, timedelta
import re
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntryDisabler
from homeassistant.util.dt import now as ha_now, parse_datetime

from .const import DOMAIN


async def async_get_device_id_from_entity(hass: HomeAssistant, entity_id):
    """Find device_id from entity_id."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    entity = entity_registry.async_get(entity_id)
    if entity is None or entity.device_id is None:
        return None

    device_entry = device_registry.async_get(entity.device_id)
    if device_entry is None:
        return None

    return device_entry.id


def get_entities_by_device_and_suffix(
    hass: HomeAssistant, device_id: str, name_suffix: str, domain: str | None = None
) -> list[er.RegistryEntry]:
    """Safely get entities by device ID and name suffix.

    This is much safer than pattern matching on unique_id alone,
    as it ensures we only affect entities from the specific device.

    Args:
        hass: Home Assistant instance
        device_id: Device ID to scope the search to
        name_suffix: Suffix to match in unique_id (e.g., "temperature")
        domain: Optional domain filter (e.g., "sensor", "switch")

    Returns:
        List of matching entity registry entries
    """
    entity_registry = er.async_get(hass)

    # Get all entities for the specific device
    device_entities = er.async_entries_for_device(entity_registry, device_id, True)

    # Filter by domain if specified
    if domain:
        device_entities = [e for e in device_entities if e.domain == domain]

    # Pattern match on unique_id within device scope
    # Match suffix at end of unique_id, with optional numeric suffix
    pattern = re.compile(rf"{re.escape(name_suffix)}(_\d+)?$")
    return [
        entry
        for entry in device_entities
        if entry.unique_id and pattern.search(entry.unique_id)
    ]


def set_device_entities_enabled_by_suffix(
    hass: HomeAssistant,
    device_id: str,
    name_suffix: str,
    enable: bool,
    domain: str | None = None,
) -> int:
    """Enable/disable entities for a specific device by suffix.

    This is the SAFE version that only affects entities from the specified device.

    Args:
        hass: Home Assistant instance
        device_id: Device ID to scope the operation to
        name_suffix: Suffix to match in unique_id
        enable: True to enable, False to disable
        domain: Optional domain filter

    Returns:
        Number of entities affected
    """
    matched_entities = get_entities_by_device_and_suffix(
        hass, device_id, name_suffix, domain
    )

    count = 0
    for entry in matched_entities:
        try:
            if enable:
                __set_entity_disabled_by(hass, entry.entity_id, None)
            else:
                __set_entity_disabled_by(
                    hass, entry.entity_id, RegistryEntryDisabler.INTEGRATION
                )
            count += 1
        except (ValueError, KeyError):
            # Log error but continue with other entities
            # Only catch specific exceptions that could occur during entity updates
            pass

    return count


def get_device_entities_enabled_by_suffix(
    hass: HomeAssistant, device_id: str, name_suffix: str, domain: str | None = None
) -> bool:
    """Check if any entities for device with suffix are enabled.

    This is the SAFE version that only checks entities from the specified device.

    Args:
        hass: Home Assistant instance
        device_id: Device ID to scope the check to
        name_suffix: Suffix to match in unique_id
        domain: Optional domain filter

    Returns:
        True if any matching entities are enabled
    """
    matched_entities = get_entities_by_device_and_suffix(
        hass, device_id, name_suffix, domain
    )

    return any(not entry.disabled for entry in matched_entities)


def __set_entity_disabled_by(
    hass: HomeAssistant, entity_id, disabled_by: RegistryEntryDisabler
):
    """Set entity disabled by state."""

    entity_registry = er.async_get(hass)

    entity_registry.async_update_entity(
        entity_id,
        disabled_by=disabled_by,
    )


def as_dt(value: datetime | date) -> datetime:
    """Convert value to tz-aware datetime in local timezone.

    - Dates become local midnight
    - Naive datetimes become local tz
    - Microseconds are removed for stable comparisons
    """
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=ha_now().tzinfo)
        return dt.replace(microsecond=0)
    return (
        datetime.combine(value, datetime.min.time())
        .astimezone(ha_now().tzinfo)
        .replace(microsecond=0)
    )


def duration_dt(start: datetime | date, end: datetime | date) -> timedelta:
    """Compute duration using normalized datetimes."""
    return as_dt(end) - as_dt(start)


def parse_dt_or_date(value: Any) -> datetime | date:
    """Parse ISO string or passthrough date/datetime."""
    if isinstance(value, (datetime, date)):
        return value
    if isinstance(value, str):
        # Date-only (YYYY-MM-DD) → date
        if "T" not in value:
            return date.fromisoformat(value)
        # Datetime ISO → datetime (aware if includes TZ)
        return parse_datetime(value)
    return value


def _format_rrule_until(dt: datetime) -> str:
    """Return RFC 5545 UNTIL in UTC basic format (YYYYMMDDTHHMMSSZ)."""
    u = as_dt(dt).astimezone(UTC)
    return u.strftime("%Y%m%dT%H%M%SZ")


def _rrule_remove_param(rrule_str: str, key: str) -> str:
    """Remove a parameter from an RRULE string."""
    parts = [
        p for p in rrule_str.split(";") if p and not p.upper().startswith(f"{key}=")
    ]
    return ";".join(parts)


def _rrule_set_param(rrule_str: str, key: str, value: str) -> str:
    """Set or replace a parameter on an RRULE string."""
    parts = [
        p for p in rrule_str.split(";") if p and not p.upper().startswith(f"{key}=")
    ]
    parts.append(f"{key}={value}")
    return ";".join(parts)


def rrule_trim_until(rrule_str: str, until_dt: datetime) -> str:
    """Trim an RRULE by setting UNTIL (and removing COUNT)."""
    if not rrule_str:
        return rrule_str
    trimmed = _rrule_remove_param(rrule_str, "UNTIL")
    trimmed = _rrule_remove_param(trimmed, "COUNT")
    return _rrule_set_param(trimmed, "UNTIL", _format_rrule_until(until_dt))


def active_instance_count(hass: HomeAssistant) -> int:
    """Return count of active entries (loaded or in setup)."""
    return sum(
        1
        for e in hass.config_entries.async_entries(DOMAIN)
        if e.disabled_by is None
        and e.state in (ConfigEntryState.LOADED, ConfigEntryState.SETUP_IN_PROGRESS)
    )


def has_single_loaded_instance(hass: HomeAssistant) -> bool:
    """Return True if exactly one active instance is present."""
    active_count = active_instance_count(hass)
    return active_count == 1


def get_primary_entry_id(hass: HomeAssistant) -> str | None:
    """Return deterministic primary entry_id among active entries."""
    entries = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.disabled_by is None
    ]
    if not entries:
        return None
    active = [
        e
        for e in entries
        if e.state in (ConfigEntryState.LOADED, ConfigEntryState.SETUP_IN_PROGRESS)
    ]
    candidates = active or entries
    return min(e.entry_id for e in candidates)


def is_primary_entry(hass: HomeAssistant, entry_id: str) -> bool:
    """Return True if entry_id is primary."""
    return get_primary_entry_id(hass) == entry_id

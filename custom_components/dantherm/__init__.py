"""Dantherm Integration."""

import logging
from typing import Any, Final

from packaging import version
import pymodbus
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    EVENT_HOMEASSISTANT_STARTED,
    Platform,
)
from homeassistant.core import CoreState, Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr, entity_registry as er
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.storage import Store
from homeassistant.helpers.translation import async_get_translations

from .const import DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .device import DanthermDevice
from .device_map import (
    ATTR_CALENDAR,
    BUTTONS,
    CALENDAR,
    CONF_BOOST_MODE_TRIGGER,
    CONF_DISABLE_NOTIFICATIONS,
    CONF_DISABLE_TEMPERATURE_UNKNOWN,
    CONF_ECO_MODE_TRIGGER,
    CONF_HOME_MODE_TRIGGER,
    COVERS,
    NUMBERS,
    REQUIRED_PYMODBUS_VERSION,
    SELECTS,
    SENSORS,
    SWITCHES,
    TIMETEXTS,
)
from .discovery import async_discover
from .helpers import get_primary_entry_id, is_primary_entry
from .notifications import async_create_exception_notification
from .services import async_setup_services

# Constants only for migration use
ATTR_DISABLE_ALARM_NOTIFICATIONS: Final = "disable_alarm_notifications"
# Number of setup attempts before discovery is triggered. Discovery will only run once with
# each startup of Home Assistant.
DISCOVERY_TRIGGER_ATTEMPT: Final = 4
ATTR_SETUP_ATTEMPTS: Final = "setup_attempts"


_LOGGER = logging.getLogger(__name__)

DANTHERM_MODBUS_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PORT): cv.string,
        vol.Optional(
            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
        ): cv.positive_int,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({cv.slug: DANTHERM_MODBUS_SCHEMA})}, extra=vol.ALLOW_EXTRA
)

PLATFORMS = [
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.COVER,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

DEFAULT_OPTIONS = {
    CONF_HOME_MODE_TRIGGER: "",
    CONF_BOOST_MODE_TRIGGER: "",
    CONF_ECO_MODE_TRIGGER: "",
    CONF_DISABLE_TEMPERATURE_UNKNOWN: False,
    CONF_DISABLE_NOTIFICATIONS: False,
}


def get_expected_serial_for_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> str | None:
    """Get the expected serial number for a config entry."""
    dev_reg = dr.async_get(hass)
    devices = dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
    # Only 1 device is expected
    for dev in devices:
        if dev.serial_number is not None:
            return dev.serial_number
    return None


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the Dantherm component."""

    hass.data[DOMAIN] = {}
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Dantherm from a config entry."""

    if version.parse(pymodbus.__version__) < version.parse(REQUIRED_PYMODBUS_VERSION):
        translations = await async_get_translations(
            hass, hass.config.language, "dantherm"
        )
        message_template = translations.get("exceptions.pymodbus_version")

        if not message_template:
            message_template = "This integration requires pymodbus version %s or newer, but %s is installed"

        raise RuntimeError(
            message_template % (REQUIRED_PYMODBUS_VERSION, pymodbus.__version__)
        )

    options = dict(entry.options)
    # If options are empty, initialize them with defaults
    if not options:
        _LOGGER.warning("No stored options found, initializing defaults")
        hass.config_entries.async_update_entry(entry, options=DEFAULT_OPTIONS)

    _LOGGER.debug("Loading stored options in setup: %s", options)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(entry.entry_id, {})

    # Get the entry data
    entry_data = hass.data[DOMAIN][entry.entry_id]
    # Set the default number of setup attempts to 0 if not already set
    entry_data.setdefault(ATTR_SETUP_ATTEMPTS, 0)

    name = entry.data[CONF_NAME]
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    # Migration: Handle old scan_interval values for existing users
    scan_interval = entry.data[CONF_SCAN_INTERVAL]
    _LOGGER.debug("Current scan_interval: %s", scan_interval)

    # Ensure scan_interval is reasonable (between 5 and 300 seconds)
    if scan_interval < 5:
        _LOGGER.warning("Scan interval %s too low, setting to 5 seconds", scan_interval)
        scan_interval = 5
    elif scan_interval > 300:
        _LOGGER.warning(
            "Scan interval %s too high, setting to 300 seconds", scan_interval
        )
        scan_interval = 300

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    # Try to connect to the device at the configured address
    device = DanthermDevice(hass, name, host, port, 1, scan_interval, entry)
    try:
        coordinator = await device.async_init_and_connect()
        if coordinator is None:
            raise ConfigEntryNotReady("Failed to create coordinator")
    except ValueError as ex:
        if entry_data[ATTR_SETUP_ATTEMPTS] <= DISCOVERY_TRIGGER_ATTEMPT:
            entry_data[ATTR_SETUP_ATTEMPTS] += 1
        if entry_data[ATTR_SETUP_ATTEMPTS] == DISCOVERY_TRIGGER_ATTEMPT:
            _LOGGER.warning(
                "Could not connect to device at %s, starting discovery", host
            )
            # Only run discovery at startup, not on later disconnects
            discovered = await async_discover(hass, host)
            found = False
            for d in discovered:
                ip = d["ip"]

                expected_serial = get_expected_serial_for_entry(hass, entry)
                if not expected_serial:
                    _LOGGER.warning(
                        "No serial number found for device registry entry: %s",
                        entry.entry_id,
                    )
                    continue

                _LOGGER.debug("Serial from device registry: %s", expected_serial)

                test_device = DanthermDevice(
                    hass, name, ip, port, 1, scan_interval, entry
                )

                try:
                    coordinator = await test_device.async_init_and_connect()
                    if coordinator is None:
                        _LOGGER.warning(
                            "Failed to create coordinator for device at %s", ip
                        )
                        continue

                    # Match serial number read from the test device with the expected
                    # serial number from config entry
                    serial = test_device.get_device_serial_number
                    if str(serial) == expected_serial:
                        _LOGGER.info("Found device at new IP %s", ip)
                        # Update config entry with new IP
                        new_data = dict(entry.data)
                        new_data[CONF_HOST] = ip
                        hass.config_entries.async_update_entry(entry, data=new_data)
                        device = test_device
                        found = True

                        # Send a notification about the rediscovery
                        if not options.get(CONF_DISABLE_NOTIFICATIONS, False):
                            await async_create_exception_notification(
                                hass,
                                name,
                                "rediscovery",
                                domain=DOMAIN.capitalize(),
                                serial_number=str(serial),
                                ip_address=ip,
                            )
                        break
                    # If the serial numbers do not match, disconnect the test device
                    await test_device.disconnect_and_close()
                except Exception:  # noqa: BLE001
                    continue
            if not found:
                raise ConfigEntryNotReady("Device not found on network") from ex
        else:
            raise ConfigEntryNotReady(f"Timeout while connecting {host}") from ex

    hass.data[DOMAIN][entry.entry_id] = {
        "device": device,
        "coordinator": coordinator,
        CONF_BOOST_MODE_TRIGGER: options.get(CONF_BOOST_MODE_TRIGGER, ""),
        CONF_ECO_MODE_TRIGGER: options.get(CONF_ECO_MODE_TRIGGER, ""),
        CONF_HOME_MODE_TRIGGER: options.get(CONF_HOME_MODE_TRIGGER, ""),
        CONF_DISABLE_TEMPERATURE_UNKNOWN: options.get(
            CONF_DISABLE_TEMPERATURE_UNKNOWN, False
        ),
        CONF_DISABLE_NOTIFICATIONS: options.get(CONF_DISABLE_NOTIFICATIONS, False),
    }

    # Execute migration of entity unique_ids (backwards compatibility) only once
    if not entry.data.get("uids_migrated", False):
        migrated = await _async_migrate_unique_ids(hass, entry, device)
        if migrated:
            # Persist that we've migrated to avoid re-running on every startup
            new_data = dict(entry.data)
            new_data["uids_migrated"] = True
            hass.config_entries.async_update_entry(entry, data=new_data)

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    try:
        await device.async_start()
    except Exception:
        _LOGGER.exception("Failed to start device")
        return False

    async def _init_after_start(event: Event | None = None) -> None:
        """Initialize the device after Home Assistant has started."""
        hass.async_create_task(device.async_init_after_start())

    # If Home Assistant is already running, we can run the routine immediately
    if hass.state != CoreState.running:
        await _init_after_start()
    else:
        # Listen for the Home Assistant started event to run the routine
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _init_after_start)

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""

    _LOGGER.debug("Migrating from version %s", config_entry.version)
    options = dict(config_entry.options)

    # Migration: Move disable_alarm_notifications to disable_notifications
    if (
        CONF_DISABLE_NOTIFICATIONS not in options
        and ATTR_DISABLE_ALARM_NOTIFICATIONS in options
    ):
        options[CONF_DISABLE_NOTIFICATIONS] = options.pop(
            ATTR_DISABLE_ALARM_NOTIFICATIONS
        )
        hass.config_entries.async_update_entry(config_entry, options=options)
        _LOGGER.debug("Migrated disable_alarm_notifications to disable_notifications")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Check if this entry was primary before unload
    was_primary = is_primary_entry(hass, entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

        # Promote and reload new primary, so it can create shared calendar
        if was_primary:
            new_primary = get_primary_entry_id(hass)
            if new_primary and new_primary != entry.entry_id:
                hass.async_create_task(hass.config_entries.async_reload(new_primary))

    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Clean up persistent data when a config entry is removed."""
    # Remove per-instance calendar storage
    await Store(hass, 1, f"{DOMAIN}_calendar_{entry.entry_id}").async_remove()

    # Clear any runtime references (entity removal already runs, but be safe)
    domain_data = hass.data.get(DOMAIN, {})
    if isinstance(domain_data, dict):
        entry_data = domain_data.get(entry.entry_id)
        if isinstance(entry_data, dict):
            entry_data.pop(ATTR_CALENDAR, None)
        # If this entry owned the global calendar pointer, drop it
        if domain_data.get(ATTR_CALENDAR) is not None:
            try:
                owner_id = getattr(domain_data[ATTR_CALENDAR], "_config_entry_id", None)
            except (AttributeError, TypeError):
                owner_id = None
            if owner_id == entry.entry_id:
                domain_data.pop(ATTR_CALENDAR, None)


async def _async_migrate_unique_ids(
    hass: HomeAssistant, entry: ConfigEntry, device: DanthermDevice
) -> bool:
    """Migrate entity registry unique_ids to serial-based format.

    - Old format: often <name>_<key> or other prefixes
    - New format: <serial>_<key>
    Handles collisions by preferring canonical entities (without numeric suffix)
    and removing duplicate entities with numeric suffix that belong to the same
    config entry.
    """

    # Using module-level imports for callback, er and entity descriptions

    # Gather all known keys from entity descriptions
    keys: set[str] = set()
    try:
        keys.update(desc.key for desc in BUTTONS)
        keys.add(CALENDAR.key)
        keys.update(desc.key for desc in COVERS)
        keys.update(desc.key for desc in NUMBERS)
        keys.update(desc.key for desc in SELECTS)
        keys.update(desc.key for desc in SENSORS)
        keys.update(desc.key for desc in SWITCHES)
        keys.update(desc.key for desc in TIMETEXTS)
    except Exception:  # noqa: BLE001
        keys = set()

    serial = str(device.get_device_serial_number)
    ent_reg = er.async_get(hass)

    changed: bool = False

    @callback
    def _async_migrate_entity_entry(
        entry_to_migrate: er.RegistryEntry,
    ) -> dict[str, str] | None:
        uid = entry_to_migrate.unique_id
        # Already in the new format
        if uid.startswith(f"{serial}_"):
            return None

        for key in keys:
            suffix = f"_{key}"
            if uid.endswith(suffix):
                new_uid = f"{serial}_{key}"
                if new_uid != uid:
                    # Check for conflicts and resolve in favor of the canonical entity (without numeric suffix)
                    conflict_entity_id = ent_reg.async_get_entity_id(
                        entry_to_migrate.domain, DOMAIN, new_uid
                    )
                    if (
                        conflict_entity_id
                        and conflict_entity_id != entry_to_migrate.entity_id
                    ):
                        # Prefer keeping the entity without a numeric suffix. If the conflicting entity_id
                        # ends with a numeric suffix (e.g. _2, _3), remove it and proceed with migration.
                        try:
                            tail = conflict_entity_id.rsplit("_", 1)[-1]
                            has_numeric_tail = tail.isdigit()
                        except Exception:  # noqa: BLE001
                            has_numeric_tail = False

                        if has_numeric_tail:
                            conflict_entry = ent_reg.async_get(conflict_entity_id)
                            # Only remove if the conflicting entity belongs to the same config entry
                            if (
                                conflict_entry
                                and conflict_entry.config_entry_id == entry.entry_id
                            ):
                                _LOGGER.debug(
                                    "Removing duplicate entity %s to resolve unique_id conflict with %s",
                                    conflict_entity_id,
                                    entry_to_migrate.entity_id,
                                )
                                ent_reg.async_remove(conflict_entity_id)
                            else:
                                # Do not touch entities from other config entries
                                return None
                        else:
                            # A non-suffixed entity already has the target unique_id; skip migrating this one
                            return None

                    _LOGGER.debug(
                        "Migrating entity %s unique_id from %s to %s",
                        entry_to_migrate.entity_id,
                        uid,
                        new_uid,
                    )
                    nonlocal changed
                    changed = True
                    return {"new_unique_id": new_uid}
                break

        # No migration needed
        return None

    await er.async_migrate_entries(hass, entry.entry_id, _async_migrate_entity_entry)
    return changed

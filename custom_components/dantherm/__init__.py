"""Dantherm Integration."""

import logging
from typing import Final

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
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.translation import async_get_translations

from .const import DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .device import DanthermDevice
from .device_map import (
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_DISABLE_NOTIFICATIONS,
    ATTR_DISABLE_TEMPERATURE_UNKNOWN,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_HOME_MODE_TRIGGER,
    REQUIRED_PYMODBUS_VERSION,
)
from .discovery import async_discover
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
    "button",
    "calendar",
    "cover",
    "number",
    "select",
    "sensor",
    "switch",
    "text",
]

DEFAULT_OPTIONS = {
    ATTR_HOME_MODE_TRIGGER: "",
    ATTR_BOOST_MODE_TRIGGER: "",
    ATTR_ECO_MODE_TRIGGER: "",
    ATTR_DISABLE_TEMPERATURE_UNKNOWN: False,
    ATTR_DISABLE_NOTIFICATIONS: False,
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


async def async_setup(hass: HomeAssistant, config):
    """Set up the Dantherm component."""

    hass.data[DOMAIN] = {}
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Dantherm device."""

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
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    # Try to connect to the device at the configured address
    device = DanthermDevice(hass, name, host, port, 1, scan_interval, entry)
    try:
        coordinator = await device.async_init_and_connect()
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

                    # Match serial number read from the test device with the expected
                    # serial number from config entry
                    serial = test_device.get_device_serial_number
                    if serial == expected_serial:
                        _LOGGER.info("Found device at new IP %s", ip)
                        # Update config entry with new IP
                        new_data = dict(entry.data)
                        new_data[CONF_HOST] = ip
                        hass.config_entries.async_update_entry(entry, data=new_data)
                        device = test_device
                        found = True

                        # Send a notification about the rediscovery
                        if not options.get(ATTR_DISABLE_NOTIFICATIONS, False):
                            await async_create_exception_notification(
                                hass,
                                name,
                                "rediscovery",
                                domain=DOMAIN.capitalize(),
                                serial_number=serial,
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
        ATTR_BOOST_MODE_TRIGGER: options.get(ATTR_BOOST_MODE_TRIGGER, ""),
        ATTR_ECO_MODE_TRIGGER: options.get(ATTR_ECO_MODE_TRIGGER, ""),
        ATTR_HOME_MODE_TRIGGER: options.get(ATTR_HOME_MODE_TRIGGER, ""),
        ATTR_DISABLE_TEMPERATURE_UNKNOWN: options.get(
            ATTR_DISABLE_TEMPERATURE_UNKNOWN, False
        ),
        ATTR_DISABLE_NOTIFICATIONS: options.get(ATTR_DISABLE_NOTIFICATIONS, False),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    try:
        await device.async_start()
    except Exception:
        _LOGGER.exception("Failed to start device")
        return False

    async def _init_after_start(event=None) -> None:
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
        ATTR_DISABLE_NOTIFICATIONS not in options
        and ATTR_DISABLE_ALARM_NOTIFICATIONS in options
    ):
        options[ATTR_DISABLE_NOTIFICATIONS] = options.pop(
            ATTR_DISABLE_ALARM_NOTIFICATIONS
        )
        hass.config_entries.async_update_entry(config_entry, options=options)
        _LOGGER.debug("Migrated disable_alarm_notifications to disable_notifications")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

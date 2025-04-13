"""Damtherm Integration."""

import logging

from packaging import version
import pymodbus
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.translation import async_get_translations

from .config_flow import (
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_HOME_MODE_TRIGGER,
)
from .const import DEFAULT_NAME, DEFAULT_SCAN_INTERVAL, DOMAIN
from .device import Device
from .device_map import REQUIRED_PYMODBUS_VERSION
from .services import async_setup_services

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
}


async def async_setup(hass: HomeAssistant, config):
    """Set up the Dantherm component."""
    hass.data[DOMAIN] = {}
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the Dantherm device."""

    if version.parse(pymodbus.__version__) < version.parse(REQUIRED_PYMODBUS_VERSION):
        translations = await async_get_translations(
            hass, hass.config.language, "dantherm"
        )
        message_template = translations.get("exceptions.pymodbus_version")

        if not message_template:
            message_template = "Dantherm integration requires pymodbus version %s or newer, but %s is installed"

        raise RuntimeError(
            message_template % (REQUIRED_PYMODBUS_VERSION, pymodbus.__version__)
        )

    # If options are empty, initialize them with defaults
    if not entry.options:
        _LOGGER.warning("No stored options found, initializing defaults")
        hass.config_entries.async_update_entry(entry, options=DEFAULT_OPTIONS)

    _LOGGER.debug("Loading stored options in setup: %s", entry.options)

    hass.data.setdefault(DOMAIN, {})

    name = entry.data[CONF_NAME]
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    scan_interval = entry.data[CONF_SCAN_INTERVAL]

    _LOGGER.debug("Setup %s.%s", DOMAIN, name)

    device = Device(hass, name, host, port, 1, scan_interval, entry)

    await device.async_load_entities()  # Load device-specific data

    try:
        await device.setup()
    except ValueError as ex:
        raise ConfigEntryNotReady(f"Timeout while connecting {host}") from ex

    # Store device instance and options
    hass.data[DOMAIN][entry.entry_id] = {
        "device": device,
        ATTR_BOOST_MODE_TRIGGER: entry.options.get(ATTR_BOOST_MODE_TRIGGER, ""),
        ATTR_ECO_MODE_TRIGGER: entry.options.get(ATTR_ECO_MODE_TRIGGER, ""),
        ATTR_HOME_MODE_TRIGGER: entry.options.get(ATTR_HOME_MODE_TRIGGER, ""),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

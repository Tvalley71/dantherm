"""Config Flow implementation."""

import contextlib
import ipaddress
import logging
import os
import re
import time
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .const import (
    DEFAULT_MODBUS_UNIT_ID,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DEFAULT_RTU_BAUDRATE,
    DEFAULT_RTU_BYTESIZE,
    DEFAULT_RTU_PARITY,
    DEFAULT_RTU_STOPBITS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .device import DanthermDevice
from .device_map import (
    ADAPTIVE_TRIGGERS,
    CONF_BAUDRATE,
    CONF_BOOST_MODE_TRIGGER,
    CONF_BYTESIZE,
    CONF_CONNECTION_TYPE,
    CONF_DISABLE_NOTIFICATIONS,
    CONF_DISABLE_TEMPERATURE_UNKNOWN,
    CONF_ECO_MODE_TRIGGER,
    CONF_HOME_MODE_TRIGGER,
    CONF_LINK_TO_PRIMARY_CALENDAR,
    CONF_MANUFACTURER,
    CONF_MODBUS_UNIT_ID,
    CONF_PARITY,
    CONF_POLLING_SPEED,
    CONF_SERIAL_PORT,
    CONF_STOPBITS,
    MANUFACTURER_MAP,
    POLLING_OPTIONS,
    POLLING_OPTIONS_LIST,
    USE_MANUFACTURER_MAP,
)
from .discovery import async_discover
from .helpers import is_primary_entry
from .modbus import (
    DEFAULT_CONNECTION_TYPE,
    MODBUS_CONNECTION_TYPE_RTU,
    MODBUS_CONNECTION_TYPE_TCP,
)

# URL constants for description placeholders
BUYMEACOFFEE_URL = "https://www.buymeacoffee.com/tvalley71"
GITHUB_URL = "https://github.com/Tvalley71/dantherm"

# Debug mode configuration
# Set environment variable DANTHERM_DEBUG=1 to enable debug mode.
IS_DEBUG = os.getenv("DANTHERM_DEBUG") == "1"

_LOGGER = logging.getLogger(__name__)

CONNECTION_TYPES = [MODBUS_CONNECTION_TYPE_TCP, MODBUS_CONNECTION_TYPE_RTU]
PARITY_OPTIONS = ["N", "E", "O"]
PARITY_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[
            SelectOptionDict(value="N", label="None"),
            SelectOptionDict(value="E", label="Even"),
            SelectOptionDict(value="O", label="Odd"),
        ]
    )
)
UNIT_ID_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=1, max=247, mode=NumberSelectorMode.BOX)
)
BYTESIZE_OPTIONS = [5, 6, 7, 8]
STOPBITS_OPTIONS = [1, 2]


# ── Schema helpers ─────────────────────────────────────────────────────────────


def _get_manufacturer_schema() -> vol.Schema:
    """Return the schema for the manufacturer selection step."""
    manufacturers = sorted(MANUFACTURER_MAP.keys())
    return vol.Schema(
        {
            vol.Required(CONF_MANUFACTURER, default=DEFAULT_NAME): vol.In(
                manufacturers
            ),
        }
    )


def _get_connection_type_schema(
    default_connection_type: str = DEFAULT_CONNECTION_TYPE,
) -> vol.Schema:
    """Return the schema for the connection type selection step."""
    return vol.Schema(
        {
            vol.Required(CONF_CONNECTION_TYPE, default=default_connection_type): vol.In(
                CONNECTION_TYPES
            ),
        }
    )


def _get_tcp_schema(
    default_host: str = "",
    default_port: int = DEFAULT_PORT,
) -> vol.Schema:
    """Return the schema for TCP connection configuration."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=default_host): str,
            vol.Required(CONF_PORT, default=default_port): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=65535)
            ),
        }
    )


def _get_rtu_schema(
    default_serial_port: str = "/dev/ttyUSB0",
    default_modbus_unit_id: int = DEFAULT_MODBUS_UNIT_ID,
    default_baudrate: int = DEFAULT_RTU_BAUDRATE,
    default_bytesize: int = DEFAULT_RTU_BYTESIZE,
    default_parity: str = DEFAULT_RTU_PARITY,
    default_stopbits: int = DEFAULT_RTU_STOPBITS,
) -> vol.Schema:
    """Return the schema for RTU/serial connection configuration."""
    return vol.Schema(
        {
            vol.Required(CONF_SERIAL_PORT, default=default_serial_port): str,
            vol.Optional(
                CONF_MODBUS_UNIT_ID, default=default_modbus_unit_id
            ): UNIT_ID_SELECTOR,
            vol.Optional(CONF_BAUDRATE, default=default_baudrate): vol.All(
                vol.Coerce(int), vol.Range(min=1200, max=921600)
            ),
            vol.Optional(CONF_BYTESIZE, default=default_bytesize): vol.In(
                BYTESIZE_OPTIONS
            ),
            vol.Optional(CONF_PARITY, default=default_parity): PARITY_SELECTOR,
            vol.Optional(CONF_STOPBITS, default=default_stopbits): vol.In(
                STOPBITS_OPTIONS
            ),
        }
    )


def _get_device_name_schema(default_name: str = DEFAULT_NAME) -> vol.Schema:
    """Return the schema for the device name step."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=default_name): str,
        }
    )


def host_valid(host: str) -> bool:
    """Return True if hostname or IP address is valid."""
    try:
        if ipaddress.ip_address(host).version in [4, 6]:
            return True
    except ValueError:
        disallowed = re.compile(r"[^a-zA-Z\d\-]")
        return all(x and not disallowed.search(x) for x in host.split("."))
    return False


@callback
def dantherm_modbus_entries(hass: HomeAssistant) -> set[str]:
    """Return configured transport targets to prevent duplicates."""
    return {
        _entry_connection_identifier(entry.data)
        for entry in hass.config_entries.async_entries(DOMAIN)
    }


def _entry_connection_identifier(data: dict[str, Any]) -> str:
    """Build a comparable identifier for a TCP or RTU connection."""
    connection_type = data.get(CONF_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE)
    if connection_type == MODBUS_CONNECTION_TYPE_RTU:
        serial_port = data.get(CONF_SERIAL_PORT, "")
        unit_id = data.get(CONF_MODBUS_UNIT_ID, DEFAULT_MODBUS_UNIT_ID)
        return f"{MODBUS_CONNECTION_TYPE_RTU}:{serial_port}:{unit_id}"

    host = data.get(CONF_HOST, "")
    port = data.get(CONF_PORT, DEFAULT_PORT)
    return f"{MODBUS_CONNECTION_TYPE_TCP}:{host}:{port}"


# ── Config flow ────────────────────────────────────────────────────────────────


class DanthermConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Dantherm Modbus configflow."""

    VERSION = 3
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._manufacturer: str | None = None
        self._device_name: str | None = None
        self._connection_type: str = DEFAULT_CONNECTION_TYPE
        # TCP connection details
        self._tcp_host: str = ""
        self._tcp_port: int = DEFAULT_PORT
        # RTU connection details
        self._rtu_serial_port: str = ""
        self._rtu_modbus_unit_id: int = DEFAULT_MODBUS_UNIT_ID
        self._rtu_baudrate: int = DEFAULT_RTU_BAUDRATE
        self._rtu_bytesize: int = DEFAULT_RTU_BYTESIZE
        self._rtu_parity: str = DEFAULT_RTU_PARITY
        self._rtu_stopbits: int = DEFAULT_RTU_STOPBITS
        # Device reference for name step
        self._device_for_name: DanthermDevice | None = None

    def _connection_in_configuration_exists(self, data: dict[str, Any]) -> bool:
        """Return True if connection target exists in configuration."""
        if IS_DEBUG:
            return False
        return _entry_connection_identifier(data) in dantherm_modbus_entries(self.hass)

    # ── Step: manufacturer ─────────────────────────────────────────────────────

    async def async_step_manufacturer(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the manufacturer selection step."""
        if user_input is not None:
            self._manufacturer = user_input[CONF_MANUFACTURER]
            return await self.async_step_connection_type()

        return self.async_show_form(
            step_id=CONF_MANUFACTURER,
            data_schema=_get_manufacturer_schema(),
        )

    # ── Step: connection_type ──────────────────────────────────────────────────

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Entry point – redirect to manufacturer or connection_type step."""
        if USE_MANUFACTURER_MAP and self._manufacturer is None:
            return await self.async_step_manufacturer()
        return await self.async_step_connection_type(user_input)

    async def async_step_connection_type(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose connection type (TCP / RTU)."""
        if user_input is not None:
            self._connection_type = user_input.get(
                CONF_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE
            )
            if self._connection_type == MODBUS_CONNECTION_TYPE_RTU:
                return await self.async_step_rtu()
            return await self.async_step_tcp()

        return self.async_show_form(
            step_id="connection_type",
            data_schema=_get_connection_type_schema(
                default_connection_type=self._connection_type
            ),
        )

    # ── Step: tcp ──────────────────────────────────────────────────────────────

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure TCP connection (host, port)."""
        errors: dict[str, str] = {}

        if user_input is None:
            default_host = ""

            # Try discovery to pre-fill host
            discovered = await async_discover(self.hass)
            if discovered:
                configured_targets = dantherm_modbus_entries(self.hass)
                available = [
                    d
                    for d in discovered
                    if (ip := d.get("ip"))
                    and f"{MODBUS_CONNECTION_TYPE_TCP}:{ip}:{DEFAULT_PORT}"
                    not in configured_targets
                ]
                if available:
                    default_host = available[0]["ip"]
                    if not self._device_name:
                        self._device_name = available[0].get("name") or None

            return self.async_show_form(
                step_id="tcp",
                data_schema=_get_tcp_schema(default_host=default_host),
            )

        host = str(user_input.get(CONF_HOST, "")).strip()
        port = int(user_input.get(CONF_PORT, DEFAULT_PORT))

        if not host_valid(host):
            errors[CONF_HOST] = "invalid_host"

        connection_data: dict[str, Any] = {
            CONF_CONNECTION_TYPE: MODBUS_CONNECTION_TYPE_TCP,
            CONF_HOST: host,
            CONF_PORT: port,
        }

        if not errors and self._connection_in_configuration_exists(connection_data):
            errors["base"] = "already_configured"

        if not errors:
            device: DanthermDevice | None = None
            try:
                device = DanthermDevice(
                    self.hass,
                    "temp",
                    host,
                    port,
                    DEFAULT_MODBUS_UNIT_ID,
                    DEFAULT_SCAN_INTERVAL,
                    None,
                )
                await device.async_init_and_connect()
                # Store connection details and device reference for next step
                self._tcp_host = host
                self._tcp_port = port
                self._device_for_name = device
                if IS_DEBUG:
                    unique = f"{host}_{int(time.time() * 1000) % 100000}"
                else:
                    unique = str(device.get_device_serial_number)
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                # Proceed to device name step
                return await self.async_step_device_name()
            except Exception:
                _LOGGER.exception("Failed to connect during TCP config flow")
                errors["base"] = "cannot_connect"
            finally:
                if device is not None and not hasattr(self, "_device_for_name"):
                    with contextlib.suppress(Exception):
                        await device.disconnect_and_close()

        if errors:
            return self.async_show_form(
                step_id="tcp",
                data_schema=_get_tcp_schema(default_host=host, default_port=port),
                errors=errors,
            )
        return None

    # ── Step: rtu ──────────────────────────────────────────────────────────────

    async def async_step_rtu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure RTU/serial connection."""
        errors: dict[str, str] = {}

        if user_input is None:
            return self.async_show_form(
                step_id="rtu",
                data_schema=_get_rtu_schema(),
            )

        serial_port = str(user_input.get(CONF_SERIAL_PORT, "")).strip()
        modbus_unit_id = int(
            user_input.get(CONF_MODBUS_UNIT_ID, DEFAULT_MODBUS_UNIT_ID)
        )
        baudrate = int(user_input.get(CONF_BAUDRATE, DEFAULT_RTU_BAUDRATE))
        bytesize = int(user_input.get(CONF_BYTESIZE, DEFAULT_RTU_BYTESIZE))
        parity = str(user_input.get(CONF_PARITY, DEFAULT_RTU_PARITY)).upper()
        stopbits = int(user_input.get(CONF_STOPBITS, DEFAULT_RTU_STOPBITS))

        if not serial_port:
            errors[CONF_SERIAL_PORT] = "invalid_serial_port"

        connection_data: dict[str, Any] = {
            CONF_CONNECTION_TYPE: MODBUS_CONNECTION_TYPE_RTU,
            CONF_SERIAL_PORT: serial_port,
            CONF_MODBUS_UNIT_ID: modbus_unit_id,
        }

        if not errors and self._connection_in_configuration_exists(connection_data):
            errors["base"] = "already_configured"

        if not errors:
            device: DanthermDevice | None = None
            try:
                device = DanthermDevice(
                    self.hass,
                    "temp",
                    serial_port,
                    serial_port,
                    modbus_unit_id,
                    DEFAULT_SCAN_INTERVAL,
                    None,
                    MODBUS_CONNECTION_TYPE_RTU,
                    baudrate,
                    bytesize,
                    parity,
                    stopbits,
                )
                await device.async_init_and_connect()
                # Store connection details and device reference
                self._rtu_serial_port = serial_port
                self._rtu_modbus_unit_id = modbus_unit_id
                self._rtu_baudrate = baudrate
                self._rtu_bytesize = bytesize
                self._rtu_parity = parity
                self._rtu_stopbits = stopbits
                self._device_for_name = device
                if IS_DEBUG:
                    unique = f"{serial_port}_{int(time.time() * 1000) % 100000}"
                else:
                    unique = str(device.get_device_serial_number)
                await self.async_set_unique_id(unique)
                self._abort_if_unique_id_configured()
                # Proceed to device name step
                return await self.async_step_device_name()
            except Exception:
                _LOGGER.exception("Failed to connect during RTU config flow")
                errors["base"] = "cannot_connect"
            finally:
                if device is not None and not hasattr(self, "_device_for_name"):
                    with contextlib.suppress(Exception):
                        await device.disconnect_and_close()

        if errors:
            return self.async_show_form(
                step_id="rtu",
                data_schema=_get_rtu_schema(
                    default_serial_port=serial_port,
                    default_modbus_unit_id=modbus_unit_id,
                    default_baudrate=baudrate,
                    default_bytesize=bytesize,
                    default_parity=parity,
                    default_stopbits=stopbits,
                ),
                errors=errors,
            )
        return None

    # ── Step: device_name ─────────────────────────────────────────────────────

    async def async_step_device_name(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Allow user to set or confirm device name."""
        device = getattr(self, "_device_for_name", None)

        if user_input is None:
            if not self._device_name and device is not None:
                try:
                    self._device_name = await device.async_get_system_name()
                except Exception:
                    _LOGGER.warning(
                        "Failed to get system name for device during config flow"
                    )
                    self._device_name = None

            default_name = self._device_name or (
                self._manufacturer.title() if self._manufacturer else DEFAULT_NAME
            )
            return self.async_show_form(
                step_id="device_name",
                data_schema=_get_device_name_schema(default_name=default_name),
            )

        device_name = str(user_input.get(CONF_NAME, "")).strip()
        if not device_name:
            if not self._device_name:
                self._device_name = (
                    self._manufacturer.title() if self._manufacturer else DEFAULT_NAME
                )

            return self.async_show_form(
                step_id="device_name",
                data_schema=_get_device_name_schema(default_name=self._device_name),
                errors={CONF_NAME: "required"},
            )

        self._device_name = device_name
        # Clean up the device reference before creating entry
        if device is not None:
            with contextlib.suppress(Exception):
                await device.disconnect_and_close()
            delattr(self, "_device_for_name")

        # Create entry based on connection type
        if self._connection_type == MODBUS_CONNECTION_TYPE_RTU:
            return self.async_create_entry(
                title=self._device_name,
                data={
                    CONF_MANUFACTURER: getattr(self, "_manufacturer", None),
                    CONF_NAME: self._device_name,
                    CONF_CONNECTION_TYPE: MODBUS_CONNECTION_TYPE_RTU,
                    CONF_SERIAL_PORT: self._rtu_serial_port,
                    CONF_MODBUS_UNIT_ID: self._rtu_modbus_unit_id,
                    CONF_BAUDRATE: self._rtu_baudrate,
                    CONF_BYTESIZE: self._rtu_bytesize,
                    CONF_PARITY: self._rtu_parity,
                    CONF_STOPBITS: self._rtu_stopbits,
                    CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                },
            )
        return self.async_create_entry(
            title=self._device_name,
            data={
                CONF_MANUFACTURER: getattr(self, "_manufacturer", None),
                CONF_NAME: self._device_name,
                CONF_CONNECTION_TYPE: MODBUS_CONNECTION_TYPE_TCP,
                CONF_HOST: self._tcp_host,
                CONF_PORT: self._tcp_port,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> DanthermOptionsFlowHandler:
        """Create the options flow."""
        return DanthermOptionsFlowHandler(config_entry)


# ── Options flow ───────────────────────────────────────────────────────────────


class DanthermOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Dantherm options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

    def _get_polling_speed_from_interval(self, interval: int) -> str:
        """Convert scan interval to polling speed option."""
        for speed, value in POLLING_OPTIONS.items():
            if value == interval:
                return speed
        return "custom"

    def _has_custom_polling_interval(self) -> bool:
        """Check if user has a custom polling interval."""
        current_interval = self.config_entry.data.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return current_interval not in POLLING_OPTIONS.values()

    def _get_polling_options_with_custom(self) -> list[str]:
        """Get polling options including current custom value if applicable."""
        options = list(POLLING_OPTIONS_LIST)
        if self._has_custom_polling_interval():
            current_interval = self.config_entry.data.get(
                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
            )
            options.append(f"custom ({current_interval}s)")
        return options

    def _apply_polling_speed(
        self,
        new_data: dict[str, Any],
        polling_speed: str,
        current_scan_interval: int,
    ) -> None:
        """Write the correct scan_interval into new_data based on polling_speed."""
        if polling_speed in POLLING_OPTIONS:
            new_data[CONF_SCAN_INTERVAL] = POLLING_OPTIONS[polling_speed]
        elif polling_speed == "custom" or polling_speed.startswith("custom ("):
            new_data[CONF_SCAN_INTERVAL] = current_scan_interval

    # ── Step: init ─────────────────────────────────────────────────────────────

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the initial welcome screen with configuration overview."""
        if user_input is not None:
            if not user_input.get("continue", False):
                return self.async_abort(reason="aborted_by_user")

            # Route to TCP or serial settings based on stored connection type
            connection_type = self.config_entry.data.get(
                CONF_CONNECTION_TYPE, DEFAULT_CONNECTION_TYPE
            )
            if connection_type == MODBUS_CONNECTION_TYPE_RTU:
                return await self.async_step_serial()
            return await self.async_step_tcp()

        schema = vol.Schema({vol.Optional("continue", default=True): bool})
        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "buymeacoffee_url": BUYMEACOFFEE_URL,
                "github_url": GITHUB_URL,
            },
        )

    # ── Step: tcp (options) ────────────────────────────────────────────────────

    async def async_step_tcp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit TCP connection settings."""
        errors: dict[str, str] = {}
        data = dict(self.config_entry.data)

        current_scan_interval = data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        current_polling_speed = self._get_polling_speed_from_interval(
            current_scan_interval
        )
        available_options = self._get_polling_options_with_custom()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=data.get(CONF_HOST, "")): str,
                vol.Required(
                    CONF_PORT, default=data.get(CONF_PORT, DEFAULT_PORT)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Optional(CONF_POLLING_SPEED, default=current_polling_speed): vol.In(
                    available_options
                ),
            }
        )

        if user_input is not None:
            host = str(user_input.get(CONF_HOST, "")).strip()
            if not host_valid(host):
                errors[CONF_HOST] = "invalid_host"

            if not errors:
                new_data = dict(self.config_entry.data)
                new_data[CONF_HOST] = host
                new_data[CONF_PORT] = int(user_input.get(CONF_PORT, DEFAULT_PORT))
                self._apply_polling_speed(
                    new_data,
                    user_input.get(CONF_POLLING_SPEED, current_polling_speed),
                    current_scan_interval,
                )
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                return await self.async_step_triggers()

        return self.async_show_form(step_id="tcp", data_schema=schema, errors=errors)

    # ── Step: serial (options) ─────────────────────────────────────────────────

    async def async_step_serial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit RTU/serial connection settings."""
        errors: dict[str, str] = {}
        data = dict(self.config_entry.data)

        current_scan_interval = data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        current_polling_speed = self._get_polling_speed_from_interval(
            current_scan_interval
        )
        available_options = self._get_polling_options_with_custom()

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SERIAL_PORT,
                    default=data.get(CONF_SERIAL_PORT, "/dev/ttyUSB0"),
                ): str,
                vol.Optional(
                    CONF_MODBUS_UNIT_ID,
                    default=data.get(CONF_MODBUS_UNIT_ID, DEFAULT_MODBUS_UNIT_ID),
                ): UNIT_ID_SELECTOR,
                vol.Optional(
                    CONF_BAUDRATE,
                    default=data.get(CONF_BAUDRATE, DEFAULT_RTU_BAUDRATE),
                ): vol.All(vol.Coerce(int), vol.Range(min=1200, max=921600)),
                vol.Optional(
                    CONF_BYTESIZE,
                    default=data.get(CONF_BYTESIZE, DEFAULT_RTU_BYTESIZE),
                ): vol.In(BYTESIZE_OPTIONS),
                vol.Optional(
                    CONF_PARITY,
                    default=data.get(CONF_PARITY, DEFAULT_RTU_PARITY),
                ): PARITY_SELECTOR,
                vol.Optional(
                    CONF_STOPBITS,
                    default=data.get(CONF_STOPBITS, DEFAULT_RTU_STOPBITS),
                ): vol.In(STOPBITS_OPTIONS),
                vol.Optional(CONF_POLLING_SPEED, default=current_polling_speed): vol.In(
                    available_options
                ),
            }
        )

        if user_input is not None:
            serial_port = str(user_input.get(CONF_SERIAL_PORT, "")).strip()
            if not serial_port:
                errors[CONF_SERIAL_PORT] = "invalid_serial_port"

            if not errors:
                new_data = dict(self.config_entry.data)
                new_data[CONF_SERIAL_PORT] = serial_port
                new_data[CONF_MODBUS_UNIT_ID] = int(
                    user_input.get(CONF_MODBUS_UNIT_ID, DEFAULT_MODBUS_UNIT_ID)
                )
                new_data[CONF_BAUDRATE] = int(
                    user_input.get(CONF_BAUDRATE, DEFAULT_RTU_BAUDRATE)
                )
                new_data[CONF_BYTESIZE] = int(
                    user_input.get(CONF_BYTESIZE, DEFAULT_RTU_BYTESIZE)
                )
                new_data[CONF_PARITY] = str(
                    user_input.get(CONF_PARITY, DEFAULT_RTU_PARITY)
                ).upper()
                new_data[CONF_STOPBITS] = int(
                    user_input.get(CONF_STOPBITS, DEFAULT_RTU_STOPBITS)
                )
                self._apply_polling_speed(
                    new_data,
                    user_input.get(CONF_POLLING_SPEED, current_polling_speed),
                    current_scan_interval,
                )
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=new_data
                )
                return await self.async_step_triggers()

        return self.async_show_form(step_id="serial", data_schema=schema, errors=errors)

    # ── Step: triggers ─────────────────────────────────────────────────────────

    async def async_step_triggers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure adaptive mode triggers and calendar linking."""
        errors: dict[str, str] = {}
        options = dict(self.config_entry.options)

        schema_dict: dict[vol.Optional, Any] = {
            vol.Optional(
                CONF_BOOST_MODE_TRIGGER,
                default=options.get(CONF_BOOST_MODE_TRIGGER, ""),
            ): str,
            vol.Optional(
                CONF_ECO_MODE_TRIGGER, default=options.get(CONF_ECO_MODE_TRIGGER, "")
            ): str,
            vol.Optional(
                CONF_HOME_MODE_TRIGGER, default=options.get(CONF_HOME_MODE_TRIGGER, "")
            ): str,
        }

        if not is_primary_entry(self.hass, self.config_entry.entry_id):
            schema_dict[
                vol.Optional(
                    CONF_LINK_TO_PRIMARY_CALENDAR,
                    default=options.get(CONF_LINK_TO_PRIMARY_CALENDAR, True),
                )
            ] = vol.Coerce(bool)

        schema = vol.Schema(schema_dict)

        if user_input is not None:
            entity_registry = er.async_get(self.hass)
            for entity_key in ADAPTIVE_TRIGGERS:
                entity_id = user_input.get(entity_key, "")
                if entity_id is None:
                    entity_id = ""
                else:
                    entity_id = str(entity_id).strip()
                user_input[entity_key] = entity_id
                if entity_id:
                    if entity_id not in [
                        entity.entity_id for entity in entity_registry.entities.values()
                    ]:
                        errors[entity_key] = "invalid_entity"

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    options={**options, **user_input},
                )
                return await self.async_step_advanced()

        return self.async_show_form(
            step_id="triggers", data_schema=schema, errors=errors
        )

    # ── Step: advanced ─────────────────────────────────────────────────────────

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure advanced options."""
        options = dict(self.config_entry.options)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DISABLE_TEMPERATURE_UNKNOWN,
                    default=options.get(CONF_DISABLE_TEMPERATURE_UNKNOWN, False),
                ): bool,
                vol.Optional(
                    CONF_DISABLE_NOTIFICATIONS,
                    default=options.get(CONF_DISABLE_NOTIFICATIONS, False),
                ): bool,
            }
        )

        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                options={**options, **user_input},
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(step_id="advanced", data_schema=schema)

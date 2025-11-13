"""Device implementation."""

from __future__ import annotations

from collections import deque
import logging
from types import MappingProxyType
from typing import Any

from propcache.api import cached_property

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .adaptive_manager import DanthermAdaptiveManager
from .const import DEVICE_TYPES
from .coordinator import DanthermCoordinator
from .device_map import (
    ATTR_AIR_QUALITY,
    ATTR_AIR_QUALITY_LEVEL,
    ATTR_ALARM,
    ATTR_BYPASS_DAMPER,
    ATTR_FILTER_LIFETIME,
    ATTR_FILTER_REMAIN,
    ATTR_FILTER_REMAIN_LEVEL,
    ATTR_HUMIDITY,
    ATTR_HUMIDITY_LEVEL,
    ATTR_INTERNAL_PREHEATER,
    ATTR_SENSOR_FILTERING,
    CONF_BOOST_MODE_TRIGGER,
    CONF_DISABLE_NOTIFICATIONS,
    CONF_DISABLE_TEMPERATURE_UNKNOWN,
    CONF_ECO_MODE_TRIGGER,
    CONF_HOME_MODE_TRIGGER,
    STATE_AUTOMATIC,
    STATE_AWAY,
    STATE_FIREPLACE,
    STATE_LEVEL_0,
    STATE_LEVEL_1,
    STATE_LEVEL_2,
    STATE_LEVEL_3,
    STATE_LEVEL_4,
    STATE_MANUAL,
    STATE_NIGHT,
    STATE_NONE,
    STATE_STANDBY,
    STATE_SUMMER,
    STATE_WEEKPROGRAM,
    ActiveUnitMode,
    BypassDamperState,
    ComponentClass,
    CurrentUnitMode,
    DanthermEntityDescription,
)
from .modbus import (
    MODBUS_REGISTER_ACTIVE_MODE,
    MODBUS_REGISTER_AIR_QUALITY,
    MODBUS_REGISTER_ALARM,
    MODBUS_REGISTER_ALARM_RESET,
    MODBUS_REGISTER_BYPASS_DAMPER,
    MODBUS_REGISTER_BYPASS_MAX_TEMP,
    MODBUS_REGISTER_BYPASS_MAX_TEMP_SUMMER,
    MODBUS_REGISTER_BYPASS_MIN_TEMP,
    MODBUS_REGISTER_BYPASS_MIN_TEMP_SUMMER,
    MODBUS_REGISTER_CURRENT_MODE,
    MODBUS_REGISTER_EXHAUST_TEMP,
    MODBUS_REGISTER_EXTRACT_TEMP,
    MODBUS_REGISTER_FAN_LEVEL,
    MODBUS_REGISTER_FILTER_LIFETIME,
    MODBUS_REGISTER_FILTER_REMAIN,
    MODBUS_REGISTER_FILTER_RESET,
    MODBUS_REGISTER_FIRMWARE_VERSION,
    MODBUS_REGISTER_HUMIDITY,
    MODBUS_REGISTER_HUMIDITY_SETPOINT,
    MODBUS_REGISTER_HUMIDITY_SETPOINT_SUMMER,
    MODBUS_REGISTER_MANUAL_BYPASS_DURATION,
    MODBUS_REGISTER_NIGHT_MODE_END_HOUR,
    MODBUS_REGISTER_NIGHT_MODE_END_MINUTE,
    MODBUS_REGISTER_NIGHT_MODE_START_HOUR,
    MODBUS_REGISTER_NIGHT_MODE_START_MINUTE,
    MODBUS_REGISTER_OUTDOOR_TEMP,
    MODBUS_REGISTER_ROOM_TEMP,
    MODBUS_REGISTER_SERIAL_NUMBER,
    MODBUS_REGISTER_SUPPLY_TEMP,
    MODBUS_REGISTER_SYSTEM_ID,
    MODBUS_REGISTER_WEEK_PROGRAM_SELECTION,
    ABSwitchPosition,
    DanthermModbus,
)
from .notifications import (
    async_create_key_value_notification,
    async_dismiss_notification,
)

_LOGGER = logging.getLogger(__name__)


class DanthermDevice(DanthermModbus, DanthermAdaptiveManager):
    """Dantherm Device."""

    # Type annotations for instance variables
    _config_entry: ConfigEntry | None
    _scan_interval: int
    _device_name: str
    _device_type: int
    _device_fw_version: int
    _device_serial_number: int
    _device_ab_switch_position: ABSwitchPosition | None
    _current_unit_mode: int | None
    _active_unit_mode: int | None
    _fan_level: int | None
    _alarm: int | None
    _sensor_filtering: bool
    _bypass_damper: int | None
    _bypass_maximum_temperature: float | None
    _filter_lifetime: int | None
    _filter_remain: int | None
    _filter_remain_level: int | None
    _last_current_operation: str | None
    _coordinator: DanthermCoordinator | None
    installed_components: int
    _options: MappingProxyType[str, Any] | dict[str, Any]
    _filtered_sensors: dict[str, dict[str, Any]]
    # Note: coordinator property is overridden below

    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        host: str,
        port: int,
        unit_id: int,
        scan_interval: int,
        config_entry: ConfigEntry | None,
    ) -> None:
        """Init device."""
        super().__init__(
            name,
            host,
            port,
            unit_id,
        )
        # Only initialize adaptive manager if we have a config_entry
        if config_entry is not None:
            DanthermAdaptiveManager.__init__(
                self,
                hass,
                config_entry,
            )
        self._config_entry: ConfigEntry | None = config_entry
        self._scan_interval = scan_interval
        self._device_name = name
        self._device_type = 0
        self._device_fw_version = 0
        self._device_serial_number = 0
        self._device_ab_switch_position: ABSwitchPosition | None = None
        self._current_unit_mode = None
        self._active_unit_mode = None
        self._fan_level = None
        self._alarm = None
        self._sensor_filtering = False
        self._bypass_damper = None
        self._bypass_maximum_temperature = None
        self._filter_lifetime = None
        self._filter_remain = None
        self._filter_remain_level = None
        self._last_current_operation = None
        self._coordinator: DanthermCoordinator | None = None
        self.installed_components = 0

        # During config flow we may not have a ConfigEntry yet
        if config_entry is not None:
            self._options = config_entry.options
        else:
            self._options = {}

        # Initialize filtered sensors
        self._filtered_sensors = {
            "humidity": {
                "history": deque(maxlen=5),
                "max_change": 5,
                "initialized": False,
            },
            "air_quality": {
                "history": deque(maxlen=5),
                "max_change": 50,
                "initialized": False,
            },
            "exhaust": {
                "history": deque(maxlen=5),
                "max_change": 2,
                "initialized": False,
            },
            "extract": {
                "history": deque(maxlen=5),
                "max_change": 2,
                "initialized": False,
            },
            "supply": {
                "history": deque(maxlen=5),
                "max_change": 2,
                "initialized": False,
            },
            "outdoor": {
                "history": deque(maxlen=5),
                "max_change": 2,
                "initialized": False,
            },
            "room": {
                "history": deque(maxlen=5),
                "max_change": 2,
                "initialized": False,
            },
        }

    @property
    def coordinator(self) -> DanthermCoordinator | None:
        """Override coordinator property from DanthermAdaptiveManager."""
        return self._coordinator

    @coordinator.setter
    def coordinator(self, value: DanthermCoordinator | None) -> None:
        """Set coordinator property."""
        self._coordinator = value

    async def async_init_and_connect(self) -> DanthermCoordinator | None:
        """Set up modbus for Dantherm Device."""

        _LOGGER.debug("Setup has started")

        # Connect and verify modbus connection
        result = await self.connect_and_verify()
        _LOGGER.info("Modbus setup completed successfully for %s", self._host)
        self.installed_components = result & 0xFFFF
        _LOGGER.debug("Installed components (610) = %s", hex(self.installed_components))

        system_id = await self._read_holding_uint32(MODBUS_REGISTER_SYSTEM_ID)
        if system_id is not None:
            self._device_type = system_id >> 24
            _LOGGER.debug("Device type = %s", self.get_device_type)
            _LOGGER.debug("Installed components (2) = %s", hex(system_id & 0xFFFF))

        fw_version = await self._read_holding_uint32(MODBUS_REGISTER_FIRMWARE_VERSION)
        if fw_version is not None:
            self._device_fw_version = fw_version
            _LOGGER.debug("Firmware version = %s", self.get_device_fw_version)

        serial_number = await self._read_holding_uint64(MODBUS_REGISTER_SERIAL_NUMBER)
        if serial_number is not None:
            self._device_serial_number = serial_number
            _LOGGER.debug("Serial number = %d", self.get_device_serial_number)

        self._device_ab_switch_position = await self.get_device_ab_switch_position()

        if self.installed_components & ComponentClass.HAC1 == ComponentClass.HAC1:
            await self._read_hac_controller()
        else:
            _LOGGER.debug("No HAC controller installed")

        # Create coordinator only if we have a config_entry (not during config flow)
        if self._config_entry is not None:
            self.coordinator = DanthermCoordinator(
                self._hass,
                self._device_name,
                self,
                self._scan_interval,
                self._config_entry,
            )

            # Load stored entities
            await self.coordinator.async_load_entities()
            return self.coordinator

        # During config flow, we don't have a config_entry yet, so return None
        return None

    async def async_start(self) -> None:
        """Start the integration."""

        # Set up adaptive triggers - only if we have a config_entry
        if self._config_entry is not None:
            await self.async_set_up_adaptive_manager()

        # Do the first refresh of entities
        if self.coordinator is not None:
            await self.coordinator.async_config_entry_first_refresh()

        # Set up tracking for adaptive triggers if any
        if (
            self._get_boost_mode_trigger_available
            or self._get_eco_mode_trigger_available
            or self._get_home_mode_trigger_available
        ):
            await self.async_set_up_tracking_for_adaptive_triggers()

        # Remove chached properties
        self.__dict__.pop("_get_filter_lifetime_entity_installed", None)
        self.__dict__.pop("_get_filter_remain_entity_installed", None)
        self.__dict__.pop("_get_filter_remain_level_entity_installed", None)
        self.__dict__.pop("_get_humidity_entity_installed", None)
        self.__dict__.pop("_get_air_quality_entity_installed", None)
        self.__dict__.pop("_get_boost_mode_trigger_available", None)
        self.__dict__.pop("_get_eco_mode_trigger_available", None)
        self.__dict__.pop("_get_home_mode_trigger_available", None)

    async def async_init_after_start(self) -> None:
        """Initialize the device after a restart."""
        await self.async_initialize_adaptive_triggers()

    async def async_install_entity(
        self, description: DanthermEntityDescription
    ) -> bool:
        """Test if the entity should be installed."""

        def exclude_from_component_class(
            description: DanthermEntityDescription,
        ) -> bool:
            """Check if entity must be excluded from component_class."""
            if description.component_class:
                return (self.installed_components & description.component_class) == 0
            return False

        async def exclude_from_entity_state(
            description: DanthermEntityDescription,
        ) -> bool:
            """Check if entity must be excluded if any of the data_exclude_if conditions are met."""

            if (
                description.data_exclude_if_above
                or description.data_exclude_if_below
                or description.data_exclude_if is not None
            ):
                if self.coordinator is not None:
                    entity_data = await self.coordinator.async_get_entity_data(
                        description
                    )
                    if entity_data:
                        state = entity_data["state"]

                        if (
                            (
                                description.data_exclude_if is not None
                                and description.data_exclude_if == state
                            )
                            or (
                                description.data_exclude_if_above is not None
                                and state >= description.data_exclude_if_above
                            )
                            or (
                                description.data_exclude_if_below is not None
                                and state <= description.data_exclude_if_below
                            )
                        ):
                            return True
            return False

        async def exclude_from_firmware_version(
            description: DanthermEntityDescription,
        ) -> bool:
            """Check if entity must be excluded based on firmware version."""
            if description.firmware_exclude_if_below is not None:
                if self.get_device_fw_version < description.firmware_exclude_if_below:
                    return True
            return False

        install = True
        if (
            exclude_from_component_class(description)
            or await exclude_from_entity_state(description)
            or await exclude_from_firmware_version(description)
        ):
            install = False

        if install:
            return True
        _LOGGER.debug("Excluding an entity=%s", description.key)
        return False

    def get_device_entities(self) -> list[er.RegistryEntry]:
        """Return all entities that belong to this integration's device."""
        if self._config_entry is None:
            return []

        entity_registry = er.async_get(self._hass)
        device_registry = dr.async_get(self._hass)

        # Find device_id der matcher denne config entry
        device_id = next(
            (
                d.id
                for d in device_registry.devices.values()
                if self._config_entry.entry_id in d.config_entries
            ),
            None,
        )

        if not device_id:
            _LOGGER.warning(
                "No device found for config entry: %s", self._config_entry.entry_id
            )
            return []

        return [
            entry
            for entry in entity_registry.entities.values()
            if entry.device_id == device_id
        ]

    def get_device_id(self) -> str | None:
        """Return the device ID for this integration's device."""
        if self._config_entry is None:
            return None

        device_registry = dr.async_get(self._hass)

        # Find device_id that matches this config entry
        device_id = next(
            (
                d.id
                for d in device_registry.devices.values()
                if self._config_entry.entry_id in d.config_entries
            ),
            None,
        )

        if not device_id:
            _LOGGER.warning(
                "No device found for config entry: %s", self._config_entry.entry_id
            )

        return device_id

    def get_entity_state_from_coordinator(
        self, entity: str, default: Any = None
    ) -> Any:
        """Get entity state from coordinator."""
        if self.coordinator is None:
            return default
        states = self.coordinator.data.get(entity, None)
        if states:
            return states["state"]
        return default

    @property
    def available(self) -> bool:
        """Return if device is available."""
        return self._attr_available

    @property
    def get_device_name(self) -> str:
        """Device name."""

        return self._device_name

    @property
    def get_device_type(self) -> str:
        """Device type."""

        device_type = DEVICE_TYPES.get(self._device_type, None)
        if device_type is None:
            device_type = f"UNKNOWN {self._device_type}"
        device_mode = None
        if self._device_ab_switch_position == ABSwitchPosition.A:
            device_mode = "Mode A"
        elif self._device_ab_switch_position == ABSwitchPosition.B:
            device_mode = "Mode B"
        if device_mode is None:
            return device_type
        return f"{device_type} ({device_mode})"

    @property
    def get_device_fw_version(self) -> float:
        """Device firmware version."""

        major = (self._device_fw_version >> 8) & 0xFF
        minor = self._device_fw_version & 0xFF
        return float(f"{major}.{minor:02}")

    @property
    def get_device_serial_number(self) -> int:
        """Device serial number."""
        return self._device_serial_number

    @property
    def get_current_unit_mode(self) -> Any:
        """Get current unit mode."""

        return self._current_unit_mode

    @property
    def get_active_unit_mode(self) -> Any:
        """Get active unit mode."""

        return self._active_unit_mode

    @property
    def get_operation_selection(self) -> Any:
        """Get operation selection."""

        if self._active_unit_mode is None or self._current_unit_mode is None:
            return None

        if self._current_unit_mode == CurrentUnitMode.Away:
            return STATE_AWAY
        if self._current_unit_mode == CurrentUnitMode.Summer:
            return STATE_SUMMER
        if self._current_unit_mode == CurrentUnitMode.Fireplace:
            return STATE_FIREPLACE
        if self._current_unit_mode == CurrentUnitMode.Night:
            return STATE_NIGHT

        if self._active_unit_mode == 0 or self._fan_level == 0:
            return STATE_STANDBY

        if (
            self._active_unit_mode & ActiveUnitMode.Automatic
            == ActiveUnitMode.Automatic
        ):
            return STATE_AUTOMATIC

        if self._active_unit_mode & ActiveUnitMode.Manual == ActiveUnitMode.Manual:
            return STATE_MANUAL

        if (
            self._active_unit_mode & ActiveUnitMode.WeekProgram
            == ActiveUnitMode.WeekProgram
        ):
            return STATE_WEEKPROGRAM

        _LOGGER.debug("Unknown mode of operation=%s", self._active_unit_mode)
        return STATE_MANUAL

    def get_current_operation(self) -> str | None:
        """Get current operation."""

        if self._active_unit_mode is None:
            return None

        current_operation = None
        if (
            self._active_unit_mode & ActiveUnitMode.Automatic
            == ActiveUnitMode.Automatic
        ):
            current_operation = STATE_AUTOMATIC
        elif self._active_unit_mode & ActiveUnitMode.Manual == ActiveUnitMode.Manual:
            if self._fan_level == 0:
                current_operation = STATE_STANDBY
            elif self._fan_level == 1:
                current_operation = STATE_LEVEL_1
            elif self._fan_level == 2:
                current_operation = STATE_LEVEL_2
            elif self._fan_level == 3:
                current_operation = STATE_LEVEL_3
            elif self._fan_level == 4:
                current_operation = STATE_LEVEL_4
        elif (
            self._active_unit_mode & ActiveUnitMode.WeekProgram
            == ActiveUnitMode.WeekProgram
        ):
            current_operation = STATE_WEEKPROGRAM
        elif self._active_unit_mode & ActiveUnitMode.Away == ActiveUnitMode.Away:
            current_operation = STATE_AWAY
        else:
            return self._last_current_operation

        self._last_current_operation = current_operation
        return current_operation

    @property
    def get_operation_mode_icon(self) -> str:
        """Get operation mode icon."""

        result = self.get_fan_level
        if not result:
            return "mdi:fan-off"
        icons = {1: "mdi:fan-speed-1", 2: "mdi:fan-speed-2", 3: "mdi:fan-speed-3"}
        return icons.get(result, "mdi:fan-plus")

    @property
    def get_fan_level_selection_icon(self) -> str:
        """Get fan level selection icon."""

        result = self.get_fan_level
        if not result:
            return "mdi:fan-off"
        icons = {1: "mdi:fan-speed-1", 2: "mdi:fan-speed-2", 3: "mdi:fan-speed-3"}
        return icons.get(result, "mdi:fan-plus")

    @property
    def get_fan_level(self) -> int | None:
        """Get fan level."""
        return self._fan_level

    @property
    def get_fan_level_icon(self) -> str:
        """Get fan level icon."""

        if self._alarm != 0:
            return "mdi:fan-alert"

        mode = self._current_unit_mode
        mode_icons = {
            CurrentUnitMode.Standby: "mdi:fan-off",
            CurrentUnitMode.Away: "mdi:bag-suitcase",
            CurrentUnitMode.Summer: "mdi:weather-sunny",
            CurrentUnitMode.Fireplace: "mdi:fire",
            CurrentUnitMode.Night: "mdi:weather-night",
            CurrentUnitMode.Automatic: "mdi:fan-auto",
            CurrentUnitMode.WeekProgram: "mdi:fan-clock",
        }
        if mode is not None and mode in mode_icons:
            return mode_icons[mode]

        op = self.get_operation_selection
        selection_icons = {
            STATE_STANDBY: "mdi:fan-off",
            STATE_AUTOMATIC: "mdi:fan-auto",
            STATE_WEEKPROGRAM: "mdi:fan-clock",
        }
        if op in selection_icons:
            return selection_icons[op]

        return "mdi:fan"

    @property
    def get_ventilation_icon(self) -> str:
        """Get ventilation icon."""

        result = self.get_fan_level
        if not result:
            return "mdi:fan-off"
        icons = {1: "mdi:fan-speed-1", 2: "mdi:fan-speed-2", 3: "mdi:fan-speed-3"}
        return icons.get(result, "mdi:fan-plus")

    @property
    def get_ventilation(self) -> dict[int, str] | None:
        """Get ventilation."""

        preset_mode = None
        if self._active_unit_mode is None or self._current_unit_mode is None:
            preset_mode = None
        elif self._current_unit_mode == CurrentUnitMode.Away:
            preset_mode = STATE_AWAY
        elif self._current_unit_mode == CurrentUnitMode.Summer:
            preset_mode = STATE_SUMMER
        elif self._current_unit_mode == CurrentUnitMode.Fireplace:
            preset_mode = STATE_FIREPLACE
        elif (
            self._active_unit_mode & ActiveUnitMode.Automatic
            == ActiveUnitMode.Automatic
        ):
            preset_mode = STATE_AUTOMATIC
        elif self._active_unit_mode & ActiveUnitMode.Manual == ActiveUnitMode.Manual:
            preset_mode = STATE_MANUAL
        elif (
            self._active_unit_mode & ActiveUnitMode.WeekProgram
            == ActiveUnitMode.WeekProgram
        ):
            preset_mode = STATE_WEEKPROGRAM

        return {
            "fan_level": self._fan_level,
            "preset_mode": preset_mode,
        }

    async def async_get_current_unit_mode(self) -> int | None:
        """Get current unit mmode."""
        self._current_unit_mode = await self._read_holding_uint32(
            MODBUS_REGISTER_CURRENT_MODE
        )
        _LOGGER.debug(
            "Current unit mode = %s",
            self._to_hex(self._current_unit_mode)
            if self._current_unit_mode is not None
            else None,
        )
        return self._current_unit_mode

    async def async_get_active_unit_mode(self) -> int | None:
        """Get active unit mode."""

        self._active_unit_mode = await self._read_holding_uint32(
            MODBUS_REGISTER_ACTIVE_MODE
        )
        _LOGGER.debug(
            "Active unit mode = %s",
            self._to_hex(self._active_unit_mode)
            if self._active_unit_mode is not None
            else None,
        )
        return self._active_unit_mode

    async def async_get_fan_level(self) -> int | None:
        """Get fan level."""

        self._fan_level = await self._read_holding_uint32(MODBUS_REGISTER_FAN_LEVEL)
        _LOGGER.debug("Fan level = %s", self._fan_level)
        return self._fan_level

    async def async_get_alarm(self) -> int | None:
        """Get alarm."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_ALARM)
        if result not in (None, 0, self._alarm):
            # Create persistent notification if alarm is not zero
            if not self._options.get(CONF_DISABLE_NOTIFICATIONS, False):
                await async_create_key_value_notification(
                    self._hass,
                    self._device_name,
                    "sensor",
                    ATTR_ALARM,
                    str(result) if result is not None else None,
                )

        self._alarm = result
        _LOGGER.debug("Alarm = %s", self._alarm)
        return self._alarm

    async def async_get_sensor_filtering(self) -> bool:
        """Get sensor filtering."""

        self._sensor_filtering = self.get_entity_state_from_coordinator(
            ATTR_SENSOR_FILTERING, False
        )
        return self._sensor_filtering

    async def async_get_week_program_selection(self) -> int | None:
        """Get week program selection."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_WEEK_PROGRAM_SELECTION)
        _LOGGER.debug("Week program selection = %s", result)
        return result

    async def async_get_calendar(self) -> None:
        """Get calendar."""

        await self.async_update_adaptive_calendar()

    @property
    def get_alarm(self) -> int | None:
        """Get alarm."""

        return self._alarm

    @property
    def get_bypass_damper_icon(self) -> str:
        """Get bypass damper icon."""

        if self._bypass_damper == BypassDamperState.Closed:
            return "mdi:valve-closed"
        if self._bypass_damper == BypassDamperState.Opened:
            return "mdi:valve-open"
        return "mdi:valve"

    @property
    def get_away_mode(self) -> bool | None:
        """Get away mode."""

        if self._current_unit_mode is None or self._active_unit_mode is None:
            return None

        if (
            self._current_unit_mode == CurrentUnitMode.Away
            or self._active_unit_mode & ActiveUnitMode.Away == ActiveUnitMode.Away
        ):
            return True
        return False

    @property
    def get_fireplace_mode(self) -> bool | None:
        """Get fireplace mode."""

        if self._current_unit_mode is None or self._active_unit_mode is None:
            return None

        if (
            self._current_unit_mode == CurrentUnitMode.Fireplace
            or self._active_unit_mode & ActiveUnitMode.Fireplace
            == ActiveUnitMode.Fireplace
        ):
            return True
        return False

    @property
    def get_summer_mode(self) -> bool | None:
        """Get summer mode."""

        if self._current_unit_mode is None or self._active_unit_mode is None:
            return None

        if (
            self._current_unit_mode == CurrentUnitMode.Summer
            or self._active_unit_mode & ActiveUnitMode.Summer == ActiveUnitMode.Summer
        ):
            return True
        return False

    @property
    def get_bypass_available(self) -> bool:
        """Get bypass available."""
        return self._bypass_maximum_temperature != 0.0

    @property
    def get_disable_bypass(self) -> bool:
        """Get disable bypass."""
        return self._bypass_maximum_temperature == 0.0

    @property
    def get_exhaust_temperature_unknown(self) -> bool:
        """Check if exhaust temperature is not applicable."""

        if self._options.get(CONF_DISABLE_TEMPERATURE_UNKNOWN, False):
            return False

        if self.get_bypass_available and self._bypass_damper in (
            BypassDamperState.InProgress,
            BypassDamperState.Opening,
            BypassDamperState.Opened,
            BypassDamperState.Closing,
        ):
            return True
        return False

    @property
    def get_supply_temperature_unknown(self) -> bool:
        """Check if supply temperature is not applicable."""

        if self._options.get(CONF_DISABLE_TEMPERATURE_UNKNOWN, False):
            return False

        if self._current_unit_mode == CurrentUnitMode.Summer:
            return True

        if self.get_bypass_available and self._bypass_damper in (
            BypassDamperState.InProgress,
            BypassDamperState.Opening,
            BypassDamperState.Opened,
            BypassDamperState.Closing,
        ):
            return True
        return False

    @property
    def get_outdoor_temperature_unknown(self) -> bool:
        """Check if outdoor temperature is not applicable."""

        if self._options.get(CONF_DISABLE_TEMPERATURE_UNKNOWN, False):
            return False

        if self._current_unit_mode == CurrentUnitMode.Summer:
            return True
        return False

    @property
    def get_filter_remain_attrs(self) -> dict[str, int] | None:
        """Get filter remain attributes."""

        result = self._filter_remain_level
        if result is not None:
            return {"level": result}
        return None

    @property
    def get_adaptive_state_attrs(self) -> dict[str, Any] | None:
        """Get adaptive state attributes."""
        if self.events:
            return {"events": self.events.to_list()}
        return None

    @property
    def get_features_attrs(self) -> dict[str, bool]:
        """Get feattures attributes."""

        return {
            "fp1": (self.installed_components & ComponentClass.FP1)
            == ComponentClass.FP1,
            "week": (self.installed_components & ComponentClass.Week)
            == ComponentClass.Week,
            ATTR_BYPASS_DAMPER: (self.installed_components & ComponentClass.Bypass)
            == ComponentClass.Bypass,
            "lrswitch": (self.installed_components & ComponentClass.LRSwitch)
            == ComponentClass.LRSwitch,
            ATTR_INTERNAL_PREHEATER: (
                self.installed_components & ComponentClass.Internal_preheater
            )
            == ComponentClass.Internal_preheater,
            "servo_flow": (self.installed_components & ComponentClass.Servo_flow)
            == ComponentClass.Servo_flow,
            ATTR_HUMIDITY: (self.installed_components & ComponentClass.RH_Senser)
            == ComponentClass.RH_Senser,
            ATTR_AIR_QUALITY: (self.installed_components & ComponentClass.VOC_sensor)
            == ComponentClass.VOC_sensor,
            "ext_override": (self.installed_components & ComponentClass.Ext_Override)
            == ComponentClass.Ext_Override,
            "hac1": (self.installed_components & ComponentClass.HAC1)
            == ComponentClass.HAC1,
            "hrc2": (self.installed_components & ComponentClass.HRC2)
            == ComponentClass.HRC2,
            "pc_tool": (self.installed_components & ComponentClass.PC_Tool)
            == ComponentClass.PC_Tool,
            "apps": (self.installed_components & ComponentClass.Apps)
            == ComponentClass.Apps,
            "zeegbee": (self.installed_components & ComponentClass.ZeegBee)
            == ComponentClass.ZeegBee,
            "di1_override": (self.installed_components & ComponentClass.DI1_Override)
            == ComponentClass.DI1_Override,
            "di2_override": (self.installed_components & ComponentClass.DI2_Override)
            == ComponentClass.DI2_Override,
        }

    @cached_property
    def _get_boost_mode_trigger_available(self) -> bool:
        """Get boost mode trigger available."""
        return bool(self._options.get(CONF_BOOST_MODE_TRIGGER, False))

    @cached_property
    def _get_eco_mode_trigger_available(self) -> bool:
        """Get eco mode trigger available."""
        return bool(self._options.get(CONF_ECO_MODE_TRIGGER, False))

    @cached_property
    def _get_home_mode_trigger_available(self) -> bool:
        """Get home mode trigger available."""
        return bool(self._options.get(CONF_HOME_MODE_TRIGGER, False))

    @cached_property
    def _get_filter_lifetime_entity_installed(self) -> bool:
        """Check if the filter lifetime entity is installed (cached)."""
        return self.coordinator is not None and self.coordinator.is_entity_installed(
            ATTR_FILTER_LIFETIME
        )

    @cached_property
    def _get_filter_remain_entity_installed(self) -> bool:
        """Check if the filter remain entity is installed (cached)."""
        return self.coordinator is not None and self.coordinator.is_entity_installed(
            ATTR_FILTER_REMAIN
        )

    @cached_property
    def _get_filter_remain_level_entity_installed(self) -> bool:
        """Check if the filter remain level entity is installed (cached)."""
        return self.coordinator is not None and self.coordinator.is_entity_installed(
            ATTR_FILTER_REMAIN_LEVEL
        )

    @cached_property
    def _get_humidity_entity_installed(self) -> bool:
        """Check if the humidity entity is installed (cached)."""
        return self.coordinator is not None and self.coordinator.is_entity_installed(
            ATTR_HUMIDITY
        )

    @cached_property
    def _get_air_quality_entity_installed(self) -> bool:
        """Check if the air quality entity is installed (cached)."""
        return self.coordinator is not None and self.coordinator.is_entity_installed(
            ATTR_AIR_QUALITY
        )

    async def set_alarm_reset(self, value: int | None = None) -> None:
        """Set alarm reset."""

        # Dismiss persistent alarm notification if it exists
        await async_dismiss_notification(self._hass, self._device_name, ATTR_ALARM)

        if value is None:
            value = self._alarm
        await self._write_holding_uint32(MODBUS_REGISTER_ALARM_RESET, value)

    async def async_get_bypass_damper(self) -> int | None:
        """Get bypass damper."""

        self._bypass_damper = await self._read_holding_uint32(
            MODBUS_REGISTER_BYPASS_DAMPER
        )
        _LOGGER.debug("Bypass damper = %s", self._bypass_damper)
        return self._bypass_damper

    async def async_get_filter_lifetime(self) -> int | None:
        """Get filter lifetime."""

        self._filter_lifetime = await self._read_holding_uint32(
            MODBUS_REGISTER_FILTER_LIFETIME
        )
        _LOGGER.debug("Filter lifetime = %s", self._filter_lifetime)

        return self._filter_lifetime

    async def async_get_filter_remain(self) -> int | None:
        """Get filter remain."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_FILTER_REMAIN)
        if result == 0 and result != self._filter_remain:
            # Create persistent notification if filter remain is zero
            if not self._options.get(CONF_DISABLE_NOTIFICATIONS, False):
                await async_create_key_value_notification(
                    self._hass,
                    self._device_name,
                    "sensor",
                    ATTR_FILTER_REMAIN,
                    str(result),
                )

        self._filter_remain = result
        _LOGGER.debug("Filter remain = %s", self._filter_remain)

        if not self._get_filter_remain_level_entity_installed:
            await self.async_get_filter_remain_level()

        return self._filter_remain

    async def async_get_filter_remain_level(self) -> int | None:
        """Get filter remain level."""

        if self._get_filter_lifetime_entity_installed:
            filter_lifetime = self._filter_lifetime
        else:
            filter_lifetime = await self._read_holding_uint32(
                MODBUS_REGISTER_FILTER_LIFETIME
            )

        if self._get_filter_remain_entity_installed:
            filter_remain = self._filter_remain
        else:
            filter_remain = await self._read_holding_uint32(
                MODBUS_REGISTER_FILTER_REMAIN
            )

        if filter_lifetime is None or filter_remain is None:
            return None

        self._filter_remain_level = 0
        if filter_remain <= filter_lifetime:
            self._filter_remain_level = int(
                (filter_lifetime - filter_remain) / (filter_lifetime / 3)
            )
        _LOGGER.debug("Filter Remain Level = %s", self._filter_remain_level)
        return self._filter_remain_level

    async def async_get_night_mode_start_time(self) -> str | None:
        """Get night mode start time."""

        hour = await self._read_holding_uint32(MODBUS_REGISTER_NIGHT_MODE_START_HOUR)
        if hour is None:
            return None
        minute = await self._read_holding_uint32(
            MODBUS_REGISTER_NIGHT_MODE_START_MINUTE
        )
        if minute is None:
            return None

        result = f"{hour:02}:{minute:02}"
        _LOGGER.debug("Night mode start = %s", result)
        return result

    async def async_get_night_mode_end_time(self) -> str | None:
        """Get night mode end time."""

        hour = await self._read_holding_uint32(MODBUS_REGISTER_NIGHT_MODE_END_HOUR)
        if hour is None:
            return None
        minute = await self._read_holding_uint32(MODBUS_REGISTER_NIGHT_MODE_END_MINUTE)
        if minute is None:
            return None

        result = f"{hour:02}:{minute:02}"
        _LOGGER.debug("Night mode end = %s", result)
        return result

    async def async_get_bypass_minimum_temperature(self) -> float | None:
        """Get bypass minimum temperature."""

        result = await self._read_holding_float32(MODBUS_REGISTER_BYPASS_MIN_TEMP, 1)
        _LOGGER.debug("Bypass minimum temperature = %.1f", result)
        return result

    async def async_get_bypass_maximum_temperature(self) -> float | None:
        """Get bypass maximum temperature."""

        self._bypass_maximum_temperature = await self._read_holding_float32(
            MODBUS_REGISTER_BYPASS_MAX_TEMP, 1
        )
        _LOGGER.debug(
            "Bypass maximum temperature = %.1f", self._bypass_maximum_temperature
        )
        return self._bypass_maximum_temperature

    async def async_get_manual_bypass_duration(self) -> int | None:
        """Get manual bypass duration."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_MANUAL_BYPASS_DURATION)
        _LOGGER.debug("Manual bypass duration = %s", result)
        return result

    async def async_get_bypass_minimum_temperature_summer(self) -> float | None:
        """Get bypass minimum temperature for summer."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_BYPASS_MIN_TEMP_SUMMER, 1
        )
        _LOGGER.debug("Bypass minimum temperature (summer) = %.1f", result)
        return result

    async def async_get_bypass_maximum_temperature_summer(self) -> float | None:
        """Get bypass maximum temperature for summer."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_BYPASS_MAX_TEMP_SUMMER, 1
        )
        _LOGGER.debug("Bypass maximum temperature (summer) = %.1f", result)
        return result

    async def set_filter_reset(self, value: int | None = None) -> None:
        """Set filter reset."""

        # Dismiss persistent alarm notification if it exists
        await async_dismiss_notification(
            self._hass, self._device_name, ATTR_FILTER_REMAIN
        )

        if value is None:
            value = 1
        await self._write_holding_uint32(MODBUS_REGISTER_FILTER_RESET, value)

    async def set_active_unit_mode(self, value: int) -> None:
        """Set active unit mode."""

        await self._write_holding_uint32(MODBUS_REGISTER_ACTIVE_MODE, value)

    async def set_operation_selection(self, operation: str | None) -> None:
        """Set operation selection."""

        current_operation = self.get_operation_selection

        if operation is None:
            return

        if current_operation == operation:
            _LOGGER.debug("Operation selection is already set to %s", operation)
            return

        async def apply_active_unit_mode(
            current_mode: int | None, active_mode: int, selection: int | None = None
        ) -> None:
            """Update the operation mode and fan level."""
            # End previous operation modes if needed
            special_modes = {
                STATE_AWAY: (CurrentUnitMode.Away, ActiveUnitMode.EndAway),
                STATE_FIREPLACE: (
                    CurrentUnitMode.Fireplace,
                    ActiveUnitMode.EndFireplace,
                ),
                STATE_SUMMER: (CurrentUnitMode.Summer, ActiveUnitMode.EndSummer),
            }
            for state, (mode, end_mode) in special_modes.items():
                # Only update if last operation was not the same
                if current_operation == state and current_mode != mode:
                    if self._last_current_operation == state:
                        continue
                    await apply_active_unit_mode(mode, end_mode)

            # Update the current unit mode
            await self.set_active_unit_mode(active_mode)

            # Update selection if provided
            if current_mode == CurrentUnitMode.Manual and selection is not None:
                await self.set_fan_level(selection)

        # Map operation to mode, active_mode, and selection
        unit_mode_map = {
            STATE_AUTOMATIC: (
                CurrentUnitMode.Automatic,
                ActiveUnitMode.Automatic,
                None,
            ),
            STATE_MANUAL: (
                CurrentUnitMode.Manual,
                ActiveUnitMode.Manual,
                1 if self._fan_level == 0 else 3 if self._fan_level == 4 else None,
            ),
            STATE_STANDBY: (
                CurrentUnitMode.Manual,
                ActiveUnitMode.Manual,
                0,
            ),
            STATE_LEVEL_0: (
                CurrentUnitMode.Manual,
                ActiveUnitMode.Manual,
                0,
            ),
            STATE_LEVEL_1: (
                CurrentUnitMode.Manual,
                ActiveUnitMode.Manual,
                1,
            ),
            STATE_LEVEL_2: (
                CurrentUnitMode.Manual,
                ActiveUnitMode.Manual,
                2,
            ),
            STATE_LEVEL_3: (
                CurrentUnitMode.Manual,
                ActiveUnitMode.Manual,
                3,
            ),
            STATE_LEVEL_4: (
                CurrentUnitMode.Manual,
                ActiveUnitMode.Manual,
                4,
            ),
            STATE_WEEKPROGRAM: (
                CurrentUnitMode.WeekProgram,
                ActiveUnitMode.WeekProgram,
                None,
            ),
            STATE_AWAY: (
                CurrentUnitMode.Away,
                ActiveUnitMode.StartAway,
                None,
            ),
            STATE_FIREPLACE: (
                CurrentUnitMode.Fireplace,
                ActiveUnitMode.StartFireplace,
                None,
            ),
            STATE_SUMMER: (
                CurrentUnitMode.Summer,
                ActiveUnitMode.StartSummer,
                None,
            ),
        }

        um_tuple = unit_mode_map.get(operation)
        if um_tuple is None:
            return

        await apply_active_unit_mode(*um_tuple)

    async def set_fan_level(self, value: int) -> None:
        """Set fan level."""

        # Write the level to the fan level register
        await self._write_holding_uint32(MODBUS_REGISTER_FAN_LEVEL, value)

    async def set_ventilation(self, value: dict[int, str]) -> None:
        """Set ventilation."""

        operation = value.get("preset_mode")
        if operation is not None:
            await self.set_operation_selection(operation)

        fan_level = value.get("fan_level")
        if fan_level is not None:
            await self.set_fan_level(fan_level)

    async def set_week_program_selection(self, value: int) -> None:
        """Set week program selection."""

        # Write the program selection to the week program selection register
        await self._write_holding_uint32(MODBUS_REGISTER_WEEK_PROGRAM_SELECTION, value)

    async def set_filter_lifetime(self, value: int) -> None:
        """Set filter lifetime."""

        # Write the lifetime to filter lifetime register
        await self._write_holding_uint32(MODBUS_REGISTER_FILTER_LIFETIME, value)

    async def set_bypass_damper(
        self, feature: CoverEntityFeature | None = None
    ) -> None:
        """Set bypass damper."""

        async def toggle_bypass_damper() -> None:
            """Toggle the bypass damper state."""
            if (
                self.get_active_unit_mode & ActiveUnitMode.ManualBypass
                == ActiveUnitMode.ManualBypass
            ):
                await self.set_active_unit_mode(ActiveUnitMode.DeselectManualBypass)
            else:
                await self.set_active_unit_mode(ActiveUnitMode.SelectManualBypass)

        if feature is CoverEntityFeature.OPEN:
            if self._bypass_damper not in (
                BypassDamperState.InProgress,
                BypassDamperState.Opened,
                BypassDamperState.Opening,
            ):
                await toggle_bypass_damper()
        elif feature is CoverEntityFeature.CLOSE:
            if self._bypass_damper not in (
                BypassDamperState.InProgress,
                BypassDamperState.Closed,
                BypassDamperState.Closing,
            ):
                await toggle_bypass_damper()

    async def set_humidity_setpoint(self, value: int) -> None:
        """Set humidity setpoint."""

        # Write the setpoint to the humidity setpoint register
        await self._write_holding_uint32(MODBUS_REGISTER_HUMIDITY_SETPOINT, value)

    async def set_humidity_setpoint_summer(self, value: int) -> None:
        """Set humidity setpoint for summer."""

        # Write the setpoint to the humidity setpoint summer register
        await self._write_holding_uint32(
            MODBUS_REGISTER_HUMIDITY_SETPOINT_SUMMER, value
        )

    async def set_night_mode_start_time(self, value: str) -> None:
        """Set night mode start time."""

        # Split the time string into hours and minutes
        hours, minutes = map(int, value.split(":"))

        if not (0 <= hours < 24 and 0 <= minutes < 60):
            _LOGGER.error("Invalid time format: %s", value)
            return

        # Write the hours to the hour register
        await self._write_holding_uint32(MODBUS_REGISTER_NIGHT_MODE_START_HOUR, hours)

        # Write the minutes to the minute register
        await self._write_holding_uint32(
            MODBUS_REGISTER_NIGHT_MODE_START_MINUTE, minutes
        )

    async def set_night_mode_end_time(self, value: str) -> None:
        """Set night mode end time."""

        # Split the time string into hours and minutes
        hours, minutes = map(int, value.split(":"))

        if not (0 <= hours < 24 and 0 <= minutes < 60):
            _LOGGER.error("Invalid time format: %s", value)
            return

        # Write the hours to the hour register
        await self._write_holding_uint32(MODBUS_REGISTER_NIGHT_MODE_END_HOUR, hours)

        # Write the minutes to the minute register
        await self._write_holding_uint32(MODBUS_REGISTER_NIGHT_MODE_END_MINUTE, minutes)

    async def set_bypass_minimum_temperature(self, value: float) -> None:
        """Set bypass minimum temperature."""

        # Write the temperature to the minimum temperature register
        await self._write_holding_float32(MODBUS_REGISTER_BYPASS_MIN_TEMP, value)

    async def set_bypass_maximum_temperature(self, value: float) -> None:
        """Set bypass maximum temperature."""

        # Write the temperature to the maximum temperature register
        await self._write_holding_float32(MODBUS_REGISTER_BYPASS_MAX_TEMP, value)

    async def set_manual_bypass_duration(self, value: int) -> None:
        """Set manual bypass duration."""

        # Write the duration to the manual bypass duration register
        await self._write_holding_uint32(MODBUS_REGISTER_MANUAL_BYPASS_DURATION, value)

    async def set_bypass_minimum_temperature_summer(self, value: float) -> None:
        """Set bypass minimum temperature for summer."""

        # Write the temperature to the minimum temperature summer register
        await self._write_holding_float32(MODBUS_REGISTER_BYPASS_MIN_TEMP_SUMMER, value)

    async def set_bypass_maximum_temperature_summer(self, value: float) -> None:
        """Set bypass maximum temperature for summer."""

        # Write the temperature to the maximum temperature summer register
        await self._write_holding_float32(MODBUS_REGISTER_BYPASS_MAX_TEMP_SUMMER, value)

    async def set_disable_bypass(self, value: bool) -> None:
        """Set automatic bypass."""

        # If value is True, set the maximum temperature to 0.0 to disable automatic bypass
        if value:
            await self.set_bypass_maximum_temperature(0.0)
        else:
            # If value is False, set the maximum temperature to a non-zero value (e.g., 24.0)
            await self.set_bypass_maximum_temperature(24.0)

    async def clear_adaptive_event_stack(self) -> None:
        """Clear the adaptive event stack."""
        if hasattr(self, "events") and self.events:
            removed_count = self.events.clear_all_events()
            _LOGGER.info(
                "Manually cleared %d events from adaptive event stack", removed_count
            )

    async def async_get_humidity(self) -> int | None:
        """Get humidity."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_HUMIDITY)
        _LOGGER.debug("Humidity = %s", result)
        if not self._sensor_filtering or result is None:
            return result
        filtered_result = self._filter_sensor("humidity", float(result))
        return int(filtered_result)

    async def async_get_humidity_level(self) -> str | None:
        """Get humidity level with hysteresis."""

        if self._get_humidity_entity_installed:
            humidity = self.get_entity_state_from_coordinator(ATTR_HUMIDITY, None)
        else:
            humidity = await self._read_holding_uint32(MODBUS_REGISTER_HUMIDITY)

        if humidity is None:
            _LOGGER.debug("Humidity Level is not available")
            return None

        previous = self.get_entity_state_from_coordinator(ATTR_HUMIDITY_LEVEL, None)

        if previous == 0 and humidity > 32:
            level = 1
        elif previous == 1:
            if humidity <= 28:
                level = 0
            elif humidity > 42:
                level = 2
            else:
                level = 1
        elif previous == 2:
            if humidity <= 38:
                level = 1
            elif humidity > 62:
                level = 3
            else:
                level = 2
        elif previous == 3 and humidity <= 58:
            level = 2
        else:  # noqa: PLR5501
            if humidity <= 30:
                level = 0
            elif humidity <= 40:
                level = 1
            elif humidity <= 60:
                level = 2
            else:
                level = 3

        _LOGGER.debug("Humidity Level = %s", level)
        return str(level)

    async def async_get_humidity_setpoint(self) -> int | None:
        """Get humidity setpoint."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_HUMIDITY_SETPOINT)
        _LOGGER.debug("Humidity setpoint = %s", result)
        return result

    async def async_get_humidity_setpoint_summer(self) -> int | None:
        """Get humidity setpoint (summer)."""

        result = await self._read_holding_uint32(
            MODBUS_REGISTER_HUMIDITY_SETPOINT_SUMMER
        )
        _LOGGER.debug("Humidity setpoint (summer) = %s", result)
        return result

    async def async_get_air_quality(self) -> int | None:
        """Get air quality."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_AIR_QUALITY)
        _LOGGER.debug("Air quality = %s", result)
        if not self._sensor_filtering or result is None:
            return result
        filtered_result = self._filter_sensor("air_quality", float(result))
        return int(filtered_result)

    async def async_get_air_quality_level(self) -> str | None:
        """Get air quality level with hysteresis."""

        if self._get_air_quality_entity_installed:
            air_quality = self.get_entity_state_from_coordinator(ATTR_AIR_QUALITY, None)
        else:
            air_quality = await self._read_holding_uint32(MODBUS_REGISTER_AIR_QUALITY)

        if air_quality is None:
            _LOGGER.debug("Air Quality Level is not available")
            return None

        previous = self.get_entity_state_from_coordinator(ATTR_AIR_QUALITY_LEVEL, None)

        if previous == 0 and air_quality > 650:
            level = 1
        elif previous == 1:
            if air_quality <= 550:
                level = 0
            elif air_quality > 1050:
                level = 2
            else:
                level = 1
        elif previous == 2:
            if air_quality <= 950:
                level = 1
            elif air_quality > 1450:
                level = 3
            else:
                level = 2
        elif previous == 3 and air_quality <= 1350:
            level = 2
        else:  # noqa: PLR5501
            if air_quality <= 600:
                level = 0
            elif air_quality <= 1000:
                level = 1
            elif air_quality <= 1400:
                level = 2
            else:
                level = 3

        _LOGGER.debug("Air Quality Level = %s", level)
        return str(level)

    async def async_get_exhaust_temperature(self) -> float | None:
        """Get exhaust temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_EXHAUST_TEMP, precision=1
        )
        _LOGGER.debug("Exhaust temperature = %.1f", result)
        if not self._sensor_filtering or result is None:
            return result
        return self._filter_sensor("exhaust", result)

    async def async_get_extract_temperature(self) -> float | None:
        """Get extract temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_EXTRACT_TEMP, precision=1
        )
        _LOGGER.debug("Extract temperature = %.1f", result)
        if not self._sensor_filtering or result is None:
            return result
        return self._filter_sensor("extract", result)

    async def async_get_supply_temperature(self) -> float | None:
        """Get supply temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_SUPPLY_TEMP, precision=1
        )
        _LOGGER.debug("Supply temperature = %.1f", result)
        if not self._sensor_filtering or result is None:
            return result
        return self._filter_sensor("supply", result)

    async def async_get_outdoor_temperature(self) -> float | None:
        """Get outdoor temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_OUTDOOR_TEMP, precision=1
        )
        _LOGGER.debug("Outdoor temperature = %.1f", result)
        if not self._sensor_filtering or result is None:
            return result
        return self._filter_sensor("outdoor", result)

    async def async_get_room_temperature(self) -> float | None:
        """Get room temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_ROOM_TEMP, precision=1
        )
        _LOGGER.debug("Room temperature = %.1f", result)
        if not self._sensor_filtering or result is None:
            return result
        return self._filter_sensor("room", result)

    async def async_get_adaptive_state(self) -> str:
        """Get adaptive state."""

        # Get the top event
        top = self.events.top()
        result = STATE_NONE
        if top:
            result = top["event"]
        _LOGGER.debug("Adaptive state = %s", result)
        return result

    async def async_get_features(self) -> str:
        """Get features."""

        return str(self.installed_components)

    def _filter_sensor(self, sensor: str, new_value: float) -> float:
        """Filter a given sensor, ensuring smooth initialization and spike reduction."""

        # Ensure the sensor type is valid
        if sensor not in self._filtered_sensors:
            raise ValueError(f"Invalid sensor: {sensor}")

        sensor_data = self._filtered_sensors[sensor]
        history: deque[float] = sensor_data["history"]

        # Collect initial samples and compute average until initialized
        if not sensor_data["initialized"]:
            if history.maxlen is not None and len(history) < history.maxlen:
                history.append(new_value)
                return float(round(sum(history) / len(history), 1))
            sensor_data["initialized"] = True

        # Compute rolling average
        rolling_average = sum(history) / len(history)

        # If new value is a spike, return rolling average (reject spike)
        if abs(new_value - rolling_average) > sensor_data["max_change"]:
            return float(round(rolling_average, 1))

        # Otherwise, accept new value and update history
        history.append(new_value)
        return new_value

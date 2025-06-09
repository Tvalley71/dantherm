"""Device implementation."""

from collections import deque
from datetime import datetime, timedelta
import logging
import os
import re

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import cached_property
from homeassistant.helpers.entity_registry import RegistryEntryDisabler
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util.dt import DEFAULT_TIME_ZONE, now as ha_now, parse_datetime

from .config_flow import (
    ADAPTIVE_TRIGGERS,
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_HOME_MODE_TRIGGER,
)
from .const import DEVICE_TYPES
from .coordinator import DanthermCoordinator
from .device_map import (
    ATTR_ADAPTIVE_STATE,
    ATTR_BOOST_MODE,
    ATTR_BOOST_MODE_TIMEOUT,
    ATTR_BOOST_OPERATION_SELECTION,
    ATTR_ECO_MODE,
    ATTR_ECO_MODE_TIMEOUT,
    ATTR_ECO_OPERATION_SELECTION,
    ATTR_FILTER_LIFETIME,
    ATTR_FILTER_REMAIN,
    ATTR_FILTER_REMAIN_LEVEL,
    ATTR_HOME_MODE,
    ATTR_HOME_MODE_TIMEOUT,
    ATTR_HOME_OPERATION_SELECTION,
    ATTR_SENSOR_FILTERING,
    STATE_AUTOMATIC,
    STATE_AWAY,
    STATE_FIREPLACE,
    STATE_LEVEL_1,
    STATE_LEVEL_2,
    STATE_LEVEL_3,
    STATE_LEVEL_4,
    STATE_MANUAL,
    STATE_NIGHT,
    STATE_NONE,
    STATE_PRIORITIES,
    STATE_STANDBY,
    STATE_SUMMER,
    STATE_WEEKPROGRAM,
    ABSwitchPosition,
    ActiveUnitMode,
    BypassDamperState,
    ComponentClass,
    CurrentUnitMode,
    DanthermEntityDescription,
)
from .modbus import (
    MODBUS_REGISTER_AB_SWITCH_POSITION,
    MODBUS_REGISTER_ACTIVE_MODE,
    MODBUS_REGISTER_AIR_QUALITY,
    MODBUS_REGISTER_ALARM,
    MODBUS_REGISTER_ALARM_RESET,
    MODBUS_REGISTER_BYPASS_DAMPER,
    MODBUS_REGISTER_BYPASS_MAX_TEMP,
    MODBUS_REGISTER_BYPASS_MIN_TEMP,
    MODBUS_REGISTER_CURRENT_MODE,
    MODBUS_REGISTER_EXHAUST_TEMP,
    MODBUS_REGISTER_EXTRACT_TEMP,
    MODBUS_REGISTER_FAN_LEVEL,
    MODBUS_REGISTER_FILTER_LIFETIME,
    MODBUS_REGISTER_FILTER_REMAIN,
    MODBUS_REGISTER_FILTER_RESET,
    MODBUS_REGISTER_FIRMWARE_VERSION,
    MODBUS_REGISTER_HUMIDITY,
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
    DanthermModbus,
)

_LOGGER = logging.getLogger(__name__)

IS_DEBUG = os.getenv("DANTHERM_DEBUG") == "1"

# This is used to represent the minimum datetime value in the system.
MIN_DT = datetime.min.replace(tzinfo=DEFAULT_TIME_ZONE)

# This is used to represent the maximum datetime value in the system.
MAX_DT = datetime.max.replace(tzinfo=DEFAULT_TIME_ZONE)


class DanthermDevice(DanthermModbus):
    """Dantherm Device."""

    def __init__(
        self,
        hass: HomeAssistant,
        name,
        host,
        port,
        unit_id,
        scan_interval,
        config_entry: ConfigEntry,
    ) -> None:
        """Init device."""
        super().__init__(
            name,
            host,
            port,
            unit_id,
        )
        self._hass = hass
        self._entry_id = config_entry.entry_id
        self._options = config_entry.options
        self._scan_interval = scan_interval
        self._device_name = name
        self._device_type = 0
        self._device_fw_version = 0
        self._device_serial_number = 0
        self._device_ab_switch_position = None
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
        self._operation_change_timeout = MIN_DT
        self.events = EventStack()
        self.coordinator = None
        self.installed_components = 0

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

        self._adaptive_triggers = {
            ATTR_BOOST_MODE_TRIGGER: {
                "name": "boost",
                "associated_entities": [
                    ATTR_BOOST_MODE,
                    ATTR_BOOST_MODE_TIMEOUT,
                    ATTR_BOOST_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": None,
                "trigger": None,
                "unsub": None,
            },
            ATTR_ECO_MODE_TRIGGER: {
                "name": "eco",
                "associated_entities": [
                    ATTR_ECO_MODE,
                    ATTR_ECO_MODE_TIMEOUT,
                    ATTR_ECO_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": None,
                "trigger": None,
                "unsub": None,
            },
            ATTR_HOME_MODE_TRIGGER: {
                "name": "home",
                "associated_entities": [
                    ATTR_HOME_MODE,
                    ATTR_HOME_MODE_TIMEOUT,
                    ATTR_HOME_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": None,
                "trigger": None,
                "unsub": None,
            },
        }

    async def async_init_and_connect(self) -> DanthermCoordinator:
        """Set up modbus for Dantherm Device."""

        _LOGGER.debug("Setup has started")

        # Remove chached properties
        self.__dict__.pop("_get_filter_lifetime_entity_installed", None)
        self.__dict__.pop("_get_filter_remain_entity_installed", None)
        self.__dict__.pop("_get_filter_remain_level_entity_installed", None)
        self.__dict__.pop("get_boost_mode_trigger_available", None)
        self.__dict__.pop("get_eco_mode_trigger_available", None)
        self.__dict__.pop("get_home_mode_trigger_available", None)

        # Connect and verify modbus connection
        result = await self.connect_and_verify()
        _LOGGER.info("Modbus setup completed successfully for %s", self._host)
        self.installed_components = result & 0xFFFF
        _LOGGER.debug("Installed components (610) = %s", hex(self.installed_components))

        system_id = await self._read_holding_uint32(MODBUS_REGISTER_SYSTEM_ID)
        self._device_type = system_id >> 24
        _LOGGER.debug("Device type = %s", self.get_device_type)
        self._device_fw_version = await self._read_holding_uint32(
            MODBUS_REGISTER_FIRMWARE_VERSION
        )
        _LOGGER.debug("Firmware version = %s", self.get_device_fw_version)
        self._device_serial_number = await self._read_holding_uint64(
            MODBUS_REGISTER_SERIAL_NUMBER
        )
        _LOGGER.debug("Serial number = %d", self.get_device_serial_number)

        self._device_ab_switch_position = await self._read_holding_uint64(
            MODBUS_REGISTER_AB_SWITCH_POSITION
        )
        _LOGGER.debug(
            "A/B switch position = %a (%s)",
            self._device_ab_switch_position,
            "A"
            if self._device_ab_switch_position == ABSwitchPosition.A
            else "B"
            if self._device_ab_switch_position == ABSwitchPosition.B
            else "Unknown",
        )

        if self.installed_components & ComponentClass.HAC1 == ComponentClass.HAC1:
            await self._read_hac_controller()
        else:
            _LOGGER.debug("No HAC controller installed")

        # Create coordinator
        self.coordinator = DanthermCoordinator(
            self._hass, self._device_name, self, self._scan_interval
        )

        # Load stored entities
        await self.coordinator.async_load_entities()

        return self.coordinator

    async def async_start(self):
        """Start the integration."""
        # Set up adaptive triggers
        await self._set_up_adaptive_triggers(self._options)

        # Do the first refresh of entities
        await self.coordinator.async_config_entry_first_refresh()

        # Set up tracking for adaptive triggers from the config options if any
        if self._options:
            await self._set_up_tracking_for_adaptive_triggers(self._options)

    async def async_initialize_after_restart(self):
        """Initialize the device after a restart."""
        await self._initialize_adaptive_triggers()

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
                entity_data = await self.coordinator.async_get_entity_data(description)
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

        install = True
        if exclude_from_component_class(description) or await exclude_from_entity_state(
            description
        ):
            install = False

        if install:
            return True
        _LOGGER.debug("Excluding an entity=%s", description.key)
        return False

    def _get_entity_state_from_coordinator(self, entity: str, default=None):
        """Get entity state from coordinator."""
        states = self.coordinator.data.get(entity, None)
        if states:
            return states["state"]
        return default

    @property
    def available(self) -> bool:
        """Return if device is available."""
        return self._attr_available

    @property
    def get_current_unit_mode(self):
        """Get current unit mode."""

        return self._current_unit_mode

    @property
    def get_active_unit_mode(self):
        """Get active unit mode."""

        return self._active_unit_mode

    @property
    def get_operation_selection(self):
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

    @property
    def get_current_operation(self):
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
    def get_fan_level(self):
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
        if mode in mode_icons:
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

    async def async_get_current_unit_mode(self):
        """Get current unit mmode."""

        self._current_unit_mode = await self._read_holding_uint32(
            MODBUS_REGISTER_CURRENT_MODE
        )
        _LOGGER.debug("Current unit mode = %s", self._to_hex(self._current_unit_mode))
        return self._current_unit_mode

    async def async_get_active_unit_mode(self):
        """Get active unit mode."""

        self._active_unit_mode = await self._read_holding_uint32(
            MODBUS_REGISTER_ACTIVE_MODE
        )
        _LOGGER.debug("Active unit mode = %s", self._to_hex(self._active_unit_mode))
        return self._active_unit_mode

    async def async_get_fan_level(self):
        """Get fan level."""

        self._fan_level = await self._read_holding_uint32(MODBUS_REGISTER_FAN_LEVEL)
        _LOGGER.debug("Fan level = %s", self._fan_level)
        return self._fan_level

    async def async_get_alarm(self):
        """Get alarm."""

        self._alarm = await self._read_holding_uint32(MODBUS_REGISTER_ALARM)
        _LOGGER.debug("Alarm = %s", self._alarm)
        return self._alarm

    async def async_sensor_filtering(self):
        """Get sensor filtering."""

        self._sensor_filtering = self._get_entity_state_from_coordinator(
            ATTR_SENSOR_FILTERING, False
        )
        return self._sensor_filtering

    async def async_get_week_program_selection(self):
        """Get week program selection."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_WEEK_PROGRAM_SELECTION)
        _LOGGER.debug("Week program selection = %s", result)
        return result

    @property
    def get_alarm(self):
        """Get alarm."""

        return self._alarm

    async def set_alarm_reset(self, value=None):
        """Reset alarm."""

        if value is None:
            value = self._alarm
        await self._write_holding_uint32(MODBUS_REGISTER_ALARM_RESET, value)

    async def async_get_bypass_damper(self):
        """Get bypass damper."""

        self._bypass_damper = await self._read_holding_uint32(
            MODBUS_REGISTER_BYPASS_DAMPER
        )
        _LOGGER.debug("Bypass damper = %s", self._bypass_damper)
        return self._bypass_damper

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

    @cached_property
    def _get_filter_lifetime_entity_installed(self) -> bool:
        """Check if the filter lifetime entity is installed (cached)."""
        return self.coordinator.is_entity_installed(ATTR_FILTER_LIFETIME)

    @cached_property
    def _get_filter_remain_entity_installed(self) -> bool:
        """Check if the filter remain entity is installed (cached)."""
        return self.coordinator.is_entity_installed(ATTR_FILTER_REMAIN)

    @cached_property
    def _get_filter_remain_level_entity_installed(self) -> bool:
        """Check if the filter remain level entity is installed (cached)."""
        return self.coordinator.is_entity_installed(ATTR_FILTER_REMAIN_LEVEL)

    async def async_get_filter_lifetime(self):
        """Get filter lifetime."""

        self._filter_lifetime = await self._read_holding_uint32(
            MODBUS_REGISTER_FILTER_LIFETIME
        )
        _LOGGER.debug("Filter lifetime = %s", self._filter_lifetime)

        return self._filter_lifetime

    async def async_get_filter_remain(self):
        """Get filter remain."""

        self._filter_remain = await self._read_holding_uint32(
            MODBUS_REGISTER_FILTER_REMAIN
        )
        _LOGGER.debug("Filter remain = %s", self._filter_remain)

        if not self._get_filter_remain_level_entity_installed:
            await self.async_get_filter_remain_level()

        return self._filter_remain

    async def async_get_filter_remain_level(self):
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

    @property
    def get_filter_remain_attrs(self):
        """Get filter remain attributes."""

        result = self._filter_remain_level
        if result is not None:
            return {"level": result}
        return None

    async def async_get_night_mode_start_time(self):
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

    async def async_get_night_mode_end_time(self):
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

    @property
    def get_bypass_available(self) -> bool:
        """Get bypass available."""
        return self._bypass_maximum_temperature != 0.0

    async def async_get_bypass_minimum_temperature(self):
        """Get bypass minimum temperature."""

        result = await self._read_holding_float32(MODBUS_REGISTER_BYPASS_MIN_TEMP, 1)
        _LOGGER.debug("Bypass minimum temperature = %.1f", result)
        return result

    async def async_get_bypass_maximum_temperature(self):
        """Get bypass maximum temperature."""

        self._bypass_maximum_temperature = await self._read_holding_float32(
            MODBUS_REGISTER_BYPASS_MAX_TEMP, 1
        )
        _LOGGER.debug(
            "Bypass maximum temperature = %.1f", self._bypass_maximum_temperature
        )
        return self._bypass_maximum_temperature

    async def async_get_manual_bypass_duration(self):
        """Get manual bypass duration."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_MANUAL_BYPASS_DURATION)
        _LOGGER.debug("Manual bypass duration = %s", result)
        return result

    @property
    def get_disable_bypass(self) -> bool:
        """Get disable bypass."""
        return self._bypass_maximum_temperature == 0.0

    async def set_filter_reset(self, value=None):
        """Reset filter."""

        if value is None:
            value = 1
        await self._write_holding_uint32(MODBUS_REGISTER_FILTER_RESET, value)

    async def set_active_unit_mode(self, value):
        """Set active unit mode."""

        await self._write_holding_uint32(MODBUS_REGISTER_ACTIVE_MODE, value)

    async def set_operation_selection(self, value):
        """Set operation selection."""

        async def update_operation(
            current_mode, active_mode, fan_level: int | None = None
        ):
            """Update the unit operation mode and fan level."""

            if self._current_unit_mode != current_mode:
                await self.set_active_unit_mode(active_mode)

            # Always set the fan level even if it's the same as before, as it may change after setting the operation mode.
            if fan_level is not None:
                await self.set_fan_level(fan_level)

        if value is None:
            return

        if value == STATE_AUTOMATIC:
            await update_operation(CurrentUnitMode.Automatic, ActiveUnitMode.Automatic)
        elif value == STATE_AWAY:
            # For away mode, update the mode accordingly
            await update_operation(CurrentUnitMode.Away, ActiveUnitMode.StartAway)
        elif value == STATE_LEVEL_1:
            await update_operation(CurrentUnitMode.Manual, ActiveUnitMode.Manual, 1)
        elif value == STATE_LEVEL_2:
            await update_operation(CurrentUnitMode.Manual, ActiveUnitMode.Manual, 2)
        elif value == STATE_LEVEL_3:
            await update_operation(CurrentUnitMode.Manual, ActiveUnitMode.Manual, 3)
        elif value == STATE_LEVEL_4:
            await update_operation(CurrentUnitMode.Manual, ActiveUnitMode.Manual, 4)
        elif value == STATE_MANUAL:
            # If in manual mode and the fan level is 0, change it to 1; otherwise leave it as is.
            fan_level = 1 if self._fan_level == 0 else None
            await update_operation(
                CurrentUnitMode.Manual, ActiveUnitMode.Manual, fan_level
            )
        elif value == STATE_STANDBY:
            # Standby means the fan should be off (0)
            await update_operation(CurrentUnitMode.Manual, ActiveUnitMode.Manual, 0)
        elif value == STATE_WEEKPROGRAM:
            await update_operation(
                CurrentUnitMode.WeekProgram, ActiveUnitMode.WeekProgram
            )

    async def set_fan_level(self, value):
        """Set fan level."""

        # Write the level to the fan level register
        await self._write_holding_uint32(MODBUS_REGISTER_FAN_LEVEL, value)

    async def set_week_program_selection(self, value):
        """Set week program selection."""

        # Write the program selection to the week program selection register
        await self._write_holding_uint32(MODBUS_REGISTER_WEEK_PROGRAM_SELECTION, value)

    async def set_filter_lifetime(self, value):
        """Set filter lifetime."""

        # Write the lifetime to filter lifetime register
        await self._write_holding_uint32(MODBUS_REGISTER_FILTER_LIFETIME, value)

    async def set_bypass_damper(self, feature: CoverEntityFeature = None):
        """Set bypass damper."""

        if self.get_active_unit_mode & 0x80 == 0x80:
            await self.set_active_unit_mode(0x8080)
        else:
            await self.set_active_unit_mode(0x80)

    async def set_night_mode_start_time(self, value):
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

    async def set_night_mode_end_time(self, value):
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

    async def set_bypass_minimum_temperature(self, value):
        """Set bypass minimum temperature."""

        # Write the temperature to the minimum temperature register
        await self._write_holding_float32(MODBUS_REGISTER_BYPASS_MIN_TEMP, value)

    async def set_bypass_maximum_temperature(self, value):
        """Set bypass maximum temperature."""

        # Write the temperature to the maximum temperature register
        await self._write_holding_float32(MODBUS_REGISTER_BYPASS_MAX_TEMP, value)

    async def set_manual_bypass_duration(self, value):
        """Set manual bypass duration."""

        # Write the duration to the manual bypass duration register
        await self._write_holding_uint32(MODBUS_REGISTER_MANUAL_BYPASS_DURATION, value)

    async def set_disable_bypass(self, value: bool):
        """Set automatic bypass."""

        # If value is True, set the maximum temperature to 0.0 to disable automatic bypass
        if value:
            await self.set_bypass_maximum_temperature(0.0)
        else:
            # If value is False, set the maximum temperature to a non-zero value (e.g., 24.0)
            await self.set_bypass_maximum_temperature(24.0)

    async def async_get_humidity(self):
        """Get humidity."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_HUMIDITY)
        _LOGGER.debug("Humidity = %s", result)
        if not self._sensor_filtering:
            return result
        return self._filter_sensor("humidity", result)

    async def async_get_air_quality(self):
        """Get air quality."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_AIR_QUALITY)
        _LOGGER.debug("Air quality = %s", result)
        if not self._sensor_filtering:
            return result
        return self._filter_sensor("air_quality", result)

    async def async_get_exhaust_temperature(self):
        """Get exhaust temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_EXHAUST_TEMP, precision=1
        )
        _LOGGER.debug("Exhaust temperature = %.1f", result)
        if not self._sensor_filtering:
            return result
        return self._filter_sensor("exhaust", result)

    async def async_get_extract_temperature(self):
        """Get extract temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_EXTRACT_TEMP, precision=1
        )
        _LOGGER.debug("Extract temperature = %.1f", result)
        if not self._sensor_filtering:
            return result
        return self._filter_sensor("extract", result)

    async def async_get_supply_temperature(self):
        """Get supply temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_SUPPLY_TEMP, precision=1
        )
        _LOGGER.debug("Supply temperature = %.1f", result)
        if not self._sensor_filtering:
            return result
        return self._filter_sensor("supply", result)

    async def async_get_outdoor_temperature(self):
        """Get outdoor temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_OUTDOOR_TEMP, precision=1
        )
        _LOGGER.debug("Outdoor temperature = %.1f", result)
        if not self._sensor_filtering:
            return result
        return self._filter_sensor("outdoor", result)

    async def async_get_room_temperature(self):
        """Get room temperature."""

        result = await self._read_holding_float32(
            MODBUS_REGISTER_ROOM_TEMP, precision=1
        )
        _LOGGER.debug("Room temperature = %.1f", result)
        if not self._sensor_filtering:
            return result
        return self._filter_sensor("room", result)

    async def async_get_adaptive_state(self) -> str:
        """Get adaptive state."""

        # Get the top event
        top = self.events.top()
        result = STATE_NONE
        if top:
            result = self.events.top()["event"]
        _LOGGER.debug("Adaptive state = %s", result)
        return result

    @property
    def get_adaptive_state_attrs(self):
        """Get adaptive state attributes."""
        if self.events:
            return {"events": self.events.to_list()}
        return None

    def _filter_sensor(self, sensor: str, new_value: float) -> float:
        """Filter a given sensor, ensuring smooth initialization and spike reduction."""

        # Ensure the sensor type is valid
        if sensor not in self._filtered_sensors:
            raise ValueError(f"Invalid sensor: {sensor}")

        sensor_data = self._filtered_sensors[sensor]
        history: deque = sensor_data["history"]

        # Collect initial samples and compute average until initialized
        if not sensor_data["initialized"]:
            if len(history) < history.maxlen:
                history.append(new_value)
                return round(sum(history) / len(history), 1)
            sensor_data["initialized"] = True

        # Compute rolling average
        rolling_average = sum(history) / len(history)

        # If new value is a spike, return rolling average (reject spike)
        if abs(new_value - rolling_average) > sensor_data["max_change"]:
            return round(rolling_average, 1)

        # Otherwise, accept new value and update history
        history.append(new_value)
        return new_value

    @cached_property
    def get_boost_mode_trigger_available(self) -> bool:
        """Get boost mode trigger available."""
        return self._options.get(ATTR_BOOST_MODE_TRIGGER, False)

    @cached_property
    def get_eco_mode_trigger_available(self) -> bool:
        """Get eco mode trigger available."""
        return self._options.get(ATTR_ECO_MODE_TRIGGER, False)

    @cached_property
    def get_home_mode_trigger_available(self) -> bool:
        """Get home mode trigger available."""
        return self._options.get(ATTR_HOME_MODE_TRIGGER, False)

    async def _set_up_adaptive_triggers(self, options: dict):
        """Enable/disable associated entities based on configured adaptive triggers."""
        entities = self._get_device_entities()

        any_trigger_available = False

        for trigger in ADAPTIVE_TRIGGERS:
            trigger_entity = options.get(trigger)

            enabled = bool(trigger_entity)
            if enabled:
                any_trigger_available = True

            trigger_data = self._adaptive_triggers.get(trigger)
            if not trigger_data:
                _LOGGER.debug("No data for trigger: %s", trigger)
                continue

            for entity_name in trigger_data["associated_entities"]:
                self._set_entity_enabled_by_suffix(entities, entity_name, enabled)

        # The adaptive_state entity should be enabled or disabled if any triggers are available.
        self._set_entity_enabled_by_suffix(
            entities, ATTR_ADAPTIVE_STATE, any_trigger_available
        )

    async def _set_up_tracking_for_adaptive_triggers(self, options: dict):
        """Set up tracking for adaptive triggers."""

        for trigger in ADAPTIVE_TRIGGERS:
            trigger_entity = options.get(trigger)
            if trigger_entity:
                trigger_data = self._adaptive_triggers[trigger]

                if trigger_entity != trigger_data["trigger"]:
                    if trigger_data["unsub"]:
                        trigger_data["unsub"]()  # remove previous listener
                    trigger_data["trigger"] = trigger_entity
                    if trigger_data["trigger"]:
                        trigger_data["unsub"] = async_track_state_change_event(
                            self._hass,
                            [trigger_data["trigger"]],
                            getattr(
                                self, f"_{trigger_data['name']}_mode_trigger_changed"
                            ),
                        )

    async def _initialize_adaptive_triggers(self) -> None:
        """Initialize adaptive triggers."""

        for trigger_name, trigger_data in self._adaptive_triggers.items():
            # Get trigger entity and skip if not available
            trigger_entity = trigger_data["trigger"]
            if not trigger_entity:
                continue

            # Get the trigger entity state
            state = self._hass.states.get(trigger_entity)
            if state is None:
                continue

            # Look up the event for this trigger
            event = self._lookup_event(trigger_data["name"])
            if event is None:
                continue

            trigger_data["timeout"] = event["timeout"]

            _LOGGER.debug(
                "Adaptive trigger '%s': timeout=%s",
                trigger_name,
                trigger_data["timeout"],
            )

    async def _boost_mode_trigger_changed(self, event):
        """Boost trigger state change callback."""
        if self._get_entity_state_from_coordinator(ATTR_BOOST_MODE):
            await self._mode_trigger_changed(ATTR_BOOST_MODE_TRIGGER, event)

    async def _eco_mode_trigger_changed(self, event):
        """Eco trigger state change callback."""
        if self._get_entity_state_from_coordinator(ATTR_ECO_MODE):
            await self._mode_trigger_changed(ATTR_ECO_MODE_TRIGGER, event)

    async def _home_mode_trigger_changed(self, event):
        """Home trigger state change callback."""
        if self._get_entity_state_from_coordinator(ATTR_HOME_MODE):
            await self._mode_trigger_changed(ATTR_HOME_MODE_TRIGGER, event)

    async def _mode_trigger_changed(self, trigger: str, event):
        """Mode trigger state change callback."""

        # Skip, if old state is None or Unknown
        old_state = event.data.get("old_state")
        if old_state is None or old_state.state == STATE_UNKNOWN:
            return

        # Skip, if new state is None
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        # Check if state is detected
        mode_data = self._adaptive_triggers[trigger]
        if new_state.state == STATE_ON:
            mode_data["detected"] = ha_now()
            _LOGGER.debug("%s detected!", trigger.capitalize())

        # Check if state is undetected
        elif new_state.state == STATE_OFF:
            mode_data["undetected"] = ha_now()
            _LOGGER.debug("%s undetected!", trigger.capitalize())

    async def async_update_adaptive_triggers(self):
        """Update adaptive triggers."""

        adaptive_trigger = None
        earliest = MAX_DT

        for trigger_name, mode_data in self._adaptive_triggers.items():
            # Skip if there is no trigger
            if not mode_data.get("trigger"):
                continue

            detected_time = mode_data["detected"]
            undetected_time = mode_data["undetected"]
            timeout_time = mode_data["timeout"]

            if detected_time:
                if undetected_time:
                    # If 'undetected' is older than 'detected',
                    # reset 'undetected'
                    if undetected_time < detected_time:
                        mode_data["undetected"] = None

                if detected_time < earliest:
                    earliest = detected_time
                    adaptive_trigger = trigger_name

            elif undetected_time:
                if undetected_time < earliest:
                    earliest = undetected_time
                    adaptive_trigger = trigger_name

            elif timeout_time and timeout_time < ha_now():
                if timeout_time < earliest:
                    earliest = timeout_time
                    adaptive_trigger = trigger_name

        if adaptive_trigger:
            await self._update_adaptive_trigger_state(adaptive_trigger)

    async def _update_adaptive_trigger_state(self, trigger_name: str):
        """Update adaptive trigger state."""

        mode_name = trigger_name.split("_", maxsplit=1)[0]
        # Check if mode is switch on
        if not self._get_entity_state_from_coordinator(f"{mode_name}_mode", False):
            return

        mode_data = self._adaptive_triggers[trigger_name]
        current_time = ha_now()

        # Check if operation mode change timeout has passed
        if current_time < self._operation_change_timeout:
            return

        current_operation = self.get_current_operation
        target_operation = None

        def get_trigger_timeout():  # Get the trigger timeout from it's number entity
            minutes = (
                3
                if IS_DEBUG
                else self._get_entity_state_from_coordinator(
                    f"{mode_name}_mode_timeout", 5
                )
            )
            return current_time + timedelta(minutes=minutes)

        if mode_data["detected"]:  # Check if the trigger is detected
            # Set new trigger timeout
            mode_data["timeout"] = get_trigger_timeout()

            # Check if this is not a repeated detection
            if not self._event_exists(mode_name):
                # Get the trigger target operation from it's selection entity
                possible_target = self._get_entity_state_from_coordinator(
                    f"{mode_name}_operation_selection", None
                )

                # Push the new event to the stack
                if self._push_event(
                    mode_name,
                    current_operation,
                    possible_target,
                    timeout=mode_data["timeout"],
                ):
                    target_operation = possible_target
            else:
                # Update the event with the new timeout
                self._update_event(mode_name, timeout=mode_data["timeout"])

            mode_data["detected"] = None

        elif mode_data["undetected"]:  # Check if the trigger is undetected
            # Set new trigger timeout
            mode_data["timeout"] = get_trigger_timeout()

            # Update the event with the new timeout
            self._update_event(mode_name, timeout=mode_data["timeout"])

            mode_data["undetected"] = None

        # Check if the trigger has timed out
        elif mode_data["timeout"] and mode_data["timeout"] < current_time:
            # If the trigger is still on extend the timeout
            state = self._hass.states.get(mode_data["trigger"])
            if state is not None and state.state == STATE_ON:
                # Set new trigger timeout
                mode_data["timeout"] = get_trigger_timeout()

                # Update the event with the new timeout
                self._update_event(mode_name, timeout=mode_data["timeout"])

                _LOGGER.debug("%s timeout extended!", trigger_name.capitalize())
                return

            # Remove event from stack
            target_operation = self._pop_event(mode_name)

            mode_data["timeout"] = None

        # Change the operation mode if any and different from the current operation
        if not target_operation or target_operation == current_operation:
            return

        # Set the operation change timeout
        self._operation_change_timeout = current_time + (
            timedelta(seconds=30)  # Default timeout for debug mode
            if IS_DEBUG
            else timedelta(minutes=2)  # Default timeout
        )

        _LOGGER.debug("Target operation = %s", target_operation)

        await self.set_operation_selection(target_operation)

    def _push_event(
        self, mode_name, current_operation, new_operation, timeout=None
    ) -> bool:
        """Push event to event stack."""
        result = self.events.push(
            mode_name, current_operation, new_operation, timeout=timeout
        )
        _LOGGER.debug("Push events: %s", self.events)
        return result

    def _update_event(self, mode_name, timeout=None):
        """Update event in event stack."""
        result = self.events.update(mode_name, timeout=timeout)
        _LOGGER.debug("Update events: %s", self.events)
        return result

    def _pop_event(self, mode_name):
        """Pop event from event stack."""
        operation = self.events.pop(mode_name)
        _LOGGER.debug("Pop events: %s = %s", mode_name, operation)
        return operation

    def _lookup_event(self, mode_name):
        """Lookup event in event stack."""
        event = self.events.lookup(mode_name)
        _LOGGER.debug("Lookup events: %s = %s", mode_name, event)
        return event

    def _event_exists(self, mode_name) -> bool:
        """Check if event exists."""
        return self.events.exists(mode_name)

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
    def get_device_fw_version(self) -> str:
        """Device firmware version."""

        major = (self._device_fw_version >> 8) & 0xFF
        minor = self._device_fw_version & 0xFF
        return f"({major}.{minor:02})"

    @property
    def get_device_serial_number(self) -> int:
        """Device serial number."""
        return self._device_serial_number

    async def get_device_id_from_entity(self, hass: HomeAssistant, entity_id):
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

    def _get_device_entities(self) -> list:
        """Return all entities that belong to this integration's device."""
        entity_registry = er.async_get(self._hass)
        device_registry = dr.async_get(self._hass)

        # Find device_id der matcher denne config entry
        device_id = next(
            (
                d.id
                for d in device_registry.devices.values()
                if self._entry_id in d.config_entries
            ),
            None,
        )

        if not device_id:
            _LOGGER.warning("No device found for config entry: %s", self._entry_id)
            return []

        return [
            entry
            for entry in entity_registry.entities.values()
            if entry.device_id == device_id
        ]

    def _set_entity_enabled_by_suffix(
        self, entities: list, name_suffix: str, enable: bool
    ):
        """Enable/disable entities that match a name suffix (with optional _#)."""
        pattern = re.compile(rf"_{name_suffix}(_\d+)?$")
        for entry in entities:
            if pattern.search(entry.unique_id):
                _LOGGER.debug(
                    "Updating entity: %s, enable: %s", entry.entity_id, enable
                )
                if enable:
                    self._set_entity_disabled_by(entry.entity_id, None)
                else:
                    self._set_entity_disabled_by(
                        entry.entity_id, RegistryEntryDisabler.INTEGRATION
                    )

    def _set_entity_disabled_by(self, entity_id, disabled_by: RegistryEntryDisabler):
        """Set entity disabled by state."""

        entity_registry = er.async_get(self._hass)

        entity_registry.async_update_entity(
            entity_id,
            disabled_by=disabled_by,
        )


class EventStack(deque):
    """Event Stack with priority and previous operation tracking."""

    def push(
        self, event, current_operation, new_operation, event_id=None, timeout=None
    ) -> bool:
        """Push an event onto the stack based on priority.

        Returns True if the event becomes the top event, otherwise False.
        """
        for item in self:
            if item["event"] == event and item.get("event_id", None) == event_id:
                # Update operation and reposition in stack
                self.remove(item)
                break

        insert_at = len(self)
        for idx, item in enumerate(self):
            if STATE_PRIORITIES.get(event, 0) > STATE_PRIORITIES.get(item["event"], 0):
                insert_at = idx
                break
            if item["event"] == event and item.get("event_id", None) != event_id:
                insert_at = idx
                break

        now = timeout if timeout is not None else ha_now()
        if insert_at == 0:
            self.appendleft(self._make_item(event, current_operation, now, event_id))
            return True

        previous_op = self[insert_at - 1]["previous"]
        self[insert_at - 1]["previous"] = new_operation
        self.insert(insert_at, self._make_item(event, previous_op, now, event_id))
        return False

    def update(self, event, event_id=None, timeout=None):
        """Update the timeout for an existing event to given timeout or now."""
        now = timeout.isoformat() if timeout is not None else ha_now().isoformat()
        for item in self:
            if item["event"] == event and item.get("event_id") == event_id:
                item["timeout"] = now
                return True
        return False

    def pop(self, event, event_id=None):
        """Remove an event (and optional ID) from the stack and adjust operation if needed.

        Returns the operation of the removed event if it was the top event, otherwise None.
        """
        for idx, item in enumerate(self):
            if item["event"] == event and item.get("event_id", None) == event_id:
                removed_item = item
                self.remove(removed_item)

                if idx == 0:
                    return removed_item["previous"]

                self[idx - 1]["previous"] = removed_item["previous"]
                return None

        return None

    def exists(self, event, event_id=None):
        """Check if an event with optional ID exists in the stack."""
        return any(
            item["event"] == event and item.get("event_id", None) == event_id
            for item in self
        )

    def lookup(self, event, event_id=None):
        """Look up the operation for a given event and optional ID in the stack."""
        for item in reversed(self):
            if item["event"] == event and item.get("event_id", None) == event_id:
                return item
        return None

    def top(self):
        """Return the top event of the stack."""
        return self[0] if self else None

    def is_top(self, event, event_id=None):
        """Check if the given event (and optional ID) is the top event in the stack."""
        return (
            bool(self)
            and self[0]["event"] == event
            and self[0].get("event_id", None) == event_id
        )

    def to_list(self):
        """Convert the event stack to a list of items."""
        return list(self)

    @classmethod
    def from_list(cls, items):
        """Create an event stack from a list of items."""
        stack = cls()
        for item in items:
            d = dict(item)
            if "timeout" in d and isinstance(d["timeout"], str):
                dt = parse_datetime(d["timeout"])
                d["timeout"] = dt if dt is not None else d["timeout"]
            stack.append(d)
        return stack

    def __repr__(self):
        """Return a string representation of the event stack."""
        return f"{self.to_list()}"

    def _make_item(self, event, operation, timeout: datetime, event_id=None):
        """Create an item for the stack."""
        item = {"event": event}
        if event_id is not None:
            item["event_id"] = event_id
        item["previous"] = operation
        item["timeout"] = timeout.isoformat()
        return item

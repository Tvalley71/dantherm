"""Device implementation."""

import asyncio
from collections import deque
from datetime import datetime, timedelta
import logging
import re

from pymodbus import ModbusException

from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.http.auth import Store
from homeassistant.components.modbus import modbus
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import Entity, EntityDescription, cached_property
from homeassistant.helpers.entity_registry import RegistryEntryDisabler
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .config_flow import (
    ADAPTIVE_TRIGGERS,
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_HOME_MODE_TRIGGER,
)
from .const import DEFAULT_NAME, DEVICE_TYPES, DOMAIN
from .device_map import (
    ATTR_ADAPTIVE_STATE,
    ATTR_BOOST_MODE,
    ATTR_BOOST_MODE_TIMEOUT,
    ATTR_BOOST_OPERATION_SELECTION,
    ATTR_BYPASS_DAMPER,
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
    STATE_AUTOMATIC,
    STATE_AWAY,
    STATE_FIREPLACE,
    STATE_LEVEL_1,
    STATE_LEVEL_2,
    STATE_LEVEL_3,
    STATE_LEVEL_4,
    STATE_MANUAL,
    STATE_NIGHT,
    STATE_PRIORITIES,
    STATE_STANDBY,
    STATE_SUMMER,
    STATE_WEEKPROGRAM,
    ActiveUnitMode,
    BypassDamperState,
    ComponentClass,
    CurrentUnitMode,
    DanthermEntityDescription,
    DataClass,
    HacComponentClass,
)

_LOGGER = logging.getLogger(__name__)


class DanthermEntity(Entity):
    """Dantherm Entity."""

    def __init__(self, device, description: DanthermEntityDescription) -> None:
        """Initialize the instance."""
        self._device = device
        self.entity_description: DanthermEntityDescription = description
        self._attr_unique_id = f"{self._device.get_device_name}_{description.key}"
        self._attr_should_poll = False
        self.attr_suspend_refresh: datetime | None = None

    async def async_added_to_hass(self):
        """Register entity for refresh interval."""
        await self._device.async_add_refresh_entity(self)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister entity for refresh interval."""
        await self._device.async_remove_refresh_entity(self)

    def suspend_refresh(self, seconds: int):
        """Suspend entity refresh for specified number of seconds."""
        self.attr_suspend_refresh = datetime.now() + timedelta(seconds=seconds)

    @property
    def key(self) -> str:
        """Return the key name."""
        return self.entity_description.key

    # @property
    # def unique_id(self) -> str | None:
    #     """Return the unique id."""
    #     return f"{self._device.get_device_name}_{self.key}"

    @property
    def translation_key(self) -> str:
        """Return the translation key name."""
        return self.key

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not self._device.available:
            return False
        return self._attr_available

    @property
    def device_info(self):
        """Device Info."""
        unique_id = self._device.get_device_name

        return {
            "identifiers": {
                (DOMAIN, unique_id),
            },
            "name": self._device.get_device_name,
            "manufacturer": DEFAULT_NAME,
            "model": self._device.get_device_type,
            "sw_version": self._device.get_device_fw_version,
            "serial_number": self._device.get_device_serial_number,
        }


class Device:
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
        self._hass = hass
        self._device_name = name
        self._entry_id = config_entry.entry_id
        self._options = config_entry.options
        self._device_type = 0
        self._device_installed_components = 0
        self._device_fw_version = 0
        self._device_serial_number = 0
        self._host = host
        self._port = port
        self._unit_id = int(unit_id)
        self._scan_interval = timedelta(seconds=scan_interval)
        self._client = modbus.AsyncModbusTcpClient(
            host=self._host, port=self._port, name=name, timeout=10
        )
        self._entity_refresh_method = None
        self._current_unit_mode = None
        self._active_unit_mode = None
        self._fan_level = None
        self._alarm = None
        self._sensor_filtering = False
        self._last_current_operation = None
        self._operation_change_timeout = datetime.min
        self._entity_store = Store(hass, version=1, key=f"{name}_entities")
        self._events = EventStack()
        self._available = True
        self._read_errors = 0
        self._entities = []
        self.store = {}
        self.data = {}

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
                "associated_entities": [
                    ATTR_BOOST_MODE,
                    ATTR_BOOST_MODE_TIMEOUT,
                    ATTR_BOOST_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": datetime.min,
                "trigger": None,
                "unsub": None,
            },
            ATTR_ECO_MODE_TRIGGER: {
                "associated_entities": [
                    ATTR_ECO_MODE,
                    ATTR_ECO_MODE_TIMEOUT,
                    ATTR_ECO_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": datetime.min,
                "trigger": None,
                "unsub": None,
            },
            ATTR_HOME_MODE_TRIGGER: {
                "associated_entities": [
                    ATTR_HOME_MODE,
                    ATTR_HOME_MODE_TIMEOUT,
                    ATTR_HOME_OPERATION_SELECTION,
                ],
                "detected": None,
                "undetected": None,
                "timeout": datetime.min,
                "trigger": None,
                "unsub": None,
            },
        }

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

    async def setup(self):
        """Set up modbus for Dantherm Device."""

        _LOGGER.debug("Setup has started")

        # Set up adaptive triggers
        await self.set_up_adaptive_triggers(self._options)

        # Connect and verify modbus connection
        result = await self._modbus_connect_and_verify()
        _LOGGER.info("Modbus setup completed successfully for %s", self._host)
        self._device_installed_components = result & 0xFFFF
        _LOGGER.debug(
            "Installed components (610) = %s", hex(self._device_installed_components)
        )

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

        # Set up tracking for adaptive triggers from the config options if any
        if self._options:
            await self.set_up_tracking_for_adaptive_triggers(self._options)

        if (
            self._device_installed_components & ComponentClass.HAC1
            == ComponentClass.HAC1
        ):
            await self._read_hac_controller()
        else:
            _LOGGER.debug("No HAC controller installed")

    async def async_install_entity(
        self, description: DanthermEntityDescription
    ) -> bool:
        """Test if the component is installed on the device."""

        def exclude_from_component_class(
            description: DanthermEntityDescription,
        ) -> bool:
            """Check if entity must be excluded from component_class."""
            if description.component_class:
                return (
                    self._device_installed_components & description.component_class
                ) == 0
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
                result = await self.async_get_entity_state(description)

                if (
                    (
                        description.data_exclude_if is not None
                        and description.data_exclude_if == result
                    )
                    or (
                        description.data_exclude_if_above is not None
                        and result >= description.data_exclude_if_above
                    )
                    or (
                        description.data_exclude_if_below is not None
                        and result <= description.data_exclude_if_below
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

    async def async_add_refresh_entity(self, entity):
        """Add entity for refresh."""

        # This is the first entity, set up interval.
        if not self._entities:
            self._entity_refresh_method = async_track_time_interval(
                self._hass, self.async_refresh_entities, self._scan_interval
            )

        _LOGGER.debug("Adding refresh entity=%s", entity.key)
        self._entities.append(entity)

    async def async_remove_refresh_entity(self, entity):
        """Remove entity for refresh."""

        if entity.key in self.data:
            self.data.pop(entity.key)
        if entity in self._entities:
            self._entities.remove(entity)

        if not self._entities:
            # This is the last entity, stop the interval timer
            self._entity_refresh_method()
            self._entity_refresh_method = None

            self._client.close()
            self._client = None
            # Wait for the client to close
            await asyncio.sleep(5)

    async def async_refresh_entities(self, _now: int | None = None) -> None:
        """Time to update entities."""

        # Check if any entities is installed
        if not self._entities:
            return

        _LOGGER.debug("<<< LOOP BEGIN - %s >>>", datetime.now().strftime("%H:%M:%S.%f"))

        # Read current unit mode
        self._current_unit_mode = await self._read_holding_uint32(
            MODBUS_REGISTER_CURRENT_MODE
        )
        _LOGGER.debug("Current unit mode = %s", hex(self._current_unit_mode))

        # Read active unit mode
        self._active_unit_mode = await self._read_holding_uint32(
            MODBUS_REGISTER_ACTIVE_MODE
        )
        _LOGGER.debug("Active unit mode = %s", hex(self._active_unit_mode))

        # Read fan level
        self._fan_level = await self._read_holding_uint32(MODBUS_REGISTER_FAN_LEVEL)
        _LOGGER.debug("Fan level = %s", self._fan_level)

        # Read alarm
        self._alarm = await self._read_holding_uint32(MODBUS_REGISTER_ALARM)
        _LOGGER.debug("Alarm = %s", self._alarm)

        self._sensor_filtering = self.data.get(ATTR_SENSOR_FILTERING, False)

        for entity in self._entities:
            await self.async_refresh_entity(entity)

        await self._update_adaptive_triggers()

        _LOGGER.debug("<<< LOOP END - %s >>>", datetime.now().strftime("%H:%M:%S.%f"))

    async def async_refresh_entity(self, entity: DanthermEntity) -> None:
        """Refresh an entity."""

        if entity.attr_suspend_refresh:
            if entity.attr_suspend_refresh > datetime.now():
                return
            entity.attr_suspend_refresh = None

        await entity.async_update_ha_state(True)

    async def async_load_entities(self):
        """Load device-specific entities."""
        store = await self._entity_store.async_load()
        if store is None:
            store = {"entities": {}}
        self.store = store

    async def async_save_entities(self):
        """Save device-specific entities."""
        await self._entity_store.async_save(self.store)

    async def set_entity_state(self, entity_key, value):
        """Set entity state for this device instance."""
        self.store["entities"][entity_key] = value
        await self.async_save_entities()

    def get_entity_state(self, entity_key, default=None):
        """Get entity state for this device instance."""
        return self.store["entities"].get(entity_key, default)

    @property
    def available(self) -> bool:
        """Indicates whether the device is available."""

        if not self._active_unit_mode:
            return False
        return self._available

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

        mode = self.get_current_unit_mode
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

    async def async_get_week_program_selection(self):
        """Get week program selection."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_WEEK_PROGRAM_SELECTION)
        _LOGGER.debug("Week program selection = %s", result)
        return result

    @property
    def get_alarm(self):
        """Get alarm."""

        return self._alarm

    async def alarm_reset(self, value=None):
        """Reset alarm."""

        if value is None:
            value = 0
        await self._write_holding_uint32(MODBUS_REGISTER_ALARM_RESET, value)

    async def async_get_bypass_damper(self):
        """Get bypass damper."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_BYPASS_DAMPER)
        _LOGGER.debug("Bypass damper = %s", result)
        return result

    @property
    def get_bypass_damper_icon(self) -> str:
        """Get bypass damper icon."""

        bypass_damper = self.data.get(ATTR_BYPASS_DAMPER, None)
        if bypass_damper == BypassDamperState.Closed:
            return "mdi:valve-closed"
        if bypass_damper == BypassDamperState.Opened:
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

    async def async_get_filter_lifetime(self):
        """Get filter lifetime."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_FILTER_LIFETIME)
        _LOGGER.debug("Filter lifetime = %s", result)

        return result

    async def async_get_filter_remain(self):
        """Get filter remain."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_FILTER_REMAIN)
        _LOGGER.debug("Filter remain = %s", result)
        return result

    @cached_property
    def _get_filter_lifetime_entity_installed(self) -> bool:
        """Check if the filter lifetime entity is installed (cached)."""
        return any(entity.key == ATTR_FILTER_LIFETIME for entity in self._entities)

    @cached_property
    def _get_filter_remain_entity_installed(self) -> bool:
        """Check if the filter remain entity is installed (cached)."""
        return any(entity.key == ATTR_FILTER_REMAIN for entity in self._entities)

    async def async_get_filter_remain_level(self):
        """Get filter remain level."""

        if self._get_filter_lifetime_entity_installed:
            filter_lifetime = self.data.get(ATTR_FILTER_LIFETIME, None)
        else:
            filter_lifetime = await self.async_get_filter_lifetime()

        if self._get_filter_remain_entity_installed:
            filter_remain = self.data.get(ATTR_FILTER_REMAIN, None)
        else:
            filter_remain = await self.async_get_filter_remain()

        if filter_lifetime is None or filter_remain is None:
            return None

        result = 0
        if filter_remain <= filter_lifetime:
            result = int((filter_lifetime - filter_remain) / (filter_lifetime / 3))
        _LOGGER.debug("Filter Remain Level = %s", result)
        return result

    @cached_property
    def _get_filter_remain_level_entity_installed(self) -> bool:
        """Check if the filter remain level entity is installed (cached)."""
        return any(entity.key == ATTR_FILTER_REMAIN_LEVEL for entity in self._entities)

    async def async_get_filter_remain_attrs(self):
        """Get filter remain attributes."""

        if self._get_filter_remain_level_entity_installed:
            result = self.data.get(ATTR_FILTER_REMAIN, None)
        else:
            result = await self.async_get_filter_remain_level()

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

    async def async_get_bypass_minimum_temperature(self):
        """Get bypass minimum temperature."""

        result = await self._read_holding_float32(MODBUS_REGISTER_BYPASS_MIN_TEMP, 1)
        _LOGGER.debug("Bypass minimum temperature = %.1f", result)
        return result

    async def async_get_bypass_maximum_temperature(self):
        """Get bypass maximum temperature."""

        result = await self._read_holding_float32(MODBUS_REGISTER_BYPASS_MAX_TEMP, 1)
        _LOGGER.debug("Bypass maximum temperature = %.1f", result)
        return result

    async def async_get_manual_bypass_duration(self):
        """Get manual bypass duration."""

        result = await self._read_holding_uint32(MODBUS_REGISTER_MANUAL_BYPASS_DURATION)
        _LOGGER.debug("Manual bypass duration = %s", result)
        return result

    async def filter_reset(self, value=None):
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
            """Update the unit operation with a short delay between mode and fan level."""

            operation_changed = False
            if self._current_unit_mode != current_mode:
                await self.set_active_unit_mode(active_mode)
                operation_changed = True

            # Always set the fan level even if it's the same as before, as it may change after setting the operation mode.
            if fan_level is not None:
                # Sleep for a second or else the fan level won't change.
                if operation_changed:
                    await asyncio.sleep(1)

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

    @property
    def get_adaptive_state(self):
        """Get adaptive state."""

        # Get the top event
        top = self._events.top()
        result = "none"
        if top:
            result = self._events.top()["event"]
        _LOGGER.debug("Adaptive state = %s", result)
        return result

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

    async def set_up_adaptive_triggers(self, options: dict):
        """Enable/disable associated entities based on configured adaptive triggers."""
        entities = self._get_device_entities()

        for trigger in ADAPTIVE_TRIGGERS:
            trigger_entity = options.get(trigger)
            enabled = bool(trigger_entity)

            mode_data = self._adaptive_triggers.get(trigger)
            if not mode_data:
                _LOGGER.debug("No data for trigger: %s", trigger)
                continue

            for entity_name in mode_data["associated_entities"]:
                self._set_entity_enabled_by_suffix(entities, entity_name, enabled)

        # The adaptive_state entity should be disabled if no adaptive triggers are configured.
        if not any(options.get(trigger) for trigger in ADAPTIVE_TRIGGERS):
            self._set_entity_enabled_by_suffix(entities, ATTR_ADAPTIVE_STATE, False)

    async def set_up_tracking_for_adaptive_triggers(self, options: dict):
        """Set up tracking for adaptive triggers."""

        def _set_up_tracking_for_adaptive_trigger(trigger_name: str, new_trigger: str):
            """Set up tracking for a adaptive trigger."""

            mode_data = self._adaptive_triggers[trigger_name]
            if new_trigger != mode_data["trigger"]:
                mode_name = trigger_name.split("_")[0]
                self.data[f"{mode_name}_mode"] = None
                if mode_data["unsub"]:
                    mode_data["unsub"]()  # remove previous listener
                mode_data["trigger"] = new_trigger
                if mode_data["trigger"]:
                    mode_data["unsub"] = async_track_state_change_event(
                        self._hass,
                        [mode_data["trigger"]],
                        getattr(self, f"_async_{mode_name}_trigger_changed"),
                    )

        for trigger in ADAPTIVE_TRIGGERS:
            trigger_entity = options.get(trigger)
            if trigger_entity:
                _set_up_tracking_for_adaptive_trigger(trigger, trigger_entity)

    async def _async_boost_trigger_changed(self, event):
        """Boost trigger state change callback."""
        if self.data[ATTR_BOOST_MODE]:
            await self._async_mode_trigger_changed(ATTR_BOOST_MODE_TRIGGER, event)

    async def _async_eco_trigger_changed(self, event):
        """Eco trigger state change callback."""
        if self.data[ATTR_ECO_MODE]:
            await self._async_mode_trigger_changed(ATTR_ECO_MODE_TRIGGER, event)

    async def _async_home_trigger_changed(self, event):
        """Home trigger state change callback."""
        if self.data[ATTR_HOME_MODE]:
            await self._async_mode_trigger_changed(ATTR_HOME_MODE_TRIGGER, event)

    async def _async_mode_trigger_changed(self, trigger: str, event):
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
            mode_data["detected"] = datetime.now()
            _LOGGER.debug("%s detected!", trigger.capitalize())

        # Check if state is undetected
        elif new_state.state == STATE_OFF:
            mode_data["undetected"] = datetime.now()
            _LOGGER.debug("%s undetected!", trigger.capitalize())

    async def _update_adaptive_triggers(self):
        """Update adaptive triggers."""

        adaptive_trigger = None
        earliest = datetime.max

        for trigger_name, mode_data in self._adaptive_triggers.items():
            # Skip if there is no trigger
            if not mode_data.get("trigger"):
                continue

            detected_time = mode_data["detected"]
            undetected_time = mode_data["undetected"]

            # Skip if both is None
            if detected_time is None and undetected_time is None:
                continue

            if detected_time:
                if undetected_time:
                    # If 'undetected' is older than 'detected',
                    # reset 'undetected'
                    if undetected_time < detected_time:
                        mode_data["undetected"] = None

                if detected_time < earliest:
                    earliest = detected_time
                    adaptive_trigger = trigger_name

            elif undetected_time < earliest:
                timeout = mode_data["timeout"]
                if timeout and timeout > datetime.now():
                    continue
                earliest = undetected_time
                adaptive_trigger = trigger_name

        if adaptive_trigger:
            await self._update_adaptive_trigger_state(adaptive_trigger)

    async def _update_adaptive_trigger_state(self, trigger_name: str):
        """Update adaptive trigger state."""

        mode_name = trigger_name.split("_", maxsplit=1)[0]
        # Check if mode is switch on
        if not self.data.get(f"{mode_name}_mode", False):
            return

        mode_data = self._adaptive_triggers[trigger_name]
        current_time = datetime.now()

        # Check if operation mode change timeout has passed
        if current_time < self._operation_change_timeout:
            return

        current_operation = self.get_current_operation
        target_operation = None

        # Check if the trigger is detected
        if mode_data["detected"]:
            # Set the timeout of the trigger
            mode_data["timeout"] = current_time + timedelta(
                minutes=self.data.get(f"{mode_name}_mode_timeout", 5)
                # seconds=10 * self.data.get(f"{mode_name}_mode_timeout", 5)
            )

            # Check if this is not a repeated detection
            if not self._event_exists(mode_name):
                # Get the mode target operation
                possible_target = self.data.get(
                    f"{mode_name}_operation_selection", None
                )

                # Push current operation and set the target operation if it has priority
                if self._push_event(mode_name, current_operation):
                    target_operation = possible_target

            mode_data["detected"] = None

        # Check if the trigger is undetected
        elif mode_data["undetected"]:
            # Remove event if undetected
            target_operation = self._pop_event(mode_name)

            mode_data["undetected"] = None

        # Change the operation mode if different from the current operation
        if not target_operation or target_operation == current_operation:
            return

        # Set the operation change timeout
        self._operation_change_timeout = current_time + timedelta(minutes=2)

        _LOGGER.debug("Target operation = %s", target_operation)

        await self.set_operation_selection(target_operation)

    def _push_event(self, mode_name, operation) -> bool:
        """Push event to event stack."""
        priority = self._events.has_priority(mode_name)
        self._events.push(mode_name, operation)
        _LOGGER.debug(self._events)
        return priority

    def _pop_event(self, mode_name):
        """Pop event from event stack."""
        operation = self._events.pop(mode_name)
        _LOGGER.debug(self._events)
        return operation

    def _event_exists(self, mode_name) -> bool:
        """Check if event exists."""
        return self._events.exists(mode_name)

    async def async_get_entity_state(self, description: DanthermEntityDescription):
        """Get entity value from description."""

        if description.data_unavailable:
            if self._options.get(description.data_unavailable, None) is None:
                return None

        if description.data_getinternal:
            if hasattr(self, f"async_{description.data_getinternal}"):
                result = await getattr(self, f"async_{description.data_getinternal}")()
            else:
                result = getattr(self, description.data_getinternal)
        elif description.data_store:
            result = self.get_entity_state(description.key, description.data_default)
        else:
            result = await self.read_holding_registers(description=description)

        return result

    async def async_get_entity_attrs(self, description: DanthermEntityDescription):
        """Get entity attributes from description."""

        result = None
        if hasattr(self, f"async_get_{description.key}_attrs"):
            result = await getattr(self, f"async_get_{description.key}_attrs")()
        elif hasattr(self, f"get_{description.key}_attrs"):
            result = getattr(self, f"get_{description.key}_attrs")
        return result

    async def read_holding_registers(
        self,
        description: EntityDescription | None = None,
        address: int | None = None,
        count=1,
        precision: int | None = None,
        scale=1,
    ):
        """Read modbus holding registers."""

        result = None
        if description:
            if not address:
                address = description.data_address
            if description.data_class == DataClass.Int32:
                result = await self._read_holding_int32(address)
            elif description.data_class == DataClass.UInt32:
                result = await self._read_holding_uint32(address)
            elif description.data_class == DataClass.UInt64:
                result = await self._read_holding_uint64(address)
            elif description.data_class == DataClass.Float32:
                if not precision:
                    precision = description.data_precision
                result = await self._read_holding_float32(address, precision)
        elif address:
            if count == 1:
                result = await self._read_holding_uint16(address)
            elif count == 2:
                result = await self._read_holding_uint32(address)
            elif count == 4:
                result = await self._read_holding_uint64(address)
        if result is None:
            _LOGGER.debug("Reading holding register=%s failed", str(address))
            return None
        result *= scale
        _LOGGER.debug("Reading holding register=%s result=%s", str(address), result)
        return result

    async def write_holding_registers(
        self,
        description: EntityDescription | None = None,
        address: int | None = None,
        value: int = 0,
        scale=1,
    ):
        """Write modbus holding registers."""

        value *= scale
        if description:
            data_class = description.data_setclass
            if not data_class:
                data_class = description.data_class
            if not address:
                address = description.data_setaddress
            if not address:
                address = description.data_address
            if data_class == DataClass.UInt32:
                await self._write_holding_uint32(address, value)
            elif data_class == DataClass.Float32:
                await self._write_holding_float32(address, value)
        else:
            await self._write_holding_registers(address, value)

    @property
    def get_device_name(self) -> str:
        """Device name."""

        return self._device_name

    @property
    def get_device_type(self) -> str:
        """Device type."""

        result = DEVICE_TYPES.get(self._device_type, None)
        if result is None:
            result = f"UNKNOWN {self._device_type}"
        return result

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

    async def _modbus_connect_and_verify(self):
        """Connect to Modbus and verify connection with retries."""
        _LOGGER.debug("Attempting Modbus connection for %s", self._host)
        connection = await self._client.connect()
        if not connection:
            _LOGGER.error("Modbus setup was unsuccessful for %s", self._host)
            raise ValueError("Modbus setup failed")

        _LOGGER.debug("Modbus connection established, verifying connection")
        for _ in range(5):
            result = await self._read_holding_uint32(610)
            if result is not None:
                _LOGGER.debug("Modbus client is connected!")
                self._available = True
                return result
            await asyncio.sleep(1)

        _LOGGER.error("Modbus client failed to respond for %s", self._host)
        self._client.close()
        raise ValueError("Modbus client failed to respond")

    async def _read_holding_registers(self, address, count):
        """Read holding registers."""
        try:
            response = await self._client.read_holding_registers(address, count=count)
            if response.isError() is False:
                return response.registers
            _LOGGER.error("Read holding registers failed: %s", response)
        except ConnectionError as err:
            _LOGGER.error("Read holding registers failed: %s", err)
            self._read_errors += 1
            if self._read_errors > 5:
                self._available = False
        return None

    async def _read_holding_registers_with_retry(
        self, address, count, retries=3, initial_delay=0.5
    ):
        """Read holding registers with retry using exponential backoff."""
        delay = initial_delay
        for _attempt in range(retries):
            result = await self._read_holding_registers(address, count)
            if result is not None:
                return result
            await asyncio.sleep(delay)
            delay *= 2
        return None

    async def _write_holding_registers(self, address, values):
        """Write holding registers."""
        try:
            await self._client.write_registers(address, values)
            _LOGGER.debug("Written %s to register address %d", values, address)
        except ConnectionError as err:
            _LOGGER.warning("Write holding registers failed: %s", err)
            self._available = False

    async def _read_holding_uint16(self, address):
        result = self._read_holding_uint32(address)
        return result & 0xFFFF

    async def _read_holding_int32(self, address):
        result = await self._read_holding_registers_with_retry(address, 2)
        return self._client.convert_from_registers(
            result, self._client.DATATYPE.INT32, "little"
        )

    async def _read_holding_uint32(self, address):
        try:
            result = await self._read_holding_registers_with_retry(address, 2)
            if result is None:
                _LOGGER.error(
                    "Failed to read holding registers for address %s", address
                )
                return None
            return self._client.convert_from_registers(
                result, self._client.DATATYPE.UINT32, "little"
            )
        except ModbusException as e:
            _LOGGER.error(
                "Exception in _read_holding_uint32 for address %s: %s", address, e
            )
            return None

    async def _write_holding_uint32(self, address, value):
        if value is None:
            return
        payload = self._client.convert_to_registers(
            int(value), self._client.DATATYPE.UINT32, "little"
        )
        await self._write_holding_registers(address, payload)

    async def _read_holding_uint64(self, address):
        result = await self._read_holding_registers_with_retry(address, 4)
        return self._client.convert_from_registers(
            result, self._client.DATATYPE.UINT64, "little"
        )

    async def _read_holding_float32(self, address, precision):
        result = await self._read_holding_registers_with_retry(address, 2)
        value = self._client.convert_from_registers(
            result, self._client.DATATYPE.FLOAT32, "little"
        )
        if value:
            if precision >= 0:
                value = round(value, precision)
            if precision == 0:
                value = int(value)
        return value

    async def _write_holding_float32(self, address, value: float):
        if value is None:
            return
        payload = self._client.convert_to_registers(
            float(value), self._client.DATATYPE.FLOAT32
        )
        await self._write_holding_registers(address, payload, "little")

    async def _read_hac_controller(self):
        _LOGGER.critical(
            "HAC controller found, please reach out for support collaboration"
        )

        result = await self._read_holding_uint32(574)
        _LOGGER.debug("HAC CO2 Level = %s ppm (574)", result)
        result = await self._read_holding_uint32(568)
        _LOGGER.debug("Low Threshold of CO2 = %s ppm (568)", result)
        result = await self._read_holding_uint32(570)
        _LOGGER.debug("Middle Threshold of CO2 = %s ppm (570)", result)
        result = await self._read_holding_uint32(572)
        _LOGGER.debug("High Threshold of CO2 = %s ppm (572)", result)
        result = await self._read_holding_uint32(244)
        _LOGGER.debug("Installed Hac components = %s (244)", hex(result))
        if result & HacComponentClass.CO2Sensor == HacComponentClass.CO2Sensor:
            _LOGGER.debug("CO2 sensor found")
        if result & HacComponentClass.PreHeater == HacComponentClass.PreHeater:
            _LOGGER.debug("Pre-heater found")
        if result & HacComponentClass.PreCooler == HacComponentClass.PreCooler:
            _LOGGER.debug("Pre-cooler found")
        if result & HacComponentClass.AfterHeater == HacComponentClass.AfterHeater:
            _LOGGER.debug("After-heater found")
        if result & HacComponentClass.AfterCooler == HacComponentClass.AfterCooler:
            _LOGGER.debug("After-cooler found")
        result = await self._read_holding_uint32(300)
        _LOGGER.debug("Hac active component = %s (300)", hex(result))
        result = await self._read_holding_int32(344)
        _LOGGER.debug("Setpoint of the T2 = %s °C (344)", result)
        result = await self._read_holding_int32(346)
        _LOGGER.debug("Setpoint of the T3 = %s °C (346)", result)
        result = await self._read_holding_int32(348)
        _LOGGER.debug("Setpoint of the T5 = %s °C (348)", result)


class EventStack:
    """Event Stack."""

    def __init__(self) -> None:
        """Initialize event stack using deque for improved performance."""
        self.stack = deque()

    def push(self, event, operation):
        """Push an event onto the stack or increase its count if it already exists."""
        for item in self.stack:
            if item["event"] == event:
                item["count"] += 1
                return False

        # If event does not exist, push it with count 1
        self.stack.append({"event": event, "operation": operation, "count": 1})
        return True

    def pop(self, event):
        """Remove an event from the stack, handling operation shifts if necessary."""
        temp = deque()
        removed_operation = None
        found = False

        while self.stack:
            item = self.stack.pop()
            if not found and item["event"] == event:
                found = True
                if item["count"] > 1:
                    item["count"] -= 1
                    self.stack.append(item)
                else:
                    removed_operation = item["operation"]
                    if self.stack:
                        top_item = self.stack.pop()
                        top_item["operation"] = removed_operation
                        self.stack.append(top_item)
                break
            temp.append(item)

        while temp:
            self.stack.append(temp.pop())

        if not found:
            return None
        return None if self.stack else removed_operation

    def exists(self, event):
        """Check if a specific event is present in the stack."""
        return any(item["event"] == event for item in self.stack)

    def lookup(self, event):
        """Find the latest occurrence of an event in the stack and return its operation."""
        for item in reversed(self.stack):
            if item["event"] == event:
                return item["operation"]
        return None

    def top(self):
        """Return the operation of the top event (last pushed)."""
        return self.stack[-1] if self.stack else None

    def is_top(self, event):
        """Check if the given event is currently the top event."""
        return bool(self.stack) and self.top()["event"] == event

    def has_priority(self, event):
        """Check if the top event has a lower priority than the event."""

        if not self.stack:
            return True  # If stack is empty, allow new event

        if len(self.stack) == 1:
            if self.top()["event"] == event and self.top()["count"] == 1:
                return True  # If the only event matches and count is 1

        return STATE_PRIORITIES.get(self.top()["event"], 0) < STATE_PRIORITIES.get(
            event, 0
        )

    def __repr__(self):
        """Return string representation of the event stack."""
        return f"Event stack: {list(self.stack)}"

"""Device implementation."""

import asyncio
from collections import deque
from datetime import datetime, timedelta
import logging
from typing import Any

from config.custom_components.dantherm.config_flow import (
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_HOME_MODE_TRIGGER,
)
from homeassistant.components.cover import CoverEntityFeature
from homeassistant.components.http.auth import Store
from homeassistant.components.modbus import modbus
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import DEFAULT_NAME, DEVICE_TYPES, DOMAIN
from .device_map import (
    ATTR_BOOST_MODE,
    ATTR_BYPASS_DAMPER,
    ATTR_ECO_MODE,
    ATTR_FILTER_LIFETIME,
    ATTR_FILTER_REMAIN,
    ATTR_HOME_MODE,
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

    def __init__(
        self,
        device,
    ) -> None:
        """Initialize the instance."""
        self._device = device
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

    @property
    def unique_id(self) -> str | None:
        """Return the unique id."""
        return f"{self._device.get_device_name}_{self.key}"

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

    global_calendar_store = None  # Static variable for shared calendar storage

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
        self._operation_last_change_time = datetime.min
        self._boost_trigger = None
        self._unsub_boost = None
        self._boost_trigger_changed = False
        self._boost_trigger_detected = False
        self._boost_timeout_time = datetime.min
        self._eco_trigger = None
        self._unsub_eco = None
        self._eco_trigger_changed = False
        self._eco_trigger_detected = False
        self._eco_timeout_time = datetime.min
        self._home_trigger = None
        self._unsub_home = None
        self._home_trigger_changed = False
        self._home_trigger_detected = False
        self._home_timeout_time = datetime.min
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

        # Use a static store instance for the shared calendar
        if Device.global_calendar_store is None:
            Device.global_calendar_store = Store(
                hass, version=1, key=f"{name}_calendar"
            )

        # Set up initial triggers from the config options
        self.update_mode_triggers_event(config_entry.options)

    async def setup(self):
        """Modbus setup for Dantherm Device."""
        _LOGGER.debug("Setup has started")

        connection = await self._client.connect()
        if not connection:
            _LOGGER.error("Modbus setup was unsuccessful for %s", self._host)
            raise ValueError("Modbus setup failed")

        _LOGGER.debug("Modbus setup completed, testing connection")
        for _ in range(5):
            result = await self._read_holding_uint32(610)
            if result is not None:
                _LOGGER.debug("Modbus client is connected!")
                self._available = True
                break
            await asyncio.sleep(1)
        else:
            _LOGGER.error("Modbus client failed to respond for %s", self._host)
            await self._client.close()
            raise ValueError("Modbus client failed to respond")

        _LOGGER.info("Modbus setup completed successfully for %s", self._host)
        self._device_installed_components = result & 0xFFFF
        _LOGGER.debug(
            "Installed components (610) = %s", hex(self._device_installed_components)
        )

        system_id = await self._read_holding_uint32(address=2)
        self._device_type = system_id >> 24
        _LOGGER.debug("Device type = %s", self.get_device_type)
        self._device_fw_version = await self._read_holding_uint32(address=24)
        _LOGGER.debug("Firmware version = %s", self.get_device_fw_version)
        self._device_serial_number = await self._read_holding_uint64(address=4)
        _LOGGER.debug("Serial number = %d", self.get_device_serial_number)

        if (
            self._device_installed_components & ComponentClass.HAC1
            == ComponentClass.HAC1
        ):
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
        else:
            _LOGGER.debug("No HAC controller installed")

    async def async_install_entity(self, description: EntityDescription) -> bool:
        """Test if the component is installed on the device."""

        install = True
        if (description.component_class) and (
            (self._device_installed_components & description.component_class) == 0
        ):
            install = False

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

        _LOGGER.debug("Adding refresh entity=%s", entity.name)
        self._entities.append(entity)

    async def async_remove_refresh_entity(self, entity):
        """Remove entity for refresh."""

        _LOGGER.debug("Removing refresh entity=%s", entity.name)
        self._entities.remove(entity)

        # Remove the entity from the data dictionary
        if entity.key in self.data:
            self.data.pop(entity.key)

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

        if not self._entities:
            return

        _LOGGER.debug(
            "Installed components = %s", hex(self._device_installed_components)
        )

        self._current_unit_mode = await self._read_holding_uint32(472)
        _LOGGER.debug("Current unit mode = %s", hex(self._current_unit_mode))

        self._active_unit_mode = await self._read_holding_uint32(168)
        _LOGGER.debug("Active unit mode = %s", hex(self._active_unit_mode))

        self._fan_level = await self._read_holding_uint32(324)
        _LOGGER.debug("Fan level = %s", self._fan_level)

        self._alarm = await self._read_holding_uint32(516)
        _LOGGER.debug("Alarm = %s", self._alarm)

        self._sensor_filtering = self.data.get(ATTR_SENSOR_FILTERING, False)
        _LOGGER.debug("Sensor Filtering = %s", self._sensor_filtering)

        for entity in self._entities:
            await self.async_refresh_entity(entity)

        await self._update_mode_triggers()

    async def async_refresh_entity(self, entity: DanthermEntity) -> None:
        """Refresh an entity."""

        if entity.attr_suspend_refresh:
            if entity.attr_suspend_refresh < datetime.now():
                entity.attr_suspend_refresh = None
                _LOGGER.debug("Remove suspension of entity=%s", entity.name)
            else:
                _LOGGER.debug("Skipping suspened entity=%s", entity.name)
                return

        _LOGGER.debug("Refresh entity=%s", entity.name)
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
        if result == 1:
            return "mdi:fan-speed-1"
        if result == 2:
            return "mdi:fan-speed-2"
        if result == 3:
            return "mdi:fan-speed-3"
        return "mdi:fan-plus"

    @property
    def get_fan_level_selection_icon(self) -> str:
        """Get fan level selection icon."""

        result = self.get_fan_level
        if not result:
            return "mdi:fan-off"
        if result == 1:
            return "mdi:fan-speed-1"
        if result == 2:
            return "mdi:fan-speed-2"
        if result == 3:
            return "mdi:fan-speed-3"
        return "mdi:fan-plus"

    @property
    def get_fan_level(self):
        """Get fan level."""

        return self._fan_level

    @property
    def get_fan_level_icon(self) -> str:
        """Get fan level icon."""

        if self._alarm != 0:
            return "mdi:fan-alert"

        result = self.get_current_unit_mode
        if result == CurrentUnitMode.Standby:
            return "mdi:fan-off"
        if result == CurrentUnitMode.Away:
            return "mdi:bag-suitcase"
        if result == CurrentUnitMode.Summer:
            return "mdi:weather-sunny"
        if result == CurrentUnitMode.Fireplace:
            return "mdi:fire"
        if result == CurrentUnitMode.Night:
            return "mdi:weather-night"
        if result == CurrentUnitMode.Automatic:
            return "mdi:fan-auto"
        if result == CurrentUnitMode.WeekProgram:
            return "mdi:fan-clock"

        result = self.get_operation_selection
        if result == STATE_STANDBY:
            return "mdi:fan-off"
        if result == STATE_AUTOMATIC:
            return "mdi:fan-auto"
        if result == STATE_WEEKPROGRAM:
            return "mdi:fan-clock"

        return "mdi:fan"

    async def async_get_week_program_selection(self):
        """Get week program selection."""

        result = await self._read_holding_uint32(466)
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
        await self._write_holding_uint32(514, value)

    async def async_get_bypass_damper(self):
        """Get bypass damper."""

        result = await self._read_holding_uint32(198)
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

        result = await self._read_holding_uint32(556)
        _LOGGER.debug("Filter lifetime = %s", result)

        return result

    async def async_get_filter_remain(self):
        """Get filter remain."""

        result = await self._read_holding_uint32(554)
        _LOGGER.debug("Filter remain = %s", result)

        return result

    async def async_get_filter_remain_level(self):
        """Get filter remain level."""

        filter_lifetime = self.data.get(ATTR_FILTER_LIFETIME, None)
        if filter_lifetime is None:
            filter_lifetime = await self.async_get_filter_lifetime()
        filter_remain = self.data.get(ATTR_FILTER_REMAIN, None)
        if filter_remain is None:
            filter_remain = await self.async_get_filter_remain()

        if filter_lifetime is None or filter_remain is None:
            return None

        if filter_remain > filter_lifetime:
            return 0
        return int((filter_lifetime - filter_remain) / (filter_lifetime / 3))

    async def async_get_filter_remain_attrs(self):
        """Get filter remain attributes."""

        result = await self.async_get_filter_remain_level()

        if result is not None:
            return {"level": result}
        return None

    async def async_get_night_mode_start_time(self):
        """Get night mode start time."""

        hour = await self._read_holding_uint32(332)
        _LOGGER.debug("Night mode start hour = %s", hour)
        minute = await self._read_holding_uint32(334)
        _LOGGER.debug("Night mode start minute = %s", minute)

        if hour is None or minute is None:
            return None
        return f"{hour:02}:{minute:02}"

    async def async_get_night_mode_end_time(self):
        """Get night mode end time."""

        hour = await self._read_holding_uint32(336)
        _LOGGER.debug("Night mode end hour = %s", hour)
        minute = await self._read_holding_uint32(338)
        _LOGGER.debug("Night mode end minute = %s", minute)

        if hour is None or minute is None:
            return None
        return f"{hour:02}:{minute:02}"

    async def async_get_bypass_minimum_temperature(self):
        """Get bypass minimum temperature."""

        result = await self._read_holding_float32(444, 1)
        _LOGGER.debug("Bypass minimum temperature = %.1f", result)

        return result

    async def async_get_bypass_maximum_temperature(self):
        """Get bypass maximum temperature."""

        result = await self._read_holding_float32(446, 1)
        _LOGGER.debug("Bypass maximum temperature = %.1f", result)

        return result

    async def async_get_manual_bypass_duration(self):
        """Get manual bypass duration."""

        result = await self._read_holding_uint32(264)
        _LOGGER.debug("Manual bypass duration = %s", result)

        return result

    async def filter_reset(self, value=None):
        """Reset filter."""

        if value is None:
            value = 1
        await self._write_holding_uint32(558, value)

    async def set_active_unit_mode(self, value):
        """Set active unit mode."""

        await self._write_holding_uint32(168, value)

    async def set_operation_selection(self, value):
        """Set operation selection."""

        async def update_operation(
            current_mode, active_mode, fan_level: int | None = None
        ):
            """Update the unit operation with a short delay between mode and fan level.

            If fan_level is None, only the unit mode is updated.
            """
            if self._current_unit_mode != current_mode:
                await self.set_active_unit_mode(active_mode)
            await asyncio.sleep(0.3)
            if fan_level is not None and self._fan_level != fan_level:
                await self.set_fan_level(fan_level)

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
        await self._write_holding_uint32(324, value)

    async def set_week_program_selection(self, value):
        """Set week program selection."""

        # Write the program selection to the week program selection register
        await self._write_holding_uint32(466, value)

    async def set_filter_lifetime(self, value):
        """Set filter lifetime."""

        # Write the lifetime to filter lifetime register
        await self._write_holding_uint32(556, value)

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
        await self._write_holding_uint32(332, hours)

        # Write the minutes to the minute register
        await self._write_holding_uint32(334, minutes)

    async def set_night_mode_end_time(self, value):
        """Set night mode end time."""

        # Split the time string into hours and minutes
        hours, minutes = map(int, value.split(":"))

        if not (0 <= hours < 24 and 0 <= minutes < 60):
            _LOGGER.error("Invalid time format: %s", value)
            return

        # Write the hours to the hour register
        await self._write_holding_uint32(336, hours)

        # Write the minutes to the minute register
        await self._write_holding_uint32(338, minutes)

    async def set_bypass_minimum_temperature(self, value):
        """Set bypass minimum temperature."""

        # Write the temperature to the minimum temperature register
        await self._write_holding_float32(444, value)

    async def set_bypass_maximum_temperature(self, value):
        """Set bypass maximum temperature."""

        # Write the temperature to the maximum temperature register
        await self._write_holding_float32(446, value)

    async def set_manual_bypass_duration(self, value):
        """Set manual bypass duration."""

        # Write the duration to the manual bypass duration register
        await self._write_holding_uint32(264, value)

    async def async_get_humidity(self):
        """Get humidity."""

        new_value = await self._read_holding_uint32(address=196)

        if not self._sensor_filtering:
            return new_value
        return self._filter_sensor("humidity", new_value)

    async def async_get_air_quality(self):
        """Get air quality."""

        new_value = await self._read_holding_uint32(address=430)

        if not self._sensor_filtering:
            return new_value
        return self._filter_sensor("air_quality", new_value)

    async def async_get_exhaust_temperature(self):
        """Get exhaust temperature."""

        new_value = await self._read_holding_float32(address=138, precision=1)

        if not self._sensor_filtering:
            return new_value
        return self._filter_sensor("exhaust", new_value)

    async def async_get_extract_temperature(self):
        """Get extract temperature."""

        new_value = await self._read_holding_float32(address=136, precision=1)

        if not self._sensor_filtering:
            return new_value
        return self._filter_sensor("extract", new_value)

    async def async_get_supply_temperature(self):
        """Get supply temperature."""

        new_value = await self._read_holding_float32(address=134, precision=1)

        if not self._sensor_filtering:
            return new_value
        return self._filter_sensor("supply", new_value)

    async def async_get_outdoor_temperature(self):
        """Get outdoor temperature."""

        new_value = await self._read_holding_float32(address=132, precision=1)

        if not self._sensor_filtering:
            return new_value
        return self._filter_sensor("outdoor", new_value)

    async def async_get_room_temperature(self):
        """Get room temperature."""

        new_value = await self._read_holding_float32(address=140, precision=1)

        if not self._sensor_filtering:
            return new_value
        return self._filter_sensor("room", new_value)

    def _filter_sensor(self, sensor: str, new_value: float) -> float:
        """Filter a given sensor, ensuring smooth initialization and spike reduction."""

        # Ensure the sensor type is valid
        if sensor not in self._filtered_sensors:
            raise ValueError(f"Invalid sensor: {sensor}")

        sensor_data = self._filtered_sensors[sensor]
        history: deque = sensor_data["history"]

        # Collect initial samples and compute average until initialized
        history.append(new_value)
        if not sensor_data["initialized"]:
            if len(history) < history.maxlen:
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

    async def set_calendar_event(self, event):
        """Set calendar event."""

        if self._events.has_priority(event):
            if event == ATTR_BOOST_MODE:
                self.data[ATTR_BOOST_MODE]
            self.set_operation_selection(event)

    def update_mode_triggers_event(self, options: dict):
        """Update tracking triggers based on new options."""

        new_boost = options.get(ATTR_BOOST_MODE_TRIGGER)
        new_eco = options.get(ATTR_ECO_MODE_TRIGGER)
        new_home = options.get(ATTR_HOME_MODE_TRIGGER)

        # Update boost trigger
        if new_boost != self._boost_trigger:
            self.data[ATTR_BOOST_MODE] = None
            if self._unsub_boost:
                self._unsub_boost()  # remove previous listener
            self._boost_trigger = new_boost
            if self._boost_trigger:
                self._unsub_boost = async_track_state_change_event(
                    self._hass,
                    [self._boost_trigger],
                    self._async_boost_trigger_changed,
                )

        # Update eco trigger
        if new_eco != self._eco_trigger:
            self.data[ATTR_ECO_MODE] = None
            if self._unsub_eco:
                self._unsub_eco()
            self._eco_trigger = new_eco
            if self._eco_trigger:
                self._unsub_eco = async_track_state_change_event(
                    self._hass,
                    [self._eco_trigger],
                    self._async_eco_trigger_changed,
                )

        # Update home trigger
        if new_home != self._home_trigger:
            self.data[ATTR_HOME_MODE] = None
            if self._unsub_home:
                self._unsub_home()
            self._home_trigger = new_home
            if self._home_trigger:
                self._unsub_home = async_track_state_change_event(
                    self._hass,
                    [self._home_trigger],
                    self._async_home_trigger_changed,
                )

    async def _async_boost_trigger_changed(self, event):
        """Boost trigger state change callback."""

        new_state = event.data.get("new_state")
        if new_state and new_state.state == "on":
            self._boost_trigger_detected = True
            _LOGGER.debug("Boost triggered!")
        else:
            self._boost_trigger_detected = False
        self._boost_trigger_changed = True

    async def _async_eco_trigger_changed(self, event):
        """Eco trigger state change callback."""

        new_state = event.data.get("new_state")
        if new_state and new_state.state == "on":
            self._eco_trigger_detected = True
            _LOGGER.debug("Eco triggered!")
        else:
            self._eco_trigger_detected = False
        self._eco_trigger_changed = True

    async def _async_home_trigger_changed(self, event):
        """Home trigger state change callback."""

        new_state = event.data.get("new_state")
        if new_state and new_state.state == "on":
            self._home_trigger_detected = True
            _LOGGER.debug("Home triggered!")
        else:
            self._home_trigger_detected = False
        self._home_trigger_changed = True

    async def _update_mode_triggers(self):
        """Update mode triggers."""

        if self._boost_trigger:
            if self._boost_trigger_changed:
                await self._update_mode_trigger("boost")
        elif self.data.get(ATTR_BOOST_MODE, None):
            self.data[ATTR_BOOST_MODE] = False

        if self._eco_trigger:
            if self._eco_trigger_changed:
                await self._update_mode_trigger("eco")
        elif self.data.get(ATTR_ECO_MODE, None):
            self.data[ATTR_ECO_MODE] = False

        if self._home_trigger:
            if self._home_trigger_changed:
                await self._update_mode_trigger("home")
        elif self.data.get(ATTR_HOME_MODE, None):
            self.data[ATTR_HOME_MODE] = False

    async def _update_mode_trigger(self, name: str):
        """Update mode."""

        if not self.data.get(f"{name}_mode", False):
            return

        current_time = datetime.now()

        # Check if timeout have passed since last mode change
        if current_time < getattr(self, f"_{name}_timeout_time"):
            return

        # Check if timeout have passed since last operation change
        if current_time - self._operation_last_change_time < timedelta(seconds=5):
            return

        _LOGGER.debug("Before: %s", self._events)

        current_operation = self.get_current_operation

        # Get the state of the trigger
        if getattr(self, f"_{name}_trigger_detected", False):
            # Set the timeout of the trigger
            setattr(
                self,
                f"_{name}_timeout_time",
                current_time
                + timedelta(seconds=self.data.get(f"{name}_trigger_timeout", 5)),
            )

            if self._events.any(name):
                return

            target_operation = self.data.get(f"{name}_operation_selection", None)

            self._events.push(name, current_operation)
            if not self._events.has_priority(name):
                target_operation = None
        else:
            target_operation = self._events.pop(name)

            setattr(self, f"_{name}_trigger_changed", False)

        _LOGGER.debug("After: %s", self._events)

        if target_operation and target_operation == current_operation:
            return

        # Update last change times
        self._operation_last_change_time = current_time

        setattr(self, f"_{name}_last_trigger_time", current_time)

        # Change the operation mode if different from the current one
        await self.set_operation_selection(target_operation)

    async def async_get_entity_state(self, description: DanthermEntityDescription):
        """Get entity value from description."""

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

    async def _read_holding_registers(self, address, count):
        """Read holding registers."""
        try:
            response = await self._client.read_holding_registers(address, count=count)
            return response.registers if response.isError() is False else None
        except ConnectionError as err:
            _LOGGER.error("Read holding registers failed: %s", err)
            self._read_errors += 1
            if self._read_errors > 5:
                self._available = False
            return None

    async def _write_holding_registers(self, address, values):
        """Write holding registers."""
        try:
            await self._client.write_registers(address, values)
        except ConnectionError as err:
            _LOGGER.error("Write holding registers failed: %s", err)
            self._available = False

    async def _read_holding_uint16(self, address):
        return self._read_holding_uint32(address) & 0xFFFF

    async def _read_holding_int32(self, address):
        result = await self._read_holding_registers(address, 2)
        return (
            self._client.convert_from_registers(
                result, self._client.DATATYPE.INT32, "little"
            )
            if result
            else None
        )

    async def _read_holding_uint32(self, address):
        result = await self._read_holding_registers(address, 2)
        return (
            self._client.convert_from_registers(
                result, self._client.DATATYPE.UINT32, "little"
            )
            if result
            else None
        )

    async def _write_holding_uint32(self, address, value):
        if value is None:
            return
        payload = self._client.convert_to_registers(
            int(value), self._client.DATATYPE.UINT32, "little"
        )
        await self._write_holding_registers(address, payload)

    async def _read_holding_uint64(self, address):
        result = await self._read_holding_registers(address, 4)
        return (
            self._client.convert_from_registers(
                result, self._client.DATATYPE.UINT64, "little"
            )
            if result
            else None
        )

    async def _read_holding_float32(self, address, precision):
        result = await self._read_holding_registers(address, 2)
        if result:
            value = self._client.convert_from_registers(
                result, self._client.DATATYPE.FLOAT32, "little"
            )
            if precision >= 0:
                value = round(value, precision)
            if precision == 0:
                value = int(value)
            return value
        return None

    async def _write_holding_float32(self, address, value: float):
        if value is None:
            return
        payload = self._client.convert_to_registers(
            float(value), self._client.DATATYPE.FLOAT32
        )
        await self._write_holding_registers(address, payload, "little")


class EventStack:
    """Event Stack."""

    def __init__(self) -> None:
        """."""
        self.stack = []

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
        for i in range(len(self.stack) - 1, -1, -1):  # Iterate from top to bottom
            if self.stack[i]["event"] == event:
                if self.stack[i]["count"] > 1:
                    self.stack[i]["count"] -= 1
                    return None

                # If count is 1, remove it
                removed_operation = self.stack[i]["operation"]
                del self.stack[i]

                # Shift operation to the event directly above it
                if i < len(self.stack):
                    self.stack[i]["operation"] = removed_operation
                    return None

                return removed_operation

        return None  # Event not found

    def any(self, event):
        """Check if a specific event is present in the stack.

        :param event: The event to look for.
        :return: True if the event is in the stack, False otherwise.
        """
        return any(item["event"] == event for item in self.stack)

    def lookup(self, event):
        """Find the latest occurrence of an event in the stack and return its operation."""
        for item in reversed(self.stack):
            if item["event"] == event:
                return item["operation"]
        return None

    def top(self):
        """Return the operation of the top event (last pushed)."""
        return self.stack[-1]["operation"] if self.stack else None

    def is_top(self, event):
        """Check if the given event is currently the top event.

        :param event: The event to check.
        :return: True if the event is on top, False otherwise.
        """
        return bool(self.stack) and self.stack[-1]["event"] == event

    def has_priority(self, event):
        """Check if the top event has a lower priority than the event.

        :param event: The event to compare against.
        :return: True if top event has lower priority, False otherwise.
        """

        if not self.stack:
            return True  # If stack is empty, allow new event

        if len(self.stack) == 1:
            if self.stack[0]["event"] == event and self.stack[0]["count"] == 1:
                return True  # If the only event matches and count is 1

        return STATE_PRIORITIES.get(self.stack[-1]["event"], 0) < STATE_PRIORITIES.get(
            event, 0
        )

    def __repr__(self):
        """."""
        return f"Stack: {self.stack}"

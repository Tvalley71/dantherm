"""The device mapping."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.calendar import CalendarEntityDescription
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntityDescription,
    CoverEntityFeature,
)
from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntityDescription
from homeassistant.components.text import TextEntityDescription, TextMode
from homeassistant.const import EntityCategory
from homeassistant.helpers.entity import EntityDescription

from .modbus import (
    MODBUS_REGISTER_FAN1_SPEED,
    MODBUS_REGISTER_FAN2_SPEED,
    MODBUS_REGISTER_INTERNAL_PREHEATER_DUTYCYCLE,
    MODBUS_REGISTER_WORK_TIME,
    DataClass,
)

REQUIRED_PYMODBUS_VERSION = "3.7.4"

SERVICE_SET_STATE = "set_state"
SERVICE_SET_CONFIGURATION = "set_configuration"
SERVICE_FILTER_RESET = "filter_reset"
SERVICE_ALARM_RESET = "alarm_reset"

ATTR_BYPASS_DAMPER: Final = "bypass_damper"

ATTR_CALENDAR: Final = "calendar"

ATTR_OPERATION_SELECTION: Final = "operation_selection"
STATE_STANDBY: Final = "standby"
STATE_AUTOMATIC: Final = "automatic"
STATE_MANUAL: Final = "manual"
STATE_WEEKPROGRAM: Final = "week_program"
STATE_AWAY: Final = "away"
STATE_SUMMER: Final = "summer"
STATE_FIREPLACE: Final = "fireplace"
STATE_NIGHT: Final = "night"
STATE_BOOST: Final = "boost"
STATE_ECO: Final = "eco"
STATE_HOME: Final = "home"

ATTR_FAN_LEVEL_SELECTION: Final = "fan_level_selection"
ATTR_FAN_LEVEL: Final = "fan_level"
STATE_FAN_LEVEL_0: Final = "0"
STATE_FAN_LEVEL_1: Final = "1"
STATE_FAN_LEVEL_2: Final = "2"
STATE_FAN_LEVEL_3: Final = "3"
STATE_FAN_LEVEL_4: Final = "4"

ATTR_WEEK_PROGRAM_SELECTION: Final = "week_program_selection"
STATE_WEEKPROGRAM_1: Final = "0"
STATE_WEEKPROGRAM_2: Final = "1"
STATE_WEEKPROGRAM_3: Final = "2"
STATE_WEEKPROGRAM_4: Final = "3"
STATE_WEEKPROGRAM_5: Final = "4"
STATE_WEEKPROGRAM_6: Final = "5"
STATE_WEEKPROGRAM_7: Final = "6"
STATE_WEEKPROGRAM_8: Final = "7"
STATE_WEEKPROGRAM_9: Final = "8"
STATE_WEEKPROGRAM_10: Final = "9"
STATE_WEEKPROGRAM_11: Final = "10"

ATTR_BOOST_OPERATION_SELECTION: Final = "boost_operation_selection"
STATE_LEVEL_3: Final = "level_3"
STATE_LEVEL_4: Final = "level_4"

ATTR_ECO_OPERATION_SELECTION: Final = "eco_operation_selection"

ATTR_HOME_OPERATION_SELECTION: Final = "home_operation_selection"
STATE_LEVEL_1: Final = "level_1"
STATE_LEVEL_2: Final = "level_2"

ATTR_DEFAULT_OPERATION_SELECTION: Final = "default_operation_selection"

ATTR_OPERATION_MODE: Final = "operation_mode"

ATTR_ALARM: Final = "alarm"
ATTR_DISABLE_ALARM_NOTIFICATIONS: Final = "disable_alarm_notifications"

ATTR_FAN1_SPEED: Final = "fan1_speed"
ATTR_FAN2_SPEED: Final = "fan2_speed"

ATTR_HUMIDITY = "humidity"
ATTR_HUMIDITY_LEVEL = "humidity_level"

ATTR_AIR_QUALITY: Final = "air_quality"
ATTR_AIR_QUALITY_LEVEL: Final = "air_quality_level"

ATTR_EXHAUST_TEMPERATURE: Final = "exhaust_temperature"

ATTR_EXTRACT_TEMPERATURE: Final = "extract_temperature"

ATTR_SUPPLY_TEMPERATURE: Final = "supply_temperature"

ATTR_OUTDOOR_TEMPERATURE: Final = "outdoor_temperature"

ATTR_ROOM_TEMPERATURE: Final = "room_temperature"

ATTR_DISABLE_TEMPERATURE_UNKNOWN: Final = "disable_temperature_unknown"

ATTR_AWAY_MODE: Final = "away_mode"

ATTR_SUMMER_MODE: Final = "summer_mode"

ATTR_BOOST_MODE_TRIGGER: Final = "boost_mode_trigger"
ATTR_BOOST_MODE: Final = "boost_mode"
ATTR_BOOST_MODE_TIMEOUT: Final = "boost_mode_timeout"

ATTR_ECO_MODE_TRIGGER: Final = "eco_mode_trigger"
ATTR_ECO_MODE: Final = "eco_mode"
ATTR_ECO_MODE_TIMEOUT: Final = "eco_mode_timeout"

ATTR_HOME_MODE_TRIGGER: Final = "home_mode_trigger"
ATTR_HOME_MODE: Final = "home_mode"
ATTR_HOME_MODE_TIMEOUT: Final = "home_mode_timeout"

ATTR_FIREPLACE_MODE: Final = "fireplace_mode"

ATTR_NIGHT_MODE: Final = "night_mode"
ATTR_NIGHT_MODE_START_TIME: Final = "night_mode_start_time"
ATTR_NIGHT_MODE_END_TIME: Final = "night_mode_end_time"

ATTR_MANUAL_BYPASS_MODE: Final = "manual_bypass_mode"
ATTR_MANUAL_BYPASS_DURATION: Final = "manual_bypass_duration"
ATTR_BYPASS_MINIMUM_TEMPERATURE: Final = "bypass_minimum_temperature"
ATTR_BYPASS_MAXIMUM_TEMPERATURE: Final = "bypass_maximum_temperature"
ATTR_DISABLE_BYPASS: Final = "disable_bypass"
ATTR_BYPASS_AVAILABLE: Final = "bypass_available"

ATTR_SENSOR_FILTERING: Final = "sensor_filtering"

ATTR_FILTER_LIFETIME: Final = "filter_lifetime"
ATTR_FILTER_REMAIN: Final = "filter_remain"
ATTR_FILTER_REMAIN_LEVEL: Final = "filter_remain_level"

ATTR_WORK_TIME: Final = "work_time"

ATTR_ADAPTIVE_STATE: Final = "adaptive_state"
STATE_NONE: Final = "none"

ATTR_INTERNAL_PREHEATER: Final = "internal_preheater"
ATTR_INTERNAL_PREHEATER_DUTYCYCLE: Final = "internal_preheater_dutycycle"

ATTR_FILTER_RESET: Final = "filter_reset"

ATTR_ALARM_RESET: Final = "alarm_reset"

ATTR_FEATURES: Final = "features"

OPERATION_SELECTIONS = [
    STATE_STANDBY,
    STATE_AUTOMATIC,
    STATE_MANUAL,
    STATE_WEEKPROGRAM,
    STATE_AWAY,
    STATE_SUMMER,
    STATE_FIREPLACE,
    STATE_NIGHT,
]

FAN_LEVEL_SELECTIONS = [
    STATE_FAN_LEVEL_0,
    STATE_FAN_LEVEL_1,
    STATE_FAN_LEVEL_2,
    STATE_FAN_LEVEL_3,
    STATE_FAN_LEVEL_4,
]

WEEK_PROGRAM_SELECTIONS = [
    STATE_WEEKPROGRAM_1,
    STATE_WEEKPROGRAM_2,
    STATE_WEEKPROGRAM_3,
    STATE_WEEKPROGRAM_4,
    STATE_WEEKPROGRAM_5,
    STATE_WEEKPROGRAM_6,
    STATE_WEEKPROGRAM_7,
    STATE_WEEKPROGRAM_8,
    STATE_WEEKPROGRAM_9,
    STATE_WEEKPROGRAM_10,
    STATE_WEEKPROGRAM_11,
]

ADAPTIVE_TRIGGERS = [
    ATTR_BOOST_MODE_TRIGGER,
    ATTR_ECO_MODE_TRIGGER,
    ATTR_HOME_MODE_TRIGGER,
]

BOOST_OPERATION_SELECTIONS = [STATE_LEVEL_2, STATE_LEVEL_3, STATE_LEVEL_4]

ECO_OPERATION_SELECTIONS = [STATE_STANDBY, STATE_LEVEL_1, STATE_LEVEL_2]

HOME_OPERATION_SELECTIONS = [
    STATE_AUTOMATIC,
    STATE_LEVEL_1,
    STATE_LEVEL_2,
    STATE_LEVEL_3,
    STATE_WEEKPROGRAM,
]

DEFAULT_OPERATION_SELECTIONS = [
    STATE_AUTOMATIC,
    STATE_LEVEL_1,
    STATE_LEVEL_2,
    STATE_LEVEL_3,
    STATE_WEEKPROGRAM,
]

STATE_PRIORITIES = {
    STATE_WEEKPROGRAM: 0,
    STATE_AUTOMATIC: 1,
    STATE_STANDBY: 2,
    STATE_LEVEL_1: 3,
    STATE_LEVEL_2: 4,
    STATE_LEVEL_3: 5,
    STATE_LEVEL_4: 6,
    STATE_ECO: 7,
    STATE_HOME: 8,
    STATE_NIGHT: 9,
    STATE_BOOST: 10,
    STATE_AWAY: 11,
}

EVENT_WORDS = STATE_PRIORITIES


class ComponentClass(int):
    """Danterm components."""

    FP1 = 0x0001
    Week = 0x0002
    Bypass = 0x0004
    LRSwitch = 0x0008
    Internal_preheater = 0x0010
    Servo_flow = 0x0020
    RH_Senser = 0x0040
    VOC_sensor = 0x0080
    Ext_Override = 0x0100
    HAC1 = 0x0200
    HRC2 = 0x0400
    PC_Tool = 0x0800
    Apps = 0x1000
    ZeegBee = 0x2000
    DI1_Override = 0x4000
    DI2_Override = 0x8000


class CurrentUnitMode(int):
    """Dantherm current unit mode class."""

    Standby = 0
    Manual = 1
    Automatic = 2
    WeekProgram = 3
    Away = 5
    Summer = 6
    Fireplace = 9
    Night = 16


class ActiveUnitMode(int):
    """Dantherm active unit mode class."""

    Automatic = 0x0002
    Manual = 0x0004
    WeekProgram = 0x0008

    Away = StartAway = 0x0010
    EndAway = 0x8010

    Night = NightEnable = 0x0020
    NightDisable = 0x8020

    Fireplace = StartFireplace = 0x0040
    EndFireplace = 0x8040

    ManualBypass = SelectManualBypass = 0x0080
    DeselectManualBypass = 0x8080

    Summer = StartSummer = 0x0800
    EndSummer = 0x8800


class BypassDamperState(int):
    """Dantherm bypass damper state class."""

    InProgress = 1
    Opening = 64
    Opened = 255
    Closing = 32
    Closed = 0


class ABSwitchPosition(Enum):
    """Dantherm A/B switch position class."""

    Unknown = 0
    A = 1
    B = 2


@dataclass
class DanthermEntityDescription(EntityDescription):
    """Dantherm Base Entity Description."""

    data_setaddress: int | None = None
    data_setinternal: str | None = None
    data_setclass: DataClass | None = None

    data_address: int | None = None
    data_getinternal: str | None = None
    data_default: Any | None = None
    data_class: DataClass = DataClass.UInt32

    icon_zero: str | None = None

    data_exclude_if: int | float | None = None
    data_exclude_if_above: int | float | None = None
    data_exclude_if_below: int | float | None = None

    firmware_exclude_if_below: float | None = None

    data_getavailable: str | None = None
    data_getunknown: str | None = None

    component_class: ComponentClass | None = None


@dataclass
class DanthermButtonEntityDescription(
    DanthermEntityDescription, ButtonEntityDescription
):
    """Dantherm Button Entity Description."""


@dataclass
class DanthermCalendarEntityDescription(
    DanthermEntityDescription, CalendarEntityDescription
):
    """Dantherm Calendar Entity Description."""


@dataclass
class DanthermCoverEntityDescription(DanthermEntityDescription, CoverEntityDescription):
    """Dantherm Cover Entity Description."""

    supported_features: CoverEntityFeature | None = None

    state_open: int | None = None
    state_close: int | None = None
    state_stop: int | None = None

    state_opening: int | None = None
    state_opened: int | None = None
    state_closing: int | None = None
    state_closed: int | None = None


@dataclass
class DanthermNumberEntityDescription(
    DanthermEntityDescription, NumberEntityDescription
):
    """Dantherm Number Entity Description."""

    data_precision: float | None = None


@dataclass
class DanthermSelectEntityDescription(
    DanthermEntityDescription, SelectEntityDescription
):
    """Dantherm Select Entity Description."""

    data_bitwise_and: int | None = None


@dataclass
class DanthermSensorEntityDescription(
    DanthermEntityDescription, SensorEntityDescription
):
    """Dantherm Sensor Entity Description."""

    data_precision: int | None = None


@dataclass
class DanthermSwitchEntityDescription(
    DanthermEntityDescription, SwitchEntityDescription
):
    """Dantherm Switch Entity Description."""

    state_seton: int | None = None
    state_setoff: int | None = None

    state_on: int | bool = True
    icon_on: str | None = None
    state_off: int | bool = False
    icon_off: str | None = None


@dataclass
class DanthermTimeTextEntityDescription(
    DanthermEntityDescription, TextEntityDescription
):
    """Dantherm Time Text Entity Description."""


BUTTONS: tuple[DanthermButtonEntityDescription, ...] = (
    DanthermButtonEntityDescription(
        key=ATTR_FILTER_RESET,
        icon="mdi:restore",
        data_setinternal="filter_reset",
        data_class=DataClass.UInt32,
    ),
    DanthermButtonEntityDescription(
        key=ATTR_ALARM_RESET,
        icon="mdi:restore-alert",
        data_setinternal="alarm_reset",
        data_class=DataClass.UInt32,
    ),
)

CALENDAR: tuple[DanthermCalendarEntityDescription, ...] = (
    DanthermCalendarEntityDescription(
        key=ATTR_CALENDAR,
        icon="mdi:calendar",
    ),
)

COVERS: tuple[DanthermCoverEntityDescription, ...] = (
    DanthermCoverEntityDescription(
        key=ATTR_BYPASS_DAMPER,
        icon="mdi:valve",
        supported_features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        data_getavailable=ATTR_BYPASS_AVAILABLE,
        data_setinternal=ATTR_BYPASS_DAMPER,
        data_getinternal=ATTR_BYPASS_DAMPER,
        state_opening=BypassDamperState.Opening,
        state_opened=BypassDamperState.Opened,
        state_closing=BypassDamperState.Closing,
        state_closed=BypassDamperState.Closed,
        component_class=ComponentClass.Bypass,
        device_class=CoverDeviceClass.DAMPER,
    ),
)

NUMBERS: tuple[DanthermNumberEntityDescription, ...] = (
    DanthermNumberEntityDescription(
        key=ATTR_FILTER_LIFETIME,
        icon="mdi:air-filter",
        data_setinternal=ATTR_FILTER_LIFETIME,
        data_getinternal=ATTR_FILTER_LIFETIME,
        native_max_value=360,
        native_min_value=0,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="d",
        mode=NumberMode.BOX,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermNumberEntityDescription(
        key=ATTR_BYPASS_MINIMUM_TEMPERATURE,
        icon="mdi:thermometer-minus",
        data_getavailable=ATTR_BYPASS_AVAILABLE,
        data_setinternal=ATTR_BYPASS_MINIMUM_TEMPERATURE,
        data_getinternal=ATTR_BYPASS_MINIMUM_TEMPERATURE,
        firmware_exclude_if_below=2.70,
        native_max_value=15,
        native_min_value=12,
        native_step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        mode=NumberMode.SLIDER,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        component_class=ComponentClass.Bypass,
    ),
    DanthermNumberEntityDescription(
        key=ATTR_BYPASS_MAXIMUM_TEMPERATURE,
        icon="mdi:thermometer-plus",
        data_getavailable=ATTR_BYPASS_AVAILABLE,
        data_setinternal=ATTR_BYPASS_MAXIMUM_TEMPERATURE,
        data_getinternal=ATTR_BYPASS_MAXIMUM_TEMPERATURE,
        firmware_exclude_if_below=2.70,
        native_max_value=27,
        native_min_value=21,
        native_step=0.1,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        mode=NumberMode.SLIDER,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        component_class=ComponentClass.Bypass,
    ),
    DanthermNumberEntityDescription(
        key=ATTR_MANUAL_BYPASS_DURATION,
        data_getavailable=ATTR_BYPASS_AVAILABLE,
        data_setinternal=ATTR_MANUAL_BYPASS_DURATION,
        data_getinternal=ATTR_MANUAL_BYPASS_DURATION,
        firmware_exclude_if_below=2.70,
        native_max_value=480,
        native_min_value=60,
        native_step=15,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="min",
        mode=NumberMode.BOX,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        component_class=ComponentClass.Bypass,
    ),
    DanthermNumberEntityDescription(
        key=ATTR_BOOST_MODE_TIMEOUT,
        data_default=5,
        data_precision=0,
        native_max_value=30,
        native_min_value=3,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="min",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermNumberEntityDescription(
        key=ATTR_ECO_MODE_TIMEOUT,
        data_default=15,
        data_precision=0,
        native_max_value=600,
        native_min_value=15,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="min",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermNumberEntityDescription(
        key=ATTR_HOME_MODE_TIMEOUT,
        data_default=60,
        data_precision=0,
        native_max_value=600,
        native_min_value=30,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="min",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)

SELECTS: tuple[DanthermSelectEntityDescription, ...] = (
    DanthermSelectEntityDescription(
        key=ATTR_OPERATION_SELECTION,
        icon="mdi:state-machine",
        data_setinternal=ATTR_OPERATION_SELECTION,
        data_getinternal=ATTR_OPERATION_SELECTION,
        options=OPERATION_SELECTIONS,
    ),
    DanthermSelectEntityDescription(
        key=ATTR_FAN_LEVEL_SELECTION,
        icon="mdi:fan",
        data_setinternal=ATTR_FAN_LEVEL,
        data_getinternal=ATTR_FAN_LEVEL,
        options=FAN_LEVEL_SELECTIONS,
    ),
    DanthermSelectEntityDescription(
        key=ATTR_WEEK_PROGRAM_SELECTION,
        icon="mdi:clock-edit",
        data_setinternal=ATTR_WEEK_PROGRAM_SELECTION,
        data_getinternal=ATTR_WEEK_PROGRAM_SELECTION,
        options=WEEK_PROGRAM_SELECTIONS,
        component_class=ComponentClass.Week,
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSelectEntityDescription(
        key=ATTR_BOOST_OPERATION_SELECTION,
        icon="mdi:state-machine",
        data_default=STATE_LEVEL_3,
        options=BOOST_OPERATION_SELECTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermSelectEntityDescription(
        key=ATTR_ECO_OPERATION_SELECTION,
        icon="mdi:state-machine",
        data_default=STATE_LEVEL_1,
        options=ECO_OPERATION_SELECTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermSelectEntityDescription(
        key=ATTR_HOME_OPERATION_SELECTION,
        icon="mdi:state-machine",
        data_default=STATE_AUTOMATIC,
        options=HOME_OPERATION_SELECTIONS,
        entity_category=EntityCategory.CONFIG,
    ),
)

SENSORS: tuple[DanthermSensorEntityDescription, ...] = (
    DanthermSensorEntityDescription(
        key=ATTR_OPERATION_MODE,
        data_getinternal="current_unit_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_ALARM,
        icon="mdi:alert-circle",
        icon_zero="mdi:alert-circle-check",
        data_getinternal=ATTR_ALARM,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_FAN_LEVEL,
        icon_zero="mdi:fan-off",
        data_getinternal=ATTR_FAN_LEVEL,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_FAN1_SPEED,
        icon="mdi:fan",
        icon_zero="mdi:fan-off",
        data_class=DataClass.Float32,
        data_address=MODBUS_REGISTER_FAN1_SPEED,
        native_unit_of_measurement="rpm",
        data_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_FAN2_SPEED,
        icon="mdi:fan",
        icon_zero="mdi:fan-off",
        data_class=DataClass.Float32,
        data_address=MODBUS_REGISTER_FAN2_SPEED,
        native_unit_of_measurement="rpm",
        data_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_HUMIDITY,
        data_getinternal=ATTR_HUMIDITY,
        data_exclude_if=0,
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        component_class=ComponentClass.RH_Senser,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_HUMIDITY_LEVEL,
        data_getinternal=ATTR_HUMIDITY_LEVEL,
        icon="mdi:water-percent",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        component_class=ComponentClass.RH_Senser,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_AIR_QUALITY,
        data_getinternal=ATTR_AIR_QUALITY,
        icon="mdi:molecule-co2",
        data_exclude_if=0,
        native_unit_of_measurement="ppm",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        component_class=ComponentClass.VOC_sensor,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_AIR_QUALITY_LEVEL,
        data_getinternal=ATTR_AIR_QUALITY_LEVEL,
        icon="mdi:molecule-co2",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        component_class=ComponentClass.VOC_sensor,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_EXHAUST_TEMPERATURE,
        data_getinternal=ATTR_EXHAUST_TEMPERATURE,
        data_getunknown=ATTR_EXHAUST_TEMPERATURE,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_EXTRACT_TEMPERATURE,
        data_getinternal=ATTR_EXTRACT_TEMPERATURE,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_SUPPLY_TEMPERATURE,
        data_getinternal=ATTR_SUPPLY_TEMPERATURE,
        data_getunknown=ATTR_SUPPLY_TEMPERATURE,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_OUTDOOR_TEMPERATURE,
        data_getinternal=ATTR_OUTDOOR_TEMPERATURE,
        data_getunknown=ATTR_OUTDOOR_TEMPERATURE,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_ROOM_TEMPERATURE,
        data_getinternal=ATTR_ROOM_TEMPERATURE,
        data_exclude_if_above=70,
        data_exclude_if_below=-40,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        component_class=ComponentClass.HRC2,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_FILTER_REMAIN,
        icon="mdi:air-filter",
        data_getinternal=ATTR_FILTER_REMAIN,
        native_unit_of_measurement="d",
        suggested_display_precision=0,
        suggested_unit_of_measurement="d",
        device_class=SensorDeviceClass.DURATION,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_FILTER_REMAIN_LEVEL,
        icon="mdi:air-filter",
        data_getinternal=ATTR_FILTER_REMAIN_LEVEL,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_WORK_TIME,
        icon="mdi:progress-clock",
        data_class=DataClass.UInt32,
        data_address=MODBUS_REGISTER_WORK_TIME,
        native_unit_of_measurement="h",
        suggested_display_precision=0,
        suggested_unit_of_measurement="h",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_INTERNAL_PREHEATER_DUTYCYCLE,
        icon="mdi:heating-coil",
        data_address=MODBUS_REGISTER_INTERNAL_PREHEATER_DUTYCYCLE,
        data_class=DataClass.UInt32,
        device_class=NumberDeviceClass.POWER_FACTOR,
        native_unit_of_measurement="%",
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        component_class=ComponentClass.Internal_preheater,
    ),
    DanthermSensorEntityDescription(
        key=ATTR_ADAPTIVE_STATE,
        icon="mdi:information",
        data_getinternal=ATTR_ADAPTIVE_STATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    # DanthermSensorEntityDescription(
    #    key=ATTR_FEATURES,
    #    icon="mdi:function",
    #    data_getinternal=ATTR_FEATURES,
    #    entity_category=EntityCategory.DIAGNOSTIC,
    # ),
)

SWITCHES: tuple[DanthermSwitchEntityDescription, ...] = (
    DanthermSwitchEntityDescription(
        key=ATTR_AWAY_MODE,
        data_setinternal="active_unit_mode",
        data_getinternal=ATTR_AWAY_MODE,
        state_on=ActiveUnitMode.StartAway,
        icon_on="mdi:bag-suitcase",
        state_off=ActiveUnitMode.EndAway,
        icon_off="mdi:bag-suitcase-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_NIGHT_MODE,
        data_setinternal="active_unit_mode",
        data_getinternal="active_unit_mode",
        state_on=ActiveUnitMode.NightEnable,
        icon_on="mdi:sleep",
        state_off=ActiveUnitMode.NightDisable,
        icon_off="mdi:sleep-off",
        device_class=SwitchDeviceClass.SWITCH,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_FIREPLACE_MODE,
        data_setinternal="active_unit_mode",
        data_getinternal=ATTR_FIREPLACE_MODE,
        state_seton=ActiveUnitMode.StartFireplace,
        icon_on="mdi:fireplace",
        state_setoff=ActiveUnitMode.EndFireplace,
        icon_off="mdi:fireplace-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_MANUAL_BYPASS_MODE,
        data_getavailable=ATTR_BYPASS_AVAILABLE,
        data_setinternal="active_unit_mode",
        data_getinternal="active_unit_mode",
        state_on=ActiveUnitMode.SelectManualBypass,
        icon_on="mdi:hand-back-right",
        state_off=ActiveUnitMode.DeselectManualBypass,
        icon_off="mdi:hand-back-right-off",
        component_class=ComponentClass.Bypass,
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_SUMMER_MODE,
        data_setinternal="active_unit_mode",
        data_getinternal=ATTR_SUMMER_MODE,
        state_seton=ActiveUnitMode.StartSummer,
        icon_on="mdi:weather-sunny",
        state_setoff=ActiveUnitMode.EndSummer,
        icon_off="mdi:weather-sunny-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_SENSOR_FILTERING,
        data_default=False,
        icon_on="mdi:filter",
        icon_off="mdi:filter-off",
        device_class=SwitchDeviceClass.SWITCH,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_BOOST_MODE,
        data_default=False,
        icon_on="mdi:rocket-launch",
        icon_off="mdi:rocket",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_ECO_MODE,
        data_default=False,
        icon_on="mdi:leaf",
        icon_off="mdi:leaf-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_HOME_MODE,
        data_default=False,
        icon_on="mdi:home",
        icon_off="mdi:home-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_DISABLE_BYPASS,
        data_setinternal=ATTR_DISABLE_BYPASS,
        data_getinternal=ATTR_DISABLE_BYPASS,
        icon_on="mdi:repeat-off",
        icon_off="mdi:repeat",
        component_class=ComponentClass.Bypass,
        device_class=SwitchDeviceClass.SWITCH,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
)

TIMETEXTS: tuple[DanthermTimeTextEntityDescription, ...] = (
    DanthermTimeTextEntityDescription(
        key=ATTR_NIGHT_MODE_START_TIME,
        icon="mdi:clock-start",
        data_setinternal=ATTR_NIGHT_MODE_START_TIME,
        data_getinternal=ATTR_NIGHT_MODE_START_TIME,
        mode=TextMode.TEXT,
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermTimeTextEntityDescription(
        key=ATTR_NIGHT_MODE_END_TIME,
        icon="mdi:clock-end",
        data_setinternal=ATTR_NIGHT_MODE_END_TIME,
        data_getinternal=ATTR_NIGHT_MODE_END_TIME,
        mode=TextMode.TEXT,
        entity_category=EntityCategory.CONFIG,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
)

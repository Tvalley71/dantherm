"""The device mapping."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Final

from homeassistant.components.button import ButtonEntityDescription
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
from homeassistant.const import EntityCategory

SERVICE_SET_STATE = "set_state"
SERVICE_FILTER_RESET = "filter_reset"
SERVICE_ALARM_RESET = "alarm_reset"

ATTR_OPERATION_SELECTION: Final = "operation_selection"
STATE_STANDBY: Final = "standby"
STATE_AUTOMATIC: Final = "automatic"
STATE_MANUAL: Final = "manual"
STATE_WEEKPROGRAM: Final = "week_program"
STATE_AWAY: Final = "away"
STATE_SUMMER: Final = "summer"
STATE_FIREPLACE: Final = "fireplace"
STATE_NIGHT: Final = "night"

ATTR_FAN_LEVEL_SELECTION: Final = "fan_level_selection"
ATTR_FAN_LEVEL: Final = "fan_level"
STATE_FAN_LEVEL_0: Final = "0"
STATE_FAN_LEVEL_1: Final = "1"
STATE_FAN_LEVEL_2: Final = "2"
STATE_FAN_LEVEL_3: Final = "3"
STATE_FAN_LEVEL_4: Final = "4"

ATTR_WEEK_PROGRAM: Final = "week_program_selection"
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

ATTR_AWAY_MODE: Final = "away_mode"

ATTR_SUMMER_MODE: Final = "summer_mode"

ATTR_FIREPLACE_MODE: Final = "fireplace_mode"

ATTR_NIGHT_MODE: Final = "night_mode"

ATTR_MANUAL_BYPASS_MODE: Final = "manual_bypass_mode"

ATTR_FILTER_RESET: Final = "filter_reset"

ATTR_ALARM_RESET: Final = "alarm_reset"

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
]


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


class HacComponentClass(int):
    """Dantherm HAC components."""

    CO2Sensor = 0x0001
    PreHeater = 0x0004
    PreCooler = 0x0008
    AfterHeater = 0x0010
    AfterCooler = 0x0020
    Hygrostat = 0x0040


class DataClass(Enum):
    """Dantherm modbus data class."""

    Int8 = 1
    UInt8 = 2
    Int16 = 3
    UInt16 = 4
    Int32 = 5
    UInt32 = 6
    UInt64 = 7
    Float32 = 8


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


@dataclass
class DanthermButtonEntityDescription(ButtonEntityDescription):
    """Dantherm Button Entity Description."""

    data_setaddress: int | None = None
    data_setinternal: str | None = None
    data_setclass: DataClass | None = None
    state: int = None
    state_entity: str | None = None

    data_address: int | None = None
    data_exclude_if: Any | None = None
    data_exclude_if_above: int | None = None
    data_exclude_if_below: int | None = None
    data_class: DataClass = DataClass.UInt16

    component_class: ComponentClass = None


@dataclass
class DanthermCoverEntityDescription(CoverEntityDescription):
    """Dantherm Cover Entity Description."""

    supported_features: CoverEntityFeature | None = None
    data_setaddress: int | None = None
    data_setinternal: str | None = None
    data_setclass: DataClass | None = None
    state_open: int = None
    state_close: int = None
    state_stop: int = None

    data_address: int | None = None
    data_getinternal: str | None = None
    data_entity: str | None = None
    data_exclude_if: Any | None = None
    data_exclude_if_above: int | None = None
    data_exclude_if_below: int | None = None
    data_class: DataClass = DataClass.UInt16
    state_opening: int = None
    state_opened: int = None
    state_closing: int = None
    state_closed: int = None

    component_class: ComponentClass = None


@dataclass
class DanthermNumberEntityDescription(NumberEntityDescription):
    """Dantherm Number Entity Description."""

    data_setaddress: int | None = None
    data_setinternal: str | None = None
    data_setclass: DataClass | None = None

    data_address: int | None = None
    data_getinternal: str | None = None
    data_precision: int | None = None
    data_entity: str | None = None
    data_exclude_if: Any | None = None
    data_exclude_if_above: int | None = None
    data_exclude_if_below: int | None = None
    data_class: DataClass = DataClass.UInt16

    component_class: ComponentClass = None


@dataclass
class DanthermSelectEntityDescription(SelectEntityDescription):
    """Dantherm Select Entity Description."""

    data_setaddress: int | None = None
    data_setinternal: str | None = None
    data_setclass: DataClass | None = None

    data_address: int | None = None
    data_getinternal: str | None = None
    data_entity: str | None = None
    data_bitwise_and: int | None = None
    data_exclude_if: Any | None = None
    data_exclude_if_above: int | None = None
    data_exclude_if_below: int | None = None
    data_class: DataClass = DataClass.UInt16

    component_class: ComponentClass = None


@dataclass
class DanthermSensorEntityDescription(SensorEntityDescription):
    """Dantherm Sensor Entity Description."""

    icon_zero: str | None = None
    data_address: int | None = None
    data_getinternal: str | None = None
    data_precision: int | None = None
    data_scale: int | None = None
    data_exclude_if: Any | None = None
    data_exclude_if_above: int | None = None
    data_exclude_if_below: int | None = None
    data_entity: str | None = None
    data_class: DataClass = DataClass.UInt16

    component_class: ComponentClass = None


@dataclass
class DanthermSwitchEntityDescription(SwitchEntityDescription):
    """Dantherm Switch Entity Description."""

    data_setaddress: int | None = None
    data_setinternal: str | None = None
    data_getinternal: str | None = None
    state_seton: int = None
    state_setoff: int = None
    data_setclass: DataClass | None = None

    state_suspend_for: int | None = None
    state_on: int = None
    icon_on: str = None
    state_off: int = None
    icon_off: str = None

    data_address: int | None = None
    data_entity: str | None = None
    data_exclude_if: Any | None = None
    data_exclude_if_above: int | None = None
    data_exclude_if_below: int | None = None
    data_class: DataClass = DataClass.UInt16

    component_class: ComponentClass = None


BUTTONS: tuple[DanthermButtonEntityDescription, ...] = (
    DanthermButtonEntityDescription(
        key=ATTR_FILTER_RESET,
        data_setinternal="filter_reset",
        data_class=DataClass.UInt32,
    ),
    DanthermButtonEntityDescription(
        key=ATTR_ALARM_RESET,
        data_setinternal="alarm_reset",
        data_class=DataClass.UInt32,
    ),
)

COVERS: tuple[DanthermCoverEntityDescription, ...] = (
    DanthermCoverEntityDescription(
        key="bypass_damper",
        supported_features=CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE,
        data_setinternal="set_bypass_damper",
        data_getinternal="get_bypass_damper",
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
        key="filter_lifetime",
        icon="mdi:air-filter",
        data_setinternal="set_filter_lifetime",
        data_getinternal="get_filter_lifetime",
        native_max_value=360,
        native_min_value=0,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="d",
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermNumberEntityDescription(
        key="bypass_minimum_temperature",
        data_address=444,
        native_max_value=15,
        native_min_value=12,
        data_class=DataClass.Float32,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        data_precision=1,
        mode=NumberMode.SLIDER,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        component_class=ComponentClass.Bypass,
    ),
    DanthermNumberEntityDescription(
        key="bypass_maximum_temperature",
        data_address=446,
        native_max_value=27,
        native_min_value=21,
        data_class=DataClass.Float32,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement="°C",
        data_precision=1,
        mode=NumberMode.SLIDER,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        component_class=ComponentClass.Bypass,
    ),
    DanthermNumberEntityDescription(
        key="manual_bypass_duration",
        data_address=264,
        native_max_value=480,
        native_min_value=60,
        data_class=DataClass.UInt32,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="min",
        native_step=15,
        mode=NumberMode.SLIDER,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.CONFIG,
        component_class=ComponentClass.Bypass,
    ),
)

SELECTS: tuple[DanthermSelectEntityDescription, ...] = (
    DanthermSelectEntityDescription(
        key=ATTR_OPERATION_SELECTION,
        icon="mdi:state-machine",
        data_setinternal=f"set_{ATTR_OPERATION_SELECTION}",
        data_getinternal=f"get_{ATTR_OPERATION_SELECTION}",
        options=OPERATION_SELECTIONS,
    ),
    DanthermSelectEntityDescription(
        key=ATTR_FAN_LEVEL_SELECTION,
        data_setinternal=f"set_{ATTR_FAN_LEVEL}",
        data_getinternal=f"get_{ATTR_FAN_LEVEL}",
        options=FAN_LEVEL_SELECTIONS,
    ),
    DanthermSelectEntityDescription(
        key=ATTR_WEEK_PROGRAM,
        icon="mdi:clock-edit-outline",
        data_address=466,
        data_class=DataClass.UInt32,
        options=WEEK_PROGRAM_SELECTIONS,
        component_class=ComponentClass.Week,
        entity_category=EntityCategory.CONFIG,
    ),
)

SENSORS: tuple[DanthermSensorEntityDescription, ...] = (
    DanthermSensorEntityDescription(
        key="operation_mode",
        data_getinternal="get_current_unit_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    DanthermSensorEntityDescription(
        key="alarm",
        icon="mdi:alert-circle-outline",
        icon_zero="mdi:alert-circle-check-outline",
        data_getinternal="get_alarm",
    ),
    DanthermSensorEntityDescription(
        key=ATTR_FAN_LEVEL,
        data_getinternal=f"get_{ATTR_FAN_LEVEL}",
    ),
    DanthermSensorEntityDescription(
        key="fan1_speed",
        icon="mdi:fan",
        icon_zero="mdi:fan-off",
        data_class=DataClass.Float32,
        data_address=100,
        native_unit_of_measurement="rpm",
        data_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSensorEntityDescription(
        key="fan2_speed",
        icon="mdi:fan",
        icon_zero="mdi:fan-off",
        data_class=DataClass.Float32,
        data_address=102,
        native_unit_of_measurement="rpm",
        data_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSensorEntityDescription(
        key="humidity",
        data_address=196,
        data_exclude_if=0,
        data_class=DataClass.UInt32,
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        component_class=ComponentClass.RH_Senser,
    ),
    DanthermSensorEntityDescription(
        key="air_quality",
        data_address=430,
        data_exclude_if=0,
        data_class=DataClass.UInt32,
        native_unit_of_measurement="ppm",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        component_class=ComponentClass.VOC_sensor,
    ),
    DanthermSensorEntityDescription(
        key="exhaust_temperature",
        data_class=DataClass.Float32,
        data_address=138,
        data_precision=1,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key="extract_temperature",
        data_class=DataClass.Float32,
        data_address=136,
        data_precision=1,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key="supply_temperature",
        data_class=DataClass.Float32,
        data_address=134,
        data_precision=1,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key="outdoor_temperature",
        data_class=DataClass.Float32,
        data_address=132,
        data_precision=1,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key="room_temperature",
        data_class=DataClass.Float32,
        data_address=140,
        data_precision=1,
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
        key="filter_remain",
        icon="mdi:air-filter",
        data_getinternal="get_filter_remain",
        native_unit_of_measurement="d",
        suggested_display_precision=0,
        suggested_unit_of_measurement="d",
        device_class=SensorDeviceClass.DURATION,
    ),
    DanthermSensorEntityDescription(
        key="filter_remain_level",
        icon="mdi:air-filter",
        data_getinternal="get_filter_remain_level",
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSensorEntityDescription(
        key="work_time",
        icon="mdi:progress-clock",
        data_class=DataClass.UInt32,
        data_address=624,
        native_unit_of_measurement="h",
        suggested_display_precision=0,
        suggested_unit_of_measurement="h",
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
    ),
    DanthermSensorEntityDescription(
        key="internal_preheater_dutycycle",
        icon="mdi:heating-coil",
        data_address=160,
        data_class=DataClass.UInt32,
        device_class=NumberDeviceClass.POWER_FACTOR,
        native_unit_of_measurement="%",
        entity_registry_visible_default=True,
        entity_registry_enabled_default=False,
        component_class=ComponentClass.Internal_preheater,
    ),
)

SWITCHES: tuple[DanthermSwitchEntityDescription, ...] = (
    DanthermSwitchEntityDescription(
        key=ATTR_AWAY_MODE,
        data_setinternal="set_active_unit_mode",
        data_getinternal=f"get_{ATTR_AWAY_MODE}",
        state_suspend_for=30,
        state_on=ActiveUnitMode.StartAway,
        icon_on="mdi:bag-suitcase-outline",
        state_off=ActiveUnitMode.EndAway,
        icon_off="mdi:bag-suitcase-off-outline",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_NIGHT_MODE,
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=ActiveUnitMode.NightEnable,
        icon_on="mdi:sleep",
        state_off=ActiveUnitMode.NightDisable,
        icon_off="mdi:sleep-off",
        device_class=SwitchDeviceClass.SWITCH,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_FIREPLACE_MODE,
        data_setinternal="set_active_unit_mode",
        data_getinternal=f"get_{ATTR_FIREPLACE_MODE}",
        state_suspend_for=30,
        state_seton=ActiveUnitMode.StartFireplace,
        icon_on="mdi:fireplace",
        state_setoff=ActiveUnitMode.EndFireplace,
        icon_off="mdi:fireplace-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_MANUAL_BYPASS_MODE,
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=ActiveUnitMode.SelectManualBypass,
        icon_on="mdi:hand-back-right-outline",
        state_off=ActiveUnitMode.DeselectManualBypass,
        icon_off="mdi:hand-back-right-off-outline",
        component_class=ComponentClass.Bypass,
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key=ATTR_SUMMER_MODE,
        data_setinternal="set_active_unit_mode",
        data_getinternal=f"get_{ATTR_SUMMER_MODE}",
        state_suspend_for=30,
        state_seton=ActiveUnitMode.StartSummer,
        icon_on="mdi:weather-sunny",
        state_setoff=ActiveUnitMode.EndSummer,
        icon_off="mdi:weather-sunny-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
)

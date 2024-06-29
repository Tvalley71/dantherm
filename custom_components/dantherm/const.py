"""The constants."""

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

DOMAIN = "dantherm"
DEFAULT_NAME = "Dantherm"
DEFAULT_SCAN_INTERVAL = 10
DEFAULT_PORT = 502


DEVICE_TYPES = {
    1: "WG200",
    2: "WG300",
    3: "WG500",
    4: "HCC 2",
    5: "HCC 2 ALU",
    6: "HCV300 ALU",
    7: "HCV500 ALU",
    8: "HCV700 ALU",
    9: "HCV400 P2",
    10: "HCV400 E1",
    11: "HCV400 P1",
    12: "HCC 2 E1",
    26: "RCV320",
}


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


class OpMode(int):
    """Dantherm mode of operation class."""

    Standby = 0
    Manual = 1
    Automatic = 2
    WeekProgram = 3
    Away = 5
    Summer = 6
    Fireplace = 9
    Night = 16


STATE_STANDBY: Final = "standby"
STATE_AUTOMATIC: Final = "automatic"
STATE_MANUAL: Final = "manual"
STATE_WEEKPROGRAM: Final = "week_program"
STATE_AWAY: Final = "away"
STATE_SUMMER: Final = "summer"
STATE_FIREPLACE: Final = "fireplace"


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
    data_setclass: DataClass | None = None
    state: int = None
    state_entity: str | None = None

    data_address: int | None = None
    data_exclude_if: Any | None = None
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
    data_entity: str | None = None
    data_exclude_if: Any | None = None
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
    data_class: DataClass = DataClass.UInt16

    component_class: ComponentClass = None


@dataclass
class DanthermSensorEntityDescription(SensorEntityDescription):
    """Dantherm Sensor Entity Description."""

    data_address: int | None = None
    data_getinternal: str | None = None
    data_precision: int | None = None
    data_scale: int | None = None
    data_exclude_if: Any | None = None
    data_entity: str | None = None
    data_zero_icon: str | None = None
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
    data_class: DataClass = DataClass.UInt16

    component_class: ComponentClass = None


BUTTONS: tuple[DanthermButtonEntityDescription, ...] = (
    DanthermButtonEntityDescription(
        key="filter_reset",
        data_setaddress=558,
        state=1,
        data_class=DataClass.UInt32,
    ),
    DanthermButtonEntityDescription(
        key="alarm_reset",
        data_setaddress=514,
        state_entity="alarm",
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
)

SELECTS: tuple[DanthermSelectEntityDescription, ...] = (
    DanthermSelectEntityDescription(
        key="operation_selection",
        icon="mdi:state-machine",
        data_setinternal="set_operation_selection",
        data_getinternal="get_operation_selection",
        options=[
            "standby",
            "automatic",
            "manual",
            "week_program",
            "away",
            "summer",
            "fireplace",
        ],
    ),
    DanthermSelectEntityDescription(
        key="fan_level_selection",
        data_setinternal="set_fan_level",
        data_getinternal="get_fan_level",
        options=["0", "1", "2", "3", "4"],
    ),
    DanthermSelectEntityDescription(
        key="week_program_selection",
        icon="mdi:clock-edit-outline",
        data_address=466,
        data_class=DataClass.UInt32,
        options=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
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
        data_getinternal="get_alarm",
        data_zero_icon="mdi:alert-circle-check-outline",
    ),
    DanthermSensorEntityDescription(
        key="fan_level",
        data_getinternal="get_fan_level",
    ),
    DanthermSensorEntityDescription(
        key="fan1_speed",
        icon="mdi:fan",
        data_class=DataClass.Float32,
        data_address=100,
        data_zero_icon="mdi:fan-off",
        native_unit_of_measurement="rpm",
        data_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    DanthermSensorEntityDescription(
        key="fan2_speed",
        icon="mdi:fan",
        data_class=DataClass.Float32,
        data_address=102,
        data_zero_icon="mdi:fan-off",
        native_unit_of_measurement="rpm",
        data_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
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
        key="preheater_dutycycle",
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
        key="away_mode",
        data_setinternal="set_active_unit_mode",
        state_seton=0x10,
        state_setoff=0x8010,
        data_getinternal="get_current_unit_mode",
        state_on=OpMode.Away,
        state_suspend_for=30,
        icon_on="mdi:bag-suitcase-outline",
        icon_off="mdi:bag-suitcase-off-outline",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key="night_mode",
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=0x20,
        icon_on="mdi:sleep",
        state_off=0x8020,
        icon_off="mdi:sleep-off",
        device_class=SwitchDeviceClass.SWITCH,
        entity_category=EntityCategory.CONFIG,
    ),
    DanthermSwitchEntityDescription(
        key="fireplace_mode",
        data_setinternal="set_active_unit_mode",
        state_seton=0x40,
        state_setoff=0x8040,
        data_getinternal="get_current_unit_mode",
        state_on=OpMode.Fireplace,
        state_suspend_for=30,
        icon_on="mdi:fireplace",
        icon_off="mdi:fireplace-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key="manual_bypass_mode",
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=0x80,
        icon_on="mdi:hand-back-right-outline",
        state_off=0x8080,
        icon_off="mdi:hand-back-right-off-outline",
        component_class=ComponentClass.Bypass,
        device_class=SwitchDeviceClass.SWITCH,
    ),
    DanthermSwitchEntityDescription(
        key="summer_mode",
        data_setinternal="set_active_unit_mode",
        state_seton=0x800,
        state_setoff=0x8800,
        data_getinternal="get_current_unit_mode",
        state_on=OpMode.Summer,
        state_suspend_for=30,
        icon_on="mdi:weather-sunny",
        icon_off="mdi:weather-sunny-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
)

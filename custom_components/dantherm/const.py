"""The constants."""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from homeassistant.components.button import ButtonEntityDescription
from homeassistant.components.cover import CoverDeviceClass, CoverEntityDescription
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
    Float32 = 7


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

    data_setaddress: int | None = None
    data_setclass: DataClass | None = None
    state_open: int = None
    state_close: int = None
    state_stop: int = None

    data_address: int | None = None
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
    data_setclass: DataClass | None = None

    data_address: int | None = None
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
    data_icon_zero: str | None = None
    data_class: DataClass = DataClass.UInt16
    icon_internal: str | None = None

    component_class: ComponentClass = None


@dataclass
class DanthermSwitchEntityDescription(SwitchEntityDescription):
    """Dantherm Switch Entity Description."""

    data_setaddress: int | None = None
    data_setinternal: str | None = None
    data_getinternal: str | None = None
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


BUTTON_TYPES: dict[str, list[DanthermButtonEntityDescription]] = {
    "filter_reset": DanthermButtonEntityDescription(
        key="filter_reset",
        data_setaddress=558,
        state=1,
    ),
    "alarm_reset": DanthermButtonEntityDescription(
        key="alarm_reset",
        data_setaddress=514,
        state_entity="alarm",
    ),
}

COVER_TYPES: dict[str, list[DanthermCoverEntityDescription]] = {
    "bypass_damper": DanthermCoverEntityDescription(
        key="bypass_damper",
        data_setaddress=168,
        data_setclass=DataClass.UInt16,
        state_open=0x0080,
        state_close=0x8080,
        data_address=198,
        data_class=DataClass.UInt16,
        state_opening=64,
        state_opened=255,
        state_closing=32,
        state_closed=0,
        component_class=ComponentClass.Bypass,
        icon="mdi:valve",
        device_class=CoverDeviceClass.DAMPER,
    )
}

NUMBER_TYPES: dict[str, list[DanthermNumberEntityDescription]] = {
    "filter_lifetime": DanthermNumberEntityDescription(
        key="filter_lifetime",
        data_class=DataClass.UInt32,
        data_address=556,
        native_max_value=360,
        native_min_value=0,
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement="d",
        mode=NumberMode.BOX,
    )
}

SELECT_TYPES: dict[str, list[DanthermSelectEntityDescription]] = {
    "operation_selection": DanthermSelectEntityDescription(
        key="operation_selection",
        data_setinternal="set_op_selection",
        data_getinternal="get_op_selection",
        options=["0", "1", "2", "3"],
    ),
    "fan_level_selection": DanthermSelectEntityDescription(
        key="fan_level_selection",
        data_setinternal="set_fan_level",
        data_getinternal="get_fan_level",
        options=["0", "1", "2", "3", "4"],
    ),
    "week_program_selection": DanthermSelectEntityDescription(
        key="week_program_selection",
        data_address=466,
        data_class=DataClass.UInt32,
        options=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ),
}

SENSOR_TYPES: dict[str, list[DanthermSensorEntityDescription]] = {
    "operation_mode": DanthermSensorEntityDescription(
        key="operation_mode",
        data_getinternal="get_current_unit_mode",
    ),
    "alarm": DanthermSensorEntityDescription(
        key="alarm",
        icon="mdi:alert-circle-outline",
        data_address=516,
        data_icon_zero="mdi:alert-circle-check-outline",
    ),
    "fan_level": DanthermSensorEntityDescription(
        key="fan_level",
        icon_internal="get_fan_icon",
        data_getinternal="get_fan_level",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "fan1_rpm": DanthermSensorEntityDescription(
        key="fan1_speed",
        icon="mdi:fan",
        data_class=DataClass.Float32,
        data_address=100,
        unit_of_measurement="rpm",
        data_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "fan2_speed": DanthermSensorEntityDescription(
        key="fan2_speed",
        icon="mdi:fan",
        data_class=DataClass.Float32,
        data_address=102,
        unit_of_measurement="rpm",
        data_precision=0,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "humidity": DanthermSensorEntityDescription(
        key="humidity",
        data_address=196,
        data_exclude_if=0,
        data_class=DataClass.UInt32,
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        # component_class=ComponentClass.RH_Senser,
    ),
    # "air_quality": DanthermSensorEntityDescription( # left out for now
    #     key="air_quality",
    #     data_address=430,
    #     data_exclude_if=0,
    #     data_class=DataClass.UInt32,
    #     native_unit_of_measurement="ppm",
    #     device_class=SensorDeviceClass.AQI,
    #     state_class=SensorStateClass.MEASUREMENT,
    #     # component_class=ComponentClass.VOC_sensor
    # ),
    "exhaust_temperature": DanthermSensorEntityDescription(
        key="exhaust_temperature",
        data_class=DataClass.Float32,
        data_address=138,
        data_precision=1,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "extract_temperature": DanthermSensorEntityDescription(
        key="extract_temperature",
        data_class=DataClass.Float32,
        data_address=136,
        data_precision=1,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "supply_temperature": DanthermSensorEntityDescription(
        key="supply_temperature",
        data_class=DataClass.Float32,
        data_address=134,
        data_precision=1,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "outdoor_temperature": DanthermSensorEntityDescription(
        key="outdoor_temperature",
        data_class=DataClass.Float32,
        data_address=132,
        data_precision=1,
        native_unit_of_measurement="°C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "filter_remain": DanthermSensorEntityDescription(
        key="filter_remain",
        data_class=DataClass.UInt32,
        data_address=554,
        native_unit_of_measurement="d",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
}

SWITCH_TYPES: dict[str, list[DanthermSwitchEntityDescription]] = {
    "away_mode": DanthermSwitchEntityDescription(
        key="away_mode",
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=0x10,
        icon_on="mdi:briefcase-outline",
        state_off=0x8010,
        icon_off="mdi:power-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "night_mode": DanthermSwitchEntityDescription(
        key="night_mode",
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=0x20,
        icon_on="mdi:weather-night",
        state_off=0x8020,
        icon_off="mdi:power-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "fireplace_mode": DanthermSwitchEntityDescription(
        key="fireplace_mode",
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=0x40,
        icon_on="mdi:fireplace",
        state_off=0x8040,
        icon_off="mdi:power-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "manual_bypass_mode": DanthermSwitchEntityDescription(
        key="manual_bypass_mode",
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=0x80,
        icon_on="mdi:arrow-decision-outline",
        state_off=0x8080,
        icon_off="mdi:arrow-decision-auto-outline",
        component_class=ComponentClass.Bypass,
        device_class=SwitchDeviceClass.SWITCH,
    ),
    "summer_mode": DanthermSwitchEntityDescription(
        key="summer_mode",
        data_setinternal="set_active_unit_mode",
        data_getinternal="get_active_unit_mode",
        state_suspend_for=30,
        state_on=0x800,
        icon_on="mdi:emoticon-cool-outline",
        state_off=8800,
        icon_off="mdi:power-off",
        device_class=SwitchDeviceClass.SWITCH,
    ),
}

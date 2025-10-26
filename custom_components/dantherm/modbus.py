"""Modbus implementation."""

import asyncio
from enum import IntEnum
import logging
import re

from pymodbus import ModbusException

from homeassistant.components.modbus import modbus
from homeassistant.helpers.entity import EntityDescription

# Modbus Register Constants
MODBUS_REGISTER_AB_SWITCH_POSITION_HAL_LEFT = 84
MODBUS_REGISTER_AB_SWITCH_POSITION_HAL_RIGHT = 86
MODBUS_REGISTER_ACTIVE_MODE = 168
MODBUS_REGISTER_AIR_QUALITY = 430
MODBUS_REGISTER_ALARM = 516
MODBUS_REGISTER_ALARM_RESET = 514
MODBUS_REGISTER_BYPASS_DAMPER = 198
MODBUS_REGISTER_BYPASS_MAX_TEMP = 446
MODBUS_REGISTER_BYPASS_MIN_TEMP = 444
MODBUS_REGISTER_BYPASS_MAX_TEMP_SUMMER = 764
MODBUS_REGISTER_BYPASS_MIN_TEMP_SUMMER = 766
MODBUS_REGISTER_CURRENT_MODE = 472
MODBUS_REGISTER_EXHAUST_TEMP = 138
MODBUS_REGISTER_EXTRACT_TEMP = 136
MODBUS_REGISTER_FAN_LEVEL = 324
MODBUS_REGISTER_FAN1_SPEED = 100
MODBUS_REGISTER_FAN2_SPEED = 102
MODBUS_REGISTER_FILTER_LIFETIME = 556
MODBUS_REGISTER_FILTER_REMAIN = 554
MODBUS_REGISTER_FILTER_RESET = 558
MODBUS_REGISTER_FIRMWARE_VERSION = 24
MODBUS_REGISTER_HUMIDITY = 196
MODBUS_REGISTER_HUMIDITY_SETPOINT = 340
MODBUS_REGISTER_HUMIDITY_SETPOINT_SUMMER = 768
MODBUS_REGISTER_INTERNAL_PREHEATER_DUTYCYCLE = 160
MODBUS_REGISTER_MANUAL_BYPASS_DURATION = 264
MODBUS_REGISTER_NIGHT_MODE_END_HOUR = 336
MODBUS_REGISTER_NIGHT_MODE_END_MINUTE = 338
MODBUS_REGISTER_NIGHT_MODE_START_HOUR = 332
MODBUS_REGISTER_NIGHT_MODE_START_MINUTE = 334
MODBUS_REGISTER_OUTDOOR_TEMP = 132
MODBUS_REGISTER_ROOM_TEMP = 140
MODBUS_REGISTER_SERIAL_NUMBER = 4
MODBUS_REGISTER_SUPPLY_TEMP = 134
MODBUS_REGISTER_SYSTEM_ID = 2
MODBUS_REGISTER_SYSTEM_ID_COMPONENTS = 610
MODBUS_REGISTER_WEEK_PROGRAM_SELECTION = 466
MODBUS_REGISTER_WORK_TIME = 624


class DataClass(IntEnum):
    """Dantherm modbus data class."""

    Int32 = 1
    UInt32 = 2
    UInt64 = 3
    Float32 = 4


class ABSwitchPosition(IntEnum):
    """Dantherm A/B switch position class."""

    Unknown = 0
    A = 1
    B = 2


_LOGGER = logging.getLogger(__name__)


class DanthermModbus:
    """Dantherm Modbus."""

    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        unit_id: int,
    ) -> None:
        """Initialize Modbus client."""
        self._host = host
        self._port = port
        self._unit_id = int(unit_id)
        self._client = modbus.AsyncModbusTcpClient(
            host=self._host, port=self._port, name=name, timeout=10
        )
        self._attr_available = False
        self._read_errors = 0
        self.coordinator = None

    async def ensure_connected(self) -> bool:
        """Ensure Modbus client is connected."""
        if self._client is None:
            self._client = modbus.AsyncModbusTcpClient(
                host=self._host, port=self._port, name="dantherm-reconnect", timeout=10
            )
        if not self._client.connected:
            _LOGGER.debug("Modbus client not connected, attempting reconnect")
            if not await self._client.connect():
                self._attr_available = False
                _LOGGER.warning("Modbus client reconnect failed")
                return False
        self._attr_available = True
        return True

    async def connect_and_verify(self):
        """Connect to Modbus and verify connection with retries."""

        _LOGGER.debug("Attempting Modbus connection for %s", self._host)
        if not await self._client.connect():
            _LOGGER.error("Modbus setup was unsuccessful for %s", self._host)
            raise ValueError("Modbus setup failed")

        _LOGGER.debug("Modbus connection established, verifying connection")
        for _ in range(5):
            result = await self._read_holding_uint32(
                MODBUS_REGISTER_SYSTEM_ID_COMPONENTS
            )
            if result is not None:
                _LOGGER.debug("Modbus client is connected!")
                self._attr_available = True
                return result
            await asyncio.sleep(1)

        _LOGGER.error("Modbus client failed to respond for %s", self._host)
        self._client.close()
        raise ValueError("Modbus client failed to respond")

    async def disconnect_and_close(self):
        """Disconnect from Modbus and close connection."""

        if self._client is None:
            _LOGGER.debug("Modbus client is already closed")
            return
        _LOGGER.debug("Disconnecting from Modbus client")
        self._attr_available = False
        self._read_errors = 0
        self._client.close()
        self._client = None
        _LOGGER.debug("Modbus client closed")
        # Wait for the client to close
        await asyncio.sleep(5)

    async def read_holding_registers(
        self,
        description: EntityDescription | None = None,
        address: int | None = None,
        count: int = 1,
        precision: int | None = None,
        scale: int = 1,
    ):
        """Read modbus holding registers."""
        if not await self.ensure_connected():
            _LOGGER.debug("Cannot read, Modbus client unavailable")
            return None

        result = None
        if description:
            if address is None:
                address = description.data_address
            match description.data_class:
                case DataClass.Int32:
                    result = await self._read_holding_int32(address)
                case DataClass.UInt32:
                    result = await self._read_holding_uint32(address)
                case DataClass.UInt64:
                    result = await self._read_holding_uint64(address)
                case DataClass.Float32:
                    if precision is None:
                        precision = description.data_precision
                    result = await self._read_holding_float32(address, precision)
        elif address:
            match count:
                case 1:
                    result = await self._read_holding_uint16(address)
                case 2:
                    result = await self._read_holding_uint32(address)
                case 4:
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
        scale: int = 1,
    ):
        """Write modbus holding registers."""
        value *= scale
        if description:
            if not address:
                address = description.data_setaddress or description.data_address
            data_class = description.data_setclass or description.data_class
            match data_class:
                case DataClass.UInt32:
                    await self._write_holding_uint32(address, value)
                case DataClass.Float32:
                    await self._write_holding_float32(address, value)
        else:
            self.coordinator.enqueue_backend(
                self.__write_holding_registers, address, value
            )

    async def get_device_ab_switch_position(self) -> ABSwitchPosition:
        """Get device A/B switch position."""

        HALLeft = await self._read_holding_uint32(
            MODBUS_REGISTER_AB_SWITCH_POSITION_HAL_LEFT
        )
        _LOGGER.debug("HALLeft = %s", HALLeft)
        HALRight = await self._read_holding_uint32(
            MODBUS_REGISTER_AB_SWITCH_POSITION_HAL_RIGHT
        )
        _LOGGER.debug("HALRight = %s", HALRight)

        result = ABSwitchPosition.Unknown
        if HALRight == 1 and HALLeft == 0:
            result = ABSwitchPosition.A
        elif HALRight == 0 and HALLeft == 1:
            result = ABSwitchPosition.B
        _LOGGER.debug("Device A/B switch position = %s", result.name)
        return result

    async def __read_holding_registers_with_retry(
        self, address: int, count: int, retries: int = 3, initial_delay: float = 0.5
    ):
        """Read holding registers with retry using exponential backoff."""
        delay = initial_delay
        for _ in range(retries):
            result = await self.__read_holding_registers(address, count)
            if result is not None:
                return result
            if self._attr_available is False:
                return None
            await asyncio.sleep(delay)
            delay *= 2
        _LOGGER.error("Failed to read holding registers for address %s", address)
        return None

    async def __read_holding_registers(self, address: int, count: int):
        """Read holding registers."""
        if not await self.ensure_connected():
            return None
        try:
            response = await self._client.read_holding_registers(address, count=count)
            if not response.isError():
                self._read_errors = 0
                return response.registers
            _LOGGER.error("Read holding registers failed: %s", response)
        except ModbusException as err:
            _LOGGER.error("Read holding registers failed: %s", err)
        self._read_errors += 1
        return None

    async def __write_holding_registers(self, address: int, values):
        """Write holding registers."""
        if not await self.ensure_connected():
            _LOGGER.debug("Modbus client is not available, cannot write")
            return
        try:
            await self._client.write_registers(address, values)
            _LOGGER.debug("Written %s to register address %d", values, address)
        except ModbusException as err:
            _LOGGER.warning("Write holding registers failed: %s", err)
            self._attr_available = False

    async def _read_holding_uint16(self, address):
        result = await self._read_holding_uint32(address)
        return result & 0xFFFF

    async def _read_holding_int32(self, address):
        result = await self.__read_holding_registers_with_retry(address, 2)
        if result is None:
            return None
        return self._client.convert_from_registers(
            result, self._client.DATATYPE.INT32, "little"
        )

    async def _read_holding_uint32(self, address):
        result = await self.__read_holding_registers_with_retry(address, 2)
        if result is None:
            return None
        return self._client.convert_from_registers(
            result, self._client.DATATYPE.UINT32, "little"
        )

    async def _write_holding_uint32(self, address, value):
        if value is None:
            return
        payload = self._client.convert_to_registers(
            int(value), self._client.DATATYPE.UINT32, "little"
        )
        self.coordinator.enqueue_backend(
            self.__write_holding_registers, address, payload
        )

    async def _read_holding_uint64(self, address):
        result = await self.__read_holding_registers_with_retry(address, 4)
        if result is None:
            return None
        return self._client.convert_from_registers(
            result, self._client.DATATYPE.UINT64, "little"
        )

    async def _read_holding_float32(self, address, precision):
        result = await self.__read_holding_registers_with_retry(address, 2)
        if result is None:
            return None
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
            float(value), self._client.DATATYPE.FLOAT32, "little"
        )
        self.coordinator.enqueue_backend(
            self.__write_holding_registers, address, payload
        )

    def _to_hex(self, value):
        """Convert value to hex string."""
        if isinstance(value, int):
            return hex(value)
        if isinstance(value, str):
            # Check if the string is a valid hexadecimal number
            if re.match(r"^0x[0-9a-fA-F]+$", value):
                return value
            # If not, convert it to an integer and then to hex
            return hex(int(value))
        return value

    async def _read_hac_controller(self):
        """Read HAC controller data."""

        class HacComponentClass(int):
            """Dantherm HAC components."""

            CO2Sensor = 0x0001
            PreHeater = 0x0004
            PreCooler = 0x0008
            AfterHeater = 0x0010
            AfterCooler = 0x0020
            Hygrostat = 0x0040

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

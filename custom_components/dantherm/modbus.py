"""Modbus implementation."""

import asyncio
import logging

from pymodbus import ModbusException
from voluptuous import Enum

from homeassistant.components.modbus import modbus
from homeassistant.helpers.entity import EntityDescription

# Modbus Register Constants
MODBUS_REGISTER_ACTIVE_MODE = 168
MODBUS_REGISTER_AIR_QUALITY = 430
MODBUS_REGISTER_ALARM = 516
MODBUS_REGISTER_ALARM_RESET = 514
MODBUS_REGISTER_BYPASS_DAMPER = 198
MODBUS_REGISTER_BYPASS_MAX_TEMP = 446
MODBUS_REGISTER_BYPASS_MIN_TEMP = 444
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


class DataClass(Enum):
    """Dantherm modbus data class."""

    Int32 = 1
    UInt32 = 2
    UInt64 = 3
    Float32 = 4


_LOGGER = logging.getLogger(__name__)


class DanthermModbus:
    """Dantherm Modbus."""

    def __init__(
        self,
        name,
        host,
        port,
        unit_id,
    ) -> None:
        """Init modbus."""
        self._host = host
        self._port = port
        self._unit_id = int(unit_id)
        self._client = modbus.AsyncModbusTcpClient(
            host=self._host, port=self._port, name=name, timeout=10
        )
        self._attr_available = False
        self._read_errors = 0
        self.coordinator = None

    async def connect_and_verify(self):
        """Connect to Modbus and verify connection with retries."""
        _LOGGER.debug("Attempting Modbus connection for %s", self._host)
        connection = await self._client.connect()
        if not connection:
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
        """Disconnect from Modbus and close connnection."""

        if self._client is None:
            _LOGGER.debug("Modbus client is already closed")
            return
        _LOGGER.debug("Disconnecting from Modbus client")
        self._attr_available = False
        self._read_errors = 0
        await self._client.close()
        _LOGGER.debug("Closing Modbus client")
        if self._client.is_socket_open():
            _LOGGER.debug("Socket is still open, closing it")
            self._client.close()
        else:
            _LOGGER.debug("Socket is already closed")
        self._client = None
        _LOGGER.debug("Modbus client closed")
        # Wait for the client to close
        await asyncio.sleep(5)

    @property
    def available(self) -> bool:
        """Return if modbus is available."""

        return self._attr_available

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
            if address is None:
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
            if not address:
                address = description.data_setaddress
            if not address:
                address = description.data_address
            data_class = description.data_setclass
            if not data_class:
                data_class = description.data_class
            if data_class == DataClass.UInt32:
                await self._write_holding_uint32(address, value)
            elif data_class == DataClass.Float32:
                await self._write_holding_float32(address, value)
        else:
            self.coordinator.enqueue_backend(
                self.__write_holding_registers, address, value
            )

    async def __read_holding_registers(self, address, count):
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
                self._attr_available = False
        return None

    async def __read_holding_registers_with_retry(
        self, address, count, retries=3, initial_delay=0.5
    ):
        """Read holding registers with retry using exponential backoff."""
        delay = initial_delay
        for _attempt in range(retries):
            result = await self.__read_holding_registers(address, count)
            if result is not None:
                return result
            await asyncio.sleep(delay)
            delay *= 2
        return None

    async def __write_holding_registers(self, address, values):
        """Write holding registers."""
        try:
            await self._client.write_registers(address, values)
            _LOGGER.debug("Written %s to register address %d", values, address)
        except ConnectionError as err:
            _LOGGER.warning("Write holding registers failed: %s", err)
            self._attr_available = False

    async def _read_holding_uint16(self, address):
        result = await self._read_holding_uint32(address)
        return result & 0xFFFF

    async def _read_holding_int32(self, address):
        result = await self.__read_holding_registers_with_retry(address, 2)
        return self._client.convert_from_registers(
            result, self._client.DATATYPE.INT32, "little"
        )

    async def _read_holding_uint32(self, address):
        try:
            result = await self.__read_holding_registers_with_retry(address, 2)
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
        self.coordinator.enqueue_backend(
            self.__write_holding_registers, address, payload
        )

    async def _read_holding_uint64(self, address):
        result = await self.__read_holding_registers_with_retry(address, 4)
        return self._client.convert_from_registers(
            result, self._client.DATATYPE.UINT64, "little"
        )

    async def _read_holding_float32(self, address, precision):
        result = await self.__read_holding_registers_with_retry(address, 2)
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
        self.coordinator.enqueue_backend(
            self.__write_holding_registers, address, payload, "little"
        )

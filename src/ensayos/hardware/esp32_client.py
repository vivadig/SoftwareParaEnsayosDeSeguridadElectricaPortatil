"""Cliente de comunicación serial con ESP32 para lectura de PZEM y control de relés."""

import logging
import time
from threading import Lock

import serial
from serial.tools import list_ports

from ensayos.config.config_hardware import hardware_config
from ensayos.models.measurement import PzemReading

logger = logging.getLogger(__name__)


class ESP32Client:
    """Cliente serial para comunicación con ESP32.

    Soporta auto-detección del puerto, reconexión y lectura thread-safe
    de módulos PZEM y control de relés vía comandos seriales.
    """

    def __init__(
        self,
        baud_rate: int | None = None,
        timeout: int | None = None,
        retry_interval: int | None = None,
        port_keywords: list[str] | None = None,
        stabilization_delay: float | None = None,
    ):
        cfg = hardware_config.esp32
        self.baud_rate = baud_rate or cfg.baud_rate
        self.timeout = timeout or cfg.timeout
        self.retry_interval = retry_interval or cfg.retry_interval
        self.port_keywords = port_keywords or cfg.port_keywords
        self.stabilization_delay = stabilization_delay or cfg.stabilization_delay

        self.port: str | None = None
        self.ser: serial.Serial | None = None
        self.is_connected: bool = False
        self._lock = Lock()

    def __enter__(self) -> "ESP32Client":
        self.port = self.find_port()
        if self.port:
            self.connect()
        else:
            logger.warning("No se encontró el ESP32 conectado.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()

    def find_port(self) -> str | None:
        """Busca el puerto serial del ESP32 usando las keywords configuradas."""
        ports = list(list_ports.comports())
        for port in ports:
            for keyword in self.port_keywords:
                if keyword in port.description:
                    logger.info("ESP32 encontrado en puerto %s", port.device)
                    return port.device
        return None

    def connect(self) -> bool:
        """Establece conexión serial con el ESP32.

        Returns:
            True si la conexión fue exitosa.

        Raises:
            ConnectionError: Si no se puede conectar al ESP32.
        """
        if not self.port:
            self.port = self.find_port()
        if not self.port:
            raise ConnectionError("No se encontró el ESP32 en ningún puerto serial.")

        try:
            self.ser = serial.Serial(self.port, self.baud_rate, timeout=self.timeout)
            time.sleep(self.stabilization_delay)
            self.is_connected = True
            logger.info("Conectado al ESP32 en puerto %s", self.port)
            return True
        except serial.SerialException as e:
            self.is_connected = False
            self.port = None
            raise ConnectionError(f"Error al conectar con el ESP32: {e}") from e

    def connect_with_retry(self) -> None:
        """Intenta conectar al ESP32, reintentando hasta lograrlo."""
        while not self.is_connected:
            self.port = self.find_port()
            if self.port:
                try:
                    self.connect()
                except ConnectionError:
                    pass
            if not self.is_connected:
                logger.info("Reintentando conexión en %d segundos...", self.retry_interval)
                time.sleep(self.retry_interval)

    def disconnect(self) -> None:
        """Cierra la conexión serial."""
        with self._lock:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.is_connected = False
                logger.info("Conexión con el ESP32 cerrada.")

    def send_command(self, command: str, timeout: float | None = None) -> str | None:
        """Envía un comando al ESP32 y espera la respuesta.

        Args:
            command: Comando a enviar.
            timeout: Timeout en segundos (usa el default si es None).

        Returns:
            Respuesta del ESP32 o None si hubo error/timeout.
        """
        if not self.is_connected or not self.ser:
            logger.warning("No hay conexión con el ESP32.")
            return None

        try:
            with self._lock:
                self.ser.reset_input_buffer()
                command_str = command.strip() + "\n"
                self.ser.write(command_str.encode("utf-8"))
                logger.debug("SEND: %s", command.strip())

                current_timeout = timeout if timeout is not None else self.timeout
                start_time = time.time()
                while True:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode("utf-8").strip()
                        if line:
                            logger.debug("RECV: %s", line)
                            return line
                    if time.time() - start_time > current_timeout:
                        logger.error("Timeout esperando respuesta del ESP32.")
                        return None
                    time.sleep(0.1)

        except serial.SerialException as e:
            logger.error("Comunicación serial fallida: %s", e)
            self.disconnect()
            return None

    def relay_on(self, relay_id: int) -> bool:
        """Enciende un relé vía ESP32.

        Args:
            relay_id: ID del relé (1 a N).

        Returns:
            True si la operación fue exitosa.
        """
        response = self.send_command(f"RELAYON{relay_id}")
        return response == f"RELE{relay_id}_ON"

    def relay_off(self, relay_id: int) -> bool:
        """Apaga un relé vía ESP32.

        Args:
            relay_id: ID del relé (1 a N).

        Returns:
            True si la operación fue exitosa.
        """
        response = self.send_command(f"RELAYOFF{relay_id}")
        return response == f"RELE{relay_id}_OFF"

    def read_pzem(self, pzem_id: int) -> PzemReading | None:
        """Lee datos de un módulo PZEM.

        Args:
            pzem_id: ID del PZEM (1 a N).

        Returns:
            PzemReading con los datos o None si hubo error.
        """
        response = self.send_command(f"PZEM{pzem_id}")
        if not response or not response.startswith(f"PZEM{pzem_id}:"):
            logger.error("Respuesta inválida del PZEM%d", pzem_id)
            return None

        try:
            data_parts = response.split(":")[1].split(",")
            data = {}
            for part in data_parts:
                key, value = part.split("=")
                data[key.strip()] = float(value.strip())
            return PzemReading.from_dict(data)
        except (IndexError, ValueError) as e:
            logger.error("Error al parsear respuesta del PZEM: %s", e)
            return None

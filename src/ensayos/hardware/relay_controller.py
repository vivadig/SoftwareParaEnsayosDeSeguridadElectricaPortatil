"""Controlador para placas de relés USB HID (dcttech USBRelay1/2/4/8, HW-554).

Soporta dos backends, elegidos con ``RELAY_BACKEND``:

- ``hidapi`` (por defecto): habla directamente el protocolo HID de la placa mediante
  la librería ``hidapi``. Funciona en Windows y en Linux.
- ``usbrelay``: usa ``usbrelay_py``, que solo está disponible en Linux (imagen Docker).
"""

import importlib
import logging
import time
from typing import Protocol

from ensayos.config.config_hardware import hardware_config

logger = logging.getLogger(__name__)

# Identificación USB de las placas dcttech
VENDOR_ID = 0x16C0
PRODUCT_ID = 0x05DF

# Comandos del protocolo dcttech (primer byte del feature report)
_CMD_ON = 0xFF
_CMD_OFF = 0xFD

# Datos de cada placa: (serie, cantidad de relés, máscara de estado; bit 0 = relé 1)
BoardInfo = tuple[str, int, int]


class RelayBoardNotFoundError(ConnectionError):
    """La placa de relés no está conectada o no responde (por ejemplo, tras un reinicio)."""


class RelayBackend(Protocol):
    """Interfaz común de los backends de relés."""

    def board_details(self) -> list[BoardInfo]:
        """Devuelve las placas conectadas."""
        ...

    def board_control(self, serial: str, relay_number: int, state: int) -> int:
        """Enciende (1) o apaga (0) un relé. Devuelve 0 si tuvo éxito."""
        ...


def _relay_count_from_product(product: str) -> int:
    """Deduce la cantidad de relés del nombre de producto (``USBRelay2`` -> 2).

    Args:
        product: Nombre de producto informado por la placa.

    Returns:
        Cantidad de relés; 8 si el nombre no tiene el formato esperado.
    """
    digits = (product or "").removeprefix("USBRelay")
    return int(digits) if digits.isdigit() else 8


class HidapiBackend:
    """Backend que usa ``hidapi`` para hablar el protocolo dcttech."""

    def __init__(self, hid_module: object | None = None):
        """Inicializa el backend.

        Args:
            hid_module: Módulo ``hid`` a usar; se inyecta en los tests.
        """
        self._hid = hid_module or importlib.import_module("hid")
        # Ruta HID de cada placa, indexada por número de serie
        self._paths: dict[str, bytes] = {}

    def _read_report(self, path: bytes) -> list[int]:
        """Lee el feature report de 8 bytes de una placa, sin el byte de report ID."""
        dev = self._hid.device()
        dev.open_path(path)
        try:
            data = dev.get_feature_report(0, 9)
        finally:
            dev.close()
        # hidapi antepone el report ID (0) cuando el dispositivo devuelve 9 bytes
        return list(data[1:] if len(data) == 9 else data)

    def board_details(self) -> list[BoardInfo]:
        """Enumera las placas y lee su serie y estado.

        Returns:
            Lista de tuplas (serie, cantidad de relés, máscara de estado).
        """
        boards: list[BoardInfo] = []
        self._paths.clear()
        for info in self._hid.enumerate(VENDOR_ID, PRODUCT_ID):
            try:
                report = self._read_report(info["path"])
            except OSError as e:
                # La placa aparece pero todavía no responde (se está reconectando)
                logger.warning("Placa de relés presente pero sin responder: %s", e)
                continue
            serial = bytes(report[:5]).decode("ascii", errors="replace")
            self._paths[serial] = info["path"]
            boards.append((serial, _relay_count_from_product(info["product_string"]), report[7]))
        return boards

    def board_control(self, serial: str, relay_number: int, state: int) -> int:
        """Enciende o apaga un relé de la placa indicada.

        Args:
            serial: Número de serie de la placa.
            relay_number: Número de relé (desde 1).
            state: 1 para encender, 0 para apagar.

        Returns:
            0 si el comando se envió, 1 si la placa no está conectada o falló el envío.
        """
        if serial not in self._paths:
            # La placa pudo haberse reconectado: se vuelve a enumerar
            self.board_details()
        path = self._paths.get(serial)
        if path is None:
            logger.error("Placa de relés %s no encontrada.", serial)
            return 1

        command = _CMD_ON if state else _CMD_OFF
        dev = self._hid.device()
        try:
            dev.open_path(path)
            written = dev.send_feature_report([0, command, relay_number, 0, 0, 0, 0, 0, 0])
        except OSError as e:
            logger.error("Error al comandar la placa de relés %s: %s", serial, e)
            self._paths.pop(serial, None)
            return 1
        finally:
            dev.close()
        return 0 if written > 0 else 1


class UsbrelayBackend:
    """Backend que usa ``usbrelay_py`` (solo Linux)."""

    def __init__(self, usbrelay_module: object | None = None):
        """Inicializa el backend y enumera las placas.

        Args:
            usbrelay_module: Módulo ``usbrelay_py`` a usar; se inyecta en los tests.
        """
        self._lib = usbrelay_module or importlib.import_module("usbrelay_py")
        # usbrelay_py exige llamar a board_count() antes que a cualquier otra función
        self._lib.board_count()

    def board_details(self) -> list[BoardInfo]:
        """Devuelve las placas informadas por ``usbrelay_py``."""
        return list(self._lib.board_details())

    def board_control(self, serial: str, relay_number: int, state: int) -> int:
        """Delega el comando en ``usbrelay_py.board_control``."""
        return self._lib.board_control(serial, relay_number, state)


def create_backend(name: str) -> RelayBackend:
    """Crea el backend de relés indicado.

    Args:
        name: ``"hidapi"`` o ``"usbrelay"``.

    Returns:
        Instancia del backend.

    Raises:
        ValueError: Si el nombre no corresponde a un backend conocido.
    """
    if name == "hidapi":
        return HidapiBackend()
    if name == "usbrelay":
        return UsbrelayBackend()
    raise ValueError(f"RELAY_BACKEND desconocido: {name!r} (usar 'hidapi' o 'usbrelay')")


class RelayController:
    """Controlador de placas de relés USB."""

    def __init__(self, backend: RelayBackend | None = None):
        """Inicializa el controlador y enumera las placas conectadas.

        Args:
            backend: Backend a usar; por defecto el configurado en ``RELAY_BACKEND``.
        """
        cfg = hardware_config.relay
        self._backend = backend or create_backend(cfg.backend)
        self._board_serial = cfg.board_serial
        self.board_count = len(self.get_boards())

    def get_boards(self) -> list[BoardInfo]:
        """Obtiene información de todas las placas conectadas.

        Returns:
            Lista de tuplas (serial, relay_count, state).
            state es un bitmask del estado de los relés.
        """
        return self._backend.board_details()

    def get_first_serial(self) -> str | None:
        """Obtiene el serial de la primera placa conectada.

        Returns:
            Serial de la primera placa, o None si no hay placas.
        """
        boards = self.get_boards()
        if not boards:
            return None
        return boards[0][0]

    def get_active_serial(self) -> str | None:
        """Obtiene el serial a usar según la configuración.

        Si RELAY_BOARD_SERIAL es 'auto', usa la primera placa disponible.
        """
        if self._board_serial == "auto":
            return self.get_first_serial()
        return self._board_serial

    def relay_count(self, serial: str) -> int:
        """Devuelve la cantidad de relés de una placa.

        Args:
            serial: Serial de la placa.

        Returns:
            Cantidad de relés, o 0 si la placa no está conectada.
        """
        for board_serial, count, _state in self.get_boards():
            if board_serial == serial:
                return count
        return 0

    def get_state(self, serial: str) -> int | None:
        """Devuelve la máscara de estado de una placa (bit 0 = relé 1).

        Args:
            serial: Serial de la placa.

        Returns:
            Máscara de estado, o None si la placa no está conectada.
        """
        for board_serial, _count, state in self.get_boards():
            if board_serial == serial:
                return state
        return None

    def control_relay(self, serial: str, relay_number: int, state: int) -> int:
        """Controla un relé específico.

        Args:
            serial: Serial de la placa (ejemplo: "6QMBS").
            relay_number: Número del relé (desde 1).
            state: 1 para encender, 0 para apagar.

        Returns:
            Resultado del comando (0 si tuvo éxito).

        Raises:
            RelayBoardNotFoundError: Si la placa no está conectada.
            ValueError: Si el relé no existe en la placa. Se interrumpe en lugar de
                seguir, para no ensayar con un circuito que no quedó conmutado.
        """
        count = self.relay_count(serial)
        if count == 0:
            raise RelayBoardNotFoundError(f"La placa de relés {serial} no está conectada.")
        if not 1 <= relay_number <= count:
            raise ValueError(
                f"El relé {relay_number} no existe en la placa {serial} ({count} relés). "
                "Revisar el mapeo RELAY_* en .env."
            )
        logger.debug("Relay %s_%d -> %s", serial, relay_number, "ON" if state else "OFF")
        return self._backend.board_control(serial, relay_number, state)

    def turn_on(self, serial: str, relay_number: int) -> int:
        """Enciende un relé.

        Args:
            serial: Serial de la placa.
            relay_number: Número del relé (desde 1).
        """
        return self.control_relay(serial, relay_number, 1)

    def turn_off(self, serial: str, relay_number: int) -> int:
        """Apaga un relé.

        Args:
            serial: Serial de la placa.
            relay_number: Número del relé (desde 1).
        """
        return self.control_relay(serial, relay_number, 0)

    def turn_off_all(
        self,
        serial: str,
        retries: int | None = None,
        retry_delay: float | None = None,
    ) -> bool:
        """Apaga todos los relés de una placa y verifica que quedaron apagados.

        Si la placa se desconectó (por ejemplo, la reinició una interferencia al
        conmutar el contactor), espera a que vuelva y reintenta.

        Args:
            serial: Serial de la placa.
            retries: Intentos máximos (por defecto RELAY_OFF_RETRIES).
            retry_delay: Segundos entre intentos (por defecto RELAY_OFF_RETRY_DELAY).

        Returns:
            True si la placa confirmó todos los relés apagados; False si no se pudo
            confirmar, en cuyo caso el contactor podría seguir cerrado.
        """
        cfg = hardware_config.relay
        retries = retries if retries is not None else cfg.off_retries
        retry_delay = retry_delay if retry_delay is not None else cfg.off_retry_delay
        for attempt in range(1, retries + 1):
            try:
                count = self.relay_count(serial)
                if count == 0:
                    raise RelayBoardNotFoundError(f"La placa de relés {serial} no está conectada.")
                for relay_number in range(1, count + 1):
                    self._backend.board_control(serial, relay_number, 0)
                if self.get_state(serial) == 0:
                    if attempt > 1:
                        logger.warning(
                            "Placa de relés %s recuperada: relés apagados en el intento %d.",
                            serial,
                            attempt,
                        )
                    return True
            except (RelayBoardNotFoundError, OSError) as e:
                logger.warning("Intento %d de apagar los relés falló: %s", attempt, e)
            time.sleep(retry_delay)
        logger.critical(
            "No se pudo confirmar el apagado de los relés de la placa %s. "
            "El contactor podría seguir cerrado: cortar la red.",
            serial,
        )
        return False

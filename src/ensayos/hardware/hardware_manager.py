"""Facade de hardware: acceso unificado a relés USB y ESP32/PZEM."""

import logging
import threading
import time

from ensayos.config.config_hardware import hardware_config
from ensayos.config.config_tests import CalibrationCorrections, tests_config
from ensayos.hardware.esp32_client import ESP32Client
from ensayos.hardware.relay_controller import RelayBoardNotFoundError, RelayController
from ensayos.models.measurement import (
    ConsumptionMeasurement,
    DielectricMeasurement,
    GroundingMeasurement,
    LeakageMeasurement,
    PzemReading,
)

logger = logging.getLogger(__name__)


class HardwareManager:
    """Facade que unifica el acceso a relés USB (dcttech/HW-554) y ESP32/PZEM.

    Provee métodos de alto nivel para:
    - Activar/desactivar relés por nombre semántico
    - Leer mediciones de los distintos módulos PZEM
    - Ejecutar el watchdog de reset
    """

    def __init__(
        self,
        relay_controller: RelayController | None = None,
        esp32_client: ESP32Client | None = None,
        corrections: CalibrationCorrections | None = None,
    ):
        self._relay = relay_controller
        self._esp32 = esp32_client
        self._cfg = hardware_config
        # Correcciones de calibración (CORRECTION_* en .env), sumadas a cada lectura
        self._corrections = corrections or tests_config.corrections
        self._relay_serial: str | None = None
        self._session_lock = threading.Lock()

    @property
    def relay(self) -> RelayController:
        if self._relay is None:
            raise RuntimeError("RelayController no inicializado.")
        return self._relay

    @property
    def esp32(self) -> ESP32Client:
        if self._esp32 is None:
            raise RuntimeError("ESP32Client no inicializado.")
        return self._esp32

    def initialize(self) -> None:
        """Inicializa los controladores de hardware."""
        if self._relay is None:
            self._relay = RelayController()

        self._relay_serial = self.relay.get_active_serial()
        if self._relay_serial:
            logger.info(f"[HARDWARE] Placa de relés USB detectada: {self._relay_serial}")
        else:
            logger.warning("[HARDWARE] No se encontró placa de relés USB conectada.")

        if self._esp32 is None:
            self._esp32 = ESP32Client()
            self._esp32.port = self._esp32.find_port()
            if self._esp32.port:
                logger.info(f"[HARDWARE] ESP32 encontrado en puerto {self._esp32.port}")
                self._esp32.connect()
                logger.info("[HARDWARE] ESP32 conectado correctamente")
            else:
                logger.warning("[HARDWARE] No se encontró ESP32 conectado.")

    # ---- Control de relés por nombre semántico ----

    def activate_relay(self, relay_number: int) -> None:
        """Activa un relé por su número."""
        if self._relay_serial:
            self.relay.turn_on(self._relay_serial, relay_number)

    def deactivate_relay(self, relay_number: int) -> None:
        """Desactiva un relé por su número.

        Si la placa se desconectó, espera a que vuelva y apaga todos los relés.
        """
        if self._relay_serial:
            try:
                self.relay.turn_off(self._relay_serial, relay_number)
            except RelayBoardNotFoundError:
                logger.warning("Placa de relés desconectada al apagar el relé %d.", relay_number)
                if not self.relay.turn_off_all(self._relay_serial):
                    raise

    def activate_relay_by_name(self, name: str) -> None:
        """Activa un relé por nombre semántico (ej: 'fuga_activa', 'pat_power')."""
        relay_number = getattr(self._cfg.relay.mapping, name)
        self.activate_relay(relay_number)

    def deactivate_relay_by_name(self, name: str) -> None:
        """Desactiva un relé por nombre semántico."""
        relay_number = getattr(self._cfg.relay.mapping, name)
        self.deactivate_relay(relay_number)

    def activate_relays(self, *relay_numbers: int) -> None:
        """Activa múltiples relés con delay configurable entre cada uno."""
        settle_delay = self._cfg.relay.settle_delay
        for i, relay_number in enumerate(relay_numbers):
            if i > 0:
                time.sleep(settle_delay)
            self.activate_relay(relay_number)

    def deactivate_relays(self, *relay_numbers: int) -> None:
        """Desactiva múltiples relés con delay entre cada uno."""
        settle_delay = self._cfg.relay.settle_delay
        for i, relay_number in enumerate(relay_numbers):
            if i > 0:
                time.sleep(settle_delay)
            self.deactivate_relay(relay_number)

    # ---- Watchdog ----

    def watchdog_reset(self) -> None:
        """Ejecuta un pulso de reset en el relé watchdog.

        Con ``RELAY_WATCHDOG=0`` no hay relé de watchdog cableado: no se hace nada
        más que registrar un aviso. La lectura fallida igual se trata como falla.
        """
        watchdog_relay = self._cfg.relay.mapping.watchdog
        if watchdog_relay == 0:
            logger.warning("Watchdog desactivado (RELAY_WATCHDOG=0): no se reinicia el ESP32.")
            return
        self.activate_relay(watchdog_relay)
        time.sleep(0.2)
        self.deactivate_relay(watchdog_relay)
        time.sleep(1)
        logger.info("Watchdog reset ejecutado.")

    # ---- Lecturas PZEM ----

    def read_pzem(self, pzem_id: int) -> PzemReading | None:
        """Lee un módulo PZEM por su ID."""
        return self.esp32.read_pzem(pzem_id)

    def read_consumption(self) -> ConsumptionMeasurement | None:
        """Lee medición de consumo desde PZEM1."""
        reading = self.read_pzem(self._cfg.pzem.consumption)
        if reading is None:
            logger.error("No se pudo leer PZEM de consumo.")
            self.watchdog_reset()
            return None
        return ConsumptionMeasurement.from_pzem(
            reading,
            correction_voltage=self._corrections.voltage,
            correction_current=self._corrections.current,
        )

    def read_consumption_and_leakage(
        self,
    ) -> tuple[ConsumptionMeasurement | None, LeakageMeasurement | None]:
        """Lee consumo (PZEM1) y fuga activa (PZEM2) simultáneamente."""
        reading_consumption = self.read_pzem(self._cfg.pzem.consumption)
        reading_leakage = self.read_pzem(self._cfg.pzem.leakage)

        if reading_consumption is None or reading_leakage is None:
            logger.error("No se pudo leer PZEM de consumo y/o fuga.")
            self.watchdog_reset()
            return None, None

        consumption = ConsumptionMeasurement.from_pzem(
            reading_consumption,
            correction_voltage=self._corrections.voltage,
            correction_current=self._corrections.current,
        )
        leakage = LeakageMeasurement.from_pzem(
            reading_leakage,
            multiplier=self._cfg.scale.leakage_current_multiplier,
            correction=self._corrections.active_leakage,
        )
        return consumption, leakage

    def read_leakage(
        self, passive: bool = False, watchdog: bool = True
    ) -> LeakageMeasurement | None:
        """Lee medición de fuga desde PZEM2.

        Args:
            passive: True para el ensayo de fuga pasiva (usa CORRECTION_PASSIVE_LEAKAGE);
                False para fuga activa (CORRECTION_ACTIVE_LEAKAGE).
            watchdog: Reiniciar el ESP32 si la lectura falla. Las lecturas opcionales
                (por ejemplo, la fuga durante un perfil de consumo) pasan False.
        """
        reading = self.read_pzem(self._cfg.pzem.leakage)
        if reading is None:
            if watchdog:
                logger.error("No se pudo leer PZEM de fuga.")
                self.watchdog_reset()
            return None
        correction = (
            self._corrections.passive_leakage if passive else self._corrections.active_leakage
        )
        return LeakageMeasurement.from_pzem(
            reading,
            multiplier=self._cfg.scale.leakage_current_multiplier,
            correction=correction,
        )

    def read_grounding(self) -> GroundingMeasurement | None:
        """Lee medición de puesta a tierra desde PZEM3."""
        reading = self.read_pzem(self._cfg.pzem.grounding)
        if reading is None:
            logger.error("No se pudo leer PZEM de puesta a tierra.")
            self.watchdog_reset()
            return None
        return GroundingMeasurement.from_pzem(
            reading,
            voltage_multiplier=self._cfg.scale.grounding_voltage_multiplier,
            resistance_multiplier=self._cfg.scale.grounding_resistance_multiplier,
            correction=self._corrections.grounding,
        )

    def read_dielectric(self) -> DielectricMeasurement | None:
        """Lee medición de rigidez dieléctrica desde PZEM2."""
        reading = self.read_pzem(self._cfg.pzem.leakage)
        if reading is None:
            logger.error("No se pudo leer PZEM de rigidez dieléctrica.")
            self.watchdog_reset()
            return None
        return DielectricMeasurement.from_pzem(
            reading,
            multiplier=self._cfg.scale.dielectric_voltage_multiplier,
            correction=self._corrections.dielectric,
            current_multiplier=self._cfg.scale.dielectric_current_multiplier,
        )

    def try_acquire_session(self) -> bool:
        """Reserva el hardware para un ensayo. False si ya hay otro en curso.

        El panel de ensayos y el perfil de consumo comparten relés y ESP32: no pueden
        correr a la vez.
        """
        return self._session_lock.acquire(blocking=False)

    def release_session(self) -> None:
        """Libera la reserva tomada con try_acquire_session."""
        if self._session_lock.locked():
            self._session_lock.release()

    def deactivate_all_relays(self) -> bool:
        """Apaga todos los relés y confirma el estado.

        Returns:
            True si se confirmó el apagado (o no hay placa de relés).
        """
        if not (self._relay_serial and self._relay):
            return True
        return self.relay.turn_off_all(self._relay_serial)

    # ---- Cleanup ----

    def shutdown(self) -> None:
        """Apaga todos los relés y cierra conexiones."""
        if self._relay_serial and self._relay:
            try:
                if self.relay.turn_off_all(self._relay_serial):
                    logger.info("Todos los relés apagados.")
            except Exception:
                logger.exception("No se pudieron apagar todos los relés.")

        if self._esp32:
            self._esp32.disconnect()
            logger.info("ESP32 desconectado.")

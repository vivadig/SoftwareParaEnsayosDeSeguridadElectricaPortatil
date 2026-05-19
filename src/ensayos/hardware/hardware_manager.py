"""Facade de hardware: acceso unificado a relés USB y ESP32/PZEM."""

import logging
import time

from ensayos.config.config_hardware import hardware_config
from ensayos.hardware.esp32_client import ESP32Client
from ensayos.hardware.relay_controller import RelayController
from ensayos.models.measurement import (
    ConsumptionMeasurement,
    DielectricMeasurement,
    GroundingMeasurement,
    LeakageMeasurement,
    PzemReading,
)

logger = logging.getLogger(__name__)


class HardwareManager:
    """Facade que unifica el acceso a relés USB (HW-554) y ESP32/PZEM.

    Provee métodos de alto nivel para:
    - Activar/desactivar relés por nombre semántico
    - Leer mediciones de los distintos módulos PZEM
    - Ejecutar el watchdog de reset
    """

    def __init__(
        self,
        relay_controller: RelayController | None = None,
        esp32_client: ESP32Client | None = None,
    ):
        self._relay = relay_controller
        self._esp32 = esp32_client
        self._cfg = hardware_config
        self._relay_serial: str | None = None

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
        """Desactiva un relé por su número."""
        if self._relay_serial:
            self.relay.turn_off(self._relay_serial, relay_number)

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
        """Ejecuta un pulso de reset en el relé watchdog."""
        watchdog_relay = self._cfg.relay.mapping.watchdog
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
        corrections = hardware_config.scale
        return ConsumptionMeasurement.from_pzem(
            reading,
            correction_voltage=0.0,
            correction_current=0.0,
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

        consumption = ConsumptionMeasurement.from_pzem(reading_consumption)
        leakage = LeakageMeasurement.from_pzem(
            reading_leakage,
            multiplier=self._cfg.scale.leakage_current_multiplier,
        )
        return consumption, leakage

    def read_leakage(self) -> LeakageMeasurement | None:
        """Lee medición de fuga desde PZEM2."""
        reading = self.read_pzem(self._cfg.pzem.leakage)
        if reading is None:
            logger.error("No se pudo leer PZEM de fuga.")
            self.watchdog_reset()
            return None
        return LeakageMeasurement.from_pzem(
            reading,
            multiplier=self._cfg.scale.leakage_current_multiplier,
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
        )

    # ---- Cleanup ----

    def shutdown(self) -> None:
        """Apaga todos los relés y cierra conexiones."""
        if self._relay_serial and self._relay:
            for i in range(1, RelayController.RELAY_COUNT + 1):
                try:
                    self.relay.turn_off(self._relay_serial, i)
                except Exception:
                    pass
            logger.info("Todos los relés apagados.")

        if self._esp32:
            self._esp32.disconnect()
            logger.info("ESP32 desconectado.")

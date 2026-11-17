"""Ensayo de perfil de consumo: muestrea el consumo del aparato durante un período largo.

A diferencia del ensayo de consumo de final de línea (unos segundos y un veredicto),
el perfil registra una muestra cada ``interval_s`` segundos durante ``duration_s``
segundos y guarda cada una en el historial de consumo, para ver cómo evoluciona el
consumo del aparato en el tiempo. No emite veredicto.
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from threading import Event

from ensayos.hardware.hardware_manager import HardwareManager
from ensayos.models.product import Product
from ensayos.models.test_result import ConsumptionSample

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProfileTick:
    """Estado del perfil, informado una vez por segundo."""

    seconds_to_next_sample: float
    seconds_to_end: float


class ConsumptionProfile:
    """Ejecuta un perfil de consumo con el contactor cerrado.

    Args:
        hardware: Fachada de hardware (relés y PZEM).
        product: Producto bajo ensayo.
        serial: Número de serie de la muestra.
        test_number: Número de ensayo (``n_ensayo``) con el que se guardan las muestras.
        duration_s: Duración total del perfil, sin contar la estabilización.
        interval_s: Tiempo entre muestras.
        settle_s: Espera inicial tras cerrar el contactor, antes de la primera muestra.
        cancel_token: Evento para detener el perfil.
        on_sample: Se llama con cada muestra tomada.
        on_tick: Se llama una vez por segundo con las cuentas regresivas.
        sleep: Función de espera (inyectable en los tests).
        clock: Reloj monotónico (inyectable en los tests).
    """

    def __init__(
        self,
        hardware: HardwareManager,
        product: Product,
        serial: str,
        test_number: int,
        duration_s: float,
        interval_s: float,
        settle_s: float = 2.0,
        cancel_token: Event | None = None,
        on_sample: Callable[[ConsumptionSample], None] | None = None,
        on_tick: Callable[[ProfileTick], None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        if interval_s <= 0:
            raise ValueError("El tiempo entre muestras debe ser mayor que cero.")
        if duration_s < interval_s:
            raise ValueError(
                "La duración del ensayo debe ser mayor o igual al tiempo entre muestras."
            )
        self.hardware = hardware
        self.product = product
        self.serial = serial
        self.test_number = test_number
        self.duration_s = duration_s
        self.interval_s = interval_s
        self.settle_s = settle_s
        self.cancel_token = cancel_token or Event()
        self.on_sample = on_sample
        self.on_tick = on_tick
        self._sleep = sleep
        self._clock = clock
        self.samples: list[ConsumptionSample] = []
        self.missed_samples = 0

    def stop(self) -> None:
        """Detiene el perfil (el contactor se abre al salir del bucle)."""
        self.cancel_token.set()

    def _wait(self, seconds: float) -> bool:
        """Espera de a 0,1 s respetando la cancelación. Devuelve False si se canceló."""
        end = self._clock() + seconds
        while self._clock() < end:
            if self.cancel_token.is_set():
                return False
            self._sleep(min(0.1, end - self._clock()))
        return not self.cancel_token.is_set()

    def _take_sample(self, number: int) -> None:
        reading = self.hardware.read_consumption()
        if reading is None:
            self.missed_samples += 1
            logger.warning("Perfil de consumo: muestra %d sin lectura del PZEM.", number)
            return
        # La fuga activa es opcional: sin PZEM2 se guarda 0 (y no se dispara el watchdog)
        leakage = self.hardware.read_leakage(watchdog=False)
        sample = ConsumptionSample(
            n_ensayo=self.test_number,
            n_muestra=number,
            marca=self.product.marca,
            modelo=self.product.modelo,
            serial=self.serial,
            fecha=time.strftime("%d/%m/%Y"),
            hora=time.strftime("%H:%M:%S"),
            tension=round(reading.voltage, 1),
            corriente=round(reading.current, 3),
            factor_potencia=round(reading.power_factor, 2),
            potencia=round(reading.power, 1),
            fuga_activa=round(leakage.leakage_ua, 1) if leakage else 0.0,
        )
        self.samples.append(sample)
        if self.on_sample:
            self.on_sample(sample)

    def run(self) -> list[ConsumptionSample]:
        """Cierra el contactor, toma las muestras y lo abre, aunque haya un error.

        Returns:
            Muestras tomadas.
        """
        relay = self.hardware._cfg.relay.mapping.fuga_activa
        logger.info(
            "Perfil de consumo: %s %s, %.0f s, una muestra cada %.0f s.",
            self.product.marca,
            self.product.modelo,
            self.duration_s,
            self.interval_s,
        )
        self.hardware.activate_relay(relay)
        try:
            if not self._wait(self.settle_s):
                return self.samples
            start = self._clock()
            number = 0
            next_sample = start
            while not self.cancel_token.is_set():
                now = self._clock()
                if now >= next_sample:
                    number += 1
                    self._take_sample(number)
                    next_sample += self.interval_s
                    if next_sample - start > self.duration_s + 1e-6:
                        break
                if self.on_tick:
                    self.on_tick(
                        ProfileTick(
                            seconds_to_next_sample=max(0.0, next_sample - self._clock()),
                            seconds_to_end=max(0.0, start + self.duration_s - self._clock()),
                        )
                    )
                if not self._wait(min(1.0, max(0.0, next_sample - self._clock()))):
                    break
        finally:
            self.hardware.deactivate_relay(relay)
        logger.info(
            "Perfil de consumo terminado: %d muestras, %d sin lectura%s.",
            len(self.samples),
            self.missed_samples,
            " (detenido)" if self.cancel_token.is_set() else "",
        )
        return self.samples

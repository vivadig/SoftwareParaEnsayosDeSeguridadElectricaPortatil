"""Clase base abstracta para ensayos de seguridad eléctrica."""

import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from threading import Event

from ensayos.config.config_tests import CalibrationCorrections, TestsConfig, tests_config
from ensayos.hardware.hardware_manager import HardwareManager
from ensayos.models.enums import TestType, Verdict
from ensayos.models.test_result import TestResult

logger = logging.getLogger(__name__)


class AbstractTest(ABC):
    """Clase base para todos los ensayos de seguridad eléctrica.

    Implementa el patrón Template Method:
        setup() → loop de measure() → teardown() → evaluate()

    Args:
        hardware: Instancia de HardwareManager.
        config: Configuración de ensayos.
        cancel_token: Event para cancelar el ensayo.
        on_progress: Callback opcional (elapsed_seconds, total_seconds).
        on_measurement: Callback opcional con la medición en cada iteración.
    """

    def __init__(
        self,
        hardware: HardwareManager,
        config: TestsConfig | None = None,
        cancel_token: Event | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        on_measurement: Callable | None = None,
    ):
        self.hardware = hardware
        self.config = config or tests_config
        self.cancel_token = cancel_token or Event()
        self.on_progress = on_progress
        self.on_measurement = on_measurement
        self.last_measurement = None

    @property
    @abstractmethod
    def test_type(self) -> TestType:
        """Tipo de ensayo."""

    @property
    @abstractmethod
    def duration_seconds(self) -> int:
        """Duración del ensayo en segundos."""

    @abstractmethod
    def setup(self) -> None:
        """Activa los relés necesarios para el ensayo."""

    @abstractmethod
    def measure(self) -> object | None:
        """Realiza una lectura de medición. Retorna el objeto de medición o None."""

    @abstractmethod
    def teardown(self) -> None:
        """Desactiva los relés usados en el ensayo."""

    @abstractmethod
    def evaluate(self, measurement: object) -> Verdict:
        """Evalúa la medición y retorna el veredicto."""

    def run(self) -> TestResult:
        """Ejecuta el ensayo completo: setup → measure loop → teardown → evaluate.

        Returns:
            TestResult con el veredicto y la última medición.
        """
        logger.info("Iniciando ensayo: %s", self.test_type.value)

        try:
            self.setup()

            elapsed = 0
            total = self.duration_seconds

            while elapsed < total and not self.cancel_token.is_set():
                elapsed += 1
                time.sleep(1)

                if self.cancel_token.is_set():
                    break

                measurement = self.measure()
                if measurement is not None:
                    self.last_measurement = measurement
                    if self.on_measurement:
                        self.on_measurement(measurement)

                if self.on_progress:
                    self.on_progress(elapsed, total)

        finally:
            self.teardown()

        if self.cancel_token.is_set():
            logger.info("Ensayo %s cancelado.", self.test_type.value)
            return TestResult(
                test_type=self.test_type,
                verdict=Verdict.NOT_RUN,
                measurement=self.last_measurement,
            )

        final = self.final_measurement()
        verdict = Verdict.NOT_RUN
        if final is not None:
            verdict = self.evaluate(final)

        logger.info("Ensayo %s finalizado: %s", self.test_type.value, verdict.value)
        return TestResult(
            test_type=self.test_type,
            verdict=verdict,
            measurement=final,
        )

    def final_measurement(self) -> object | None:
        """Medición sobre la que se evalúa y reporta el ensayo.

        Por defecto es la última lectura. Los ensayos que deben considerar
        todo el intervalo (p. ej. el peor caso) sobrescriben este método.
        """
        return self.last_measurement

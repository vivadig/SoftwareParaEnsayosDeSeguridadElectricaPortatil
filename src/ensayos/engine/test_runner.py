"""Orquestador de ensayos: gestiona la cola, ejecución cíclica y verificación."""

import logging
import time
from collections.abc import Callable
from threading import Event

from ensayos.config.config_tests import tests_config
from ensayos.engine.tests.active_leakage import ActiveLeakageTest
from ensayos.engine.tests.consumption import ConsumptionTest
from ensayos.engine.tests.dielectric import DielectricTest
from ensayos.engine.tests.grounding import GroundingTest
from ensayos.engine.tests.passive_leakage import PassiveLeakageTest
from ensayos.hardware.hardware_manager import HardwareManager
from ensayos.models.enums import DeviceClass, TestType
from ensayos.models.product import Product
from ensayos.models.test_result import TestResult

logger = logging.getLogger(__name__)

TEST_CLASS_MAP = {
    TestType.CONSUMPTION: ConsumptionTest,
    TestType.ACTIVE_LEAKAGE: ActiveLeakageTest,
    TestType.PASSIVE_LEAKAGE: PassiveLeakageTest,
    TestType.GROUNDING: GroundingTest,
    TestType.DIELECTRIC: DielectricTest,
}


class TestRunner:
    """Orquestador de ensayos de seguridad eléctrica.

    Soporta los modos:
    - End-of-Line: ejecuta una cola de ensayos seleccionados.
    - Cíclico: repite N veces con espera configurable.
    - Verificación: secuencia fija de pass/fail patterns.
    """

    def __init__(
        self,
        hardware: HardwareManager,
        cancel_token: Event | None = None,
        on_test_started: Callable[[TestType], None] | None = None,
        on_test_completed: Callable[[TestResult], None] | None = None,
        on_progress: Callable[[int, int], None] | None = None,
        on_measurement: Callable | None = None,
        on_all_completed: Callable[[list[TestResult]], None] | None = None,
        on_cycle_completed: Callable[[int, int], None] | None = None,
    ):
        self.hardware = hardware
        self.cancel_token = cancel_token or Event()
        self.on_test_started = on_test_started
        self.on_test_completed = on_test_completed
        self.on_progress = on_progress
        self.on_measurement = on_measurement
        self.on_all_completed = on_all_completed
        self.on_cycle_completed = on_cycle_completed

    def stop(self) -> None:
        """Señala la cancelación de la ejecución actual."""
        self.cancel_token.set()

    def _build_queue(
        self,
        selected_tests: list[TestType],
        product: Product,
    ) -> list[TestType]:
        """Construye la cola de ensayos optimizada.

        Optimización de FDL: si consumo y fuga_activa están seleccionados,
        el ensayo de consumo lee PZEM2 simultáneamente, así que se elimina
        fuga_activa de la cola.
        """
        queue = list(selected_tests)

        has_consumption = TestType.CONSUMPTION in queue
        has_active_leakage = TestType.ACTIVE_LEAKAGE in queue
        if has_consumption and has_active_leakage:
            queue.remove(TestType.ACTIVE_LEAKAGE)
            logger.info("Fuga activa eliminada de la cola (cubierta por consumo).")

        return queue

    def _create_test(
        self,
        test_type: TestType,
        product: Product,
        include_leakage: bool = False,
    ):
        """Crea una instancia del ensayo correspondiente."""
        common_kwargs = {
            "hardware": self.hardware,
            "cancel_token": self.cancel_token,
            "on_progress": self.on_progress,
            "on_measurement": self.on_measurement,
        }

        if test_type == TestType.CONSUMPTION:
            return ConsumptionTest(
                **common_kwargs,
                rated_current=product.corriente,
                rated_power=product.potencia,
                include_leakage=include_leakage,
            )
        elif test_type == TestType.DIELECTRIC:
            return DielectricTest(
                **common_kwargs,
                device_class=product.clase,
            )
        elif test_type == TestType.PASSIVE_LEAKAGE:
            return PassiveLeakageTest(
                **common_kwargs,
                doubled_limit=product.fuga_pasiva_duplicada,
            )
        else:
            test_class = TEST_CLASS_MAP[test_type]
            return test_class(**common_kwargs)

    def run_end_of_line(
        self,
        selected_tests: list[TestType],
        product: Product,
    ) -> list[TestResult]:
        """Ejecuta un ciclo End-of-Line con los ensayos seleccionados.

        Args:
            selected_tests: Lista de tipos de ensayo a ejecutar.
            product: Producto bajo ensayo.

        Returns:
            Lista de TestResult con los resultados.
        """
        self.cancel_token.clear()
        results: list[TestResult] = []

        include_leakage = (
            TestType.CONSUMPTION in selected_tests and TestType.ACTIVE_LEAKAGE in selected_tests
        )
        queue = self._build_queue(selected_tests, product)

        for test_type in queue:
            if self.cancel_token.is_set():
                break

            if self.on_test_started:
                self.on_test_started(test_type)

            is_consumption_with_leakage = test_type == TestType.CONSUMPTION and include_leakage
            test = self._create_test(test_type, product, include_leakage=is_consumption_with_leakage)
            result = test.run()
            results.append(result)

            # Si consumo midió fuga activa, agregar su resultado
            if is_consumption_with_leakage and isinstance(test, ConsumptionTest):
                if test.last_leakage is not None:
                    from ensayos.engine.verdict import evaluate_active_leakage

                    leakage_verdict = evaluate_active_leakage(test.last_leakage.leakage_ua)
                    leakage_result = TestResult(
                        test_type=TestType.ACTIVE_LEAKAGE,
                        verdict=leakage_verdict,
                        measurement=test.last_leakage,
                    )
                    results.append(leakage_result)
                    if self.on_test_completed:
                        self.on_test_completed(leakage_result)

            if self.on_test_completed:
                self.on_test_completed(result)

            # Pausa entre ensayos
            inter_delay = self.hardware._cfg.relay.settle_delay
            time.sleep(tests_config.durations.inter_test_delay)

        if self.on_all_completed:
            self.on_all_completed(results)

        return results

    def run_cyclic(
        self,
        selected_tests: list[TestType],
        product: Product,
        repeat_count: int,
        wait_between_seconds: float = 0.0,
    ) -> list[list[TestResult]]:
        """Ejecuta ensayos en modo cíclico.

        Args:
            selected_tests: Ensayos a ejecutar en cada ciclo.
            product: Producto bajo ensayo.
            repeat_count: Cantidad de ciclos.
            wait_between_seconds: Espera entre ciclos (segundos).

        Returns:
            Lista de listas de TestResult (una lista por ciclo).
        """
        self.cancel_token.clear()
        all_cycles: list[list[TestResult]] = []

        for cycle in range(repeat_count):
            if self.cancel_token.is_set():
                break

            logger.info("Ciclo %d/%d", cycle + 1, repeat_count)
            results = self.run_end_of_line(selected_tests, product)
            all_cycles.append(results)

            if self.on_cycle_completed:
                self.on_cycle_completed(cycle + 1, repeat_count)

            # Espera entre ciclos (excepto después del último)
            if cycle < repeat_count - 1 and wait_between_seconds > 0:
                logger.info("Esperando %.1f segundos entre ciclos...", wait_between_seconds)
                elapsed = 0.0
                while elapsed < wait_between_seconds and not self.cancel_token.is_set():
                    time.sleep(1)
                    elapsed += 1.0

        return all_cycles

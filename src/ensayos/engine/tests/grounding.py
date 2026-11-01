"""Ensayo de puesta a tierra (PAT)."""

import logging
import time

from ensayos.engine.tests.base import AbstractTest
from ensayos.engine.verdict import evaluate_grounding
from ensayos.models.enums import TestType, Verdict
from ensayos.models.measurement import GroundingMeasurement

logger = logging.getLogger(__name__)


class GroundingTest(AbstractTest):
    """Ensayo de puesta a tierra (PAT): mide resistencia de continuidad.

    Secuencia de relés (FDL):
        1. Activa rele1_3 (pat_power)
        2. Espera settle_delay
        3. Activa rele1_7 (pat_enable)
    Teardown: desactiva en orden inverso.
    Lectura: PZEM3 (grounding) → R = (V × factor_V) / I × factor_R + corrección

    Se evalúa el peor caso del intervalo (resistencia máxima y corriente mínima).
    Una lectura fallida se declara FAIL porque no se puede verificar la continuidad.
    """

    def __init__(self, *args, with_cord: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.with_cord = with_cord
        self._max_resistance_mohm: float | None = None
        self._min_current_a: float | None = None
        self._missed_readings = 0

    @property
    def test_type(self) -> TestType:
        return TestType.GROUNDING

    @property
    def duration_seconds(self) -> int:
        return self.config.durations.grounding

    def setup(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        settle = self.hardware._cfg.relay.settle_delay
        self.hardware.activate_relay(relay_map.pat_power)
        time.sleep(settle)
        self.hardware.activate_relay(relay_map.pat_enable)

    def measure(self) -> GroundingMeasurement | None:
        measurement = self.hardware.read_grounding()
        if measurement is None:
            self._missed_readings += 1
            return None
        if measurement.resistance_mohm < 0:
            measurement = GroundingMeasurement(resistance_mohm=0.0, current_a=measurement.current_a)

        # Acumular el peor caso del intervalo
        if (
            self._max_resistance_mohm is None
            or measurement.resistance_mohm > self._max_resistance_mohm
        ):
            self._max_resistance_mohm = measurement.resistance_mohm
        if self._min_current_a is None or measurement.current_a < self._min_current_a:
            self._min_current_a = measurement.current_a
        return measurement

    def teardown(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        settle = self.hardware._cfg.relay.settle_delay
        self.hardware.deactivate_relay(relay_map.pat_enable)
        time.sleep(settle)
        self.hardware.deactivate_relay(relay_map.pat_power)

    def final_measurement(self) -> GroundingMeasurement | None:
        """Peor caso del intervalo: resistencia máxima y corriente mínima."""
        if self._max_resistance_mohm is None or self._min_current_a is None:
            return None
        return GroundingMeasurement(
            resistance_mohm=self._max_resistance_mohm, current_a=self._min_current_a
        )

    def evaluate(self, measurement: GroundingMeasurement) -> Verdict:
        if self._missed_readings > 0:
            logger.warning(
                "Puesta a tierra: %d lecturas fallidas; continuidad no verificada.",
                self._missed_readings,
            )
            return Verdict.FAIL
        return evaluate_grounding(
            measurement.resistance_mohm, measurement.current_a, self.with_cord
        )

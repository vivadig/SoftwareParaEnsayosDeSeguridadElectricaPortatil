"""Ensayo de puesta a tierra (PAT)."""

import time

from ensayos.engine.tests.base import AbstractTest
from ensayos.engine.verdict import evaluate_grounding
from ensayos.models.enums import TestType, Verdict
from ensayos.models.measurement import GroundingMeasurement


class GroundingTest(AbstractTest):
    """Ensayo de puesta a tierra (PAT): mide resistencia de continuidad.

    Secuencia de relés (FDL):
        1. Activa rele1_3 (pat_power)
        2. Espera settle_delay
        3. Activa rele1_7 (pat_enable)
    Teardown: desactiva en orden inverso.
    Lectura: PZEM3 (grounding) → R = (V × factor_V) / I × factor_R + corrección
    """

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
        if measurement is not None and measurement.resistance_mohm < 0:
            return GroundingMeasurement(resistance_mohm=0.0)
        return measurement

    def teardown(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        settle = self.hardware._cfg.relay.settle_delay
        self.hardware.deactivate_relay(relay_map.pat_enable)
        time.sleep(settle)
        self.hardware.deactivate_relay(relay_map.pat_power)

    def evaluate(self, measurement: GroundingMeasurement) -> Verdict:
        return evaluate_grounding(measurement.resistance_mohm)

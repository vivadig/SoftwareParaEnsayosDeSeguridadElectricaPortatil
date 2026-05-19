"""Ensayo de fuga activa."""

from ensayos.engine.tests.base import AbstractTest
from ensayos.engine.verdict import evaluate_active_leakage
from ensayos.models.enums import TestType, Verdict
from ensayos.models.measurement import LeakageMeasurement


class ActiveLeakageTest(AbstractTest):
    """Ensayo de fuga activa: mide corriente de fuga con el equipo energizado.

    Secuencia de relés (FDL): activa rele1_1 (fuga_activa)
    Lectura: PZEM2 (fuga) × multiplicador (default 10) → μA
    """

    @property
    def test_type(self) -> TestType:
        return TestType.ACTIVE_LEAKAGE

    @property
    def duration_seconds(self) -> int:
        return self.config.durations.active_leakage

    def setup(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        self.hardware.activate_relay(relay_map.fuga_activa)

    def measure(self) -> LeakageMeasurement | None:
        return self.hardware.read_leakage()

    def teardown(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        self.hardware.deactivate_relay(relay_map.fuga_activa)

    def evaluate(self, measurement: LeakageMeasurement) -> Verdict:
        return evaluate_active_leakage(measurement.leakage_ua)

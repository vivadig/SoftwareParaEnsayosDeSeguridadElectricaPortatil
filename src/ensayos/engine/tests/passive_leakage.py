"""Ensayo de fuga pasiva."""

import time

from ensayos.engine.tests.base import AbstractTest
from ensayos.engine.verdict import evaluate_passive_leakage
from ensayos.models.enums import TestType, Verdict
from ensayos.models.measurement import LeakageMeasurement


class PassiveLeakageTest(AbstractTest):
    """Ensayo de fuga pasiva: mide corriente de fuga con el equipo desenergizado.

    Secuencia de relés (FDL):
        1. Activa rele1_2 (fuga_pasiva)
        2. Espera settle_delay
        3. Activa rele1_1 (fuga_activa)
    Teardown: desactiva en orden inverso.
    Lectura: PZEM2 (fuga) × multiplicador → μA
    """

    def __init__(self, *args, doubled_limit: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.doubled_limit = doubled_limit

    @property
    def test_type(self) -> TestType:
        return TestType.PASSIVE_LEAKAGE

    @property
    def duration_seconds(self) -> int:
        return self.config.durations.passive_leakage

    def setup(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        settle = self.hardware._cfg.relay.settle_delay
        self.hardware.activate_relay(relay_map.fuga_pasiva)
        time.sleep(settle)
        self.hardware.activate_relay(relay_map.fuga_activa)

    def measure(self) -> LeakageMeasurement | None:
        return self.hardware.read_leakage()

    def teardown(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        settle = self.hardware._cfg.relay.settle_delay
        self.hardware.deactivate_relay(relay_map.fuga_activa)
        time.sleep(settle)
        self.hardware.deactivate_relay(relay_map.fuga_pasiva)

    def evaluate(self, measurement: LeakageMeasurement) -> Verdict:
        return evaluate_passive_leakage(measurement.leakage_ua, self.doubled_limit)

"""Ensayo de rigidez dieléctrica."""

import time

from ensayos.engine.tests.base import AbstractTest
from ensayos.engine.verdict import evaluate_dielectric
from ensayos.models.enums import DeviceClass, TestType, Verdict
from ensayos.models.measurement import DielectricMeasurement


class DielectricTest(AbstractTest):
    """Ensayo de rigidez dieléctrica: mide la tensión que soporta el aislamiento.

    Secuencia de relés (FDL):
        Clase 1: rele1_4 (dielectric_class1) + rele1_6 (dielectric_enable)
        Clase 2: rele1_5 (dielectric_class2) + rele1_6 (dielectric_enable)
    Teardown: desactiva rele1_6, luego rele1_4 y rele1_5.
    Lectura: PZEM2 (leakage) voltage × multiplicador → V
    """

    def __init__(self, *args, device_class: DeviceClass = DeviceClass.CLASS_1, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_class = device_class

    @property
    def test_type(self) -> TestType:
        return TestType.DIELECTRIC

    @property
    def duration_seconds(self) -> int:
        return self.config.durations.dielectric

    def setup(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        settle = self.hardware._cfg.relay.settle_delay

        if self.device_class == DeviceClass.CLASS_1:
            self.hardware.activate_relay(relay_map.dielectric_class1)
        else:
            self.hardware.activate_relay(relay_map.dielectric_class2)

        time.sleep(settle)
        self.hardware.activate_relay(relay_map.dielectric_enable)

    def measure(self) -> DielectricMeasurement | None:
        return self.hardware.read_dielectric()

    def teardown(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        settle = self.hardware._cfg.relay.settle_delay

        self.hardware.deactivate_relay(relay_map.dielectric_enable)
        time.sleep(settle)
        self.hardware.deactivate_relay(relay_map.dielectric_class1)
        time.sleep(settle)
        self.hardware.deactivate_relay(relay_map.dielectric_class2)

    def evaluate(self, measurement: DielectricMeasurement) -> Verdict:
        return evaluate_dielectric(measurement.voltage, self.device_class)

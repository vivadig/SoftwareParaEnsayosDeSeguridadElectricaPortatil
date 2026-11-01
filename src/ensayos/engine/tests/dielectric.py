"""Ensayo de rigidez dieléctrica."""

import logging
import time

from ensayos.engine.tests.base import AbstractTest
from ensayos.engine.verdict import evaluate_dielectric
from ensayos.models.enums import DeviceClass, TestType, Verdict
from ensayos.models.measurement import DielectricMeasurement

logger = logging.getLogger(__name__)


class DielectricTest(AbstractTest):
    """Ensayo de rigidez dieléctrica: verifica que el aislamiento soporte la tensión de ensayo.

    Criterio (IEC 60335-1, Anexo A.2): la tensión de ensayo debe mantenerse aplicada
    y la corriente no debe superar el límite de ruptura en ninguna lectura. Por eso
    se evalúa el peor caso del intervalo (tensión mínima y corriente máxima), no la
    última lectura. Si alguna lectura falla, no se puede descartar una ruptura y el
    ensayo se declara FAIL.

    Secuencia de relés (FDL):
        Clase 1: rele1_4 (dielectric_class1) + rele1_6 (dielectric_enable)
        Clase 2: rele1_5 (dielectric_class2) + rele1_6 (dielectric_enable)
    Teardown: desactiva rele1_6, luego rele1_4 y rele1_5.
    Lectura: PZEM2 (leakage) voltage × multiplicador → V, current × multiplicador → mA
    """

    def __init__(self, *args, device_class: DeviceClass = DeviceClass.CLASS_1, **kwargs):
        super().__init__(*args, **kwargs)
        self.device_class = device_class
        self._min_voltage: float | None = None
        self._peak_current_ma: float | None = None
        self._missed_readings = 0

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
        measurement = self.hardware.read_dielectric()
        if measurement is None:
            self._missed_readings += 1
            return None

        # Acumular el peor caso del intervalo
        if self._min_voltage is None or measurement.voltage < self._min_voltage:
            self._min_voltage = measurement.voltage
        if self._peak_current_ma is None or measurement.current_ma > self._peak_current_ma:
            self._peak_current_ma = measurement.current_ma
        return measurement

    def teardown(self) -> None:
        relay_map = self.hardware._cfg.relay.mapping
        settle = self.hardware._cfg.relay.settle_delay

        self.hardware.deactivate_relay(relay_map.dielectric_enable)
        time.sleep(settle)
        self.hardware.deactivate_relay(relay_map.dielectric_class1)
        time.sleep(settle)
        self.hardware.deactivate_relay(relay_map.dielectric_class2)

    def final_measurement(self) -> DielectricMeasurement | None:
        """Peor caso del intervalo: tensión mínima y corriente máxima."""
        if self._min_voltage is None or self._peak_current_ma is None:
            return None
        return DielectricMeasurement(voltage=self._min_voltage, current_ma=self._peak_current_ma)

    def evaluate(self, measurement: DielectricMeasurement) -> Verdict:
        if self._missed_readings > 0:
            logger.warning(
                "Rigidez dieléctrica: %d lecturas fallidas; no se puede descartar ruptura.",
                self._missed_readings,
            )
            return Verdict.FAIL
        return evaluate_dielectric(measurement.voltage, measurement.current_ma, self.device_class)

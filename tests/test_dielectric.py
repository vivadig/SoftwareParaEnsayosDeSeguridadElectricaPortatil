"""Tests del criterio de rigidez dieléctrica (IEC 60335-1, Anexo A.2)."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ensayos.engine.tests.dielectric import DielectricTest
from ensayos.engine.verdict import evaluate_dielectric
from ensayos.models.enums import DeviceClass, Verdict
from ensayos.models.measurement import DielectricMeasurement, PzemReading


class TestEvaluateDielectric:
    """Pruebas de la función pura de veredicto."""

    @pytest.mark.parametrize(
        ("device_class", "voltage"),
        [(DeviceClass.CLASS_1, 1000.0), (DeviceClass.CLASS_2, 2500.0)],
    )
    def test_ok_con_tension_y_sin_ruptura(self, device_class: DeviceClass, voltage: float) -> None:
        assert evaluate_dielectric(voltage, 1.0, device_class) == Verdict.OK

    def test_falla_por_ruptura(self) -> None:
        assert evaluate_dielectric(1000.0, 5.1, DeviceClass.CLASS_1) == Verdict.FAIL

    def test_limite_de_corriente_inclusive(self) -> None:
        assert evaluate_dielectric(1000.0, 5.0, DeviceClass.CLASS_1) == Verdict.OK

    def test_falla_si_no_se_alcanza_la_tension(self) -> None:
        # Con aislamiento perfecto pero tensión insuficiente, el ensayo no es válido
        assert evaluate_dielectric(800.0, 0.0, DeviceClass.CLASS_1) == Verdict.FAIL

    def test_clase_2_requiere_2500_v(self) -> None:
        assert evaluate_dielectric(2000.0, 0.0, DeviceClass.CLASS_2) == Verdict.FAIL

    def test_tolerancia_de_tension(self) -> None:
        assert evaluate_dielectric(970.0, 0.0, DeviceClass.CLASS_1) == Verdict.OK
        assert evaluate_dielectric(969.0, 0.0, DeviceClass.CLASS_1) == Verdict.FAIL

    def test_limite_de_corriente_configurable(self) -> None:
        assert (
            evaluate_dielectric(1000.0, 20.0, DeviceClass.CLASS_1, max_current_ma=30.0)
            == Verdict.OK
        )


def test_from_pzem_convierte_corriente_a_ma() -> None:
    reading = PzemReading(voltage=100.0, current=0.002, power=0.0, energy=0.0)
    measurement = DielectricMeasurement.from_pzem(reading, multiplier=10.0)
    assert measurement.voltage == pytest.approx(1000.0)
    assert measurement.current_ma == pytest.approx(2.0)


class FakeHardware:
    """Hardware simulado que devuelve una secuencia fija de lecturas."""

    def __init__(self, readings: list[DielectricMeasurement | None]):
        self._readings = iter(readings)
        mapping = SimpleNamespace(dielectric_class1=4, dielectric_class2=5, dielectric_enable=6)
        self._cfg = SimpleNamespace(relay=SimpleNamespace(mapping=mapping, settle_delay=0.0))

    def activate_relay(self, relay: int) -> None:
        pass

    def deactivate_relay(self, relay: int) -> None:
        pass

    def read_dielectric(self) -> DielectricMeasurement | None:
        return next(self._readings)


def _run(readings: list[DielectricMeasurement | None]):
    test = DielectricTest(FakeHardware(readings), device_class=DeviceClass.CLASS_1)
    with (
        patch("ensayos.engine.tests.base.time.sleep"),
        patch.object(DielectricTest, "duration_seconds", len(readings)),
    ):
        return test.run()


class TestDielectricTestRun:
    """Pruebas del ensayo completo con hardware simulado."""

    def test_ruptura_intermedia_se_detecta(self) -> None:
        # La última lectura es buena, pero hubo una ruptura en el medio
        result = _run(
            [
                DielectricMeasurement(1000.0, 1.0),
                DielectricMeasurement(1000.0, 12.0),
                DielectricMeasurement(1000.0, 1.0),
            ]
        )
        assert result.verdict == Verdict.FAIL
        assert result.measurement.current_ma == pytest.approx(12.0)

    def test_caida_de_tension_intermedia_se_detecta(self) -> None:
        result = _run(
            [
                DielectricMeasurement(1000.0, 1.0),
                DielectricMeasurement(600.0, 1.0),
                DielectricMeasurement(1000.0, 1.0),
            ]
        )
        assert result.verdict == Verdict.FAIL
        assert result.measurement.voltage == pytest.approx(600.0)

    def test_lectura_fallida_es_falla(self) -> None:
        result = _run(
            [DielectricMeasurement(1000.0, 1.0), None, DielectricMeasurement(1000.0, 1.0)]
        )
        assert result.verdict == Verdict.FAIL

    def test_ensayo_correcto(self) -> None:
        result = _run([DielectricMeasurement(1000.0, 0.5)] * 3)
        assert result.verdict == Verdict.OK

    def test_sin_lecturas_no_se_ejecuta(self) -> None:
        result = _run([None, None])
        assert result.verdict == Verdict.NOT_RUN

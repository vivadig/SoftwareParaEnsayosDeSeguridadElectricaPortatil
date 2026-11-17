"""Tests: en los ensayos de seguridad, un medidor que no responde da FALLA."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ensayos.engine.tests.active_leakage import ActiveLeakageTest
from ensayos.engine.tests.consumption import ConsumptionTest
from ensayos.engine.tests.passive_leakage import PassiveLeakageTest
from ensayos.models.enums import Verdict
from ensayos.models.measurement import LeakageMeasurement


class FakeHardware:
    """Hardware simulado: devuelve una secuencia fija de lecturas de fuga."""

    def __init__(self, readings):
        self._readings = iter(readings)
        mapping = SimpleNamespace(fuga_activa=1, fuga_pasiva=2)
        self._cfg = SimpleNamespace(relay=SimpleNamespace(mapping=mapping, settle_delay=0.0))

    def activate_relay(self, relay):
        pass

    def deactivate_relay(self, relay):
        pass

    def read_leakage(self, passive=False):
        return next(self._readings)

    def read_consumption(self):
        return next(self._readings)


def _run(cls, readings, **kwargs):
    test = cls(FakeHardware(readings), **kwargs)
    with (
        patch("ensayos.engine.tests.base.time.sleep"),
        patch("ensayos.engine.tests.passive_leakage.time.sleep"),
        patch.object(cls, "duration_seconds", len(readings)),
    ):
        return test.run()


@pytest.mark.parametrize("cls", [ActiveLeakageTest, PassiveLeakageTest])
class TestFugaSinMedidor:
    def test_sin_ninguna_lectura_da_falla(self, cls):
        result = _run(cls, [None, None, None])
        assert result.verdict == Verdict.FAIL
        assert result.measurement is None

    def test_una_lectura_perdida_da_falla(self, cls):
        result = _run(cls, [LeakageMeasurement(100.0), None, LeakageMeasurement(100.0)])
        assert result.verdict == Verdict.FAIL

    def test_todas_las_lecturas_ok(self, cls):
        result = _run(cls, [LeakageMeasurement(100.0)] * 3)
        assert result.verdict == Verdict.OK


def test_consumo_sin_medidor_sigue_sin_ejecutar():
    # El consumo es una verificación funcional, no de seguridad
    with patch.object(ConsumptionTest, "settle_seconds", 0):
        result = _run(ConsumptionTest, [None, None], rated_power=40.0)
    assert result.verdict == Verdict.NOT_RUN

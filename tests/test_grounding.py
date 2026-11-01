"""Tests del ensayo de puesta a tierra (IEC 60335-1, Anexo A.1)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ensayos.database.schemas import initialize_database
from ensayos.database.sqlite_repository import SQLiteProductRepository
from ensayos.engine.test_runner import TestRunner
from ensayos.engine.tests.grounding import GroundingTest
from ensayos.engine.verdict import evaluate_grounding
from ensayos.models.enums import DeviceClass, TestType, Verdict
from ensayos.models.measurement import GroundingMeasurement, PzemReading
from ensayos.models.product import Product


class TestEvaluateGrounding:
    """Pruebas de la función pura de veredicto."""

    def test_con_cable_limite_200_mohm(self) -> None:
        assert evaluate_grounding(200.0, 15.0, with_cord=True) == Verdict.OK
        assert evaluate_grounding(201.0, 15.0, with_cord=True) == Verdict.FAIL

    def test_sin_cable_limite_100_mohm(self) -> None:
        assert evaluate_grounding(100.0, 15.0, with_cord=False) == Verdict.OK
        assert evaluate_grounding(150.0, 15.0, with_cord=False) == Verdict.FAIL

    def test_falla_si_la_corriente_no_alcanza_10_a(self) -> None:
        assert evaluate_grounding(50.0, 9.9) == Verdict.FAIL
        assert evaluate_grounding(50.0, 10.0) == Verdict.OK

    def test_sobre_rango_falla(self) -> None:
        assert evaluate_grounding(float("inf"), 0.0) == Verdict.FAIL


def test_from_pzem_guarda_la_corriente() -> None:
    reading = PzemReading(voltage=0.15, current=15.0, power=0.0, energy=0.0)
    measurement = GroundingMeasurement.from_pzem(reading)
    assert measurement.current_a == pytest.approx(15.0)
    assert measurement.resistance_mohm == pytest.approx(100.0)


class FakeHardware:
    """Hardware simulado que devuelve una secuencia fija de lecturas."""

    def __init__(self, readings: list[GroundingMeasurement | None]):
        self._readings = iter(readings)
        mapping = SimpleNamespace(pat_power=3, pat_enable=7)
        self._cfg = SimpleNamespace(relay=SimpleNamespace(mapping=mapping, settle_delay=0.0))

    def activate_relay(self, relay: int) -> None:
        pass

    def deactivate_relay(self, relay: int) -> None:
        pass

    def read_grounding(self) -> GroundingMeasurement | None:
        return next(self._readings)


def _run(readings: list[GroundingMeasurement | None], with_cord: bool = True):
    test = GroundingTest(FakeHardware(readings), with_cord=with_cord)
    with (
        patch("ensayos.engine.tests.base.time.sleep"),
        patch("ensayos.engine.tests.grounding.time.sleep"),
        patch.object(GroundingTest, "duration_seconds", len(readings)),
    ):
        return test.run()


class TestGroundingTestRun:
    """Pruebas del ensayo completo con hardware simulado."""

    def test_pico_intermedio_de_resistencia_se_detecta(self) -> None:
        result = _run(
            [
                GroundingMeasurement(80.0, 15.0),
                GroundingMeasurement(250.0, 15.0),
                GroundingMeasurement(80.0, 15.0),
            ]
        )
        assert result.verdict == Verdict.FAIL
        assert result.measurement.resistance_mohm == pytest.approx(250.0)

    def test_caida_de_corriente_intermedia_se_detecta(self) -> None:
        result = _run(
            [
                GroundingMeasurement(80.0, 15.0),
                GroundingMeasurement(80.0, 5.0),
                GroundingMeasurement(80.0, 15.0),
            ]
        )
        assert result.verdict == Verdict.FAIL

    def test_lectura_fallida_es_falla(self) -> None:
        result = _run([GroundingMeasurement(80.0, 15.0), None])
        assert result.verdict == Verdict.FAIL

    def test_resistencia_negativa_se_lleva_a_cero(self) -> None:
        result = _run([GroundingMeasurement(-5.0, 15.0)] * 2)
        assert result.verdict == Verdict.OK
        assert result.measurement.resistance_mohm == 0.0

    def test_limite_segun_cable(self) -> None:
        readings = [GroundingMeasurement(150.0, 15.0)] * 2
        assert _run(readings, with_cord=True).verdict == Verdict.OK
        assert _run(readings, with_cord=False).verdict == Verdict.FAIL


def _product(**kwargs) -> Product:
    defaults = {
        "marca": "Marca",
        "modelo": "Modelo",
        "descripcion": "",
        "potencia": 1000.0,
        "tension": 220.0,
        "corriente": 4.5,
        "frecuencia": 50.0,
        "clase": DeviceClass.CLASS_1,
    }
    defaults.update(kwargs)
    return Product(**defaults)


def test_runner_pasa_la_condicion_del_producto() -> None:
    runner = TestRunner(hardware=MagicMock())
    test = runner._create_test(TestType.GROUNDING, _product(con_cable_alimentacion=False))
    assert isinstance(test, GroundingTest)
    assert test.with_cord is False


def test_producto_conserva_si_tiene_cable(tmp_path) -> None:
    db = str(tmp_path / "ensayos.db")
    initialize_database(db)
    repo = SQLiteProductRepository(db)
    assert repo.create(_product())
    stored = repo.get_by_brand_model("Marca", "Modelo")
    assert stored.con_cable_alimentacion is True

    stored.con_cable_alimentacion = False
    assert repo.update(stored)
    assert repo.get_by_id(stored.id).con_cable_alimentacion is False

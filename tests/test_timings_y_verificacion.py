"""Tests de los tiempos de la base y del criterio de verificación con patrones."""

import math

import pytest

from ensayos.config.config_tests import tests_config
from ensayos.config.timings import config_with_timings, to_seconds
from ensayos.engine.test_runner import TestRunner
from ensayos.engine.verification import check_pattern, missing_patterns, pattern_product
from ensayos.models.enums import DeviceClass, TestType, Verdict
from ensayos.models.measurement import (
    DielectricMeasurement,
    GroundingMeasurement,
    LeakageMeasurement,
)
from ensayos.models.test_result import TestResult

# ---------------------------------------------------------------- tiempos


@pytest.mark.parametrize(
    "value,unit,expected",
    [
        (5, "Segundos", 5),
        (2, "Minutos", 120),
        (1, "Horas", 3600),
        (7, None, 7),
        (None, "Minutos", 9),
    ],
)
def test_to_seconds(value, unit, expected):
    assert to_seconds(value, unit, default=9) == expected


def test_config_con_tiempos_de_la_base():
    cfg = config_with_timings(
        {
            "consumo_duracion": 10,
            "consumo_unidad": "Segundos",
            "fuga_activa_duracion": 1,
            "fuga_activa_unidad": "Minutos",
            "pat_duracion": None,
        }
    )
    assert cfg.durations.consumption == 10
    assert cfg.durations.active_leakage == 60
    assert cfg.durations.grounding == tests_config.durations.grounding  # sin valor: .env
    assert cfg.durations.consumption_settle == tests_config.durations.consumption_settle
    assert cfg.leakage == tests_config.leakage  # el resto no cambia


def test_el_runner_pasa_la_configuracion_a_los_ensayos():
    cfg = config_with_timings({"rigidez_duracion": 42, "rigidez_unidad": "Segundos"})
    runner = TestRunner(hardware=object(), config=cfg)
    test = runner._create_test(TestType.DIELECTRIC, pattern_product(1))
    assert test.duration_seconds == 42


# ---------------------------------------------------------------- verificación


def _r(test_type, verdict, measurement):
    return TestResult(test_type=test_type, verdict=verdict, measurement=measurement)


def test_patron_que_pasa_dentro_de_tolerancia():
    c = check_pattern(
        _r(TestType.ACTIVE_LEAKAGE, Verdict.OK, LeakageMeasurement(505.0)), 1, 500.0, 10
    )
    assert c.ok and c.key == "fuga" and c.within_tolerance


def test_patron_que_falla_con_veredicto_falla():
    c = check_pattern(
        _r(TestType.GROUNDING, Verdict.FAIL, GroundingMeasurement(300.0, 10.0)), 2, 310.0, 10
    )
    assert c.ok and c.key == "pat"


def test_fuera_de_tolerancia():
    c = check_pattern(
        _r(TestType.DIELECTRIC, Verdict.FAIL, DielectricMeasurement(1000, 8.0)), 2, 6.0, 10
    )
    assert not c.ok and "+33.3 %" in c.reason


def test_veredicto_distinto_del_esperado():
    c = check_pattern(
        _r(TestType.ACTIVE_LEAKAGE, Verdict.FAIL, LeakageMeasurement(500.0)), 1, 500.0, 10
    )
    assert not c.ok and "se esperaba OK" in c.reason


def test_sin_medicion_o_infinita():
    sin = check_pattern(_r(TestType.ACTIVE_LEAKAGE, Verdict.FAIL, None), 2, 500.0, 10)
    inf = check_pattern(
        _r(TestType.GROUNDING, Verdict.FAIL, GroundingMeasurement(math.inf, 0.0)), 2, 500.0, 10
    )
    assert not sin.ok and "sin medición" in sin.reason
    assert not inf.ok and "sin medición" in inf.reason


def test_patron_sin_valor():
    c = check_pattern(
        _r(TestType.ACTIVE_LEAKAGE, Verdict.OK, LeakageMeasurement(500.0)), 1, 0.0, 10
    )
    assert not c.ok and "sin valor" in c.reason


def test_patrones_faltantes():
    completos = {f"{k}_{s}": 1.0 for k in ("fuga", "pat", "rd") for s in ("pasa", "falla")}
    assert missing_patterns(completos) == []
    assert missing_patterns({**completos, "rd_falla": 0}) == ["patrón 2: rigidez dieléctrica"]


def test_producto_del_patron_es_clase_1():
    assert pattern_product(2).clase == DeviceClass.CLASS_1

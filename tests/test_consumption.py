"""Tests del ensayo de consumo (IEC 60335-1, 10.1 y 10.2)."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ensayos.database.schemas import initialize_database
from ensayos.database.sqlite_repository import SQLiteProductRepository
from ensayos.engine.test_runner import TestRunner
from ensayos.engine.tests.consumption import ConsumptionTest
from ensayos.engine.verdict import current_limits, evaluate_consumption, power_limits
from ensayos.models.enums import ApplianceType, DeviceClass, TestType, Verdict
from ensayos.models.measurement import ConsumptionMeasurement
from ensayos.models.product import Product

HEATING = ApplianceType.HEATING
MOTOR = ApplianceType.MOTOR


class TestPowerLimits:
    """Tabla 1: desviación de la potencia."""

    @pytest.mark.parametrize("appliance_type", [HEATING, MOTOR])
    def test_hasta_25_w_solo_mas_20(self, appliance_type: ApplianceType) -> None:
        lower, upper = power_limits(20.0, appliance_type)
        assert lower is None
        assert upper == pytest.approx(24.0)

    def test_calefaccion_hasta_200_w_mas_menos_10(self) -> None:
        assert power_limits(100.0, HEATING) == pytest.approx((90.0, 110.0))

    def test_calefaccion_mas_de_200_w_usa_20_w_si_es_mayor(self) -> None:
        # 5 % de 300 W = 15 W < 20 W
        assert power_limits(300.0, HEATING) == pytest.approx((270.0, 320.0))

    def test_calefaccion_mas_de_200_w_usa_5_pct_si_es_mayor(self) -> None:
        # 5 % de 2000 W = 100 W > 20 W
        assert power_limits(2000.0, HEATING) == pytest.approx((1800.0, 2100.0))

    def test_motor_hasta_300_w_solo_mas_20(self) -> None:
        lower, upper = power_limits(300.0, MOTOR)
        assert lower is None
        assert upper == pytest.approx(360.0)

    def test_motor_mas_de_300_w_usa_60_w_si_es_mayor(self) -> None:
        # 15 % de 350 W = 52,5 W < 60 W
        assert power_limits(350.0, MOTOR)[1] == pytest.approx(410.0)
        # 15 % de 1000 W = 150 W > 60 W
        assert power_limits(1000.0, MOTOR)[1] == pytest.approx(1150.0)


class TestCurrentLimits:
    """Tabla 2: desviación de la corriente."""

    def test_calefaccion_mas_de_1_a(self) -> None:
        # 5 % de 1,5 A = 0,075 A < 0,10 A
        assert current_limits(1.5, HEATING) == pytest.approx((1.35, 1.6))

    def test_motor_entre_0_2_y_1_5_a(self) -> None:
        lower, upper = current_limits(1.0, MOTOR)
        assert lower is None
        assert upper == pytest.approx(1.2)

    def test_motor_mas_de_1_5_a_usa_0_30_a_si_es_mayor(self) -> None:
        assert current_limits(1.6, MOTOR)[1] == pytest.approx(1.9)


class TestEvaluateConsumption:
    """Veredicto combinado de potencia y corriente."""

    def test_calefactor_dentro_de_tolerancia(self) -> None:
        assert evaluate_consumption(9.0, 9.1, 2050.0, 2000.0, HEATING) == Verdict.OK

    def test_calefactor_excede_potencia(self) -> None:
        assert evaluate_consumption(9.0, 9.1, 2150.0, 2000.0, HEATING) == Verdict.FAIL

    def test_calefactor_por_debajo_de_menos_10(self) -> None:
        assert evaluate_consumption(8.0, 9.1, 1750.0, 2000.0, HEATING) == Verdict.FAIL

    def test_motor_sin_limite_inferior_normativo(self) -> None:
        # 70 % del nominal: pasa porque la norma no fija mínimo para motores
        assert evaluate_consumption(3.2, 4.5, 700.0, 1000.0, MOTOR) == Verdict.OK

    def test_motor_bajo_minimo_funcional(self) -> None:
        # 40 % del nominal: el aparato probablemente no funciona
        assert evaluate_consumption(1.8, 4.5, 400.0, 1000.0, MOTOR) == Verdict.FAIL

    def test_solo_se_evalua_lo_declarado(self) -> None:
        assert evaluate_consumption(99.0, 0.0, 2000.0, 2000.0, HEATING) == Verdict.OK

    def test_sin_valores_declarados_no_se_ejecuta(self) -> None:
        assert evaluate_consumption(1.0, 0.0, 100.0, 0.0, HEATING) == Verdict.NOT_RUN


class FakeHardware:
    """Hardware simulado que devuelve una secuencia fija de lecturas."""

    def __init__(self, readings: list[ConsumptionMeasurement | None]):
        self._readings = iter(readings)
        mapping = SimpleNamespace(fuga_activa=1)
        self._cfg = SimpleNamespace(relay=SimpleNamespace(mapping=mapping, settle_delay=0.0))

    def activate_relay(self, relay: int) -> None:
        pass

    def deactivate_relay(self, relay: int) -> None:
        pass

    def read_consumption(self) -> ConsumptionMeasurement | None:
        return next(self._readings)


def _run(readings: list[ConsumptionMeasurement | None], **kwargs):
    test = ConsumptionTest(FakeHardware(readings), **kwargs)
    with (
        patch("ensayos.engine.tests.base.time.sleep"),
        patch.object(ConsumptionTest, "duration_seconds", len(readings)),
    ):
        return test.run()


class TestConsumptionTestRun:
    """Pruebas del ensayo completo con hardware simulado."""

    def test_evalua_el_promedio_del_intervalo(self) -> None:
        # La última lectura sola (2200 W) fallaría; el promedio (2050 W) pasa
        result = _run(
            [
                ConsumptionMeasurement(220.0, 9.0, 1900.0, 1.0),
                ConsumptionMeasurement(220.0, 9.0, 2050.0, 1.0),
                ConsumptionMeasurement(220.0, 9.0, 2200.0, 1.0),
            ],
            rated_power=2000.0,
            appliance_type=HEATING,
        )
        assert result.verdict == Verdict.OK
        assert result.measurement.power == pytest.approx(2050.0)

    def test_usa_potencia_activa_y_no_aparente(self) -> None:
        # V × I = 1100 VA, pero la potencia activa es 700 W (cos φ = 0,64)
        result = _run(
            [ConsumptionMeasurement(220.0, 5.0, 700.0, 0.64)] * 2,
            rated_power=1000.0,
            appliance_type=HEATING,
        )
        assert result.verdict == Verdict.FAIL


def test_runner_pasa_el_tipo_de_aparato() -> None:
    runner = TestRunner(hardware=MagicMock())
    product = Product("M", "P", "", 1000.0, 220.0, 4.5, 50.0, DeviceClass.CLASS_1)
    product.tipo_aparato = MOTOR
    test = runner._create_test(TestType.CONSUMPTION, product)
    assert isinstance(test, ConsumptionTest)
    assert test.appliance_type == MOTOR


def test_producto_conserva_el_tipo_de_aparato(tmp_path) -> None:
    db = str(tmp_path / "ensayos.db")
    initialize_database(db)
    repo = SQLiteProductRepository(db)
    product = Product("M", "P", "", 1000.0, 220.0, 4.5, 50.0, DeviceClass.CLASS_1)
    assert repo.create(product)
    stored = repo.get_by_brand_model("M", "P")
    assert stored.tipo_aparato == HEATING

    stored.tipo_aparato = MOTOR
    assert repo.update(stored)
    assert repo.get_by_id(stored.id).tipo_aparato == MOTOR

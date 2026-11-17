"""Tests de la aplicación de las correcciones de calibración (CORRECTION_*) a las lecturas."""

from unittest.mock import MagicMock

import pytest

from ensayos.config.config_tests import CalibrationCorrections
from ensayos.engine.tests.passive_leakage import PassiveLeakageTest
from ensayos.hardware.hardware_manager import HardwareManager
from ensayos.models.measurement import PzemReading

CORRECCIONES = CalibrationCorrections(
    voltage=2.0,
    current=0.05,
    active_leakage=10.0,
    passive_leakage=-20.0,
    grounding=5.0,
    dielectric=-30.0,
)


def make_manager(reading: PzemReading, corrections=CORRECCIONES) -> HardwareManager:
    """HardwareManager con un ESP32 simulado que siempre devuelve la misma lectura."""
    esp32 = MagicMock()
    esp32.read_pzem.return_value = reading
    return HardwareManager(
        relay_controller=MagicMock(), esp32_client=esp32, corrections=corrections
    )


def test_consumo_aplica_correccion_de_tension_y_corriente():
    m = make_manager(PzemReading(voltage=228.0, current=1.0, power=228.0, energy=0.0))
    medicion = m.read_consumption()
    assert medicion.voltage == pytest.approx(230.0)
    assert medicion.current == pytest.approx(1.05)


def test_consumo_y_fuga_aplica_ambas_correcciones():
    m = make_manager(PzemReading(voltage=228.0, current=1.0, power=228.0, energy=0.0))
    consumo, fuga = m.read_consumption_and_leakage()
    assert consumo.voltage == pytest.approx(230.0)
    escala = m._cfg.scale.leakage_current_multiplier
    assert fuga.leakage_ua == pytest.approx(1.0 * escala + 10.0)


def test_fuga_activa_y_pasiva_usan_su_propia_correccion():
    m = make_manager(PzemReading(voltage=0.0, current=50.0, power=0.0, energy=0.0))
    base = 50.0 * m._cfg.scale.leakage_current_multiplier
    assert m.read_leakage().leakage_ua == pytest.approx(base + 10.0)
    assert m.read_leakage(passive=True).leakage_ua == pytest.approx(base - 20.0)


def test_puesta_a_tierra_aplica_correccion():
    sin = make_manager(
        PzemReading(voltage=0.2, current=10.0, power=0.0, energy=0.0), CalibrationCorrections()
    )
    con = make_manager(PzemReading(voltage=0.2, current=10.0, power=0.0, energy=0.0))
    assert con.read_grounding().resistance_mohm == pytest.approx(
        sin.read_grounding().resistance_mohm + 5.0
    )


def test_rigidez_aplica_correccion_de_tension():
    sin = make_manager(
        PzemReading(voltage=100.0, current=0.001, power=0.0, energy=0.0), CalibrationCorrections()
    )
    con = make_manager(PzemReading(voltage=100.0, current=0.001, power=0.0, energy=0.0))
    assert con.read_dielectric().voltage == pytest.approx(sin.read_dielectric().voltage - 30.0)
    assert con.read_dielectric().current_ma == pytest.approx(sin.read_dielectric().current_ma)


def test_sin_correcciones_no_cambia_la_lectura():
    m = make_manager(
        PzemReading(voltage=228.0, current=1.0, power=228.0, energy=0.0), CalibrationCorrections()
    )
    medicion = m.read_consumption()
    assert medicion.voltage == 228.0
    assert medicion.current == 1.0


def test_ensayo_de_fuga_pasiva_pide_la_correccion_pasiva():
    hardware = MagicMock()
    test = PassiveLeakageTest.__new__(PassiveLeakageTest)
    test.hardware = hardware
    test.measure()
    hardware.read_leakage.assert_called_once_with(passive=True)

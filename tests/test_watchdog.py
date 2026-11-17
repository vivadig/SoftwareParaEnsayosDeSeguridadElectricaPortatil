"""Tests del watchdog de HardwareManager, incluido RELAY_WATCHDOG=0."""

from dataclasses import replace
from unittest.mock import MagicMock, patch

import pytest

from ensayos.config.config_hardware import hardware_config
from ensayos.hardware.hardware_manager import HardwareManager


def make_manager(watchdog: int) -> tuple[HardwareManager, MagicMock]:
    """Crea un HardwareManager con relés simulados y el watchdog indicado."""
    relay = MagicMock()
    esp32 = MagicMock()
    esp32.read_pzem.return_value = None
    manager = HardwareManager(relay_controller=relay, esp32_client=esp32)
    manager._relay_serial = "BITFT"
    mapping = replace(hardware_config.relay.mapping, watchdog=watchdog)
    manager._cfg = replace(hardware_config, relay=replace(hardware_config.relay, mapping=mapping))
    return manager, relay


@pytest.fixture(autouse=True)
def sin_esperas():
    with patch("ensayos.hardware.hardware_manager.time.sleep"):
        yield


def test_watchdog_pulsa_el_rele_configurado():
    manager, relay = make_manager(watchdog=2)
    manager.watchdog_reset()
    relay.turn_on.assert_called_once_with("BITFT", 2)
    relay.turn_off.assert_called_once_with("BITFT", 2)


def test_watchdog_desactivado_no_toca_reles(caplog):
    manager, relay = make_manager(watchdog=0)
    manager.watchdog_reset()
    relay.turn_on.assert_not_called()
    relay.turn_off.assert_not_called()
    assert "Watchdog desactivado" in caplog.text


def test_lectura_fallida_con_watchdog_desactivado_sigue_siendo_falla():
    manager, relay = make_manager(watchdog=0)
    assert manager.read_grounding() is None
    relay.turn_on.assert_not_called()

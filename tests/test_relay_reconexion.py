"""Tests de la tolerancia del control de relés a desconexiones de la placa USB."""

from unittest.mock import MagicMock

import pytest

from ensayos.hardware.hardware_manager import HardwareManager
from ensayos.hardware.relay_controller import (
    HidapiBackend,
    RelayBoardNotFoundError,
    RelayController,
)
from tests.test_relay_backend import PATH, FakeBoard, FakeDevice


class FlakyBoard(FakeBoard):
    """Placa que desaparece del bus durante algunas enumeraciones y luego vuelve.

    Al volver, como una placa real reiniciada, arranca con todos los relés apagados.
    """

    def __init__(self, offline_enumerations: int = 0, listed_but_unopenable: bool = False):
        super().__init__()
        self.offline_enumerations = offline_enumerations
        self.listed_but_unopenable = listed_but_unopenable


def make_flaky_hid(board: FlakyBoard) -> MagicMock:
    """Módulo ``hid`` simulado cuya placa falta durante ``offline_enumerations`` llamadas."""

    def enumerate_(vid, pid):
        if board.offline_enumerations > 0:
            board.offline_enumerations -= 1
            board.connected = False  # abrirla falla mientras está fuera del bus
            board.state = 0  # el reinicio deja los relés apagados
            if board.listed_but_unopenable:
                return [{"path": PATH, "product_string": board.product}]
            return []
        board.connected = True
        return [{"path": PATH, "product_string": board.product}]

    hid = MagicMock()
    hid.enumerate.side_effect = enumerate_
    hid.device.side_effect = lambda: FakeDevice(board)
    return hid


def make_controller(board: FlakyBoard) -> RelayController:
    return RelayController(backend=HidapiBackend(hid_module=make_flaky_hid(board)))


def test_placa_listada_pero_sin_responder_se_omite():
    board = FlakyBoard(offline_enumerations=1, listed_but_unopenable=True)
    backend = HidapiBackend(hid_module=make_flaky_hid(board))
    assert backend.board_details() == []
    assert backend.board_details() == [("BITFT", 2, 0)]


def test_comando_con_placa_desconectada_lanza_error_especifico():
    board = FlakyBoard()
    controller = make_controller(board)
    board.offline_enumerations = 5
    with pytest.raises(RelayBoardNotFoundError):
        controller.turn_on("BITFT", 1)


def test_turn_off_all_espera_la_reconexion():
    board = FlakyBoard()
    controller = make_controller(board)
    controller.turn_on("BITFT", 1)
    board.offline_enumerations = 3  # se cae durante tres enumeraciones
    assert controller.turn_off_all("BITFT", retries=10, retry_delay=0)
    assert board.state == 0


def test_turn_off_all_informa_si_la_placa_no_vuelve(caplog):
    board = FlakyBoard()
    controller = make_controller(board)
    board.offline_enumerations = 100
    assert not controller.turn_off_all("BITFT", retries=3, retry_delay=0)
    assert "cortar la red" in caplog.text


def test_turn_off_all_normal():
    board = FlakyBoard()
    controller = make_controller(board)
    controller.turn_on("BITFT", 1)
    controller.turn_on("BITFT", 2)
    assert controller.turn_off_all("BITFT", retries=1, retry_delay=0)
    assert board.state == 0


def test_deactivate_relay_recupera_la_placa():
    relay = MagicMock()
    relay.turn_off.side_effect = RelayBoardNotFoundError("caída")
    relay.turn_off_all.return_value = True
    manager = HardwareManager(relay_controller=relay, esp32_client=MagicMock())
    manager._relay_serial = "BITFT"
    manager.deactivate_relay(1)
    relay.turn_off_all.assert_called_once_with("BITFT")


def test_deactivate_relay_propaga_si_no_se_recupera():
    relay = MagicMock()
    relay.turn_off.side_effect = RelayBoardNotFoundError("caída")
    relay.turn_off_all.return_value = False
    manager = HardwareManager(relay_controller=relay, esp32_client=MagicMock())
    manager._relay_serial = "BITFT"
    with pytest.raises(RelayBoardNotFoundError):
        manager.deactivate_relay(1)

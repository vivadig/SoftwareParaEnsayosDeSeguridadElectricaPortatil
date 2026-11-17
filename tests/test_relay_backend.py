"""Tests del controlador de relés USB con el backend hidapi simulado."""

from unittest.mock import MagicMock

import pytest

from ensayos.hardware.relay_controller import (
    HidapiBackend,
    RelayController,
    UsbrelayBackend,
    create_backend,
)

PATH = b"\\\\?\\HID#VID_16C0&PID_05DF#placa"


class FakeDevice:
    """Dispositivo HID simulado que guarda el estado de los relés."""

    def __init__(self, board: "FakeBoard"):
        self._board = board

    def open_path(self, path: bytes) -> None:
        if not self._board.connected:
            raise OSError("open failed")

    def close(self) -> None:
        pass

    def get_feature_report(self, report_id: int, length: int) -> list[int]:
        # Igual que en Windows: report ID + 8 bytes (serie, 2 bytes libres, estado)
        return [0, *self._board.serial.encode(), 0, 0, self._board.state]

    def send_feature_report(self, data: list[int]) -> int:
        self._board.sent.append(data)
        _, command, relay = data[:3]
        if command == 0xFF:
            self._board.state |= 1 << (relay - 1)
        elif command == 0xFD:
            self._board.state &= ~(1 << (relay - 1))
        return len(data)


class FakeBoard:
    """Placa USBRelay2 simulada."""

    def __init__(self, serial: str = "BITFT", product: str = "USBRelay2"):
        self.serial = serial
        self.product = product
        self.state = 0
        self.connected = True
        self.sent: list[list[int]] = []


def make_hid(board: FakeBoard) -> MagicMock:
    """Crea un módulo ``hid`` simulado con una placa conectada."""
    hid = MagicMock()
    hid.enumerate.side_effect = lambda vid, pid: (
        [{"path": PATH, "product_string": board.product}] if board.connected else []
    )
    hid.device.side_effect = lambda: FakeDevice(board)
    return hid


@pytest.fixture
def board() -> FakeBoard:
    return FakeBoard()


@pytest.fixture
def controller(board: FakeBoard) -> RelayController:
    return RelayController(backend=HidapiBackend(hid_module=make_hid(board)))


class TestHidapiBackend:
    def test_detecta_serie_cantidad_y_estado(self, controller):
        assert controller.board_count == 1
        assert controller.get_boards() == [("BITFT", 2, 0)]
        assert controller.get_active_serial() == "BITFT"

    def test_cantidad_de_reles_por_producto(self):
        backend = HidapiBackend(hid_module=make_hid(FakeBoard(product="USBRelay8")))
        assert backend.board_details()[0][1] == 8

    def test_enciende_y_apaga(self, controller, board):
        assert controller.turn_on("BITFT", 2) == 0
        assert board.sent[-1][:3] == [0, 0xFF, 2]
        assert controller.get_state("BITFT") == 0b10
        assert controller.turn_off("BITFT", 2) == 0
        assert board.sent[-1][:3] == [0, 0xFD, 2]
        assert controller.get_state("BITFT") == 0

    def test_rele_inexistente_interrumpe(self, controller, board):
        with pytest.raises(ValueError, match="no existe"):
            controller.turn_on("BITFT", 3)
        assert board.sent == []

    def test_placa_desconectada(self, controller, board):
        board.connected = False
        backend = controller._backend
        assert backend.board_control("BITFT", 1, 1) == 1

    def test_turn_off_all(self, controller, board):
        controller.turn_on("BITFT", 1)
        controller.turn_on("BITFT", 2)
        controller.turn_off_all("BITFT")
        assert controller.get_state("BITFT") == 0

    def test_sin_placas(self):
        board = FakeBoard()
        board.connected = False
        controller = RelayController(backend=HidapiBackend(hid_module=make_hid(board)))
        assert controller.board_count == 0
        assert controller.get_active_serial() is None


class TestUsbrelayBackend:
    def test_delegar_en_usbrelay_py(self):
        lib = MagicMock()
        lib.board_details.return_value = (("6QMBS", 8, 0),)
        lib.board_control.return_value = 0
        controller = RelayController(backend=UsbrelayBackend(usbrelay_module=lib))
        lib.board_count.assert_called_once()
        assert controller.turn_on("6QMBS", 8) == 0
        lib.board_control.assert_called_once_with("6QMBS", 8, 1)


def test_backend_desconocido():
    with pytest.raises(ValueError, match="RELAY_BACKEND"):
        create_backend("serial")

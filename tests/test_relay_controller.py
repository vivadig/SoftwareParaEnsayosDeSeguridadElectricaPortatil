"""Tests para el controlador de relés."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Mock de usbrelay_py para permitir tests sin el módulo instalado
sys.modules["usbrelay_py"] = MagicMock()


@pytest.fixture
def mock_usbrelay():
    """Mock del módulo usbrelay_py."""
    with patch("src.relay_controller.usbrelay_py") as mock:
        mock.board_count.return_value = 1
        mock.board_details.return_value = (("6QMBS", 8, 0),)
        mock.board_control.return_value = 9
        yield mock


def test_relay_controller_init(mock_usbrelay):
    """Test de inicialización del controlador."""
    from src.relay_controller import RelayController

    controller = RelayController()

    mock_usbrelay.board_count.assert_called_once()
    assert controller.board_count == 1


def test_get_boards(mock_usbrelay):
    """Test de obtención de placas conectadas."""
    from src.relay_controller import RelayController

    controller = RelayController()
    boards = controller.get_boards()

    assert len(boards) == 1
    assert boards[0][0] == "6QMBS"
    assert boards[0][1] == 8
    assert boards[0][2] == 0


def test_control_relay_on(mock_usbrelay):
    """Test de encendido de relé."""
    from src.relay_controller import RelayController

    controller = RelayController()
    result = controller.control_relay("6QMBS", 1, 1)

    mock_usbrelay.board_control.assert_called_once_with("6QMBS", 1, 1)
    assert result == 9


def test_control_relay_off(mock_usbrelay):
    """Test de apagado de relé."""
    from src.relay_controller import RelayController

    controller = RelayController()
    result = controller.control_relay("6QMBS", 1, 0)

    mock_usbrelay.board_control.assert_called_once_with("6QMBS", 1, 0)
    assert result == 9


def test_turn_on(mock_usbrelay):
    """Test del método turn_on."""
    from src.relay_controller import RelayController

    controller = RelayController()
    controller.turn_on("6QMBS", 1)

    mock_usbrelay.board_control.assert_called_once_with("6QMBS", 1, 1)


def test_turn_off(mock_usbrelay):
    """Test del método turn_off."""
    from src.relay_controller import RelayController

    controller = RelayController()
    controller.turn_off("6QMBS", 1)

    mock_usbrelay.board_control.assert_called_once_with("6QMBS", 1, 0)


def test_get_first_serial(mock_usbrelay):
    """Test de obtención del primer serial."""
    from src.relay_controller import RelayController

    controller = RelayController()
    serial = controller.get_first_serial()

    assert serial == "6QMBS"


def test_get_first_serial_no_boards(mock_usbrelay):
    """Test de obtención del primer serial sin placas conectadas."""
    from src.relay_controller import RelayController

    mock_usbrelay.board_details.return_value = ()

    controller = RelayController()
    serial = controller.get_first_serial()

    assert serial is None

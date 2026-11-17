"""Tests de la integración de los paneles de ensayo y de productos en la ventana principal."""

import os
from unittest.mock import patch

import pytest

pytest.importorskip("PyQt5.QtWidgets")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication  # noqa: E402

from ensayos.gui.widgets.product_form import ProductForm  # noqa: E402
from ensayos.gui.widgets.test_panel import TestPanel  # noqa: E402
from ensayos.models.enums import DeviceClass  # noqa: E402
from ensayos.models.product import Product  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    # Sin hardware real: HardwareManager simulado
    with patch("ensayos.gui.main_window.HardwareManager"):
        from ensayos.gui.main_window import MainWindow

        w = MainWindow(db_path=str(tmp_path / "ensayos.db"))
    yield w
    w.close()


def _tab_titles(window) -> list[str]:
    tabs = window.tabWidget
    return [tabs.tabText(i).strip() for i in range(tabs.count())]


def test_pestanas_reemplazadas_por_los_paneles(window):
    tabs = window.tabWidget
    titles = _tab_titles(window)
    assert isinstance(tabs.widget(titles.index("Ensayos")), TestPanel)
    assert isinstance(tabs.widget(titles.index("Productos")), ProductForm)
    # El resto de las pestañas del .ui sigue en su lugar
    assert titles == [
        "Ensayos",
        "Consumo",
        "Verificación",
        "Productos",
        "Historial",
        "Configuraciones",
        "Exportar",
    ]
    assert tabs.currentWidget() is window.test_panel


def test_producto_nuevo_aparece_en_el_panel_de_ensayos(window):
    assert window.test_panel.lista_productos.count() == 0
    window._product_repo.create(
        Product(
            marca="Acme",
            modelo="P1",
            descripcion="Pava",
            potencia=2000,
            tension=220,
            corriente=9.1,
            frecuencia=50,
            clase=DeviceClass.CLASS_1,
        )
    )
    window.product_form.products_changed.emit()
    assert window.test_panel.lista_productos.count() == 1


def test_fin_de_ensayo_recarga_el_historial(window):
    with patch.object(window, "_load_tables") as load:
        window.test_panel.signals.all_completed.emit([])
    load.assert_called_once()

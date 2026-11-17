"""Tests de las pestañas Consumo y Exportar de la ventana principal (hardware simulado)."""

import os
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("PyQt5.QtWidgets")
pytest.importorskip("pglive")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from openpyxl import load_workbook  # noqa: E402
from PyQt5.QtCore import QDate  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402

from ensayos.models.enums import DeviceClass  # noqa: E402
from ensayos.models.measurement import ConsumptionMeasurement  # noqa: E402
from ensayos.models.product import Product  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def dialogos(monkeypatch):
    log: list[tuple[str, str]] = []
    for kind in ("warning", "critical", "information"):
        monkeypatch.setattr(
            QMessageBox, kind, staticmethod(lambda *a, k=kind, **kw: log.append((k, a[2])))
        )
    return log


@pytest.fixture
def window(app, tmp_path, dialogos):
    hardware = MagicMock()
    hardware.try_acquire_session.return_value = True
    hardware._cfg.relay.mapping.fuga_activa = 1
    hardware.read_consumption.return_value = ConsumptionMeasurement(230.0, 0.16, 37.6, 1.0)
    hardware.read_leakage.return_value = None
    with patch("ensayos.gui.main_window.HardwareManager", return_value=hardware):
        from ensayos.gui.main_window import MainWindow

        w = MainWindow(db_path=str(tmp_path / "e.db"))
    w._product_repo.create(
        Product(
            marca="Bancolab",
            modelo="Soldador",
            descripcion="",
            potencia=40,
            tension=220,
            corriente=0.18,
            frecuencia=50,
            clase=DeviceClass.CLASS_1,
        )
    )
    w.product_form.products_changed.emit()
    yield w
    w.close()


def _esperar(app, cond, timeout=10.0):
    fin = time.time() + timeout
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()
    return cond()


# ---------------------------------------------------------------- Consumo


def test_botones_de_consumo_y_exportar_conectados(window):
    for name in (
        "boton_ensayar_consumo",
        "boton_parada_consumo",
        "boton_reset_muestras",
        "boton_buscar_muestras",
        "boton_exportar_escritorio",
        "boton_exportar_externo",
        "boton_exportar_mail",
    ):
        btn = getattr(window, name)
        assert btn.receivers(btn.clicked) > 0, name


def test_producto_nuevo_aparece_en_consumo(window):
    assert window.combo_productos_consumo.count() == 1


def test_perfil_de_consumo_completo(app, window, monkeypatch):
    monkeypatch.setattr(
        "ensayos.gui.consumption_tab.tests_config",
        SimpleNamespace(durations=SimpleNamespace(consumption_profile_settle=0)),
    )
    window._config_repo.save_timings(tiempo_ensayo_consumo=2, tiempo_entre_muestras=1)
    window.input_nro_serie_consumo.setText("SN-1")
    window.boton_ensayar_consumo.click()
    assert not window.boton_ensayar_consumo.isEnabled()
    assert _esperar(app, lambda: window.boton_ensayar_consumo.isEnabled())

    rows = window._consumo_repo.list_all()
    assert len(rows) == 3  # t = 0, 1 y 2 s
    assert {r["nro_serial"] for r in rows} == {"SN-1"}
    assert window.tabla_historial_consumo.rowCount() == 3
    assert window.consumption_tab._plots["potencia"].point_count() == 3
    assert window.label_potencia_activa_consumo.text() == "37.6"
    window._hardware.release_session.assert_called_once()

    window.boton_reset_muestras.click()
    assert window.consumption_tab._plots["potencia"].point_count() == 0
    assert window.label_muestra_actual.text() == "-"
    assert len(window._consumo_repo.list_all()) == 3  # el reset no borra el historial


def test_hardware_ocupado(window, dialogos):
    window._hardware.try_acquire_session.return_value = False
    window.boton_ensayar_consumo.click()
    assert dialogos[-1][0] == "warning" and "otro ensayo" in dialogos[-1][1]
    assert window.boton_ensayar_consumo.isEnabled()


# ---------------------------------------------------------------- Exportar


def test_exportar_a_escritorio(window, tmp_path, monkeypatch, dialogos):
    monkeypatch.setattr(window.export_tab, "desktop_dir", lambda: str(tmp_path))
    path = window.export_tab.export_to_desktop()
    assert path and os.path.exists(path)
    assert {ws.title for ws in load_workbook(path).worksheets} == {"FDL", "CONSUMO", "VERIFICACION"}
    assert dialogos[-1][0] == "information"


def test_exportar_con_fechas_invertidas(window, dialogos):
    window.input_fecha_desde.setDate(QDate.currentDate().addDays(1))
    assert window.export_tab.export_to_desktop() is None
    assert dialogos[-1][0] == "warning"


def test_exportar_a_carpeta(window, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "ensayos.gui.export_tab.QFileDialog.getExistingDirectory", lambda *a, **k: str(tmp_path)
    )
    path = window.export_tab.export_to_folder()
    assert path and os.path.dirname(path) == str(tmp_path)


def test_mail_sin_destinatarios_o_invalidos(window, dialogos):
    assert window.export_tab.export_by_email() is False
    assert "al menos una" in dialogos[-1][1]
    window.input_mail_1.setText("no-es-un-mail")
    assert window.export_tab.export_by_email() is False
    assert "no-es-un-mail" in dialogos[-1][1]


def test_mail_envia_el_excel_adjunto(window, monkeypatch, dialogos):
    enviados = {}

    def fake_send(recipients, path, **kw):
        enviados["to"] = recipients
        enviados["existe"] = os.path.exists(path)
        return True

    monkeypatch.setattr("ensayos.gui.export_tab.send_email_with_attachment", fake_send)
    window.input_mail_1.setText("calidad@ejemplo.com")
    window.input_mail_3.setText("lab@ejemplo.com")
    assert window.export_tab.export_by_email() is True
    assert enviados == {"to": ["calidad@ejemplo.com", "lab@ejemplo.com"], "existe": True}
    assert dialogos[-1][0] == "information"


def test_mail_fallido_avisa(window, monkeypatch, dialogos):
    monkeypatch.setattr("ensayos.gui.export_tab.send_email_with_attachment", lambda *a, **k: False)
    window.input_mail_1.setText("calidad@ejemplo.com")
    assert window.export_tab.export_by_email() is False
    assert dialogos[-1][0] == "critical" and "SMTP" in dialogos[-1][1]

"""Tests de las pestañas Configuraciones y Verificación (ventana offscreen, hardware simulado)."""

import os
import time
from unittest.mock import MagicMock, patch

import pytest

pytest.importorskip("PyQt5.QtWidgets")
pytest.importorskip("pglive")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402

from ensayos.models.enums import TestType, Verdict  # noqa: E402
from ensayos.models.measurement import (  # noqa: E402
    DielectricMeasurement,
    GroundingMeasurement,
    LeakageMeasurement,
)
from ensayos.models.test_result import TestResult  # noqa: E402


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
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Ok))
    return log


@pytest.fixture
def window(app, tmp_path, dialogos):
    hardware = MagicMock()
    hardware.try_acquire_session.return_value = True
    hardware.read_pzem.return_value = MagicMock(voltage=229.8)
    with patch("ensayos.gui.main_window.HardwareManager", return_value=hardware):
        from ensayos.gui.main_window import MainWindow

        w = MainWindow(db_path=str(tmp_path / "e.db"))
    yield w
    w.close()


def _esperar(app, cond, timeout=10.0):
    fin = time.time() + timeout
    while time.time() < fin and not cond():
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()
    return cond()


# ---------------------------------------------------------------- Configuraciones


def test_carga_los_tiempos_de_la_base(window):
    assert window.spinbox_tiempo_func.value() == 5
    assert window.combo_magnitud_func_fdl.currentText() == "Segundos"
    assert window.spinbox_tiempo_consumo.value() == 60
    assert window.spinbox_tiempo_muestras.value() == 5
    assert window.radio_ensayo_fdl.isChecked()


def test_guardar_y_aplicar_modo_ciclico(window, dialogos):
    window.spinbox_tiempo_fuga_activa.setValue(6)
    window.combo_magnitud_fuga_activa_fdl.setCurrentText("Minutos")
    window.radio_ensayo_ciclico.setChecked(True)
    window.spinbox_cantidad_ensayos.setValue(3)
    window.spinbox_tiempo_entre_ensayos.setValue(10)
    window.boton_guardar_configuraciones.click()
    t = window._config_repo.get_timings()
    assert (t["fuga_activa_duracion"], t["fuga_activa_unidad"]) == (6, "Minutos")
    assert t["cant_ensayos_ciclicos"] == 3 and t["tiempo_entre_ensayos"] == 10
    assert dialogos[-1][0] == "information"
    # El panel de ensayos queda en cíclico, 3 repeticiones, 10 s
    p = window.test_panel
    assert p.combo_modo.currentIndex() == 1
    assert p.spin_repeticiones.value() == 3 and p.spin_espera.value() == 10


def test_los_ensayos_usan_los_tiempos_guardados(window):
    from ensayos.config.timings import config_with_timings

    window.spinbox_tiempo_r_pat.setValue(7)
    window.boton_guardar_configuraciones.click()
    assert config_with_timings(window._config_repo.get_timings()).durations.grounding == 7


def test_consumo_con_duracion_menor_que_el_muestreo(window, dialogos):
    window.spinbox_tiempo_consumo.setValue(3)  # 3 s
    window.spinbox_tiempo_muestras.setValue(5)  # cada 5 s
    window.boton_guardar_configuraciones.click()
    assert dialogos[-1][0] == "warning"
    assert window._config_repo.get_timings()["tiempo_ensayo_consumo"] == 60  # no se guardó


def test_valores_predeterminados(window, dialogos):
    window.spinbox_tiempo_func.setValue(50)
    window.boton_guardar_configuraciones.click()
    window.boton_valores_predeterminados.click()
    assert window.spinbox_tiempo_func.value() == 5
    assert window._config_repo.get_timings()["consumo_duracion"] == 5
    assert "fábrica" in dialogos[-1][1]


def test_modo_consumo_lleva_a_la_pestana_consumo(window):
    window.radio_ensayo_consumo.setChecked(True)
    window.boton_guardar_configuraciones.click()
    assert window.tabWidget.currentWidget() is window.tab_7


# ---------------------------------------------------------------- Administración


def test_menu_administracion_abre_el_login(window):
    window.action_administracion.trigger()
    assert window._login_window is not None and window._login_window.isVisible()
    window._login_window.close()


# ---------------------------------------------------------------- Verificación

PATRONES = {
    "fuga_pasa": 500,
    "pat_pasa": 100,
    "rd_pasa": 1,
    "fuga_falla": 2000,
    "pat_falla": 400,
    "rd_falla": 10,
}


class FakeRunner:
    """TestRunner simulado: devuelve resultados según el patrón (producto "1" o "2")."""

    def __init__(self, *a, **k):
        self.stopped = False

    def stop(self):
        self.stopped = True

    def run_end_of_line(self, tests, product):
        if product.modelo == "1":
            return [
                TestResult(TestType.ACTIVE_LEAKAGE, Verdict.OK, LeakageMeasurement(510.0)),
                TestResult(TestType.GROUNDING, Verdict.OK, GroundingMeasurement(98.0, 10.0)),
                TestResult(TestType.DIELECTRIC, Verdict.OK, DielectricMeasurement(1000, 1.05)),
            ]
        return [
            TestResult(TestType.ACTIVE_LEAKAGE, Verdict.FAIL, LeakageMeasurement(1990.0)),
            TestResult(TestType.GROUNDING, Verdict.FAIL, GroundingMeasurement(405.0, 10.0)),
            TestResult(TestType.DIELECTRIC, Verdict.FAIL, DielectricMeasurement(1000, 13.0)),
        ]


def test_verificacion_sin_patrones_cargados(window, dialogos):
    window.boton_ensayar_verificacion.click()
    assert dialogos[-1][0] == "warning" and "Administración" in dialogos[-1][1]
    window._hardware.try_acquire_session.assert_not_called()


def test_verificacion_completa(app, window, dialogos, monkeypatch):
    window._config_repo.save_verification_patterns(**PATRONES)
    monkeypatch.setattr("ensayos.gui.verification_tab.TestRunner", FakeRunner)
    window.boton_ensayar_verificacion.click()
    assert _esperar(app, lambda: window.boton_ensayar_verificacion.isEnabled())

    estado = window.label_estado_verificacion.text()
    # rd falla: 13 mA contra un patrón de 10 mA (+30 %, fuera de ±10 %)
    assert estado == "Verificación NO APROBADA."
    assert "patrón 2 rd" in dialogos[-1][1]
    assert window.label_tension_verificacion.text() == "229.8"
    assert window.label_fuga_medicion_pasa.text() == "510.0"
    assert window.label_fuga_patron_pasa.text() == "500.0"
    assert window.label_rd_medicion_falla.text() == "13.0"
    assert "#2e7d32" in window.frame_fuga_veredicto_pasa.styleSheet()  # verde
    assert "#c62828" in window.frame_rd_veredicto_falla.styleSheet()  # rojo
    assert window.label_280.text() == "mA"
    rows = window._verif_repo.list_all()
    assert len(rows) == 1 and rows[0]["fuga_pasa"] == 510.0 and rows[0]["rd_falla"] == 13.0
    assert window.tabla_historial_verificacion.rowCount() == 1
    window._hardware.release_session.assert_called_once()


def test_verificacion_aprobada(app, window, monkeypatch):
    window._config_repo.save_verification_patterns(**{**PATRONES, "rd_falla": 12.5})
    monkeypatch.setattr("ensayos.gui.verification_tab.TestRunner", FakeRunner)
    window.boton_ensayar_verificacion.click()
    assert _esperar(app, lambda: window.boton_ensayar_verificacion.isEnabled())
    assert window.label_estado_verificacion.text() == "Verificación APROBADA."


def test_cancelar_al_pedir_el_patron(window, monkeypatch):
    window._config_repo.save_verification_patterns(**PATRONES)
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Cancel))
    window.boton_ensayar_verificacion.click()
    assert window.label_estado_verificacion.text() == "Verificación cancelada."
    assert window.boton_ensayar_verificacion.isEnabled()
    window._hardware.release_session.assert_called_once()

"""Prueba de punta a punta de los ensayos desde el panel de la ventana principal.

Usa el hardware real y una carga resistiva (soldador) enchufada en el DUT.
Cada escenario se lanza con el botón ENSAYAR, como lo haría el operario.
"""

import os
import sqlite3
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402

DB = sys.argv[1]
dialogos: list[str] = []
QMessageBox.warning = staticmethod(lambda *a, **k: dialogos.append(f"warning: {a[2]}"))
QMessageBox.critical = staticmethod(lambda *a, **k: dialogos.append(f"critical: {a[2]}"))

app = QApplication(sys.argv)
from ensayos.gui.main_window import MainWindow  # noqa: E402
from ensayos.gui.styles import BUTTON_ACTIVE, BUTTON_NORMAL  # noqa: E402
from ensayos.models.enums import ApplianceType, DeviceClass, TestType  # noqa: E402
from ensayos.models.product import Product  # noqa: E402

w = MainWindow(db_path=DB)
w.show()
panel = w.test_panel
hw = w._hardware
serie = hw._relay_serial

# Errores del hilo de ensayo (si no, quedan ocultos en el executor)
errores_hilo: list[str] = []
_submit = panel._executor.submit


def submit(fn, *args, **kwargs):
    fut = _submit(fn, *args, **kwargs)
    fut.add_done_callback(
        lambda f: f.exception() and errores_hilo.append(f"{type(f.exception()).__name__}: {f.exception()}")
    )
    return fut


panel._executor.submit = submit

# Producto: soldador de 40 W, calefacción, Clase I, cable fijo
w._product_repo.create(Product(
    marca="Bancolab", modelo="Soldador 40W", descripcion="Carga resistiva de prueba",
    potencia=40, tension=220, corriente=0.18, frecuencia=50, clase=DeviceClass.CLASS_1,
    con_cable_alimentacion=True, tipo_aparato=ApplianceType.HEATING,
))
panel.refresh_products()
panel.lista_productos.setCurrentRow(0)
panel.input_serial.setText("SN-PRUEBA-001")
app.processEvents()

terminado = {"ok": False}
panel.signals.all_completed.connect(lambda _r: terminado.update(ok=True))


def elegir(tests: set[TestType]) -> None:
    for tt, btn in panel._test_buttons.items():
        btn.setStyleSheet(BUTTON_ACTIVE if tt in tests else BUTTON_NORMAL)


def esperar(timeout: float) -> bool:
    fin = time.time() + timeout
    while time.time() < fin:
        app.processEvents()
        if terminado["ok"]:
            return True
        if errores_hilo and not panel.boton_parada.isEnabled():
            return False
        time.sleep(0.05)
    return False


def filas_historial() -> int:
    with sqlite3.connect(DB) as c:
        return c.execute("SELECT COUNT(*) FROM historial_fdl").fetchone()[0]


def escenario(nombre, tests, timeout=60, ciclico=None, parar_a=None):
    print(f"\n=== {nombre} ===")
    terminado["ok"] = False
    errores_hilo.clear()
    n_dlg = len(dialogos)
    antes = filas_historial()
    elegir(tests)
    if ciclico:
        panel.combo_modo.setCurrentIndex(1)
        panel.spin_repeticiones.setValue(ciclico[0])
        panel.spin_espera.setValue(ciclico[1])
        panel.combo_unidad_espera.setCurrentIndex(0)
    else:
        panel.combo_modo.setCurrentIndex(0)
    t0 = time.time()
    QTest.mouseClick(panel.boton_ensayar, Qt.LeftButton)
    if parar_a is not None:
        while time.time() - t0 < parar_a:
            app.processEvents(); time.sleep(0.05)
        QTest.mouseClick(panel.boton_parada, Qt.LeftButton)
    fin = esperar(timeout)
    time.sleep(0.3)
    app.processEvents()
    dur = time.time() - t0
    res = {tt.value: (panel.labels_medicion[tt.value].text(), panel.labels_veredicto[tt.value].text())
           for tt in tests}
    estado = hw.relay.get_state(serie)
    print(f"terminó={fin} ({dur:.1f} s) | resultados={res}")
    print(f"relés al final={estado} | historial +{filas_historial() - antes} | "
          f"UI lista={panel.boton_ensayar.isEnabled()} | errores hilo={errores_hilo} | "
          f"diálogos={dialogos[n_dlg:]}")
    if not fin and panel.boton_parada.isEnabled():
        # El hilo murió y la UI quedó "en ensayo": se libera para seguir probando
        panel._set_ui_running(False)
    if estado:
        hw.relay.turn_off_all(serie)
    return fin, res, estado


escenario("1. Consumo (final de línea)", {TestType.CONSUMPTION})
escenario("2. Fuga activa (sin PZEM2)", {TestType.ACTIVE_LEAKAGE})
escenario("3. Fuga pasiva (sin PZEM2)", {TestType.PASSIVE_LEAKAGE})
escenario("4. Puesta a tierra (relés 3 y 7 no existen)", {TestType.GROUNDING}, timeout=30)
escenario("5. Rigidez dieléctrica (relés 4-6 no existen)", {TestType.DIELECTRIC}, timeout=30)
escenario("6. Consumo cíclico: 2 repeticiones, 2 s de espera", {TestType.CONSUMPTION},
          timeout=90, ciclico=(2, 2))
escenario("7. PARADA a los 2 s de un consumo", {TestType.CONSUMPTION}, timeout=30, parar_a=2.0)

# Historial en la pestaña
w._load_tables()
t = w.tabla_historial_fdl
print(f"\n=== Historial ===\nfilas en la tabla de la GUI: {t.rowCount()}")
with sqlite3.connect(DB) as c:
    c.row_factory = sqlite3.Row
    for r in c.execute("SELECT * FROM historial_fdl ORDER BY id"):
        d = dict(r)
        print({k: v for k, v in d.items() if v not in (None, "", 0, 0.0)})
headers = [t.horizontalHeaderItem(i).text() for i in range(t.columnCount())]
print("columnas GUI:", headers)
if t.rowCount():
    print("fila 1 GUI:", [t.item(0, i).text() if t.item(0, i) else "" for i in range(t.columnCount())])

w.close()
app.processEvents()
print("relés al cerrar:", hw.relay.get_state(serie))

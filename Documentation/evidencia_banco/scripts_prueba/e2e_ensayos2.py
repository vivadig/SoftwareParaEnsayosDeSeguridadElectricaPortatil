"""Segunda tanda: veredicto con el producto correcto, cíclico, PARADA y cierre en medio de un ensayo."""

import os
import sqlite3
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402

DB = sys.argv[1]
QMessageBox.warning = staticmethod(lambda *a, **k: print("DIALOGO warning:", a[2]))
QMessageBox.critical = staticmethod(lambda *a, **k: print("DIALOGO critical:", a[2]))

app = QApplication(sys.argv)
from ensayos.gui.main_window import MainWindow  # noqa: E402
from ensayos.gui.styles import BUTTON_ACTIVE, BUTTON_NORMAL  # noqa: E402
from ensayos.models.enums import TestType  # noqa: E402

w = MainWindow(db_path=DB)
panel, hw = w.test_panel, w._hardware
serie = hw._relay_serial

# Seleccionar el soldador de 40 W de calefacción (no el de motor de la prueba anterior)
idx = next(i for i, p in enumerate(panel._products) if p.modelo == "Soldador 40W")
panel.lista_productos.setCurrentRow(idx)
p = panel._selected_product
print(f"Producto: {p.marca} {p.modelo} {p.potencia} W {p.tipo_aparato.value} {p.clase.value}")
for tt, btn in panel._test_buttons.items():
    btn.setStyleSheet(BUTTON_ACTIVE if tt == TestType.CONSUMPTION else BUTTON_NORMAL)

eventos: list[str] = []
panel.signals.all_completed.connect(lambda r: eventos.append(f"all_completed {time.time():.1f}"))


def executor_ocupado() -> bool:
    return bool(panel._executor._work_queue.qsize()) or any(
        t.is_alive() and panel._executor._work_queue.unfinished_tasks
        for t in panel._executor._threads
    )


def pump(seg: float) -> None:
    fin = time.time() + seg
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.05)


def historial() -> int:
    with sqlite3.connect(DB) as c:
        return c.execute("SELECT COUNT(*) FROM historial_fdl").fetchone()[0]


def correr_hasta_idle(timeout: float) -> float:
    t0 = time.time()
    fut = panel._last_future
    while time.time() - t0 < timeout and not fut.done():
        app.processEvents()
        time.sleep(0.05)
    pump(0.3)
    return time.time() - t0


_submit = panel._executor.submit


def submit(fn, *a, **k):
    panel._last_future = _submit(fn, *a, **k)
    return panel._last_future


panel._executor.submit = submit

# ---------------------------------------------------------------- A. veredicto
print("\n=== A. Consumo final de línea con el producto correcto ===")
eventos.clear(); h0 = historial()
panel.combo_modo.setCurrentIndex(0)
QTest.mouseClick(panel.boton_ensayar, Qt.LeftButton)
dur = correr_hasta_idle(30)
print(f"duró {dur:.1f} s | medición={panel.labels_medicion['consumo'].text()} "
      f"veredicto={panel.labels_veredicto['consumo'].text()} | historial +{historial() - h0} | "
      f"relés={hw.relay.get_state(serie)}")

# ---------------------------------------------------------------- B. cíclico
print("\n=== B. Cíclico: 3 repeticiones, 2 s entre ciclos ===")
eventos.clear(); h0 = historial()
panel.combo_modo.setCurrentIndex(1)
panel.spin_repeticiones.setValue(3)
panel.spin_espera.setValue(2)
panel.combo_unidad_espera.setCurrentIndex(0)
print("unidad de espera:", panel.combo_unidad_espera.currentText())
t0 = time.time()
QTest.mouseClick(panel.boton_ensayar, Qt.LeftButton)
ui_libre_en = None
while not panel._last_future.done() and time.time() - t0 < 120:
    app.processEvents()
    if ui_libre_en is None and panel.boton_ensayar.isEnabled():
        ui_libre_en = time.time() - t0
    time.sleep(0.05)
pump(0.3)
print(f"terminó el hilo a los {time.time() - t0:.1f} s | la UI se habilitó a los "
      f"{ui_libre_en if ui_libre_en is None else round(ui_libre_en, 1)} s | eventos all_completed="
      f"{len(eventos)} | historial +{historial() - h0} | contador 'Hechos'="
      f"{panel.label_ensayos_hechos.text()} | relés={hw.relay.get_state(serie)}")

# ---------------------------------------------------------------- C. PARADA
print("\n=== C. PARADA a los 2 s (final de línea) ===")
eventos.clear(); h0 = historial()
panel.combo_modo.setCurrentIndex(0)
t0 = time.time()
QTest.mouseClick(panel.boton_ensayar, Qt.LeftButton)
pump(2.0)
print("relés durante el ensayo:", hw.relay.get_state(serie))
QTest.mouseClick(panel.boton_parada, Qt.LeftButton)
dur = correr_hasta_idle(30)
print(f"se detuvo {dur:.1f} s después de PARADA | veredicto="
      f"{panel.labels_veredicto['consumo'].text()} | historial +{historial() - h0} | "
      f"UI lista={panel.boton_ensayar.isEnabled()} | relés={hw.relay.get_state(serie)}")

# ---------------------------------------------------------------- D. cerrar la ventana
print("\n=== D. Cerrar la ventana a los 2 s de un consumo ===")
t0 = time.time()
QTest.mouseClick(panel.boton_ensayar, Qt.LeftButton)
pump(2.0)
print("relés antes de cerrar:", hw.relay.get_state(serie))
w.close()
app.processEvents()
print("relés justo después de cerrar:", hw.relay.get_state(serie))
estados = []
while not panel._last_future.done() and time.time() - t0 < 30:
    estados.append(hw.relay.get_state(serie))
    time.sleep(0.5)
print(f"el hilo del ensayo siguió {time.time() - t0 - 2:.1f} s después de cerrar | "
      f"relés mientras tanto={sorted(set(estados))} | relés al final={hw.relay.get_state(serie)}")

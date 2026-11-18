"""Verifica en el banco las correcciones de la prueba de punta a punta."""

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
from ensayos.gui.main_window import MainWindow, _format_cell  # noqa: E402
from ensayos.gui.styles import BUTTON_ACTIVE, BUTTON_NORMAL  # noqa: E402
from ensayos.models.enums import TestType  # noqa: E402

w = MainWindow(db_path=DB)
panel, hw = w.test_panel, w._hardware
serie = hw._relay_serial
idx = next(i for i, p in enumerate(panel._products) if p.modelo == "Soldador 40W")
panel.lista_productos.setCurrentRow(idx)


def pump(seg):
    fin = time.time() + seg
    while time.time() < fin:
        app.processEvents()
        time.sleep(0.05)


def historial():
    with sqlite3.connect(DB) as c:
        return c.execute("SELECT COUNT(*) FROM historial_fdl").fetchone()[0]


def lanzar(tests, ciclico=None):
    for tt, btn in panel._test_buttons.items():
        btn.setStyleSheet(BUTTON_ACTIVE if tt in tests else BUTTON_NORMAL)
    panel.combo_modo.setCurrentIndex(1 if ciclico else 0)
    if ciclico:
        panel.spin_repeticiones.setValue(ciclico[0])
        panel.spin_espera.setValue(ciclico[1])
        panel.combo_unidad_espera.setCurrentIndex(0)
    QTest.mouseClick(panel.boton_ensayar, Qt.LeftButton)
    app.processEvents()


def esperar_ui_libre(timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        app.processEvents()
        if panel.boton_ensayar.isEnabled():
            pump(0.3)
            return time.time() - t0
        time.sleep(0.05)
    return None


print("=== 1. Consumo con estabilización (soldador 40 W, calefacción) ===")
h0, d0 = historial(), len(dialogos)
lanzar({TestType.CONSUMPTION})
dur = esperar_ui_libre(30)
print(f"duró {dur:.1f} s | medición={panel.labels_medicion['consumo'].text()} "
      f"veredicto={panel.labels_veredicto['consumo'].text()} | historial +{historial() - h0} | "
      f"relés={hw.relay.get_state(serie)}")

print("\n=== 2. Cíclico 3 x consumo, 2 s entre ciclos: UI bloqueada hasta el final ===")
h0 = historial()
t0 = time.time()
lanzar({TestType.CONSUMPTION}, ciclico=(3, 2))
dur = esperar_ui_libre(120)
print(f"la UI se liberó a los {dur:.1f} s | historial +{historial() - h0} | "
      f"relés={hw.relay.get_state(serie)}")

print("\n=== 3. Puesta a tierra con relés inexistentes: error visible y UI libre ===")
d0 = len(dialogos)
lanzar({TestType.GROUNDING})
dur = esperar_ui_libre(30)
print(f"UI libre a los {dur if dur is None else round(dur, 1)} s | diálogos={dialogos[d0:]} | "
      f"relés={hw.relay.get_state(serie)}")

print("\n=== 4. Fuga activa sin PZEM2: FALLA ===")
lanzar({TestType.ACTIVE_LEAKAGE})
dur = esperar_ui_libre(30)
print(f"veredicto={panel.labels_veredicto['fuga_activa'].text()} | relés={hw.relay.get_state(serie)}")

print("\n=== 5. Historial en la GUI ===")
w._load_tables()
t = w.tabla_historial_fdl
headers = [t.horizontalHeaderItem(i).text() for i in range(t.columnCount())]
fila = {headers[i]: (t.item(0, i).text() if t.item(0, i) else "") for i in range(t.columnCount())}
print({k: fila[k] for k in ("Tensión", "A Medida", "FP", "W Medida", "Consumo", "Fuga")})
print("registro viejo formateado:", _format_cell("227.95999999999998"))

print("\n=== 6. Cerrar la ventana a los 2 s de un consumo ===")
lanzar({TestType.CONSUMPTION})
pump(2.0)
print("relés antes de cerrar:", hw.relay.get_state(serie))
t0 = time.time()
w.close()
app.processEvents()
print(f"close() tardó {time.time() - t0:.1f} s (espera al hilo) | relés después={hw.relay.get_state(serie)} "
      f"| hilo vivo={any(th.is_alive() for th in panel._executor._threads)}")

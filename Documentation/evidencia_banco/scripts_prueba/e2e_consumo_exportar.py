"""Prueba en el banco de las pestañas Consumo y Exportar (hardware real, soldador)."""

import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox  # noqa: E402

DB, OUTDIR = sys.argv[1], sys.argv[2]
dialogos = []
for kind in ("warning", "critical", "information"):
    setattr(QMessageBox, kind, staticmethod(lambda *a, k=kind, **kw: dialogos.append((k, a[2]))))
QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: OUTDIR)

app = QApplication(sys.argv)
from ensayos.gui.main_window import MainWindow  # noqa: E402

w = MainWindow(db_path=DB)
hw = w._hardware
serie = hw._relay_serial
print("hardware:", serie, "| ESP32:", hw._esp32 and hw._esp32.port)

# Perfil corto: 20 s, una muestra cada 5 s
w._config_repo.save_timings(tiempo_ensayo_consumo=20, tiempo_ensayo_consumo_unidad="Segundos",
                            tiempo_entre_muestras=5, tiempo_entre_muestras_unidad="Segundos")
idx = next(i for i, p in enumerate(w.consumption_tab._products) if p.modelo == "Soldador 40W")
w.combo_productos_consumo.setCurrentIndex(idx)
w.input_nro_serie_consumo.setText("SN-PERFIL-001")
antes = len(w._consumo_repo.list_all())

print("\n=== Perfil de consumo (20 s, cada 5 s) ===")
t0 = time.time()
w.boton_ensayar_consumo.click()
relés_durante, ticks = [], set()
while not w.boton_ensayar_consumo.isEnabled() and time.time() - t0 < 60:
    app.processEvents()
    if int(time.time() - t0) % 3 == 0:
        relés_durante.append(hw.relay.get_state(serie))
    ticks.add((w.label_tiempo_muestra.text(), w.label_fin_ensayo.text()))
    time.sleep(0.1)
app.processEvents()
dur = time.time() - t0
nuevas = w._consumo_repo.list_all()[: len(w._consumo_repo.list_all()) - antes]
print(f"duró {dur:.1f} s | muestras guardadas: {len(nuevas)} | estado relés durante: "
      f"{sorted(set(relés_durante))} | al final: {hw.relay.get_state(serie)}")
for r in reversed(nuevas):
    print(f"  ensayo {r['n_ensayo']} muestra {r['n_muestra']}: {r['tension']} V, {r['corriente']} A, "
          f"{r['potencia_ac']} W, FP {r['fp']}, fuga {r['cdf']} µA, {r['hora']}")
print("puntos en el gráfico de potencia:", w.consumption_tab._plots["potencia"].point_count())
print("valores en vivo:", {n: getattr(w, n).text() for n in (
    "label_ensayo_actual", "label_muestra_actual", "label_tension_consumo",
    "label_corriente_consumo", "label_fp_consumo", "label_potencia_activa_consumo",
    "label_fuga_activa_consumo")})
print("cuentas regresivas vistas (ejemplos):", sorted(ticks)[:4])
print("filas en la tabla de Consumo:", w.tabla_historial_consumo.rowCount(),
      "| en Historial:", w.tabla_historial_consumo_2.rowCount())

print("\n=== PARADA a los 8 s ===")
t0 = time.time()
w.boton_ensayar_consumo.click()
while time.time() - t0 < 8:
    app.processEvents(); time.sleep(0.05)
w.boton_parada_consumo.click()
while not w.boton_ensayar_consumo.isEnabled() and time.time() - t0 < 30:
    app.processEvents(); time.sleep(0.05)
print(f"se detuvo a los {time.time() - t0:.1f} s | muestras: {w.label_muestra_actual.text()} | "
      f"relés: {hw.relay.get_state(serie)}")

print("\n=== Buscar por serie ===")
w.input_nro_serie_consumo.setText("SN-PERFIL-001")
w.boton_buscar_muestras.click()
print("filas filtradas:", w.tabla_historial_consumo.rowCount())

print("\n=== Exportar a carpeta (como un pendrive) ===")
w.boton_exportar_externo.click()
print("archivos:", os.listdir(OUTDIR), "| diálogo:", dialogos[-1])
from openpyxl import load_workbook  # noqa: E402

wb = load_workbook(os.path.join(OUTDIR, os.listdir(OUTDIR)[0]))
print({ws.title: ws.max_row - 1 for ws in wb.worksheets}, "filas de datos por hoja")

print("\n=== Mail sin SMTP configurado ===")
w.input_mail_1.setText("prueba@ejemplo.com")
w.boton_exportar_mail.click()
print("diálogo:", dialogos[-1])

w.close()
app.processEvents()
print("\nrelés al cerrar:", hw.relay.get_state(serie))

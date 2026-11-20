"""Prueba de punta a punta (sin energizar): GUI, pestañas, productos y base de datos.

Abre la ventana principal real (con el hardware real) en modo offscreen, maneja los
widgets como lo haría el operario y verifica lo que queda guardado en la base.
"""

import os
import sqlite3
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox, QPushButton  # noqa: E402

DB = sys.argv[1]
if os.path.exists(DB):
    os.remove(DB)

resultados: list[tuple[bool, str, str]] = []


def check(ok: bool, nombre: str, detalle: str = "") -> None:
    resultados.append((bool(ok), nombre, detalle))
    print(("OK   " if ok else "FALLA"), nombre, ("— " + detalle) if detalle else "")


# Los diálogos modales se aceptan solos y se registran
dialogos: list[str] = []
QMessageBox.warning = staticmethod(lambda *a, **k: dialogos.append(f"warning: {a[2]}"))
QMessageBox.critical = staticmethod(lambda *a, **k: dialogos.append(f"critical: {a[2]}"))
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)

app = QApplication(sys.argv)
from ensayos.gui.main_window import MainWindow  # noqa: E402
from ensayos.models.enums import ApplianceType  # noqa: E402

w = MainWindow(db_path=DB)
w.show()
app.processEvents()

# --- arranque y hardware
hw = w._hardware
check(hw._relay_serial == "BITFT", "GUI detecta la placa de relés", str(hw._relay_serial))
check(hw._esp32 is not None and hw._esp32.is_connected, "GUI conecta la ESP32",
      getattr(hw._esp32, "port", None) or "")

# --- pestañas
titles = [w.tabWidget.tabText(i).strip() for i in range(w.tabWidget.count())]
check(titles[0] == "Ensayos" and "Productos" in titles, "Pestañas de la ventana", ", ".join(titles))

# --- botones sin lógica en las pestañas heredadas
for nombre in ("boton_ensayar_consumo", "boton_ensayar_verificacion", "boton_guardar_configuraciones",
               "boton_valores_predeterminados", "boton_exportar_escritorio", "boton_exportar_mail",
               "boton_exportar_externo"):
    btn = w.findChild(QPushButton, nombre)
    conectado = btn is not None and btn.receivers(btn.clicked) > 0
    check(conectado, f"Botón '{btn.text() if btn else nombre}' conectado", nombre)

# --- alta de producto desde el formulario
f = w.product_form
f.input_marca.setText("Bancolab")
f.input_modelo.setText("Soldador-40")
f.input_descripcion.setText("Soldador de prueba")
f.input_potencia.setValue(40)
f.input_tension.setValue(220)
f.input_corriente.setValue(0.18)
f.combo_clase.setCurrentIndex(0)
f.check_cable.setChecked(True)
f.combo_tipo.setCurrentIndex(0)
QTest.mouseClick(f.boton_agregar, Qt.LeftButton)
app.processEvents()

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
rows = con.execute("SELECT * FROM productos").fetchall()
check(len(rows) == 1 and rows[0]["marca"] == "Bancolab", "Alta de producto guardada en la base",
      dict(rows[0]) and f"{rows[0]['marca']} {rows[0]['modelo']}, {rows[0]['potencia']} W" if rows else "")
check(w.test_panel.lista_productos.count() == 1, "Producto nuevo aparece en Ensayos",
      f"{w.test_panel.lista_productos.count()} en la lista")

# --- validación: alta sin marca/modelo
n_dialogos = len(dialogos)
f.input_marca.setText("")
QTest.mouseClick(f.boton_agregar, Qt.LeftButton)
check(len(dialogos) == n_dialogos + 1 and con.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 1,
      "Rechaza producto sin marca", dialogos[-1] if dialogos else "")

# --- edición
f.lista_productos.setCurrentRow(0)
app.processEvents()
check(f.input_marca.text() == "Bancolab", "Seleccionar producto carga el formulario", f.input_marca.text())
f.input_potencia.setValue(38)
f.combo_tipo.setCurrentIndex(1)  # Motor
f.check_fuga_duplicada.setChecked(True)
QTest.mouseClick(f.boton_editar, Qt.LeftButton)
row = con.execute("SELECT potencia, tipo_aparato, fuga_pasiva_duplicada FROM productos").fetchone()
check(row["potencia"] == 38 and row["tipo_aparato"] == ApplianceType.MOTOR.value
      and row["fuga_pasiva_duplicada"] == 1, "Edición guardada (potencia, tipo, fuga duplicada)",
      dict(row).__repr__())

# --- segundo producto y baja
f.input_marca.setText("Bancolab"); f.input_modelo.setText("Borrar-me")
QTest.mouseClick(f.boton_agregar, Qt.LeftButton)
f.lista_productos.setCurrentRow(1)
QTest.mouseClick(f.boton_eliminar, Qt.LeftButton)
modelos = [r[0] for r in con.execute("SELECT modelo FROM productos")]
check(modelos == ["Soldador-40"], "Baja de producto", ", ".join(modelos))

# --- búsqueda
f.input_buscar.setText("solda")
visibles = [f.lista_productos.item(i).text() for i in range(f.lista_productos.count())
            if not f.lista_productos.item(i).isHidden()]
check(len(visibles) == 1, "Búsqueda de productos", ", ".join(visibles))

# --- persistencia: reabrir la base
con.close()
from ensayos.database.sqlite_repository import SQLiteProductRepository  # noqa: E402

p = SQLiteProductRepository(DB).list_all()
check(len(p) == 1 and p[0].potencia == 38, "Persistencia tras reabrir la base",
      f"{p[0].marca} {p[0].modelo} {p[0].potencia} W {p[0].tipo_aparato.value}" if p else "")

w.close()
app.processEvents()
check(hw._esp32 is None or not hw._esp32.is_connected, "Cerrar la ventana libera la ESP32")
print("DIALOGOS:", dialogos)
print("RESUMEN:", sum(r[0] for r in resultados), "/", len(resultados))

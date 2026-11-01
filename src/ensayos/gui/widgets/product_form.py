"""Widget de ABM (Alta-Baja-Modificación) de productos."""

import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ensayos.database.sqlite_repository import SQLiteProductRepository
from ensayos.models.enums import DeviceClass
from ensayos.models.product import Product

logger = logging.getLogger(__name__)


class ProductForm(QWidget):
    """Widget para gestionar productos (agregar, editar, eliminar).

    Emite ``products_changed`` cuando la lista de productos se modifica,
    para que la ventana principal actualice sus listas.
    """

    products_changed = pyqtSignal()

    def __init__(self, product_repo: SQLiteProductRepository, parent=None):
        super().__init__(parent)
        self._repo = product_repo
        self._selected_product: Product | None = None
        self._setup_ui()
        self._connect_signals()
        self.refresh_list()

    # ── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Búsqueda
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Buscar producto...")
        layout.addWidget(self.input_buscar)

        # Lista
        self.lista_productos = QListWidget()
        layout.addWidget(self.lista_productos)

        # Campos de edición
        form = QVBoxLayout()

        self.input_marca = QLineEdit()
        self.input_marca.setPlaceholderText("Marca")
        form.addWidget(QLabel("Marca"))
        form.addWidget(self.input_marca)

        self.input_modelo = QLineEdit()
        self.input_modelo.setPlaceholderText("Modelo")
        form.addWidget(QLabel("Modelo"))
        form.addWidget(self.input_modelo)

        self.input_descripcion = QLineEdit()
        self.input_descripcion.setPlaceholderText("Descripción")
        form.addWidget(QLabel("Descripción"))
        form.addWidget(self.input_descripcion)

        row_specs = QHBoxLayout()

        self.input_potencia = QDoubleSpinBox()
        self.input_potencia.setMaximum(99999)
        self.input_potencia.setSuffix(" W")
        row_specs.addWidget(QLabel("Potencia"))
        row_specs.addWidget(self.input_potencia)

        self.input_tension = QDoubleSpinBox()
        self.input_tension.setMaximum(99999)
        self.input_tension.setSuffix(" V")
        row_specs.addWidget(QLabel("Tensión"))
        row_specs.addWidget(self.input_tension)

        self.input_corriente = QDoubleSpinBox()
        self.input_corriente.setMaximum(99999)
        self.input_corriente.setDecimals(3)
        self.input_corriente.setSuffix(" A")
        row_specs.addWidget(QLabel("Corriente"))
        row_specs.addWidget(self.input_corriente)

        form.addLayout(row_specs)

        row_extra = QHBoxLayout()

        self.input_frecuencia = QSpinBox()
        self.input_frecuencia.setMaximum(400)
        self.input_frecuencia.setValue(50)
        self.input_frecuencia.setSuffix(" Hz")
        row_extra.addWidget(QLabel("Frecuencia"))
        row_extra.addWidget(self.input_frecuencia)

        self.combo_clase = QComboBox()
        self.combo_clase.addItems(["Clase 1", "Clase 2"])
        row_extra.addWidget(QLabel("Clase"))
        row_extra.addWidget(self.combo_clase)

        self.check_fuga_duplicada = QCheckBox("Límite de fuga pasiva duplicado")
        self.check_fuga_duplicada.setToolTip(
            "IEC 60335-1, 16.2: marcar solo si el aparato cumple alguna condición:\n"
            "- todos los controles tienen posición de apagado en todos los polos;\n"
            "- no tiene más control que un protector térmico;\n"
            "- ningún termostato, limitador o regulador tiene posición de apagado;\n"
            "- tiene filtros de interferencia de radio."
        )
        row_extra.addWidget(self.check_fuga_duplicada)

        self.check_cable = QCheckBox("Cable de alimentación fijo")
        self.check_cable.setChecked(True)
        self.check_cable.setToolTip(
            "IEC 60335-1, A.1: con cable fijo la PAT se mide desde la ficha (límite 200 mΩ).\n"
            "Sin cable fijo (borne o ficha de aparato), el límite es 100 mΩ."
        )
        row_extra.addWidget(self.check_cable)

        form.addLayout(row_extra)
        layout.addLayout(form)

        # Botones
        btn_row = QHBoxLayout()
        self.boton_agregar = QPushButton("Agregar")
        self.boton_editar = QPushButton("Editar")
        self.boton_editar.setEnabled(False)
        self.boton_eliminar = QPushButton("Eliminar")
        self.boton_eliminar.setEnabled(False)
        btn_row.addWidget(self.boton_agregar)
        btn_row.addWidget(self.boton_editar)
        btn_row.addWidget(self.boton_eliminar)
        layout.addLayout(btn_row)

    def _connect_signals(self) -> None:
        self.lista_productos.currentRowChanged.connect(self._on_selection_changed)
        self.input_buscar.textChanged.connect(self._filtrar)
        self.boton_agregar.clicked.connect(self._agregar)
        self.boton_editar.clicked.connect(self._editar)
        self.boton_eliminar.clicked.connect(self._eliminar)

    # ── Lógica ────────────────────────────────────────────────────────

    def refresh_list(self) -> None:
        self.lista_productos.clear()
        self._products = self._repo.list_all()
        for p in self._products:
            self.lista_productos.addItem(f"{p.marca} - {p.modelo}")

    def _filtrar(self) -> None:
        filtro = self.input_buscar.text().lower()
        for i in range(self.lista_productos.count()):
            item = self.lista_productos.item(i)
            item.setHidden(filtro not in item.text().lower())

    def _on_selection_changed(self, row: int) -> None:
        if 0 <= row < len(self._products):
            self._selected_product = self._products[row]
            p = self._selected_product
            self.input_marca.setText(p.marca)
            self.input_modelo.setText(p.modelo)
            self.input_descripcion.setText(p.descripcion)
            self.input_potencia.setValue(p.potencia)
            self.input_tension.setValue(p.tension)
            self.input_corriente.setValue(p.corriente)
            self.input_frecuencia.setValue(int(p.frecuencia))
            self.combo_clase.setCurrentIndex(0 if p.clase == DeviceClass.CLASS_1 else 1)
            self.check_fuga_duplicada.setChecked(p.fuga_pasiva_duplicada)
            self.check_cable.setChecked(p.con_cable_alimentacion)
            self.boton_editar.setEnabled(True)
            self.boton_eliminar.setEnabled(True)
        else:
            self._selected_product = None
            self.boton_editar.setEnabled(False)
            self.boton_eliminar.setEnabled(False)

    def _read_form(self) -> Product:
        clase = DeviceClass.CLASS_1 if self.combo_clase.currentIndex() == 0 else DeviceClass.CLASS_2
        return Product(
            marca=self.input_marca.text().strip(),
            modelo=self.input_modelo.text().strip(),
            descripcion=self.input_descripcion.text().strip(),
            potencia=self.input_potencia.value(),
            tension=self.input_tension.value(),
            corriente=self.input_corriente.value(),
            frecuencia=float(self.input_frecuencia.value()),
            clase=clase,
            fuga_pasiva_duplicada=self.check_fuga_duplicada.isChecked(),
            con_cable_alimentacion=self.check_cable.isChecked(),
        )

    def _agregar(self) -> None:
        product = self._read_form()
        if not product.marca or not product.modelo:
            QMessageBox.warning(self, "Campos requeridos", "Marca y modelo son obligatorios.")
            return
        if self._repo.create(product):
            self.refresh_list()
            self.products_changed.emit()
        else:
            QMessageBox.critical(self, "Error", "No se pudo agregar el producto.")

    def _editar(self) -> None:
        if self._selected_product is None:
            return
        product = self._read_form()
        product.id = self._selected_product.id
        if self._repo.update(product):
            self.refresh_list()
            self.products_changed.emit()
        else:
            QMessageBox.critical(self, "Error", "No se pudo editar el producto.")

    def _eliminar(self) -> None:
        if self._selected_product is None:
            return
        reply = QMessageBox.question(
            self, "Confirmar", f"¿Eliminar {self._selected_product.marca} - {self._selected_product.modelo}?",
        )
        if reply == QMessageBox.Yes:
            self._repo.delete(self._selected_product.id)
            self.refresh_list()
            self.products_changed.emit()

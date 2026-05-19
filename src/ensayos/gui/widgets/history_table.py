"""Widgets de tablas de historial: FDL, consumo y verificación."""

import logging

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ensayos.database.sqlite_repository import (
    SQLiteConsumptionHistoryRepository,
    SQLiteFdlHistoryRepository,
    SQLiteVerificationHistoryRepository,
)

logger = logging.getLogger(__name__)

COLOR_OK = QColor(0, 180, 0)
COLOR_FAIL = QColor(220, 0, 0)

HEADERS_FDL = [
    "N.º", "Marca", "Modelo", "N.º Serie", "Fecha", "Hora",
    "Tensión (V)", "Corriente (A)", "FP", "Potencia (W)", "Consumo V.",
    "Fuga A. (μA)", "Fuga Activa V.", "Fuga P. (μA)", "Fuga Pasiva V.",
    "R. PAT (mΩ)", "PAT V.", "Rigidez D. V.",
]

HEADERS_CONSUMO = [
    "N.º Ensayo", "N.º Muestra", "Marca", "Modelo", "N.º Serie",
    "Fecha", "Hora", "Tensión (V)", "Corriente (A)", "FP",
    "Potencia (W)", "Fuga Activa (μA)",
]

HEADERS_VERIFICACION = [
    "ID", "Fecha", "Hora", "FUGA-PASA", "PAT-PASA", "RD-PASA",
    "FUGA-FALLA", "PAT-FALLA", "RD-FALLA",
]


class HistoryTableFdl(QWidget):
    """Tabla de historial de ensayos Final de Línea."""

    def __init__(self, fdl_repo: SQLiteFdlHistoryRepository, parent=None):
        super().__init__(parent)
        self._repo = fdl_repo
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Buscar en historial FDL...")
        self.input_buscar.textChanged.connect(self._filtrar)
        layout.addWidget(self.input_buscar)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(HEADERS_FDL))
        self.tabla.setHorizontalHeaderLabels(HEADERS_FDL)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla)

    def refresh(self) -> None:
        rows = self._repo.list_all()
        self.tabla.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                row.get("id", ""),
                row.get("marca", ""),
                row.get("producto", ""),
                row.get("serial", ""),
                row.get("fecha", ""),
                row.get("hora", ""),
                row.get("tension", ""),
                row.get("a_medida", ""),
                row.get("fp", ""),
                row.get("w_medida", ""),
                row.get("consumo", ""),
                row.get("fuga_medida", ""),
                row.get("fuga", ""),
                row.get("cn_medido", ""),
                row.get("cn", ""),
                row.get("pat_medida", ""),
                row.get("pat", ""),
                row.get("resistida", ""),
            ]
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                # Colorear veredictos
                val_str = str(val).strip().upper()
                if val_str == "OK":
                    item.setForeground(QBrush(COLOR_OK))
                elif val_str == "FALLA":
                    item.setForeground(QBrush(COLOR_FAIL))
                self.tabla.setItem(i, j, item)

    def _filtrar(self) -> None:
        filtro = self.input_buscar.text().lower()
        for i in range(self.tabla.rowCount()):
            match = False
            for j in range(self.tabla.columnCount()):
                item = self.tabla.item(i, j)
                if item and filtro in item.text().lower():
                    match = True
                    break
            self.tabla.setRowHidden(i, not match)


class HistoryTableConsumo(QWidget):
    """Tabla de historial de ensayos de consumo."""

    def __init__(self, consumo_repo: SQLiteConsumptionHistoryRepository, parent=None):
        super().__init__(parent)
        self._repo = consumo_repo
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Buscar en historial consumo...")
        self.input_buscar.textChanged.connect(self._filtrar)
        row.addWidget(self.input_buscar)

        self.boton_buscar = QPushButton("Buscar")
        self.boton_buscar.clicked.connect(self._buscar_avanzado)
        row.addWidget(self.boton_buscar)

        self.boton_reset = QPushButton("Reset")
        self.boton_reset.clicked.connect(self.refresh)
        row.addWidget(self.boton_reset)

        layout.addLayout(row)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(HEADERS_CONSUMO))
        self.tabla.setHorizontalHeaderLabels(HEADERS_CONSUMO)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla)

    def refresh(self) -> None:
        rows = self._repo.list_all()
        self._populate(rows)

    def _populate(self, rows: list[dict]) -> None:
        self.tabla.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                row.get("n_ensayo", ""),
                row.get("n_muestra", ""),
                row.get("marca", ""),
                row.get("modelo", ""),
                row.get("nro_serial", ""),
                row.get("fecha", ""),
                row.get("hora", ""),
                row.get("tension", ""),
                row.get("corriente", ""),
                row.get("fp", ""),
                row.get("potencia_ac", ""),
                row.get("cdf", ""),
            ]
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.tabla.setItem(i, j, item)

    def _filtrar(self) -> None:
        filtro = self.input_buscar.text().lower()
        for i in range(self.tabla.rowCount()):
            match = False
            for j in range(self.tabla.columnCount()):
                item = self.tabla.item(i, j)
                if item and filtro in item.text().lower():
                    match = True
                    break
            self.tabla.setRowHidden(i, not match)

    def _buscar_avanzado(self) -> None:
        query = self.input_buscar.text().strip()
        if query:
            rows = self._repo.search(query=query)
            self._populate(rows)
        else:
            self.refresh()


class HistoryTableVerificacion(QWidget):
    """Tabla de historial de verificación."""

    def __init__(self, verif_repo: SQLiteVerificationHistoryRepository, parent=None):
        super().__init__(parent)
        self._repo = verif_repo
        self._setup_ui()
        self.refresh()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(len(HEADERS_VERIFICACION))
        self.tabla.setHorizontalHeaderLabels(HEADERS_VERIFICACION)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla)

    def refresh(self) -> None:
        rows = self._repo.list_all()
        self.tabla.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                row.get("id", ""),
                row.get("fecha", ""),
                row.get("hora", ""),
                row.get("fuga_pasa", ""),
                row.get("pat_pasa", ""),
                row.get("rd_pasa", ""),
                row.get("fuga_falla", ""),
                row.get("pat_falla", ""),
                row.get("rd_falla", ""),
            ]
            for j, val in enumerate(values):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                self.tabla.setItem(i, j, item)

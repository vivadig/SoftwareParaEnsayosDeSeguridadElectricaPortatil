"""Ventana principal de la aplicación de ensayos de seguridad eléctrica.

Carga el interfaz desde el archivo .ui de FDL y conecta la lógica de negocio.
Las pestañas "Ensayos" y "Productos" del .ui se reemplazan por los paneles
TestPanel y ProductForm, que tienen la lógica (y los campos de producto que
eligen los límites de IEC 60335-1).
"""

import logging
from pathlib import Path

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QWidget

from ensayos.config.config_database import database_config
from ensayos.config.config_gui import gui_config
from ensayos.database.schemas import initialize_database
from ensayos.database.sqlite_repository import (
    SQLiteConfigRepository,
    SQLiteConsumptionHistoryRepository,
    SQLiteFdlHistoryRepository,
    SQLiteProductRepository,
    SQLiteVerificationHistoryRepository,
)
from ensayos.gui.widgets.live_plot_widget import LivePlotWidget
from ensayos.gui.widgets.product_form import ProductForm
from ensayos.gui.widgets.test_panel import TestPanel
from ensayos.hardware.hardware_manager import HardwareManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Ventana principal que carga el UI desde archivo .ui de FDL."""

    def __init__(self, db_path: str | None = None):
        super().__init__()

        # Cargar UI desde archivo con widgets custom
        ui_path = Path(__file__).parent / "resources" / "gui_c12_s0.ui"
        custom_widgets = {"LivePlotWidget": LivePlotWidget}
        uic.loadUi(str(ui_path), self, custom_widgets)

        # Inicializar base de datos
        db = db_path or database_config.path
        initialize_database(db)

        # Repositorios
        self._product_repo = SQLiteProductRepository(db)
        self._fdl_repo = SQLiteFdlHistoryRepository(db)
        self._consumo_repo = SQLiteConsumptionHistoryRepository(db)
        self._verif_repo = SQLiteVerificationHistoryRepository(db)
        self._config_repo = SQLiteConfigRepository(db)

        # Hardware - Inicializar y detectar dispositivos
        self._hardware = HardwareManager()
        self._hardware.initialize()

        # Paneles con la lógica de ensayos y de productos
        self._integrate_panels()

        # Conectar signals
        self._connect_signals()

        logger.info("MainWindow inicializada desde UI file")

    def _connect_signals(self) -> None:
        """Conecta los signals del UI a los slots correspondientes."""
        # Cargar datos en tablas
        self._load_tables()

        # Productos nuevos o editados aparecen en el panel de ensayos
        self.product_form.products_changed.connect(self.test_panel.refresh_products)
        # Al terminar un ensayo, TestPanel guarda el historial (se conectó primero)
        # y después se recargan las tablas
        self.test_panel.signals.all_completed.connect(lambda _results: self._load_tables())

        # Conexiones básicas de menú
        try:
            # Buscar la acción Salir en el menú
            for action in self.findChildren(type(self.menuBar().addAction(""))):
                if action.text() == "Salir":
                    action.triggered.connect(self.close)
        except Exception as e:
            logger.debug(f"No se pudo conectar acción Salir: {e}")

    def _integrate_panels(self) -> None:
        """Reemplaza las pestañas "Ensayos" y "Productos" del .ui por los paneles con lógica."""
        self.test_panel = TestPanel(
            self._hardware, self._product_repo, self._fdl_repo, self._config_repo
        )
        self.product_form = ProductForm(self._product_repo)
        self._replace_tab(self.tab, self.test_panel)
        self._replace_tab(self.tab_3, self.product_form)
        self.tabWidget.setCurrentWidget(self.test_panel)

    def _replace_tab(self, old: QWidget, new: QWidget) -> None:
        """Reemplaza una pestaña del .ui por otro widget, en la misma posición y título.

        Args:
            old: Página de la pestaña original.
            new: Widget que la reemplaza.
        """
        index = self.tabWidget.indexOf(old)
        title = self.tabWidget.tabText(index)
        self.tabWidget.removeTab(index)
        self.tabWidget.insertTab(index, new, title)
        old.deleteLater()

    def _load_tables(self) -> None:
        """Carga los datos de las tablas desde la BD."""
        try:
            # Tabla historial FDL
            if hasattr(self, 'tabla_historial_fdl'):
                fdl_data = self._fdl_repo.list_all()
                rows = [[d.get(k) for k in ['id', 'marca', 'producto', 'serial', 'fecha', 'hora', 'tension', 'A_medida', 'fp', 'W_medida', 'consumo', 'fuga_medida', 'fuga', 'cn_medido', 'cn', 'pat_medida', 'pat', 'resistida']] for d in fdl_data]
                self._populate_table(
                    self.tabla_historial_fdl,
                    rows,
                    ["ID", "Marca", "Producto", "Serial", "Fecha", "Hora", "Tensión", "A Medida", "FP", "W Medida", "Consumo", "Fuga Medida", "Fuga", "CN Medido", "CN", "PAT Medida", "PAT", "Resistida"]
                )
        except Exception as e:
            logger.debug(f"Error cargando tabla historial FDL: {e}")

        try:
            # Tabla historial verificación
            if hasattr(self, 'tabla_historial_verificacion'):
                verif_data = self._verif_repo.list_all()
                rows = [[d.get(k) for k in ['id', 'fecha', 'hora', 'fuga_pasa', 'pat_pasa', 'rd_pasa', 'fuga_falla', 'pat_falla', 'rd_falla']] for d in verif_data]
                self._populate_table(
                    self.tabla_historial_verificacion,
                    rows,
                    ["ID", "Fecha", "Hora", "Fuga Pasa", "PAT Pasa", "RD Pasa", "Fuga Falla", "PAT Falla", "RD Falla"]
                )
        except Exception as e:
            logger.debug(f"Error cargando tabla verificación: {e}")

        try:
            # Tabla historial consumo
            if hasattr(self, 'tabla_historial_consumo'):
                consumo_data = self._consumo_repo.list_all()
                rows = [[d.get(k) for k in ['id', 'n_ensayo', 'n_muestra', 'marca', 'modelo', 'nro_serial', 'fecha', 'hora', 'tension', 'corriente', 'fp', 'potencia_ac', 'cdf']] for d in consumo_data]
                self._populate_table(
                    self.tabla_historial_consumo,
                    rows,
                    ["ID", "N Ensayo", "N Muestra", "Marca", "Modelo", "Serial", "Fecha", "Hora", "Tensión", "Corriente", "FP", "Potencia AC", "CDF"]
                )
        except Exception as e:
            logger.debug(f"Error cargando tabla consumo: {e}")

    def _populate_table(self, table_widget, data, headers) -> None:
        """Popula un QTableWidget con datos."""
        table_widget.setColumnCount(len(headers))
        table_widget.setHorizontalHeaderLabels(headers)
        table_widget.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(str(value) if value is not None else "")
                table_widget.setItem(row_idx, col_idx, item)

        table_widget.resizeColumnsToContents()

    def closeEvent(self, event) -> None:
        """Maneja el cierre de la ventana."""
        try:
            self._hardware.shutdown()
        except Exception:
            logger.exception("Error al apagar hardware")
        event.accept()

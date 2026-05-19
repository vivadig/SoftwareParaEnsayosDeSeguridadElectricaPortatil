"""Ventana principal de la aplicación de ensayos de seguridad eléctrica.

Carga el interfaz desde el archivo .ui de FDL y conecta la lógica de negocio.
"""

import logging
from pathlib import Path

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QTableWidgetItem, QListWidgetItem
from PyQt5.QtCore import QCoreApplication, Qt

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

        # Conectar signals
        self._connect_signals()

        logger.info("MainWindow inicializada desde UI file")

    def _connect_signals(self) -> None:
        """Conecta los signals del UI a los slots correspondientes."""
        # Cargar datos en tablas
        self._load_tables()

        # Cargar productos
        self._load_products()

        # Conectar búsqueda de productos
        if hasattr(self, 'boton_buscar_muestras'):
            self.boton_buscar_muestras.clicked.connect(self._search_products)
        if hasattr(self, 'boton_buscar_productos'):
            self.boton_buscar_productos.clicked.connect(self._search_products)

        # Conexiones básicas de menú
        try:
            # Buscar la acción Salir en el menú
            for action in self.findChildren(type(self.menuBar().addAction(""))):
                if action.text() == "Salir":
                    action.triggered.connect(self.close)
        except Exception as e:
            logger.debug(f"No se pudo conectar acción Salir: {e}")

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

    def _load_products(self) -> None:
        """Carga la lista de productos en la interfaz."""
        try:
            products = self._product_repo.list_all()
            logger.info(f"Cargando {len(products)} productos")

            # Cargar en ambas listas (tab Ensayos y tab Productos)
            for list_widget_name in ['lista_productos_fdl', 'lista_productos']:
                if hasattr(self, list_widget_name):
                    list_widget = getattr(self, list_widget_name)
                    list_widget.clear()
                    for product in products:
                        display_text = f"{product.marca} - {product.modelo} ({product.potencia}W)"
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.UserRole, product)
                        list_widget.addItem(item)
                    logger.info(f"✓ Productos cargados en {list_widget_name}")
                else:
                    logger.warning(f"{list_widget_name} no encontrada en el UI")
        except Exception as e:
            logger.exception(f"Error cargando productos: {e}")

    def _search_products(self) -> None:
        """Busca productos por texto."""
        try:
            # Buscar en lista_productos_fdl (tab Ensayos) usando input_buscar_muestras
            if hasattr(self, 'input_buscar_muestras') and hasattr(self, 'lista_productos_fdl'):
                search_text = self.input_buscar_muestras.text().lower()
                all_products = self._product_repo.list_all()
                self.lista_productos_fdl.clear()

                for product in all_products:
                    display_text = f"{product.marca} - {product.modelo} ({product.potencia}W)"
                    if search_text in display_text.lower():
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.UserRole, product)
                        self.lista_productos_fdl.addItem(item)

            # Buscar en lista_productos (tab Productos) usando input_buscar_productos
            if hasattr(self, 'input_buscar_productos') and hasattr(self, 'lista_productos'):
                search_text = self.input_buscar_productos.text().lower()
                all_products = self._product_repo.list_all()
                self.lista_productos.clear()

                for product in all_products:
                    display_text = f"{product.marca} - {product.modelo} ({product.potencia}W)"
                    if search_text in display_text.lower():
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.UserRole, product)
                        self.lista_productos.addItem(item)
        except Exception as e:
            logger.debug(f"Error buscando productos: {e}")

    def closeEvent(self, event) -> None:
        """Maneja el cierre de la ventana."""
        try:
            self._hardware.shutdown()
        except Exception:
            logger.exception("Error al apagar hardware")
        event.accept()

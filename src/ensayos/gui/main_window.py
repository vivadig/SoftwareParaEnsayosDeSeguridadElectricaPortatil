"""Ventana principal de la aplicación de ensayos de seguridad eléctrica.

Carga el interfaz desde el archivo .ui de FDL y conecta la lógica de negocio.
Las pestañas "Ensayos" y "Productos" del .ui se reemplazan por los paneles
TestPanel y ProductForm, que tienen la lógica (y los campos de producto que
eligen los límites de IEC 60335-1). Las pestañas "Consumo" y "Exportar" usan
los widgets del .ui, conectados por ConsumptionTab y ExportTab.
"""

import logging
from pathlib import Path

from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QWidget

from ensayos.config.config_database import database_config
from ensayos.database.schemas import initialize_database
from ensayos.database.sqlite_repository import (
    SQLiteConfigRepository,
    SQLiteConsumptionHistoryRepository,
    SQLiteFdlHistoryRepository,
    SQLiteProductRepository,
    SQLiteVerificationHistoryRepository,
)
from ensayos.gui.consumption_tab import ConsumptionTab
from ensayos.gui.export_tab import ExportTab
from ensayos.gui.login_dialog import LoginDialog
from ensayos.gui.settings_tab import SettingsTab
from ensayos.gui.verification_tab import VerificationTab
from ensayos.gui.widgets.product_form import ProductForm
from ensayos.gui.widgets.test_panel import TestPanel
from ensayos.hardware.hardware_manager import HardwareManager

logger = logging.getLogger(__name__)


def _format_cell(value: object) -> str:
    """Texto de una celda del historial: números con más de 3 decimales se redondean.

    Los registros viejos guardaron floats sin redondear (por ejemplo 227.95999999999998).
    """
    if value is None:
        return ""
    text = str(value)
    try:
        number = float(text)
    except ValueError:
        return text
    if "." in text and len(text.split(".")[1]) > 3:
        return f"{number:.3f}"
    return text


class MainWindow(QMainWindow):
    """Ventana principal que carga el UI desde archivo .ui de FDL."""

    def __init__(self, db_path: str | None = None):
        super().__init__()

        # Cargar UI desde archivo (los gráficos son LivePlotWidget de pglive, según el .ui)
        ui_path = Path(__file__).parent / "resources" / "gui_c12_s0.ui"
        uic.loadUi(str(ui_path), self)

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

        # Pestañas Consumo (perfil de consumo) y Exportar
        self.consumption_tab = ConsumptionTab(
            self,
            self._hardware,
            self._product_repo,
            self._consumo_repo,
            self._config_repo,
            on_samples_changed=self._load_consumption_table,
        )
        self.export_tab = ExportTab(self, db)

        # Pestañas Configuraciones y Verificación
        self.settings_tab = SettingsTab(self, self._config_repo, on_saved=self._apply_settings)
        self.verification_tab = VerificationTab(
            self, self._hardware, self._config_repo, self._verif_repo, on_saved=self._load_tables
        )
        self._login_window = None

        # Conectar signals
        self._connect_signals()

        logger.info("MainWindow inicializada desde UI file")

    def _connect_signals(self) -> None:
        """Conecta los signals del UI a los slots correspondientes."""
        # Cargar datos en tablas
        self._load_tables()

        # Productos nuevos o editados aparecen en el panel de ensayos y en Consumo
        self.product_form.products_changed.connect(self.test_panel.refresh_products)
        self.product_form.products_changed.connect(self.consumption_tab.refresh_products)
        # Al terminar un ensayo, TestPanel guarda el historial (se conectó primero)
        # y después se recargan las tablas
        self.test_panel.signals.all_completed.connect(lambda _results: self._load_tables())

        # Menú Archivo: Administración (patrones de verificación y contraseña) y Salir
        self.menuArchivo.clear()
        self.action_administracion = self.menuArchivo.addAction("Administración…")
        self.action_administracion.triggered.connect(self.open_admin)
        self.menuArchivo.addSeparator()
        self.menuArchivo.addAction("Salir").triggered.connect(self.close)

    def open_admin(self) -> None:
        """Abre el login de administración (y, con la clave correcta, el panel)."""
        self._login_window = LoginDialog(self._config_repo)
        self._login_window.show()

    def _apply_settings(self, mode: str, repetitions: int, wait_seconds: float) -> None:
        """Aplica lo guardado en Configuraciones al panel de ensayos.

        Args:
            mode: "fdl", "ciclico" o "consumo".
            repetitions: Repeticiones del modo cíclico.
            wait_seconds: Espera entre ciclos (s).
        """
        self.test_panel.apply_mode(mode == "ciclico", repetitions, wait_seconds)
        if mode == "consumo":
            self.tabWidget.setCurrentWidget(self.tab_7)

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
            if hasattr(self, "tabla_historial_fdl"):
                fdl_data = self._fdl_repo.list_all()
                rows = [
                    [
                        d.get(k)
                        for k in [
                            "id",
                            "marca",
                            "producto",
                            "serial",
                            "fecha",
                            "hora",
                            "tension",
                            "a_medida",
                            "fp",
                            "w_medida",
                            "consumo",
                            "fuga_medida",
                            "fuga",
                            "cn_medido",
                            "cn",
                            "pat_medida",
                            "pat",
                            "resistida",
                        ]
                    ]
                    for d in fdl_data
                ]
                self._populate_table(
                    self.tabla_historial_fdl,
                    rows,
                    [
                        "ID",
                        "Marca",
                        "Producto",
                        "Serial",
                        "Fecha",
                        "Hora",
                        "Tensión",
                        "A Medida",
                        "FP",
                        "W Medida",
                        "Consumo",
                        "Fuga Medida",
                        "Fuga",
                        "CN Medido",
                        "CN",
                        "PAT Medida",
                        "PAT",
                        "Resistida",
                    ],
                )
        except Exception as e:
            logger.debug(f"Error cargando tabla historial FDL: {e}")

        try:
            # Tabla historial verificación
            if hasattr(self, "tabla_historial_verificacion"):
                verif_data = self._verif_repo.list_all()
                rows = [
                    [
                        d.get(k)
                        for k in [
                            "id",
                            "fecha",
                            "hora",
                            "fuga_pasa",
                            "pat_pasa",
                            "rd_pasa",
                            "fuga_falla",
                            "pat_falla",
                            "rd_falla",
                        ]
                    ]
                    for d in verif_data
                ]
                self._populate_table(
                    self.tabla_historial_verificacion,
                    rows,
                    [
                        "ID",
                        "Fecha",
                        "Hora",
                        "Fuga Pasa",
                        "PAT Pasa",
                        "RD Pasa",
                        "Fuga Falla",
                        "PAT Falla",
                        "RD Falla",
                    ],
                )
        except Exception as e:
            logger.debug(f"Error cargando tabla verificación: {e}")

        self._load_consumption_table()

    _CONSUMPTION_COLUMNS = (
        ("n_ensayo", "N.º Ensayo"),
        ("n_muestra", "N.º Muestra"),
        ("marca", "Marca"),
        ("modelo", "Modelo"),
        ("nro_serial", "Serie"),
        ("fecha", "Fecha"),
        ("hora", "Hora"),
        ("tension", "Tensión (V)"),
        ("corriente", "Corriente (A)"),
        ("fp", "FP"),
        ("potencia_ac", "Potencia (W)"),
        ("cdf", "Fuga activa (µA)"),
    )

    def _load_consumption_table(self) -> None:
        """Recarga el historial de consumo (pestañas Consumo e Historial)."""
        try:
            self.show_consumption_rows(self._consumo_repo.list_all())
        except Exception as e:
            logger.debug(f"Error cargando tabla consumo: {e}")

    def show_consumption_rows(self, consumo_data: list[dict]) -> None:
        """Muestra filas del historial de consumo en las tablas de Consumo e Historial.

        Args:
            consumo_data: Filas de la tabla ensayos_consumo.
        """
        keys = [k for k, _ in self._CONSUMPTION_COLUMNS]
        headers = [h for _, h in self._CONSUMPTION_COLUMNS]
        rows = [[d.get(k) for k in keys] for d in consumo_data]
        for name in ("tabla_historial_consumo", "tabla_historial_consumo_2"):
            if hasattr(self, name):
                self._populate_table(getattr(self, name), rows, headers)

    def _populate_table(self, table_widget, data, headers) -> None:
        """Popula un QTableWidget con datos."""
        table_widget.setColumnCount(len(headers))
        table_widget.setHorizontalHeaderLabels(headers)
        table_widget.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(_format_cell(value))
                table_widget.setItem(row_idx, col_idx, item)

        table_widget.resizeColumnsToContents()

    def closeEvent(self, event) -> None:
        """Maneja el cierre de la ventana: detiene el ensayo en curso y apaga el hardware."""
        for panel in (self.test_panel, self.consumption_tab, self.verification_tab):
            try:
                panel.stop_and_wait()
            except Exception:
                logger.exception("Error al detener el ensayo en curso")
        try:
            self._hardware.shutdown()
        except Exception:
            logger.exception("Error al apagar hardware")
        event.accept()

"""Panel de ensayos: selección de tests, ejecución y visualización de resultados."""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ensayos.database.sqlite_repository import (
    SQLiteConfigRepository,
    SQLiteFdlHistoryRepository,
    SQLiteProductRepository,
)
from ensayos.engine.test_runner import TestRunner
from ensayos.gui.styles import (
    BUTTON_ACTIVE,
    BUTTON_NORMAL,
    PROGRESS_BAR_GREEN,
    PROGRESS_BAR_NORMAL,
    PROGRESS_BAR_RED,
)
from ensayos.hardware.hardware_manager import HardwareManager
from ensayos.models.enums import DeviceClass, TestMode, TestType, TimeUnit, Verdict
from ensayos.models.product import Product
from ensayos.models.test_result import FdlTestRecord, TestResult

logger = logging.getLogger(__name__)


class TestSignals(QObject):
    """Señales unificadas para comunicación thread → GUI."""

    test_state_changed = pyqtSignal(str, object)  # (evento, datos)
    progress_updated = pyqtSignal(str, int)  # (test_type, porcentaje)
    measurement_updated = pyqtSignal(str, object)  # (test_type, measurement)
    verdict_updated = pyqtSignal(str, str)  # (test_type, verdict)
    all_completed = pyqtSignal(list)  # lista de TestResult
    error = pyqtSignal(str)


class TestPanel(QWidget):
    """Panel principal de ensayos FDL con selección de tests y resultados.

    Es un thin shell que delega toda la lógica al TestRunner.
    """

    def __init__(
        self,
        hardware: HardwareManager,
        product_repo: SQLiteProductRepository,
        fdl_repo: SQLiteFdlHistoryRepository,
        config_repo: SQLiteConfigRepository,
        parent=None,
    ):
        super().__init__(parent)
        self._hardware = hardware
        self._product_repo = product_repo
        self._fdl_repo = fdl_repo
        self._config_repo = config_repo
        self._selected_product: Product | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._runner: TestRunner | None = None

        self.signals = TestSignals()
        self._setup_ui()
        self._connect_signals()
        self.refresh_products()

    # ── UI ────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Selección de producto
        prod_row = QHBoxLayout()
        self.input_buscar = QLineEdit()
        self.input_buscar.setPlaceholderText("Buscar producto...")
        prod_row.addWidget(self.input_buscar)
        layout.addLayout(prod_row)

        self.lista_productos = QListWidget()
        layout.addWidget(self.lista_productos)

        # Info del producto seleccionado
        info_row = QHBoxLayout()
        self.label_marca = QLabel("-")
        self.label_modelo = QLabel("-")
        self.label_clase = QLabel("-")
        self.label_potencia = QLabel("-")
        self.label_tension = QLabel("-")
        self.label_corriente = QLabel("-")
        for lbl_name, lbl in [
            ("Marca:", self.label_marca), ("Modelo:", self.label_modelo),
            ("Clase:", self.label_clase), ("W:", self.label_potencia),
            ("V:", self.label_tension), ("A:", self.label_corriente),
        ]:
            info_row.addWidget(QLabel(lbl_name))
            info_row.addWidget(lbl)
        layout.addLayout(info_row)

        # Serial
        serial_row = QHBoxLayout()
        serial_row.addWidget(QLabel("N.º Serie:"))
        self.input_serial = QLineEdit()
        serial_row.addWidget(self.input_serial)
        layout.addLayout(serial_row)

        # Botones de ensayo (toggle)
        btn_row = QHBoxLayout()
        self._test_buttons: dict[TestType, QPushButton] = {}
        for tt in TestType:
            btn = QPushButton(tt.value.replace("_", " ").title())
            btn.setStyleSheet(BUTTON_ACTIVE)
            btn.setCheckable(False)
            btn.clicked.connect(self._make_toggle(btn))
            self._test_buttons[tt] = btn
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        # Modo de ensayo
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Modo:"))
        self.combo_modo = QComboBox()
        self.combo_modo.addItems(["Final de Línea", "Cíclico"])
        mode_row.addWidget(self.combo_modo)

        mode_row.addWidget(QLabel("Repeticiones:"))
        self.spin_repeticiones = QSpinBox()
        self.spin_repeticiones.setMinimum(1)
        self.spin_repeticiones.setMaximum(9999)
        self.spin_repeticiones.setValue(1)
        mode_row.addWidget(self.spin_repeticiones)

        mode_row.addWidget(QLabel("Espera:"))
        self.spin_espera = QSpinBox()
        self.spin_espera.setMinimum(0)
        self.spin_espera.setMaximum(99999)
        self.spin_espera.setValue(0)
        mode_row.addWidget(self.spin_espera)

        self.combo_unidad_espera = QComboBox()
        self.combo_unidad_espera.addItems(["Segundos", "Minutos", "Horas"])
        mode_row.addWidget(self.combo_unidad_espera)
        layout.addLayout(mode_row)

        # Barras de progreso por ensayo
        self.progress_bars: dict[str, QProgressBar] = {}
        self.labels_medicion: dict[str, QLabel] = {}
        self.labels_veredicto: dict[str, QLabel] = {}

        for tt in TestType:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{tt.value.replace('_', ' ').title()}:"))

            pb = QProgressBar()
            pb.setMaximum(100)
            pb.setStyleSheet(PROGRESS_BAR_NORMAL)
            self.progress_bars[tt.value] = pb
            row.addWidget(pb)

            lbl_med = QLabel("-")
            lbl_med.setMinimumWidth(80)
            lbl_med.setAlignment(Qt.AlignCenter)
            self.labels_medicion[tt.value] = lbl_med
            row.addWidget(lbl_med)

            lbl_ver = QLabel("-")
            lbl_ver.setMinimumWidth(60)
            lbl_ver.setAlignment(Qt.AlignCenter)
            self.labels_veredicto[tt.value] = lbl_ver
            row.addWidget(lbl_ver)

            layout.addLayout(row)

        # Progreso general
        self.progress_general = QProgressBar()
        self.progress_general.setMaximum(100)
        layout.addWidget(self.progress_general)

        # Botones de acción
        action_row = QHBoxLayout()
        self.boton_ensayar = QPushButton("ENSAYAR")
        self.boton_ensayar.setEnabled(False)
        self.boton_ensayar.setMinimumHeight(40)
        action_row.addWidget(self.boton_ensayar)

        self.boton_parada = QPushButton("PARADA")
        self.boton_parada.setMinimumHeight(40)
        self.boton_parada.setEnabled(False)
        action_row.addWidget(self.boton_parada)

        # Contador de ensayos
        self.label_ensayos_hechos = QLabel("0")
        action_row.addWidget(QLabel("Hechos:"))
        action_row.addWidget(self.label_ensayos_hechos)

        layout.addLayout(action_row)

    def _connect_signals(self) -> None:
        self.input_buscar.textChanged.connect(self._filtrar_productos)
        self.lista_productos.currentRowChanged.connect(self._on_product_selected)
        self.boton_ensayar.clicked.connect(self._iniciar_ensayo)
        self.boton_parada.clicked.connect(self._detener_ensayo)
        self.combo_modo.currentIndexChanged.connect(self._on_mode_changed)

        # Señales thread → GUI
        self.signals.progress_updated.connect(self._on_progress)
        self.signals.measurement_updated.connect(self._on_measurement)
        self.signals.verdict_updated.connect(self._on_verdict)
        self.signals.all_completed.connect(self._on_all_completed)
        self.signals.error.connect(self._on_error)

    # ── Productos ─────────────────────────────────────────────────────

    def refresh_products(self) -> None:
        self.lista_productos.clear()
        self._products = self._product_repo.list_all()
        for p in self._products:
            self.lista_productos.addItem(f"{p.marca} - {p.modelo}")

    def _filtrar_productos(self) -> None:
        filtro = self.input_buscar.text().lower()
        for i in range(self.lista_productos.count()):
            item = self.lista_productos.item(i)
            item.setHidden(filtro not in item.text().lower())

    def _on_product_selected(self, row: int) -> None:
        if 0 <= row < len(self._products):
            p = self._products[row]
            self._selected_product = p
            self.label_marca.setText(p.marca)
            self.label_modelo.setText(p.modelo)
            self.label_clase.setText("Clase 1" if p.clase == DeviceClass.CLASS_1 else "Clase 2")
            self.label_potencia.setText(str(p.potencia))
            self.label_tension.setText(str(p.tension))
            self.label_corriente.setText(str(p.corriente))
            self.boton_ensayar.setEnabled(True)

            # Clase 2: deshabilitar fuga activa, pasiva y PAT
            if p.clase == DeviceClass.CLASS_2:
                for tt in (TestType.ACTIVE_LEAKAGE, TestType.PASSIVE_LEAKAGE, TestType.GROUNDING):
                    self._test_buttons[tt].setEnabled(False)
                    self._test_buttons[tt].setStyleSheet(BUTTON_NORMAL)
            else:
                for tt in (TestType.ACTIVE_LEAKAGE, TestType.PASSIVE_LEAKAGE, TestType.GROUNDING):
                    self._test_buttons[tt].setEnabled(True)
                    self._test_buttons[tt].setStyleSheet(BUTTON_ACTIVE)

    def _on_mode_changed(self, idx: int) -> None:
        is_cyclic = idx == 1
        self.spin_repeticiones.setEnabled(is_cyclic)
        self.spin_espera.setEnabled(is_cyclic)
        self.combo_unidad_espera.setEnabled(is_cyclic)

    # ── Toggle botones ────────────────────────────────────────────────

    def _make_toggle(self, btn: QPushButton):
        def toggle():
            if btn.styleSheet() == BUTTON_NORMAL:
                btn.setStyleSheet(BUTTON_ACTIVE)
            else:
                btn.setStyleSheet(BUTTON_NORMAL)
        return toggle

    def _get_selected_tests(self) -> list[TestType]:
        selected = []
        for tt, btn in self._test_buttons.items():
            if btn.styleSheet() == BUTTON_ACTIVE and btn.isEnabled():
                selected.append(tt)
        return selected

    # ── Ensayo ────────────────────────────────────────────────────────

    def _iniciar_ensayo(self) -> None:
        if self._selected_product is None:
            return

        selected = self._get_selected_tests()
        if not selected:
            QMessageBox.warning(self, "Sin ensayos", "Seleccione al menos un ensayo.")
            return

        self._limpiar_resultados()
        self._set_ui_running(True)

        from threading import Event
        cancel = Event()

        self._runner = TestRunner(
            hardware=self._hardware,
            cancel_token=cancel,
            on_test_started=self._cb_test_started,
            on_test_completed=self._cb_test_completed,
            on_progress=self._cb_progress,
            on_measurement=self._cb_measurement,
            on_all_completed=self._cb_all_completed,
            on_cycle_completed=self._cb_cycle_completed,
        )

        is_cyclic = self.combo_modo.currentIndex() == 1
        product = self._selected_product

        if is_cyclic:
            unit = TimeUnit(self.combo_unidad_espera.currentText())
            wait_secs = unit.to_seconds(self.spin_espera.value())
            self._executor.submit(
                self._runner.run_cyclic,
                selected, product, self.spin_repeticiones.value(), wait_secs,
            )
        else:
            self._executor.submit(self._runner.run_end_of_line, selected, product)

    def _detener_ensayo(self) -> None:
        if self._runner:
            self._runner.stop()

    def _set_ui_running(self, running: bool) -> None:
        self.boton_ensayar.setEnabled(not running)
        self.boton_parada.setEnabled(running)
        self.lista_productos.setEnabled(not running)
        self.input_buscar.setEnabled(not running)
        self.input_serial.setEnabled(not running)
        for btn in self._test_buttons.values():
            btn.setEnabled(not running)
        if not running:
            self.progress_general.setRange(0, 100)
            self.progress_general.setValue(0)

    def _limpiar_resultados(self) -> None:
        for tt in TestType:
            self.progress_bars[tt.value].setValue(0)
            self.progress_bars[tt.value].setStyleSheet(PROGRESS_BAR_NORMAL)
            self.labels_medicion[tt.value].setText("-")
            self.labels_veredicto[tt.value].setText("-")
            self.labels_veredicto[tt.value].setStyleSheet("")

    # ── Callbacks del TestRunner (se ejecutan en worker thread) ───────

    def _cb_test_started(self, test_type: TestType) -> None:
        self.signals.test_state_changed.emit("started", test_type.value)

    def _cb_test_completed(self, result: TestResult) -> None:
        verdict_str = result.verdict.value
        self.signals.verdict_updated.emit(result.test_type.value, verdict_str)

        # Extraer valor de medición para el label
        measurement = result.measurement
        if measurement is not None:
            from ensayos.models.measurement import (
                ConsumptionMeasurement,
                DielectricMeasurement,
                GroundingMeasurement,
                LeakageMeasurement,
            )

            if isinstance(measurement, ConsumptionMeasurement):
                text = f"{measurement.power_w:.1f} W"
            elif isinstance(measurement, LeakageMeasurement):
                text = f"{measurement.leakage_ua:.1f} μA"
            elif isinstance(measurement, GroundingMeasurement):
                text = f"{measurement.resistance_mohm:.1f} mΩ / {measurement.current_a:.1f} A"
            elif isinstance(measurement, DielectricMeasurement):
                text = f"{measurement.voltage:.0f} V / {measurement.current_ma:.2f} mA"
            else:
                text = str(measurement)
            self.signals.measurement_updated.emit(result.test_type.value, text)

    def _cb_progress(self, elapsed: int, total: int) -> None:
        if total > 0:
            pct = int(elapsed * 100 / total)
            self.signals.progress_updated.emit("general", pct)

    def _cb_measurement(self, *args) -> None:
        pass  # Las mediciones en tiempo real se manejan vía on_test_completed

    def _cb_all_completed(self, results: list[TestResult]) -> None:
        self.signals.all_completed.emit(results)

    def _cb_cycle_completed(self, current: int, total: int) -> None:
        self.signals.test_state_changed.emit("cycle", (current, total))

    # ── Slots (se ejecutan en GUI thread) ─────────────────────────────

    def _on_progress(self, key: str, pct: int) -> None:
        if key == "general":
            self.progress_general.setValue(pct)
        elif key in self.progress_bars:
            self.progress_bars[key].setValue(pct)

    def _on_measurement(self, key: str, text) -> None:
        if key in self.labels_medicion:
            self.labels_medicion[key].setText(str(text))

    def _on_verdict(self, key: str, verdict: str) -> None:
        if key in self.labels_veredicto:
            self.labels_veredicto[key].setText(verdict)
            if verdict == Verdict.OK.value:
                self.progress_bars[key].setStyleSheet(PROGRESS_BAR_GREEN)
                self.labels_veredicto[key].setStyleSheet("color: green; font-weight: bold;")
            elif verdict == Verdict.FAIL.value:
                self.progress_bars[key].setStyleSheet(PROGRESS_BAR_RED)
                self.labels_veredicto[key].setStyleSheet("color: red; font-weight: bold;")

    def _on_all_completed(self, results: list[TestResult]) -> None:
        self._set_ui_running(False)
        self._guardar_historial(results)

        # Actualizar contador
        count = int(self.label_ensayos_hechos.text()) + 1
        self.label_ensayos_hechos.setText(str(count))

    def _on_error(self, msg: str) -> None:
        self._set_ui_running(False)
        QMessageBox.critical(self, "Error de ensayo", msg)

    # ── Persistencia ──────────────────────────────────────────────────

    def _guardar_historial(self, results: list[TestResult]) -> None:
        if not self._selected_product:
            return

        p = self._selected_product
        record = FdlTestRecord(
            marca=p.marca,
            modelo=p.modelo,
            serial=self.input_serial.text().strip(),
            fecha=time.strftime("%d/%m/%Y"),
            hora=time.strftime("%H:%M:%S"),
        )

        for r in results:
            m = r.measurement
            if r.test_type == TestType.CONSUMPTION and m is not None:
                from ensayos.models.measurement import ConsumptionMeasurement
                if isinstance(m, ConsumptionMeasurement):
                    record.tension = m.voltage_v
                    record.corriente = m.current_a
                    record.factor_potencia = m.power_factor
                    record.potencia = m.power_w
                record.veredicto_consumo = r.verdict
            elif r.test_type == TestType.ACTIVE_LEAKAGE:
                if m is not None:
                    from ensayos.models.measurement import LeakageMeasurement
                    if isinstance(m, LeakageMeasurement):
                        record.fuga_activa_medida = m.leakage_ua
                record.veredicto_fuga_activa = r.verdict
            elif r.test_type == TestType.PASSIVE_LEAKAGE:
                if m is not None:
                    from ensayos.models.measurement import LeakageMeasurement
                    if isinstance(m, LeakageMeasurement):
                        record.fuga_pasiva_medida = m.leakage_ua
                record.veredicto_fuga_pasiva = r.verdict
            elif r.test_type == TestType.GROUNDING:
                if m is not None:
                    from ensayos.models.measurement import GroundingMeasurement
                    if isinstance(m, GroundingMeasurement):
                        record.pat_medida = m.resistance_mohm
                record.veredicto_pat = r.verdict
            elif r.test_type == TestType.DIELECTRIC:
                if m is not None:
                    from ensayos.models.measurement import DielectricMeasurement
                    if isinstance(m, DielectricMeasurement):
                        record.rigidez_medida = m.current_ma
                record.veredicto_rigidez = r.verdict

        self._fdl_repo.save(record)

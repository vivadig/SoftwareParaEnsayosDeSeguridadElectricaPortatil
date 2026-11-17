"""Lógica de la pestaña "Verificación" de la ventana principal.

Guía al operario para ensayar los dos patrones (de a uno) y muestra, para cada uno,
la medición, el valor del patrón y si la comprobación se cumple.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QWidget

from ensayos.config.config_tests import tests_config
from ensayos.config.timings import config_with_timings
from ensayos.database.sqlite_repository import (
    SQLiteConfigRepository,
    SQLiteVerificationHistoryRepository,
)
from ensayos.engine.test_runner import TestRunner
from ensayos.engine.verification import (
    PATTERNS,
    UNITS,
    VERIFICATION_TESTS,
    PatternCheck,
    check_pattern,
    missing_patterns,
    pattern_product,
)
from ensayos.hardware.hardware_manager import HardwareManager

logger = logging.getLogger(__name__)

STYLE_OK = "background-color: #2e7d32; color: white; font-weight: bold;"
STYLE_FAIL = "background-color: #c62828; color: white; font-weight: bold;"
# Etiquetas de unidad de rigidez del .ui heredado (decían V; se evalúa la corriente)
RD_UNIT_LABELS = ("label_280", "label_281", "label_294", "label_295")


class _Signals(QObject):
    pattern_done = pyqtSignal(int, object, object)  # (patrón, resultados, excepción)
    status = pyqtSignal(str)


class VerificationTab:
    """Controlador de la pestaña Verificación.

    Args:
        window: Ventana principal (tiene los widgets del .ui como atributos).
        hardware: Fachada de hardware compartida.
        config_repo: Repositorio de configuración (valores de los patrones y tiempos).
        verif_repo: Repositorio del historial de verificación.
        on_saved: Se llama al guardar una verificación (para recargar el historial).
    """

    def __init__(
        self,
        window: QWidget,
        hardware: HardwareManager,
        config_repo: SQLiteConfigRepository,
        verif_repo: SQLiteVerificationHistoryRepository,
        on_saved=None,
    ):
        self.w = window
        self._hardware = hardware
        self._config_repo = config_repo
        self._verif_repo = verif_repo
        self._on_saved = on_saved or (lambda: None)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._runner: TestRunner | None = None
        self._patterns: dict = {}
        self._checks: dict[int, list[PatternCheck]] = {}
        self._stopped = False
        self.signals = _Signals()
        self.signals.pattern_done.connect(self._on_pattern_done)
        self.signals.status.connect(self.w.label_estado_verificacion.setText)

        for name in RD_UNIT_LABELS:
            if hasattr(self.w, name):
                getattr(self.w, name).setText(UNITS["rd"])
        self.w.boton_ensayar_verificacion.clicked.connect(self.start)
        self.w.boton_parada_verificacion.clicked.connect(self.stop)
        self.w.boton_parada_verificacion.setEnabled(False)
        self.w.label_fecha_verificacion.setText(time.strftime("%d/%m/%Y"))
        self.w.label_estado_verificacion.setText("Preparado.")

    # ── Flujo ─────────────────────────────────────────────────────────

    def start(self) -> None:
        """Inicia la verificación: pide conectar el patrón 1."""
        self._patterns = self._config_repo.get_verification_patterns()
        missing = missing_patterns(self._patterns)
        if missing:
            QMessageBox.warning(
                self.w,
                "Patrones sin cargar",
                "Faltan los valores de: "
                + ", ".join(missing)
                + ".\n\nCargarlos en Archivo → Administración.",
            )
            return
        if not self._hardware.try_acquire_session():
            QMessageBox.warning(self.w, "Hardware ocupado", "Hay otro ensayo en curso.")
            return
        self._stopped = False
        self._checks = {}
        self._clear()
        self._show_line_voltage()
        self._set_running(True)
        self._ask_and_run(1)

    def _ask_and_run(self, pattern: int) -> None:
        suffix, expected = PATTERNS[pattern]
        texto = "debe PASAR" if pattern == 1 else "debe FALLAR"
        self.w.label_estado_verificacion.setText(f"Conecte el patrón {pattern} ({texto}).")
        answer = QMessageBox.question(
            self.w,
            f"Patrón {pattern}",
            f"Conecte el PATRÓN {pattern} ({texto}) en el lugar del aparato a ensayar "
            "y presione Aceptar.\n\nNo toque el patrón ni los cables durante el ensayo.",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if answer != QMessageBox.Ok:
            self._finish("Verificación cancelada.")
            return
        self.signals.status.emit(f"Ensayando el patrón {pattern}...")
        self._runner = TestRunner(
            hardware=self._hardware,
            on_test_started=lambda tt, p=pattern: self.signals.status.emit(
                f"Patrón {p}: {tt.value.replace('_', ' ')}..."
            ),
            config=config_with_timings(self._config_repo.get_timings()),
        )
        future = self._executor.submit(
            self._runner.run_end_of_line, list(VERIFICATION_TESTS), pattern_product(pattern)
        )
        future.add_done_callback(
            lambda f, p=pattern: self.signals.pattern_done.emit(
                p, None if f.exception() else f.result(), f.exception()
            )
        )

    def _on_pattern_done(self, pattern: int, results, exc) -> None:
        if exc is not None:
            logger.error("Error en la verificación: %s", exc, exc_info=exc)
            ok = self._safe_relays_off()
            msg = f"{type(exc).__name__}: {exc}"
            if not ok:
                msg += "\n\n¡No se pudo confirmar el apagado de los relés: cortar la red!"
            QMessageBox.critical(self.w, "Error en la verificación", msg)
            self._finish("Error en la verificación.")
            return
        if self._stopped:
            self._finish("Verificación detenida.")
            return
        suffix, _ = PATTERNS[pattern]
        tol = tests_config.verification.tolerance_pct
        checks = [
            check_pattern(
                r,
                pattern,
                float(self._patterns.get(f"{VERIFICATION_TESTS[r.test_type]}_{suffix}") or 0),
                tol,
            )
            for r in results
            if r.test_type in VERIFICATION_TESTS
        ]
        self._checks[pattern] = checks
        self._show(checks)
        if pattern == 1:
            self._ask_and_run(2)
            return
        self._save()
        all_checks = self._checks[1] + self._checks[2]
        if all(c.ok for c in all_checks):
            self._finish("Verificación APROBADA.")
        else:
            failed = [f"patrón {c.pattern} {c.key}: {c.reason}" for c in all_checks if not c.ok]
            self._finish("Verificación NO APROBADA.")
            QMessageBox.warning(self.w, "Verificación no aprobada", "\n".join(failed))

    def stop(self) -> None:
        """Detiene la verificación en curso."""
        self._stopped = True
        if self._runner:
            self._runner.stop()

    def stop_and_wait(self) -> None:
        """Detiene la verificación y espera al hilo (al cerrar la ventana)."""
        self.stop()
        self._executor.shutdown(wait=True, cancel_futures=True)

    def _finish(self, status: str) -> None:
        self.w.label_estado_verificacion.setText(status)
        self._set_running(False)
        self._hardware.release_session()

    def _safe_relays_off(self) -> bool:
        try:
            return self._hardware.deactivate_all_relays()
        except Exception:
            logger.exception("No se pudieron apagar los relés.")
            return False

    # ── GUI ───────────────────────────────────────────────────────────

    def _set_running(self, running: bool) -> None:
        self.w.boton_ensayar_verificacion.setEnabled(not running)
        self.w.boton_parada_verificacion.setEnabled(running)

    def _show_line_voltage(self) -> None:
        try:
            reading = self._hardware.read_pzem(self._hardware._cfg.pzem.consumption)
        except Exception:
            reading = None
        voltage = getattr(reading, "voltage", None)
        self.w.label_tension_verificacion.setText(
            f"{voltage:.1f}" if isinstance(voltage, int | float) else "-"
        )

    def _clear(self) -> None:
        self.w.label_fecha_verificacion.setText(time.strftime("%d/%m/%Y"))
        for suffix, _ in PATTERNS.values():
            for key in VERIFICATION_TESTS.values():
                getattr(self.w, f"label_{key}_medicion_{suffix}").setText("-")
                getattr(self.w, f"label_{key}_patron_{suffix}").setText("-")
                getattr(self.w, f"frame_{key}_veredicto_{suffix}").setStyleSheet("")

    def _show(self, checks: list[PatternCheck]) -> None:
        for c in checks:
            suffix, _ = PATTERNS[c.pattern]
            measured = "-" if c.measured is None else f"{c.measured:.1f}"
            getattr(self.w, f"label_{c.key}_medicion_{suffix}").setText(measured)
            getattr(self.w, f"label_{c.key}_patron_{suffix}").setText(f"{c.reference:.1f}")
            frame = getattr(self.w, f"frame_{c.key}_veredicto_{suffix}")
            frame.setStyleSheet(STYLE_OK if c.ok else STYLE_FAIL)
            frame.setToolTip(c.reason)

    def _save(self) -> None:
        values = {}
        for pattern, checks in self._checks.items():
            suffix, _ = PATTERNS[pattern]
            for c in checks:
                values[f"{c.key}_{suffix}"] = c.measured
        self._verif_repo.save(
            fecha=time.strftime("%d/%m/%Y"),
            hora=time.strftime("%H:%M:%S"),
            fuga_pasa=values.get("fuga_pasa"),
            pat_pasa=values.get("pat_pasa"),
            rd_pasa=values.get("rd_pasa"),
            fuga_falla=values.get("fuga_falla"),
            pat_falla=values.get("pat_falla"),
            rd_falla=values.get("rd_falla"),
        )
        self._on_saved()

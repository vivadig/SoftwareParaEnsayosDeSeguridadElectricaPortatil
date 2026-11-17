"""Lógica de la pestaña "Consumo" (perfil de consumo) de la ventana principal.

Conecta los widgets del .ui (combo de producto, serie, botones, gráficos y etiquetas)
con ConsumptionProfile, que corre en un hilo aparte.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox, QWidget

from ensayos.config.config_tests import tests_config
from ensayos.database.sqlite_repository import (
    SQLiteConfigRepository,
    SQLiteConsumptionHistoryRepository,
    SQLiteProductRepository,
)
from ensayos.engine.consumption_profile import ConsumptionProfile, ProfileTick
from ensayos.gui.widgets.live_plot_widget import PlotSeries
from ensayos.hardware.hardware_manager import HardwareManager
from ensayos.models.enums import TimeUnit
from ensayos.models.test_result import ConsumptionSample

logger = logging.getLogger(__name__)

# Valores por defecto de la tabla "tiempos" si la base no los tiene
DEFAULT_DURATION_S = 60
DEFAULT_INTERVAL_S = 5


class _Signals(QObject):
    """Señales hilo de ensayo → GUI."""

    sample = pyqtSignal(object)  # ConsumptionSample
    tick = pyqtSignal(object)  # ProfileTick
    error = pyqtSignal(str)
    finished = pyqtSignal()


def _seconds(timings: dict, value_key: str, unit_key: str, default: float) -> float:
    """Convierte un tiempo de la tabla "tiempos" (valor + unidad) a segundos."""
    value = timings.get(value_key)
    if value is None:
        return default
    try:
        return TimeUnit(timings.get(unit_key) or TimeUnit.SECONDS.value).to_seconds(float(value))
    except ValueError:
        return float(value)


class ConsumptionTab:
    """Controlador de la pestaña Consumo.

    Args:
        window: Ventana principal (tiene los widgets del .ui como atributos).
        hardware: Fachada de hardware compartida con el panel de ensayos.
        product_repo: Repositorio de productos.
        consumo_repo: Repositorio del historial de consumo.
        config_repo: Repositorio de configuración (tiempos del perfil).
        on_samples_changed: Se llama cuando hay muestras nuevas (para recargar tablas).
    """

    def __init__(
        self,
        window: QWidget,
        hardware: HardwareManager,
        product_repo: SQLiteProductRepository,
        consumo_repo: SQLiteConsumptionHistoryRepository,
        config_repo: SQLiteConfigRepository,
        on_samples_changed=None,
    ):
        self.w = window
        self._hardware = hardware
        self._product_repo = product_repo
        self._consumo_repo = consumo_repo
        self._config_repo = config_repo
        self._on_samples_changed = on_samples_changed or (lambda: None)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._profile: ConsumptionProfile | None = None
        self._products = []
        self._elapsed_s = 0.0
        self.signals = _Signals()

        self._plots = {
            "potencia": PlotSeries(self.w.grafico_potencia, "Potencia activa", "W"),
            "corriente": PlotSeries(self.w.grafico_corriente, "Corriente", "A"),
            "tension": PlotSeries(self.w.grafico_tension, "Tensión", "V"),
            "fuga_activa": PlotSeries(self.w.grafico_fuga, "Fuga activa", "µA"),
        }

        self.w.boton_ensayar_consumo.clicked.connect(self.start)
        self.w.boton_parada_consumo.clicked.connect(self.stop)
        self.w.boton_reset_muestras.clicked.connect(self.reset)
        self.w.boton_buscar_muestras.clicked.connect(self.search)
        self.signals.sample.connect(self._on_sample)
        self.signals.tick.connect(self._on_tick)
        self.signals.error.connect(self._on_error)
        self.signals.finished.connect(self._on_finished)

        self.w.boton_parada_consumo.setEnabled(False)
        self.refresh_products()

    # ── Productos ─────────────────────────────────────────────────────

    def refresh_products(self) -> None:
        """Recarga el combo de productos."""
        combo = self.w.combo_productos_consumo
        combo.clear()
        self._products = self._product_repo.list_all()
        for p in self._products:
            combo.addItem(f"{p.marca} - {p.modelo}")

    def _selected_product(self):
        idx = self.w.combo_productos_consumo.currentIndex()
        return self._products[idx] if 0 <= idx < len(self._products) else None

    # ── Ensayo ────────────────────────────────────────────────────────

    def durations(self) -> tuple[float, float]:
        """Duración del perfil y tiempo entre muestras (s), de la tabla "tiempos"."""
        timings = self._config_repo.get_timings()
        duration = _seconds(
            timings, "tiempo_ensayo_consumo", "tiempo_ensayo_consumo_unidad", DEFAULT_DURATION_S
        )
        interval = _seconds(
            timings, "tiempo_entre_muestras", "tiempo_entre_muestras_unidad", DEFAULT_INTERVAL_S
        )
        return duration, interval

    def start(self) -> None:
        """Inicia un perfil de consumo con el producto y la serie elegidos."""
        product = self._selected_product()
        if product is None:
            QMessageBox.warning(self.w, "Sin producto", "Seleccione un producto.")
            return
        duration, interval = self.durations()
        if interval <= 0 or duration < interval:
            QMessageBox.warning(
                self.w,
                "Tiempos inválidos",
                "La duración del ensayo debe ser mayor o igual al tiempo entre muestras.",
            )
            return
        if not self._hardware.try_acquire_session():
            QMessageBox.warning(self.w, "Hardware ocupado", "Hay otro ensayo en curso.")
            return

        self.reset()
        test_number = self._consumo_repo.next_test_number()
        self._profile = ConsumptionProfile(
            self._hardware,
            product,
            serial=self.w.input_nro_serie_consumo.text().strip(),
            test_number=test_number,
            duration_s=duration,
            interval_s=interval,
            settle_s=tests_config.durations.consumption_profile_settle,
            cancel_token=Event(),
            on_sample=self._save_and_emit,
            on_tick=self.signals.tick.emit,
        )
        self.w.label_ensayo_actual.setText(str(test_number))
        self._set_running(True)
        future = self._executor.submit(self._profile.run)
        future.add_done_callback(self._on_future_done)

    def _save_and_emit(self, sample: ConsumptionSample) -> None:
        """En el hilo de ensayo: guarda la muestra y avisa a la GUI."""
        if not self._consumo_repo.save(sample):
            logger.error("No se pudo guardar la muestra %d.", sample.n_muestra)
        self.signals.sample.emit(sample)

    def _on_future_done(self, future) -> None:
        """En el hilo de ensayo: informa el error (si hubo) y libera el hardware."""
        exc = future.exception() if not future.cancelled() else None
        if exc is not None:
            logger.error("El perfil de consumo terminó con error: %s", exc, exc_info=exc)
            try:
                ok = self._hardware.deactivate_all_relays()
            except Exception:
                ok = False
            msg = f"{type(exc).__name__}: {exc}"
            if not ok:
                msg += "\n\n¡No se pudo confirmar el apagado de los relés: cortar la red!"
            self.signals.error.emit(msg)
        self._hardware.release_session()
        self.signals.finished.emit()

    def stop(self) -> None:
        """Detiene el perfil en curso."""
        if self._profile:
            self._profile.stop()

    def stop_and_wait(self) -> None:
        """Detiene el perfil y espera al hilo (al cerrar la ventana)."""
        self.stop()
        self._executor.shutdown(wait=True, cancel_futures=True)

    # ── GUI ───────────────────────────────────────────────────────────

    def _set_running(self, running: bool) -> None:
        self.w.boton_ensayar_consumo.setEnabled(not running)
        self.w.boton_reset_muestras.setEnabled(not running)
        self.w.combo_productos_consumo.setEnabled(not running)
        self.w.input_nro_serie_consumo.setEnabled(not running)
        self.w.boton_parada_consumo.setEnabled(running)

    def _on_sample(self, sample: ConsumptionSample) -> None:
        x = self._elapsed_s
        values = {
            "potencia": sample.potencia,
            "corriente": sample.corriente,
            "tension": sample.tension,
            "fuga_activa": sample.fuga_activa,
        }
        for key, series in self._plots.items():
            series.add_point(x, values[key])
        self.w.label_muestra_actual.setText(str(sample.n_muestra))
        self.w.label_tension_consumo.setText(f"{sample.tension:.1f}")
        self.w.label_corriente_consumo.setText(f"{sample.corriente:.3f}")
        self.w.label_fp_consumo.setText(f"{sample.factor_potencia:.2f}")
        self.w.label_potencia_activa_consumo.setText(f"{sample.potencia:.1f}")
        self.w.label_fuga_activa_consumo.setText(f"{sample.fuga_activa:.1f}")
        self._on_samples_changed()

    def _on_tick(self, tick: ProfileTick) -> None:
        if self._profile:
            self._elapsed_s = self._profile.duration_s - tick.seconds_to_end
        self.w.label_tiempo_muestra.setText(f"{tick.seconds_to_next_sample:.0f} s")
        self.w.label_fin_ensayo.setText(f"{tick.seconds_to_end:.0f} s")

    def _on_error(self, msg: str) -> None:
        QMessageBox.critical(self.w, "Error en el ensayo de consumo", msg)

    def _on_finished(self) -> None:
        self._set_running(False)
        self.w.label_tiempo_muestra.setText("-")
        self.w.label_fin_ensayo.setText("-")
        self._on_samples_changed()

    def reset(self) -> None:
        """Borra los gráficos y los valores en vivo (no toca el historial guardado)."""
        for series in self._plots.values():
            series.clear()
        self._elapsed_s = 0.0
        for name in (
            "label_muestra_actual",
            "label_ensayo_actual",
            "label_tension_consumo",
            "label_corriente_consumo",
            "label_fp_consumo",
            "label_potencia_activa_consumo",
            "label_fuga_activa_consumo",
            "label_tiempo_muestra",
            "label_fin_ensayo",
        ):
            getattr(self.w, name).setText("-")

    def search(self) -> None:
        """Filtra la tabla del historial de consumo por serie o, si no hay, por producto."""
        query = self.w.input_nro_serie_consumo.text().strip()
        if not query:
            product = self._selected_product()
            query = product.modelo if product else ""
        rows = self._consumo_repo.search(query=query or None)
        self.w.show_consumption_rows(rows)

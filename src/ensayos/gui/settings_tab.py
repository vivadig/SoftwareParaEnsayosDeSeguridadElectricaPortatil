"""Lógica de la pestaña "Configuraciones" de la ventana principal.

Edita la tabla "tiempos" de la base: duración de cada ensayo, cantidad de repeticiones
y espera del modo cíclico, y duración y período de muestreo del perfil de consumo.
"""

import logging

from PyQt5.QtWidgets import QMessageBox, QWidget

from ensayos.config.timings import to_seconds
from ensayos.database.sqlite_repository import SQLiteConfigRepository

logger = logging.getLogger(__name__)

# Campo de la tabla "tiempos" → (spinbox, combo de unidad) del .ui
FIELDS = {
    "consumo": ("spinbox_tiempo_func", "combo_magnitud_func_fdl"),
    "fuga_activa": ("spinbox_tiempo_fuga_activa", "combo_magnitud_fuga_activa_fdl"),
    "fuga_pasiva": ("spinbox_tiempo_fuga_pasiva", "combo_magnitud_fuga_pasiva_fdl"),
    "pat": ("spinbox_tiempo_r_pat", "combo_magnitud_r_pat_fdl"),
    "rigidez": ("spinbox_tiempo_rigidez_dielectrica", "combo_magnitud_rigidez_dielectrica_fdl"),
    "tiempo_entre_ensayos": ("spinbox_tiempo_entre_ensayos", "combo_magnitud_entre_ensayos"),
    "tiempo_ensayo_consumo": ("spinbox_tiempo_consumo", "combo_magnitud_consumo"),
    "tiempo_entre_muestras": ("spinbox_tiempo_muestras", "combo_magnitud_muestras"),
}

# Valores de fábrica (los mismos que crea la base)
DEFAULTS = {
    "consumo": (5, "Segundos"),
    "fuga_activa": (5, "Segundos"),
    "fuga_pasiva": (5, "Segundos"),
    "pat": (5, "Segundos"),
    "rigidez": (5, "Segundos"),
    "tiempo_entre_ensayos": (1, "Segundos"),
    "tiempo_ensayo_consumo": (60, "Segundos"),
    "tiempo_entre_muestras": (5, "Segundos"),
}
DEFAULT_CYCLES = 1


def _columns(field: str) -> tuple[str, str]:
    """Columnas de valor y de unidad de un campo en la tabla "tiempos"."""
    if field in ("tiempo_entre_ensayos", "tiempo_ensayo_consumo", "tiempo_entre_muestras"):
        return field, f"{field}_unidad"
    return f"{field}_duracion", f"{field}_unidad"


class SettingsTab:
    """Controlador de la pestaña Configuraciones.

    Args:
        window: Ventana principal (tiene los widgets del .ui como atributos).
        config_repo: Repositorio de configuración (tabla "tiempos").
        on_saved: Se llama con el tipo de ensayo elegido ("fdl", "ciclico" o "consumo"),
            la cantidad de repeticiones y la espera entre ensayos (s) después de guardar.
    """

    def __init__(self, window: QWidget, config_repo: SQLiteConfigRepository, on_saved=None):
        self.w = window
        self._repo = config_repo
        self._on_saved = on_saved or (lambda *_: None)
        # lambda: clicked envía checked=False, que caería en el parámetro notify
        self.w.boton_guardar_configuraciones.clicked.connect(lambda: self.save())
        self.w.boton_valores_predeterminados.clicked.connect(self.restore_defaults)
        self.load()

    # ── Widgets ───────────────────────────────────────────────────────

    def _set(self, field: str, value: float, unit: str) -> None:
        spin_name, combo_name = FIELDS[field]
        spin, combo = getattr(self.w, spin_name), getattr(self.w, combo_name)
        if combo.findText(unit) < 0:
            # Unidad que este combo no ofrece (por ejemplo "Horas"): se pasa a segundos
            value, unit = to_seconds(value, unit, value), "Segundos"
        combo.setCurrentText(unit)
        spin.setValue(float(value))

    def _get(self, field: str) -> tuple[int, str]:
        spin_name, combo_name = FIELDS[field]
        return int(getattr(self.w, spin_name).value()), getattr(self.w, combo_name).currentText()

    def mode(self) -> str:
        """Tipo de ensayo elegido: "fdl", "ciclico" o "consumo"."""
        if self.w.radio_ensayo_ciclico.isChecked():
            return "ciclico"
        if self.w.radio_ensayo_consumo.isChecked():
            return "consumo"
        return "fdl"

    # ── Acciones ──────────────────────────────────────────────────────

    def load(self) -> None:
        """Carga en los widgets los tiempos guardados en la base."""
        timings = self._repo.get_timings()
        for field, (default_value, default_unit) in DEFAULTS.items():
            value_col, unit_col = _columns(field)
            value = timings.get(value_col)
            unit = timings.get(unit_col) or default_unit
            self._set(field, default_value if value is None else value, unit)
        cycles = int(timings.get("cant_ensayos_ciclicos") or DEFAULT_CYCLES)
        self.w.spinbox_cantidad_ensayos.setValue(cycles)
        # El tipo de ensayo no se guarda: se deduce de la cantidad de repeticiones
        (self.w.radio_ensayo_ciclico if cycles > 1 else self.w.radio_ensayo_fdl).setChecked(True)

    def validate(self) -> str | None:
        """Devuelve un mensaje de error, o None si los tiempos son válidos."""
        duration = to_seconds(*self._get("tiempo_ensayo_consumo"), 0)
        interval = to_seconds(*self._get("tiempo_entre_muestras"), 0)
        if duration < interval:
            return (
                "En el ensayo de consumo, la duración tiene que ser mayor o igual "
                "al tiempo entre muestras."
            )
        return None

    def save(self, notify: bool = True) -> bool:
        """Guarda los tiempos en la base y avisa a los paneles de ensayo.

        Args:
            notify: Mostrar el aviso de guardado.

        Returns:
            True si se guardó.
        """
        error = self.validate()
        if error:
            QMessageBox.warning(self.w, "Tiempos inválidos", error)
            return False
        values: dict = {"cant_ensayos_ciclicos": int(self.w.spinbox_cantidad_ensayos.value())}
        for field in FIELDS:
            value_col, unit_col = _columns(field)
            values[value_col], values[unit_col] = self._get(field)
        if not self._repo.save_timings(**values):
            QMessageBox.critical(self.w, "Error", "No se pudieron guardar los tiempos.")
            return False
        wait_s = to_seconds(*self._get("tiempo_entre_ensayos"), 0)
        self._on_saved(self.mode(), values["cant_ensayos_ciclicos"], wait_s)
        if notify:
            QMessageBox.information(self.w, "Guardado", "Tiempos de ensayo guardados.")
        return True

    def restore_defaults(self) -> None:
        """Vuelve a los valores de fábrica y los guarda."""
        for field, (value, unit) in DEFAULTS.items():
            self._set(field, value, unit)
        self.w.spinbox_cantidad_ensayos.setValue(DEFAULT_CYCLES)
        self.w.radio_ensayo_fdl.setChecked(True)
        if self.save(notify=False):
            QMessageBox.information(
                self.w, "Valores predeterminados", "Se restablecieron los tiempos de fábrica."
            )

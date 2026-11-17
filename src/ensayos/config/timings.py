"""Tiempos de ensayo guardados en la base (tabla "tiempos"), editables desde la GUI.

La pestaña Configuraciones guarda las duraciones con su unidad. Este módulo las
convierte a la configuración que usan los ensayos (TestsConfig.durations). Si la base
no tiene un valor, se usa el de .env (TEST_*_DURATION).
"""

from dataclasses import replace

from ensayos.config.config_tests import TestsConfig, tests_config
from ensayos.models.enums import TimeUnit

# Ensayo → (columna de duración, columna de unidad, campo de TestDurations)
TEST_TIMING_COLUMNS = {
    "consumption": ("consumo_duracion", "consumo_unidad"),
    "active_leakage": ("fuga_activa_duracion", "fuga_activa_unidad"),
    "passive_leakage": ("fuga_pasiva_duracion", "fuga_pasiva_unidad"),
    "grounding": ("pat_duracion", "pat_unidad"),
    "dielectric": ("rigidez_duracion", "rigidez_unidad"),
}


def to_seconds(value: float | None, unit: str | None, default: float) -> float:
    """Convierte un valor con unidad ("Segundos", "Minutos", "Horas") a segundos.

    Args:
        value: Valor guardado (None si no hay).
        unit: Unidad guardada (None o vacía se toma como segundos).
        default: Valor a devolver si no hay valor.

    Returns:
        Segundos.
    """
    if value is None:
        return default
    try:
        return TimeUnit(unit or TimeUnit.SECONDS.value).to_seconds(float(value))
    except ValueError:
        return float(value)


def config_with_timings(timings: dict, base: TestsConfig = tests_config) -> TestsConfig:
    """Devuelve la configuración de ensayos con las duraciones de la base.

    Args:
        timings: Fila de la tabla "tiempos" (SQLiteConfigRepository.get_timings).
        base: Configuración de partida.

    Returns:
        Copia de ``base`` con las duraciones reemplazadas (en segundos enteros).
    """
    durations = base.durations
    changes = {}
    for field, (value_col, unit_col) in TEST_TIMING_COLUMNS.items():
        current = getattr(durations, field)
        seconds = to_seconds(timings.get(value_col), timings.get(unit_col), current)
        changes[field] = max(1, round(seconds))
    return replace(base, durations=replace(durations, **changes))

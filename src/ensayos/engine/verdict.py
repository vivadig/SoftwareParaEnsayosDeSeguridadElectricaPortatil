"""Funciones puras de evaluación de veredictos para ensayos de seguridad eléctrica.

Cada función recibe valores medidos y umbrales configurables,
y retorna un Verdict (OK / FAIL). Sin efectos secundarios ni dependencias de UI.
"""

from ensayos.config.config_tests import tests_config
from ensayos.models.enums import DeviceClass, Verdict


def evaluate_consumption_current(
    measured_current: float,
    rated_current: float,
    min_pct: float | None = None,
    max_pct: float | None = None,
) -> Verdict:
    """Evalúa si la corriente medida está dentro del rango aceptable.

    Args:
        measured_current: Corriente medida (A).
        rated_current: Corriente nominal del producto (A).
        min_pct: Porcentaje mínimo aceptable (default: config).
        max_pct: Porcentaje máximo aceptable (default: config).

    Returns:
        Verdict.OK si está dentro del rango, Verdict.FAIL si no.
    """
    cfg = tests_config.consumption
    min_pct = min_pct if min_pct is not None else cfg.current_min_pct
    max_pct = max_pct if max_pct is not None else cfg.current_max_pct

    lower = rated_current * (min_pct / 100.0)
    upper = rated_current * (max_pct / 100.0)

    if lower < measured_current < upper:
        return Verdict.OK
    return Verdict.FAIL


def evaluate_consumption_power(
    measured_power: float,
    rated_power: float,
    min_pct: float | None = None,
    max_pct: float | None = None,
) -> Verdict:
    """Evalúa si la potencia medida está dentro del rango aceptable.

    Args:
        measured_power: Potencia aparente medida (W).
        rated_power: Potencia nominal del producto (W).
        min_pct: Porcentaje mínimo aceptable (default: config).
        max_pct: Porcentaje máximo aceptable (default: config).

    Returns:
        Verdict.OK si está dentro del rango, Verdict.FAIL si no.
    """
    cfg = tests_config.consumption
    min_pct = min_pct if min_pct is not None else cfg.power_min_pct
    max_pct = max_pct if max_pct is not None else cfg.power_max_pct

    lower = rated_power * (min_pct / 100.0)
    upper = rated_power * (max_pct / 100.0)

    if lower < measured_power < upper:
        return Verdict.OK
    return Verdict.FAIL


def evaluate_consumption(
    measured_current: float,
    rated_current: float,
    measured_power: float,
    rated_power: float,
) -> tuple[Verdict, Verdict]:
    """Evalúa el ensayo de consumo completo.

    Returns:
        Tupla (veredicto_corriente, veredicto_potencia).
    """
    return (
        evaluate_consumption_current(measured_current, rated_current),
        evaluate_consumption_power(measured_power, rated_power),
    )


def evaluate_active_leakage(
    leakage_ua: float,
    max_ua: float | None = None,
) -> Verdict:
    """Evalúa fuga activa.

    Args:
        leakage_ua: Corriente de fuga medida (μA).
        max_ua: Umbral máximo aceptable (default: config).

    Returns:
        Verdict.OK si < umbral, Verdict.FAIL si >= umbral.
    """
    max_ua = max_ua if max_ua is not None else tests_config.leakage.active_max_ua
    return Verdict.OK if leakage_ua < max_ua else Verdict.FAIL


def evaluate_passive_leakage(
    leakage_ua: float,
    max_ua: float | None = None,
) -> Verdict:
    """Evalúa fuga pasiva.

    Args:
        leakage_ua: Corriente de fuga medida (μA).
        max_ua: Umbral máximo aceptable (default: config).

    Returns:
        Verdict.OK si < umbral, Verdict.FAIL si >= umbral.
    """
    max_ua = max_ua if max_ua is not None else tests_config.leakage.passive_max_ua
    return Verdict.OK if leakage_ua < max_ua else Verdict.FAIL


def evaluate_grounding(
    resistance_mohm: float,
    max_mohm: float | None = None,
) -> Verdict:
    """Evalúa puesta a tierra (PAT).

    Args:
        resistance_mohm: Resistencia medida (mΩ). float('inf') indica sobre-rango.
        max_mohm: Umbral máximo aceptable (default: config).

    Returns:
        Verdict.OK si < umbral, Verdict.FAIL si >= umbral o sobre-rango.
    """
    max_mohm = max_mohm if max_mohm is not None else tests_config.grounding.max_mohm
    if resistance_mohm == float("inf"):
        return Verdict.FAIL
    return Verdict.OK if resistance_mohm < max_mohm else Verdict.FAIL


def evaluate_dielectric(
    voltage: float,
    device_class: DeviceClass,
    class1_min_v: float | None = None,
    class2_min_v: float | None = None,
) -> Verdict:
    """Evalúa rigidez dieléctrica.

    Args:
        voltage: Tensión resistida medida (V).
        device_class: Clase del dispositivo (1 o 2).
        class1_min_v: Umbral mínimo para Clase 1 (default: config).
        class2_min_v: Umbral mínimo para Clase 2 (default: config).

    Returns:
        Verdict.OK si > umbral para la clase, Verdict.FAIL si <= umbral.
    """
    cfg = tests_config.dielectric
    if device_class == DeviceClass.CLASS_1:
        threshold = class1_min_v if class1_min_v is not None else cfg.class1_min_v
    else:
        threshold = class2_min_v if class2_min_v is not None else cfg.class2_min_v

    return Verdict.OK if voltage > threshold else Verdict.FAIL

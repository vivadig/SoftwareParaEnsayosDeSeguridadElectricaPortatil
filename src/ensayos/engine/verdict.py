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
    doubled_limit: bool = False,
    max_ua: float | None = None,
) -> Verdict:
    """Evalúa fuga pasiva (IEC 60335-1, 16.2).

    Args:
        leakage_ua: Corriente de fuga medida (μA).
        doubled_limit: True si el producto cumple una condición de la norma que
            duplica el límite (p. ej. controles con apagado en todos los polos).
        max_ua: Umbral base aceptable (default: config).

    Returns:
        Verdict.OK si < umbral, Verdict.FAIL si >= umbral.
    """
    max_ua = max_ua if max_ua is not None else tests_config.leakage.passive_max_ua
    if doubled_limit:
        max_ua *= 2
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
    min_voltage: float,
    peak_current_ma: float,
    device_class: DeviceClass,
    test_voltage: float | None = None,
    voltage_tolerance_pct: float | None = None,
    max_current_ma: float | None = None,
) -> Verdict:
    """Evalúa rigidez dieléctrica (IEC 60335-1, Anexo A.2).

    El ensayo aprueba solo si la tensión de ensayo se mantuvo aplicada durante
    todo el ensayo y no hubo ruptura (corriente por encima del límite). Si la
    tensión no alcanzó el valor de ensayo, el aislamiento no fue verificado y
    el resultado es FAIL (criterio conservador: nunca un falso aprobado).

    Args:
        min_voltage: Tensión mínima registrada durante el ensayo (V).
        peak_current_ma: Corriente máxima registrada durante el ensayo (mA).
        device_class: Clase del dispositivo (1 o 2).
        test_voltage: Tensión de ensayo nominal (default: config según clase).
        voltage_tolerance_pct: Tolerancia por debajo de la tensión de ensayo (%).
        max_current_ma: Corriente máxima admisible (mA) (default: config).

    Returns:
        Verdict.OK si la tensión se alcanzó y la corriente no superó el límite,
        Verdict.FAIL en caso contrario.
    """
    cfg = tests_config.dielectric
    if test_voltage is None:
        if device_class == DeviceClass.CLASS_1:
            test_voltage = cfg.class1_test_v
        else:
            test_voltage = cfg.class2_test_v
    if voltage_tolerance_pct is None:
        voltage_tolerance_pct = cfg.voltage_tolerance_pct
    if max_current_ma is None:
        max_current_ma = cfg.max_current_ma

    min_required_v = test_voltage * (1 - voltage_tolerance_pct / 100.0)
    if min_voltage < min_required_v:
        return Verdict.FAIL
    return Verdict.OK if peak_current_ma <= max_current_ma else Verdict.FAIL

"""Funciones puras de evaluación de veredictos para ensayos de seguridad eléctrica.

Cada función recibe valores medidos y umbrales configurables,
y retorna un Verdict (OK / FAIL). Sin efectos secundarios ni dependencias de UI.
"""

from ensayos.config.config_tests import tests_config
from ensayos.models.enums import ApplianceType, DeviceClass, Verdict


def _consumption_limits(
    rated: float,
    appliance_type: ApplianceType,
    small_max: float,
    heating_mid_max: float,
    motor_mid_max: float,
    heating_abs: float,
    motor_abs: float,
) -> tuple[float | None, float]:
    """Límites (inferior, superior) según la estructura común de las Tablas 1 y 2.

    Returns:
        Tupla (límite inferior o None si la norma no lo fija, límite superior).
    """
    if rated <= small_max:
        return None, rated * 1.20
    if appliance_type == ApplianceType.HEATING:
        if rated <= heating_mid_max:
            return rated * 0.90, rated * 1.10
        return rated * 0.90, rated + max(rated * 0.05, heating_abs)
    if rated <= motor_mid_max:
        return None, rated * 1.20
    return None, rated + max(rated * 0.15, motor_abs)


def power_limits(rated_w: float, appliance_type: ApplianceType) -> tuple[float | None, float]:
    """Desviación admisible de la potencia (IEC 60335-1, 10.1, Tabla 1)."""
    return _consumption_limits(rated_w, appliance_type, 25.0, 200.0, 300.0, 20.0, 60.0)


def current_limits(rated_a: float, appliance_type: ApplianceType) -> tuple[float | None, float]:
    """Desviación admisible de la corriente (IEC 60335-1, 10.2, Tabla 2)."""
    return _consumption_limits(rated_a, appliance_type, 0.2, 1.0, 1.5, 0.10, 0.30)


def _within(
    measured: float,
    rated: float,
    limits: tuple[float | None, float],
    functional_min_pct: float,
) -> Verdict:
    lower, upper = limits
    if lower is None:
        # La norma no fija mínimo: control funcional (no normativo)
        lower = rated * functional_min_pct / 100.0
    return Verdict.OK if lower <= measured <= upper else Verdict.FAIL


def evaluate_consumption(
    measured_current: float,
    rated_current: float,
    measured_power: float,
    rated_power: float,
    appliance_type: ApplianceType = ApplianceType.HEATING,
    functional_min_pct: float | None = None,
) -> Verdict:
    """Evalúa el ensayo de consumo (IEC 60335-1, 10.1 y 10.2).

    Solo se evalúan los valores nominales declarados (mayores a cero).

    Args:
        measured_current: Corriente medida (A).
        rated_current: Corriente nominal del producto (A); 0 si no está declarada.
        measured_power: Potencia activa medida (W).
        rated_power: Potencia nominal del producto (W); 0 si no está declarada.
        appliance_type: Tipo de aparato (define la tolerancia).
        functional_min_pct: Mínimo funcional (%) cuando la norma no fija límite
            inferior (default: config).

    Returns:
        Verdict.OK si todos los valores declarados están dentro de tolerancia,
        Verdict.FAIL si alguno no lo está, Verdict.NOT_RUN si no hay ninguno
        declarado.
    """
    if functional_min_pct is None:
        functional_min_pct = tests_config.consumption.functional_min_pct

    verdicts = []
    if rated_power > 0:
        limits = power_limits(rated_power, appliance_type)
        verdicts.append(_within(measured_power, rated_power, limits, functional_min_pct))
    if rated_current > 0:
        limits = current_limits(rated_current, appliance_type)
        verdicts.append(_within(measured_current, rated_current, limits, functional_min_pct))

    if not verdicts:
        return Verdict.NOT_RUN
    return Verdict.OK if all(v == Verdict.OK for v in verdicts) else Verdict.FAIL


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
    current_a: float,
    with_cord: bool = True,
    max_mohm: float | None = None,
    min_current_a: float | None = None,
) -> Verdict:
    """Evalúa puesta a tierra (IEC 60335-1, Anexo A.1).

    Si la corriente de ensayo no alcanzó el mínimo, la continuidad no fue
    verificada en condiciones de norma y el resultado es FAIL.

    Args:
        resistance_mohm: Resistencia medida (mΩ). float('inf') indica sobre-rango.
        current_a: Corriente de ensayo medida (A).
        with_cord: True si el aparato tiene cable de alimentación fijo (la
            medición desde la ficha lo incluye).
        max_mohm: Umbral máximo aceptable (default: config según with_cord).
        min_current_a: Corriente mínima de ensayo (default: config).

    Returns:
        Verdict.OK si la corriente alcanzó el mínimo y la resistencia no supera
        el umbral, Verdict.FAIL en caso contrario o sobre-rango.
    """
    cfg = tests_config.grounding
    if max_mohm is None:
        max_mohm = cfg.max_mohm_with_cord if with_cord else cfg.max_mohm
    if min_current_a is None:
        min_current_a = cfg.min_current_a

    if resistance_mohm == float("inf") or current_a < min_current_a:
        return Verdict.FAIL
    return Verdict.OK if resistance_mohm <= max_mohm else Verdict.FAIL


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

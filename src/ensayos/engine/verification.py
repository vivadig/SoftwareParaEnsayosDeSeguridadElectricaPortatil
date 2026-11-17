"""Verificación del equipo con patrones.

Se ensayan dos patrones de valor conocido, conectados de a uno por el operario:
el patrón 1 debe dar OK y el patrón 2 debe dar FALLA en fuga activa, puesta a tierra
y rigidez dieléctrica. Cada medición, además, tiene que estar dentro de una tolerancia
del valor del patrón (VERIFICATION_TOLERANCE_PCT). El equipo queda verificado solo si
se cumplen las 6 comprobaciones.
"""

import math
from dataclasses import dataclass

from ensayos.models.enums import ApplianceType, DeviceClass, TestType, Verdict
from ensayos.models.measurement import (
    DielectricMeasurement,
    GroundingMeasurement,
    LeakageMeasurement,
)
from ensayos.models.product import Product
from ensayos.models.test_result import TestResult

# Ensayos de la verificación y la clave con la que aparecen en la base y en la GUI
VERIFICATION_TESTS: dict[TestType, str] = {
    TestType.ACTIVE_LEAKAGE: "fuga",
    TestType.GROUNDING: "pat",
    TestType.DIELECTRIC: "rd",
}
UNITS = {"fuga": "µA", "pat": "mΩ", "rd": "mA"}

# Patrón → (sufijo en la base y en la GUI, veredicto esperado)
PATTERNS: dict[int, tuple[str, Verdict]] = {
    1: ("pasa", Verdict.OK),
    2: ("falla", Verdict.FAIL),
}


@dataclass(frozen=True)
class PatternCheck:
    """Resultado de un ensayo sobre un patrón."""

    key: str  # "fuga", "pat" o "rd"
    pattern: int  # 1 o 2
    expected: Verdict
    verdict: Verdict
    measured: float | None
    reference: float
    within_tolerance: bool
    ok: bool
    reason: str


def measured_value(result: TestResult) -> float | None:
    """Magnitud que se compara con el patrón: fuga (µA), resistencia (mΩ) o corriente (mA)."""
    m = result.measurement
    if isinstance(m, LeakageMeasurement):
        return m.leakage_ua
    if isinstance(m, GroundingMeasurement):
        return m.resistance_mohm
    if isinstance(m, DielectricMeasurement):
        return m.current_ma
    return None


def check_pattern(
    result: TestResult, pattern: int, reference: float, tolerance_pct: float
) -> PatternCheck:
    """Compara el resultado de un ensayo sobre un patrón con lo esperado.

    Args:
        result: Resultado del ensayo.
        pattern: Número de patrón (1 debe pasar, 2 debe fallar).
        reference: Valor del patrón.
        tolerance_pct: Diferencia admitida entre medición y patrón (%).

    Returns:
        La comprobación, con el motivo si no se cumple.
    """
    key = VERIFICATION_TESTS[result.test_type]
    expected = PATTERNS[pattern][1]
    measured = measured_value(result)
    problems = []
    within = False
    if reference <= 0:
        problems.append("patrón sin valor cargado")
    elif measured is None or not math.isfinite(measured):
        problems.append("sin medición")
    else:
        within = abs(measured - reference) <= reference * tolerance_pct / 100
        if not within:
            diff = (measured - reference) / reference * 100
            problems.append(f"difiere {diff:+.1f} % del patrón (máx. ±{tolerance_pct:g} %)")
    if result.verdict != expected:
        problems.append(f"veredicto {result.verdict.value}, se esperaba {expected.value}")
    return PatternCheck(
        key=key,
        pattern=pattern,
        expected=expected,
        verdict=result.verdict,
        measured=measured,
        reference=reference,
        within_tolerance=within,
        ok=not problems,
        reason="; ".join(problems) or "OK",
    )


def missing_patterns(patterns: dict) -> list[str]:
    """Valores de patrón sin cargar (en 0), con nombre legible.

    Args:
        patterns: Fila de la tabla cotas_verificacion.
    """
    names = {"fuga": "fuga", "pat": "puesta a tierra", "rd": "rigidez dieléctrica"}
    missing = []
    for number, (suffix, _) in PATTERNS.items():
        for key in VERIFICATION_TESTS.values():
            if float(patterns.get(f"{key}_{suffix}") or 0) <= 0:
                missing.append(f"patrón {number}: {names[key]}")
    return missing


def pattern_product(number: int) -> Product:
    """Producto con el que se ensaya un patrón: Clase I, con cable fijo."""
    return Product(
        marca="Patrón",
        modelo=str(number),
        descripcion="Patrón de verificación",
        potencia=0.0,
        tension=0.0,
        corriente=0.0,
        frecuencia=50.0,
        clase=DeviceClass.CLASS_1,
        con_cable_alimentacion=True,
        tipo_aparato=ApplianceType.HEATING,
    )

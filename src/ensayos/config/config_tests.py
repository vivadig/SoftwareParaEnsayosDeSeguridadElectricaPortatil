"""Configuración de ensayos: umbrales, tiempos y correcciones de calibración."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _get_float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


def _get_int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


@dataclass(frozen=True)
class ConsumptionThresholds:
    """Umbrales de aprobación para ensayo de consumo (% del nominal)."""

    current_min_pct: float = _get_float("CONSUMPTION_CURRENT_MIN_PCT", 50.0)
    current_max_pct: float = _get_float("CONSUMPTION_CURRENT_MAX_PCT", 105.0)
    power_min_pct: float = _get_float("CONSUMPTION_POWER_MIN_PCT", 75.0)
    power_max_pct: float = _get_float("CONSUMPTION_POWER_MAX_PCT", 110.0)


@dataclass(frozen=True)
class LeakageThresholds:
    """Umbrales de aprobación para ensayos de fuga (μA)."""

    active_max_ua: float = _get_float("ACTIVE_LEAKAGE_MAX_UA", 750.0)
    # IEC 60335-1, 16.2 (Clase I portátil). Se duplica solo si el producto cumple
    # alguna de las condiciones de la norma (ver Product.fuga_pasiva_duplicada).
    passive_max_ua: float = _get_float("PASSIVE_LEAKAGE_MAX_UA", 750.0)


@dataclass(frozen=True)
class GroundingThresholds:
    """Umbrales de aprobación para ensayo de puesta a tierra.

    Según IEC 60335-1, Anexo A.1 (ensayo de rutina): corriente de al menos 10 A
    desde una fuente de no más de 12 V; resistencia máxima de 0,2 Ω para aparatos
    con cable de alimentación (medida desde la ficha) y 0,1 Ω para los demás.
    """

    max_mohm: float = _get_float("GROUNDING_MAX_MOHM", 100.0)
    max_mohm_with_cord: float = _get_float("GROUNDING_MAX_MOHM_WITH_CORD", 200.0)
    min_current_a: float = _get_float("GROUNDING_MIN_CURRENT_A", 10.0)


@dataclass(frozen=True)
class DielectricThresholds:
    """Parámetros de aprobación para ensayo de rigidez dieléctrica.

    Según IEC 60335-1, Anexo A.2 (ensayo de rutina), para tensión nominal > 150 V:
    1000 V con aislamiento básico (Clase I) y 2500 V con aislamiento doble o
    reforzado (Clase II). Hay ruptura si la corriente supera 5 mA (hasta 30 mA
    admitidos para aparatos con alta corriente de fuga).
    """

    class1_test_v: float = _get_float("DIELECTRIC_CLASS1_TEST_V", 1000.0)
    class2_test_v: float = _get_float("DIELECTRIC_CLASS2_TEST_V", 2500.0)
    # Tolerancia admitida por debajo de la tensión de ensayo (%)
    voltage_tolerance_pct: float = _get_float("DIELECTRIC_VOLTAGE_TOLERANCE_PCT", 3.0)
    max_current_ma: float = _get_float("DIELECTRIC_MAX_CURRENT_MA", 5.0)


@dataclass(frozen=True)
class TestDurations:
    """Duraciones de cada ensayo (en segundos)."""

    consumption: int = _get_int("TEST_CONSUMPTION_DURATION", 5)
    active_leakage: int = _get_int("TEST_ACTIVE_LEAKAGE_DURATION", 5)
    passive_leakage: int = _get_int("TEST_PASSIVE_LEAKAGE_DURATION", 5)
    grounding: int = _get_int("TEST_GROUNDING_DURATION", 5)
    dielectric: int = _get_int("TEST_DIELECTRIC_DURATION", 5)
    inter_test_delay: float = _get_float("TEST_INTER_TEST_DELAY", 0.2)


@dataclass(frozen=True)
class CalibrationCorrections:
    """Correcciones de calibración aplicadas a cada medición."""

    voltage: float = _get_float("CORRECTION_VOLTAGE", 0.0)
    current: float = _get_float("CORRECTION_CURRENT", 0.0)
    active_leakage: float = _get_float("CORRECTION_ACTIVE_LEAKAGE", 0.0)
    passive_leakage: float = _get_float("CORRECTION_PASSIVE_LEAKAGE", 0.0)
    grounding: float = _get_float("CORRECTION_GROUNDING", 0.0)
    dielectric: float = _get_float("CORRECTION_DIELECTRIC", 0.0)


@dataclass(frozen=True)
class TestsConfig:
    """Configuración completa de ensayos."""

    consumption: ConsumptionThresholds = ConsumptionThresholds()
    leakage: LeakageThresholds = LeakageThresholds()
    grounding: GroundingThresholds = GroundingThresholds()
    dielectric: DielectricThresholds = DielectricThresholds()
    durations: TestDurations = TestDurations()
    corrections: CalibrationCorrections = CalibrationCorrections()


tests_config = TestsConfig()

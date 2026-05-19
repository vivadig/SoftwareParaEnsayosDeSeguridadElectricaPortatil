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
    passive_max_ua: float = _get_float("PASSIVE_LEAKAGE_MAX_UA", 1500.0)


@dataclass(frozen=True)
class GroundingThresholds:
    """Umbrales de aprobación para ensayo de puesta a tierra (mΩ)."""

    max_mohm: float = _get_float("GROUNDING_MAX_MOHM", 100.0)


@dataclass(frozen=True)
class DielectricThresholds:
    """Umbrales de aprobación para ensayo de rigidez dieléctrica (V)."""

    class1_min_v: float = _get_float("DIELECTRIC_CLASS1_MIN_V", 800.0)
    class2_min_v: float = _get_float("DIELECTRIC_CLASS2_MIN_V", 2000.0)


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

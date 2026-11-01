"""Configuración de hardware: ESP32, relés USB y PZEM."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _get_int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def _get_float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


def _get_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


def _get_list(key: str, default: str) -> list[str]:
    raw = os.environ.get(key, default)
    return [item.strip() for item in raw.split(",")]


@dataclass(frozen=True)
class ESP32Config:
    """Configuración de conexión serial con ESP32."""

    baud_rate: int = _get_int("ESP32_BAUD_RATE", 115200)
    timeout: int = _get_int("ESP32_TIMEOUT", 2)
    retry_interval: int = _get_int("ESP32_RETRY_INTERVAL", 5)
    port_keywords: list[str] = field(
        default_factory=lambda: _get_list("ESP32_PORT_KEYWORDS", "ESP32,CP210x,CP2102")
    )
    stabilization_delay: float = _get_float("ESP32_STABILIZATION_DELAY", 2.0)


@dataclass(frozen=True)
class RelayMapping:
    """Mapeo de nombres semánticos de relés a números de relé."""

    fuga_activa: int = _get_int("RELAY_FUGA_ACTIVA", 1)
    fuga_pasiva: int = _get_int("RELAY_FUGA_PASIVA", 2)
    pat_power: int = _get_int("RELAY_PAT_POWER", 3)
    dielectric_class1: int = _get_int("RELAY_DIELECTRIC_CLASS1", 4)
    dielectric_class2: int = _get_int("RELAY_DIELECTRIC_CLASS2", 5)
    dielectric_enable: int = _get_int("RELAY_DIELECTRIC_ENABLE", 6)
    pat_enable: int = _get_int("RELAY_PAT_ENABLE", 7)
    watchdog: int = _get_int("RELAY_WATCHDOG", 8)


@dataclass(frozen=True)
class PzemMapping:
    """Mapeo de módulos PZEM a sus IDs."""

    consumption: int = _get_int("PZEM_CONSUMPTION", 1)
    leakage: int = _get_int("PZEM_LEAKAGE", 2)
    grounding: int = _get_int("PZEM_GROUNDING", 3)


@dataclass(frozen=True)
class ScaleFactors:
    """Factores de escala para conversión de mediciones."""

    leakage_current_multiplier: float = _get_float("LEAKAGE_CURRENT_MULTIPLIER", 10.0)
    grounding_voltage_multiplier: float = _get_float("GROUNDING_VOLTAGE_MULTIPLIER", 10.0)
    grounding_resistance_multiplier: float = _get_float("GROUNDING_RESISTANCE_MULTIPLIER", 1000.0)
    dielectric_voltage_multiplier: float = _get_float("DIELECTRIC_VOLTAGE_MULTIPLIER", 10.0)
    # Convierte la corriente del PZEM2 (A) a corriente en el circuito de AT (mA).
    # Debe calibrarse según dónde esté ubicado el PZEM (primario o secundario).
    dielectric_current_multiplier: float = _get_float("DIELECTRIC_CURRENT_MULTIPLIER", 1000.0)


@dataclass(frozen=True)
class RelayConfig:
    """Configuración completa de relés USB."""

    board_serial: str = _get_str("RELAY_BOARD_SERIAL", "auto")
    settle_delay: float = _get_float("RELAY_SETTLE_DELAY", 0.05)
    mapping: RelayMapping = field(default_factory=RelayMapping)


@dataclass(frozen=True)
class HardwareConfig:
    """Configuración completa de hardware."""

    esp32: ESP32Config = field(default_factory=ESP32Config)
    relay: RelayConfig = field(default_factory=RelayConfig)
    pzem: PzemMapping = field(default_factory=PzemMapping)
    scale: ScaleFactors = field(default_factory=ScaleFactors)


hardware_config = HardwareConfig()

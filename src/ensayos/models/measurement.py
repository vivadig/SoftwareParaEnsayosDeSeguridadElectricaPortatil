"""Modelos de mediciones eléctricas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PzemReading:
    """Lectura cruda de un módulo PZEM."""

    voltage: float
    current: float
    power: float
    energy: float
    power_factor: float = 0.0

    @classmethod
    def from_dict(cls, data: dict) -> "PzemReading":
        """Crea una lectura desde el diccionario de respuesta del ESP32.

        El ESP32 responde con formato: V=220.50,C=5.30,P=1176.50,E=12.34
        """
        return cls(
            voltage=data.get("V", 0.0),
            current=data.get("C", 0.0),
            power=data.get("P", 0.0),
            energy=data.get("E", 0.0),
            power_factor=data.get("FP", 0.0),
        )


@dataclass(frozen=True)
class ConsumptionMeasurement:
    """Medición de consumo con correcciones aplicadas."""

    voltage: float
    current: float
    power: float
    power_factor: float

    @classmethod
    def from_pzem(
        cls,
        reading: PzemReading,
        correction_voltage: float = 0.0,
        correction_current: float = 0.0,
    ) -> "ConsumptionMeasurement":
        return cls(
            voltage=reading.voltage + correction_voltage,
            current=reading.current + correction_current,
            power=reading.power,
            power_factor=reading.power_factor,
        )


@dataclass(frozen=True)
class LeakageMeasurement:
    """Medición de corriente de fuga en μA."""

    leakage_ua: float

    @classmethod
    def from_pzem(
        cls,
        reading: PzemReading,
        multiplier: float = 10.0,
        correction: float = 0.0,
    ) -> "LeakageMeasurement":
        return cls(
            leakage_ua=(reading.current * multiplier) + correction,
        )


@dataclass(frozen=True)
class GroundingMeasurement:
    """Medición de resistencia de puesta a tierra en mΩ."""

    resistance_mohm: float

    @classmethod
    def from_pzem(
        cls,
        reading: PzemReading,
        voltage_multiplier: float = 10.0,
        resistance_multiplier: float = 1000.0,
        correction: float = 0.0,
    ) -> "GroundingMeasurement":
        if reading.current == 0:
            return cls(resistance_mohm=float("inf"))
        resistance = (reading.voltage * voltage_multiplier) / reading.current
        return cls(
            resistance_mohm=(resistance * resistance_multiplier) + correction,
        )


@dataclass(frozen=True)
class DielectricMeasurement:
    """Medición de rigidez dieléctrica en V."""

    voltage: float

    @classmethod
    def from_pzem(
        cls,
        reading: PzemReading,
        multiplier: float = 10.0,
        correction: float = 0.0,
    ) -> "DielectricMeasurement":
        return cls(
            voltage=(reading.voltage * multiplier) + correction,
        )

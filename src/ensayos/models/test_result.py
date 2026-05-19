"""Modelo de resultado de ensayo."""

from dataclasses import dataclass, field
from datetime import datetime

from ensayos.models.enums import TestType, Verdict
from ensayos.models.measurement import (
    ConsumptionMeasurement,
    DielectricMeasurement,
    GroundingMeasurement,
    LeakageMeasurement,
)

Measurement = (
    ConsumptionMeasurement | LeakageMeasurement | GroundingMeasurement | DielectricMeasurement
)


@dataclass
class TestResult:
    """Resultado individual de un ensayo."""

    test_type: TestType
    verdict: Verdict
    measurement: Measurement | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class FdlTestRecord:
    """Registro completo de un ensayo Final de Línea."""

    marca: str
    modelo: str
    serial: str
    fecha: str
    hora: str
    tension: float = 0.0
    corriente: float = 0.0
    factor_potencia: float = 0.0
    potencia: float = 0.0
    veredicto_consumo: Verdict = Verdict.NOT_RUN
    fuga_activa_medida: float = 0.0
    veredicto_fuga_activa: Verdict = Verdict.NOT_RUN
    fuga_pasiva_medida: float = 0.0
    veredicto_fuga_pasiva: Verdict = Verdict.NOT_RUN
    pat_medida: float = 0.0
    veredicto_pat: Verdict = Verdict.NOT_RUN
    rigidez_medida: float = 0.0
    veredicto_rigidez: Verdict = Verdict.NOT_RUN


@dataclass
class ConsumptionSample:
    """Muestra individual de un ensayo de perfil de consumo."""

    n_ensayo: int
    n_muestra: int
    marca: str
    modelo: str
    serial: str
    fecha: str
    hora: str
    tension: float = 0.0
    corriente: float = 0.0
    factor_potencia: float = 0.0
    potencia: float = 0.0
    fuga_activa: float = 0.0

"""Enumeraciones del sistema de ensayos."""

from enum import Enum


class DeviceClass(Enum):
    """Clase del dispositivo bajo ensayo según norma."""

    CLASS_1 = 1
    CLASS_2 = 2


class TestType(Enum):
    """Tipos de ensayo de seguridad eléctrica."""

    CONSUMPTION = "consumo"
    ACTIVE_LEAKAGE = "fuga_activa"
    PASSIVE_LEAKAGE = "fuga_pasiva"
    GROUNDING = "puesta_a_tierra"
    DIELECTRIC = "rigidez_dielectrica"


class Verdict(Enum):
    """Resultado de un ensayo."""

    OK = "OK"
    FAIL = "FALLA"
    NOT_RUN = "NO_EJECUTADO"


class TestMode(Enum):
    """Modos de ejecución de ensayos."""

    END_OF_LINE = "final_de_linea"
    CYCLIC = "ciclico"
    VERIFICATION = "verificacion"
    CONSUMPTION_PROFILE = "perfil_consumo"


class TimeUnit(Enum):
    """Unidades de tiempo para configuración."""

    SECONDS = "Segundos"
    MINUTES = "Minutos"
    HOURS = "Horas"

    def to_seconds(self, value: float) -> float:
        """Convierte un valor en esta unidad a segundos."""
        if self == TimeUnit.SECONDS:
            return value
        if self == TimeUnit.MINUTES:
            return value * 60
        return value * 3600

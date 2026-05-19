"""Modelo de producto (dispositivo bajo ensayo)."""

from dataclasses import dataclass

from ensayos.models.enums import DeviceClass


@dataclass
class Product:
    """Producto registrado en el sistema para ensayos."""

    marca: str
    modelo: str
    descripcion: str
    potencia: float
    tension: float
    corriente: float
    frecuencia: float
    clase: DeviceClass
    id: int | None = None

    @property
    def power_w(self) -> float:
        return self.potencia

    @property
    def voltage_v(self) -> float:
        return self.tension

    @property
    def current_a(self) -> float:
        return self.corriente

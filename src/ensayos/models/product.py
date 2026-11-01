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
    # IEC 60335-1, 16.2: el límite de fuga pasiva se duplica si todos los controles
    # tienen posición de apagado en todos los polos, si el aparato no tiene más control
    # que un protector térmico, si ningún termostato/limitador/regulador tiene posición
    # de apagado, o si tiene filtros de interferencia.
    fuga_pasiva_duplicada: bool = False
    # IEC 60335-1, A.1: con cable de alimentación fijo la medición desde la ficha
    # incluye el cable y el límite es 0,2 Ω; sin él (borne o ficha de aparato), 0,1 Ω.
    con_cable_alimentacion: bool = True

    @property
    def power_w(self) -> float:
        return self.potencia

    @property
    def voltage_v(self) -> float:
        return self.tension

    @property
    def current_a(self) -> float:
        return self.corriente

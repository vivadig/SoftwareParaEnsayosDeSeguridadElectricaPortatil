"""Interfaces (Protocol) de repositorios de datos."""

from typing import Protocol

from ensayos.models.product import Product
from ensayos.models.test_result import ConsumptionSample, FdlTestRecord


class ProductRepository(Protocol):
    """Interfaz para operaciones CRUD de productos."""

    def create(self, product: Product) -> bool: ...

    def get_by_id(self, product_id: int) -> Product | None: ...

    def get_by_brand_model(self, marca: str, modelo: str) -> Product | None: ...

    def list_all(self) -> list[Product]: ...

    def update(self, product: Product) -> bool: ...

    def delete(self, product_id: int) -> bool: ...


class FdlHistoryRepository(Protocol):
    """Interfaz para historial de ensayos Final de Línea."""

    def save(self, record: FdlTestRecord) -> bool: ...

    def list_all(self) -> list[FdlTestRecord]: ...

    def search(
        self,
        fecha: str | None = None,
        marca: str | None = None,
        query: str | None = None,
    ) -> list[FdlTestRecord]: ...

    def delete_all(self) -> bool: ...


class ConsumptionHistoryRepository(Protocol):
    """Interfaz para historial de ensayos de consumo."""

    def save(self, sample: ConsumptionSample) -> bool: ...

    def list_all(self) -> list[ConsumptionSample]: ...

    def search(
        self,
        fecha: str | None = None,
        query: str | None = None,
    ) -> list[ConsumptionSample]: ...

    def delete_all(self) -> bool: ...


class VerificationHistoryRepository(Protocol):
    """Interfaz para historial de verificación."""

    def save(
        self,
        fecha: str,
        hora: str,
        fuga_pasa: float,
        pat_pasa: float,
        rd_pasa: float,
        fuga_falla: float,
        pat_falla: float,
        rd_falla: float,
    ) -> bool: ...

    def list_all(self) -> list[dict]: ...


class ConfigRepository(Protocol):
    """Interfaz para configuración persistida en DB."""

    def get_corrections(self) -> dict: ...

    def save_corrections(
        self,
        tension: float,
        corriente: float,
        fuga: float,
        corte_neutro: float,
        puesta_a_tierra: float,
        tension_resistida: float,
    ) -> bool: ...

    def get_timings(self) -> dict: ...

    def save_timings(self, **kwargs) -> bool: ...

    def get_verification_patterns(self) -> dict: ...

    def save_verification_patterns(
        self,
        fuga_pasa: float,
        pat_pasa: float,
        rd_pasa: float,
        fuga_falla: float,
        pat_falla: float,
        rd_falla: float,
    ) -> bool: ...

    def get_admin_credentials(self) -> tuple[str, str] | None: ...

    def set_admin_password(self, new_password: str) -> bool: ...

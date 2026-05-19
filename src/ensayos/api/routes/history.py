"""Endpoints de historial: FDL, consumo y verificación."""

import logging

from fastapi import APIRouter, Depends

from ensayos.api.auth import verify_credentials
from ensayos.database.sqlite_repository import (
    SQLiteConsumptionHistoryRepository,
    SQLiteFdlHistoryRepository,
    SQLiteVerificationHistoryRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["historial"])

_fdl_repo: SQLiteFdlHistoryRepository | None = None
_consumo_repo: SQLiteConsumptionHistoryRepository | None = None
_verif_repo: SQLiteVerificationHistoryRepository | None = None


def set_repositories(
    fdl: SQLiteFdlHistoryRepository,
    consumo: SQLiteConsumptionHistoryRepository,
    verificacion: SQLiteVerificationHistoryRepository,
) -> None:
    """Configura los repositorios a usar."""
    global _fdl_repo, _consumo_repo, _verif_repo  # noqa: PLW0603
    _fdl_repo = fdl
    _consumo_repo = consumo
    _verif_repo = verificacion


def _get_fdl_repo() -> SQLiteFdlHistoryRepository:
    return _fdl_repo or SQLiteFdlHistoryRepository()


def _get_consumo_repo() -> SQLiteConsumptionHistoryRepository:
    return _consumo_repo or SQLiteConsumptionHistoryRepository()


def _get_verif_repo() -> SQLiteVerificationHistoryRepository:
    return _verif_repo or SQLiteVerificationHistoryRepository()


@router.get("/historial-fdl")
def historial_fdl(
    fecha: str | None = None,
    marca: str | None = None,
    busqueda: str | None = None,
    usuario: str = Depends(verify_credentials),
):
    """Devuelve el historial de ensayos FDL.

    Filtros opcionales: ?fecha=12/02/2026&marca=Samsung&busqueda=texto
    """
    repo = _get_fdl_repo()
    resultados = repo.search(fecha=fecha, marca=marca, query=busqueda)

    # Filtro de búsqueda general sobre todos los campos
    if busqueda:
        busqueda_lower = busqueda.lower()
        resultados = [
            r for r in resultados
            if any(busqueda_lower in str(v).lower() for v in r.values())
        ]

    return {
        "total": len(resultados),
        "historiales": resultados,
    }


@router.get("/historial-consumo")
def historial_consumo(
    fecha: str | None = None,
    busqueda: str | None = None,
    usuario: str = Depends(verify_credentials),
):
    """Devuelve el historial de ensayos de consumo."""
    repo = _get_consumo_repo()
    resultados = repo.search(fecha=fecha, query=busqueda)

    if busqueda:
        busqueda_lower = busqueda.lower()
        resultados = [
            r for r in resultados
            if any(busqueda_lower in str(v).lower() for v in r.values())
        ]

    return {
        "total": len(resultados),
        "historiales": resultados,
    }


@router.get("/historial-verificacion")
def historial_verificacion(
    fecha: str | None = None,
    usuario: str = Depends(verify_credentials),
):
    """Devuelve el historial de verificaciones."""
    repo = _get_verif_repo()
    resultados = repo.list_all()

    if fecha:
        resultados = [r for r in resultados if r.get("fecha") == fecha]

    return {
        "total": len(resultados),
        "historiales": resultados,
    }

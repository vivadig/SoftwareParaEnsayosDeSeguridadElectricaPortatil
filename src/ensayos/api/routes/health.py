"""Endpoints de health y resumen diario."""

import datetime
import logging

from fastapi import APIRouter, Depends

from ensayos.api.auth import verify_credentials
from ensayos.database.sqlite_repository import SQLiteFdlHistoryRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])

_fdl_repo: SQLiteFdlHistoryRepository | None = None


def set_fdl_repository(repo: SQLiteFdlHistoryRepository) -> None:
    """Configura el repositorio FDL para el resumen."""
    global _fdl_repo  # noqa: PLW0603
    _fdl_repo = repo


def _get_fdl_repo() -> SQLiteFdlHistoryRepository:
    return _fdl_repo or SQLiteFdlHistoryRepository()


@router.get("/health")
def health():
    """Endpoint para verificar que el servidor está activo."""
    return {"status": "ok", "servicio": "Ensayos Seguridad Electrica API"}


@router.get("/resumen-hoy")
def resumen_hoy(usuario: str = Depends(verify_credentials)):
    """Devuelve el resumen de ensayos del día de hoy."""
    hoy = datetime.date.today().strftime("%d/%m/%Y")
    repo = _get_fdl_repo()

    resultados = repo.search(fecha=hoy)

    total = len(resultados)
    falla = 0
    for registro in resultados:
        verdicts = [
            str(registro.get("consumo", "")).strip().upper(),
            str(registro.get("fuga", "")).strip().upper(),
            str(registro.get("cn", "")).strip().upper(),
            str(registro.get("pat", "")).strip().upper(),
            str(registro.get("resistida", "")).strip().upper(),
        ]
        if any("FALLA" in v for v in verdicts):
            falla += 1

    return {
        "fecha": hoy,
        "total": total,
        "ok": total - falla,
        "falla": falla,
    }

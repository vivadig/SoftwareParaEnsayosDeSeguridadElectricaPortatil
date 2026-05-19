"""Autenticación HTTP Basic para la API REST."""

import logging
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ensayos.database.sqlite_repository import SQLiteConfigRepository

logger = logging.getLogger(__name__)

security = HTTPBasic()

_config_repo: SQLiteConfigRepository | None = None


def set_config_repository(repo: SQLiteConfigRepository) -> None:
    """Configura el repositorio a usar para autenticación."""
    global _config_repo  # noqa: PLW0603
    _config_repo = repo


def get_config_repo() -> SQLiteConfigRepository:
    if _config_repo is None:
        return SQLiteConfigRepository()
    return _config_repo


def verify_credentials(
    credentials: HTTPBasicCredentials = Depends(security),
) -> str:
    """Dependencia FastAPI que verifica credenciales HTTP Basic contra la DB.

    Returns:
        Nombre de usuario autenticado.

    Raises:
        HTTPException 401 si las credenciales son inválidas.
        HTTPException 500 si hay error de DB.
    """
    repo = get_config_repo()

    try:
        admin_creds = repo.get_admin_credentials()
    except Exception as e:
        logger.error("Error al leer credenciales de admin: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al leer la base de datos",
        ) from e

    if admin_creds is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No hay datos de admin configurados",
        )

    db_usuario, db_contrasena = admin_creds

    usuario_correcto = secrets.compare_digest(
        credentials.username.strip(), db_usuario.strip()
    )
    contrasena_correcta = secrets.compare_digest(
        credentials.password.strip(), db_contrasena.strip()
    )

    if not (usuario_correcto and contrasena_correcta):
        logger.warning("Intento de autenticación fallido para usuario: %s", credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
            headers={"WWW-Authenticate": "Basic"},
        )

    logger.debug("Usuario autenticado: %s", credentials.username)
    return credentials.username

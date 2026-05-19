"""Factory de la aplicación FastAPI."""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ensayos.api.auth import set_config_repository
from ensayos.api.routes import health, history
from ensayos.config.config_api import api_config
from ensayos.config.config_database import database_config
from ensayos.database.schemas import initialize_database
from ensayos.database.sqlite_repository import (
    SQLiteConfigRepository,
    SQLiteConsumptionHistoryRepository,
    SQLiteFdlHistoryRepository,
    SQLiteVerificationHistoryRepository,
)

logger = logging.getLogger(__name__)


def create_app(db_path: str | None = None) -> FastAPI:
    """Crea y configura la aplicación FastAPI.

    Args:
        db_path: Ruta a la base de datos SQLite. Si es None, usa la config.
    """
    db = db_path or database_config.path

    # Inicializar DB
    initialize_database(db)

    # Crear repositorios
    config_repo = SQLiteConfigRepository(db)
    fdl_repo = SQLiteFdlHistoryRepository(db)
    consumo_repo = SQLiteConsumptionHistoryRepository(db)
    verif_repo = SQLiteVerificationHistoryRepository(db)

    # Inyectar repositorios en los módulos de rutas
    set_config_repository(config_repo)
    history.set_repositories(fdl_repo, consumo_repo, verif_repo)
    health.set_fdl_repository(fdl_repo)

    # Crear app
    app = FastAPI(
        title="Ensayos de Seguridad Electrica - API",
        version="1.0.0",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Registrar routers
    app.include_router(history.router)
    app.include_router(health.router)

    # Montar archivos estáticos de la PWA (si el directorio existe)
    static_dir = Path(__file__).resolve().parent.parent.parent.parent / "static"
    if static_dir.exists():
        app.mount("/app", StaticFiles(directory=str(static_dir), html=True), name="pwa")
        logger.info("PWA montada en /app desde %s", static_dir)

    return app


def run_server(db_path: str | None = None) -> None:
    """Inicia el servidor uvicorn."""
    import uvicorn

    app = create_app(db_path)
    logger.info("Iniciando API en %s:%d", api_config.host, api_config.port)
    uvicorn.run(app, host=api_config.host, port=api_config.port)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_server()

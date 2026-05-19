"""Configuración de base de datos."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    """Configuración de conexión a base de datos SQLite."""

    path: str = os.environ.get("DATABASE_PATH", "data/ensayos.db")


database_config = DatabaseConfig()

"""Configuración de la API REST."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ApiConfig:
    """Configuración del servidor FastAPI."""

    host: str = os.environ.get("API_HOST", "0.0.0.0")
    port: int = int(os.environ.get("API_PORT", 8000))
    cors_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.environ.get("API_CORS_ORIGINS", "*").split(",")
        ]
    )


api_config = ApiConfig()

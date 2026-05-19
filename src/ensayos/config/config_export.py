"""Configuración de exportación: SMTP y rutas."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class SmtpConfig:
    """Configuración del servidor SMTP para envío de emails."""

    host: str = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port: int = int(os.environ.get("SMTP_PORT", 465))
    user: str = os.environ.get("SMTP_USER", "")
    password: str = os.environ.get("SMTP_PASSWORD", "")


@dataclass(frozen=True)
class ExportConfig:
    """Configuración completa de exportación."""

    smtp: SmtpConfig = SmtpConfig()
    default_dir: str = os.environ.get("EXPORT_DEFAULT_DIR", "~/Desktop")


export_config = ExportConfig()

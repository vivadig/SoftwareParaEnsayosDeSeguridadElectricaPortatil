"""Envío de historiales por email via SMTP."""

import logging
import os
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from ensayos.config.config_export import export_config

logger = logging.getLogger(__name__)


def send_email_with_attachment(
    recipients: list[str],
    attachment_path: str,
    subject: str = "Historiales SYGLAB",
    body: str = "",
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
) -> bool:
    """Envía un email con un archivo adjunto via SMTP SSL.

    Args:
        recipients: Lista de direcciones de email destinatarias.
        attachment_path: Ruta al archivo a adjuntar.
        subject: Asunto del email.
        body: Cuerpo del email.
        smtp_host: Host SMTP (usa config si es None).
        smtp_port: Puerto SMTP (usa config si es None).
        smtp_user: Usuario SMTP (usa config si es None).
        smtp_password: Contraseña SMTP (usa config si es None).

    Returns:
        True si el envío fue exitoso.
    """
    cfg = export_config.smtp
    host = smtp_host or cfg.host
    port = smtp_port or cfg.port
    user = smtp_user or cfg.user
    password = smtp_password or cfg.password

    if not user or not password:
        logger.error("Credenciales SMTP no configuradas. Configure SMTP_USER y SMTP_PASSWORD.")
        return False

    # Filtrar destinatarios vacíos
    recipients = [r.strip() for r in recipients if r.strip()]
    if not recipients:
        logger.error("No hay destinatarios válidos.")
        return False

    attachment = Path(attachment_path)
    if not attachment.exists():
        logger.error("Archivo adjunto no encontrado: %s", attachment_path)
        return False

    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body, "plain"))

        with open(attachment, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            "attachment",
            filename=attachment.name,
        )
        msg.attach(part)

        with smtplib.SMTP_SSL(host, port) as server:
            server.login(user, password)
            server.sendmail(user, recipients, msg.as_string())

        logger.info("Email enviado a: %s", ", ".join(recipients))
        return True

    except smtplib.SMTPException as e:
        logger.error("Error al enviar email: %s", e)
        return False

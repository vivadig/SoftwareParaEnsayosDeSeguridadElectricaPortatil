"""Lógica de la pestaña "Exportar" de la ventana principal.

Exporta los historiales del rango de fechas elegido a un Excel, en el escritorio, en una
carpeta elegida (por ejemplo, un pendrive) o adjunto en un mail.
"""

import logging
import re
import tempfile
from datetime import date
from pathlib import Path

from PyQt5.QtCore import QDate, QStandardPaths, Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from ensayos.export.email_sender import send_email_with_attachment
from ensayos.export.excel_exporter import export_to_excel

logger = logging.getLogger(__name__)

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ExportTab:
    """Controlador de la pestaña Exportar.

    Args:
        window: Ventana principal (tiene los widgets del .ui como atributos).
        db_path: Base de datos de la que se exporta.
    """

    def __init__(self, window: QWidget, db_path: str | None):
        self.w = window
        self._db_path = db_path
        today = QDate.currentDate()
        self.w.input_fecha_desde.setDate(today)
        self.w.input_fecha_hasta.setDate(today)
        self.w.input_fecha_desde.setCalendarPopup(True)
        self.w.input_fecha_hasta.setCalendarPopup(True)

        self.w.boton_exportar_escritorio.clicked.connect(self.export_to_desktop)
        self.w.boton_exportar_externo.clicked.connect(self.export_to_folder)
        self.w.boton_exportar_mail.clicked.connect(self.export_by_email)

    # ── Datos del formulario ──────────────────────────────────────────

    def date_range(self) -> tuple[date, date] | None:
        """Rango de fechas elegido, o None (con aviso) si "desde" es posterior a "hasta"."""
        desde = self.w.input_fecha_desde.date().toPyDate()
        hasta = self.w.input_fecha_hasta.date().toPyDate()
        if desde > hasta:
            QMessageBox.warning(
                self.w, "Fechas inválidas", "La fecha 'Desde' es posterior a la fecha 'Hasta'."
            )
            return None
        return desde, hasta

    def filename(self, desde: date, hasta: date) -> str:
        """Nombre del archivo: Historial_AAAA-MM-DD[_AAAA-MM-DD].xlsx."""
        if desde == hasta:
            return f"Historial_{desde.isoformat()}.xlsx"
        return f"Historial_{desde.isoformat()}_{hasta.isoformat()}.xlsx"

    def recipients(self) -> list[str] | None:
        """Direcciones cargadas, o None (con aviso) si alguna es inválida o no hay ninguna."""
        values = [getattr(self.w, f"input_mail_{i}").text().strip() for i in range(1, 6)]
        values = [v for v in values if v]
        invalid = [v for v in values if not _EMAIL.match(v)]
        if invalid:
            QMessageBox.warning(self.w, "Direcciones inválidas", "Revisar: " + ", ".join(invalid))
            return None
        if not values:
            QMessageBox.warning(self.w, "Sin destinatarios", "Cargue al menos una dirección.")
            return None
        return values

    # ── Exportaciones ─────────────────────────────────────────────────

    def _export(self, folder: str | Path) -> str | None:
        rango = self.date_range()
        if rango is None:
            return None
        output = Path(folder) / self.filename(*rango)
        try:
            return export_to_excel(str(output), *rango, db_path=self._db_path)
        except OSError as e:
            QMessageBox.critical(self.w, "No se pudo exportar", f"{output}\n\n{e}")
            return None

    def desktop_dir(self) -> str:
        """Escritorio del usuario (en Windows puede estar dentro de OneDrive)."""
        return QStandardPaths.writableLocation(QStandardPaths.DesktopLocation)

    def export_to_desktop(self) -> str | None:
        """Exporta el Excel al escritorio."""
        path = self._export(self.desktop_dir())
        if path:
            QMessageBox.information(self.w, "Exportado", f"Historial exportado en:\n{path}")
        return path

    def export_to_folder(self) -> str | None:
        """Exporta el Excel a una carpeta elegida (pendrive u otra unidad)."""
        folder = QFileDialog.getExistingDirectory(
            self.w, "Elegir carpeta o unidad de destino", self.desktop_dir()
        )
        if not folder:
            return None
        path = self._export(folder)
        if path:
            QMessageBox.information(self.w, "Exportado", f"Historial exportado en:\n{path}")
        return path

    def export_by_email(self) -> bool:
        """Exporta el Excel y lo envía por mail a las direcciones cargadas."""
        recipients = self.recipients()
        if recipients is None:
            return False
        with tempfile.TemporaryDirectory() as tmp:
            path = self._export(tmp)
            if path is None:
                return False
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            try:
                sent = send_email_with_attachment(
                    recipients,
                    path,
                    subject=f"Historiales de ensayos - {Path(path).stem}",
                    body="Se adjuntan los historiales de ensayos de seguridad eléctrica.",
                )
            finally:
                QApplication.restoreOverrideCursor()
        if sent:
            QMessageBox.information(self.w, "Enviado", "Mail enviado a: " + ", ".join(recipients))
        else:
            QMessageBox.critical(
                self.w,
                "No se pudo enviar",
                "No se pudo enviar el mail. Verificar la conexión y la configuración SMTP "
                "(SMTP_HOST, SMTP_PORT, SMTP_USER y SMTP_PASSWORD en .env).",
            )
        return sent

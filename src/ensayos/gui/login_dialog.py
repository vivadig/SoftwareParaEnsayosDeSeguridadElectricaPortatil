"""Diálogo de login para acceder al panel de administración."""

import logging
from pathlib import Path

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox

from ensayos.config.config_gui import gui_config
from ensayos.database.sqlite_repository import SQLiteConfigRepository
from ensayos.gui.styles import INPUT_ERROR

logger = logging.getLogger(__name__)


class LoginDialog(QtWidgets.QMainWindow):
    """Ventana de login que valida credenciales contra la DB."""

    def __init__(self, config_repo: SQLiteConfigRepository, parent=None):
        super().__init__(parent)
        ui_path = Path(gui_config.ui_dir) / "login.ui"
        uic.loadUi(str(ui_path), self)
        self.setWindowTitle("Login")

        self._config_repo = config_repo
        self._admin_window = None

        self.boton_aceptar.clicked.connect(self._verificar_credenciales)
        self.boton_cancelar.clicked.connect(self.close)

    def _verificar_credenciales(self) -> None:
        usuario = self.input_user.text()
        contrasena = self.input_password.text()

        credentials = self._config_repo.get_admin_credentials()
        if credentials is None:
            QMessageBox.critical(self, "Error", "No hay credenciales de admin configuradas.")
            return

        admin_user, admin_pass = credentials

        if usuario == admin_user and contrasena == admin_pass:
            self.input_user.clear()
            self.input_password.clear()
            self.input_user.setStyleSheet("")
            self.input_password.setStyleSheet("")
            self._abrir_admin()
        else:
            self.input_user.setStyleSheet(INPUT_ERROR)
            self.input_password.setStyleSheet(INPUT_ERROR)
            QMessageBox.warning(self, "Error de Login", "Usuario o contraseña incorrectos.")

    def _abrir_admin(self) -> None:
        from ensayos.gui.admin_dialog import AdminDialog

        self._admin_window = AdminDialog(self._config_repo)
        self._admin_window.show()
        self.close()

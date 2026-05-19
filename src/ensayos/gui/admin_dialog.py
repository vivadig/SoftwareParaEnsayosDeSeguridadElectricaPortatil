"""Panel de administración: correcciones de calibración y patrones de verificación."""

import logging
from pathlib import Path

from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import QMessageBox

from ensayos.config.config_gui import gui_config
from ensayos.database.sqlite_repository import SQLiteConfigRepository

logger = logging.getLogger(__name__)


class AdminDialog(QtWidgets.QMainWindow):
    """Ventana de administración para correcciones y cotas de verificación."""

    def __init__(self, config_repo: SQLiteConfigRepository, parent=None):
        super().__init__(parent)
        ui_path = Path(gui_config.ui_dir) / "admin.ui"
        uic.loadUi(str(ui_path), self)
        self.setWindowTitle("Admin")

        self._config_repo = config_repo

        self.boton_aplicar.clicked.connect(self._guardar)
        self.boton_cancelar.clicked.connect(self.close)

        self._cargar_datos()

    def _cargar_datos(self) -> None:
        correcciones = self._config_repo.get_corrections()
        if correcciones:
            self.input_correccion_tension.setValue(float(correcciones.get("tension", 0)))
            self.input_correccion_corriente.setValue(float(correcciones.get("corriente", 0)))
            self.input_correccion_fuga_activa.setValue(float(correcciones.get("fuga", 0)))
            self.input_correccion_fuga_pasiva.setValue(float(correcciones.get("corte_neutro", 0)))
            self.input_correccion_puesta_a_tierra.setValue(float(correcciones.get("puesta_a_tierra", 0)))
            self.input_correccion_rigidez_dielectrica.setValue(float(correcciones.get("tension_resistida", 0)))

        cotas = self._config_repo.get_verification_patterns()
        if cotas:
            self.input_cota_verificacion_fuga_pasa.setValue(float(cotas.get("fuga_pasa", 0)))
            self.input_cota_verificacion_pat_pasa.setValue(float(cotas.get("pat_pasa", 0)))
            self.input_cota_verificacion_rd_pasa.setValue(float(cotas.get("rd_pasa", 0)))
            self.input_cota_verificacion_fuga_falla.setValue(float(cotas.get("fuga_falla", 0)))
            self.input_cota_verificacion_pat_falla.setValue(float(cotas.get("pat_falla", 0)))
            self.input_cota_verificacion_rd_falla.setValue(float(cotas.get("rd_falla", 0)))

    def _guardar(self) -> None:
        try:
            self._config_repo.save_corrections(
                tension=self.input_correccion_tension.value(),
                corriente=self.input_correccion_corriente.value(),
                fuga=self.input_correccion_fuga_activa.value(),
                corte_neutro=self.input_correccion_fuga_pasiva.value(),
                puesta_a_tierra=self.input_correccion_puesta_a_tierra.value(),
                tension_resistida=self.input_correccion_rigidez_dielectrica.value(),
            )

            self._config_repo.save_verification_patterns(
                fuga_pasa=self.input_cota_verificacion_fuga_pasa.value(),
                pat_pasa=self.input_cota_verificacion_pat_pasa.value(),
                rd_pasa=self.input_cota_verificacion_rd_pasa.value(),
                fuga_falla=self.input_cota_verificacion_fuga_falla.value(),
                pat_falla=self.input_cota_verificacion_pat_falla.value(),
                rd_falla=self.input_cota_verificacion_rd_falla.value(),
            )

            # Cambio de contraseña (opcional)
            pwd_actual = self.input_password_actual.text()
            pwd_nueva = self.input_password_nueva.text()
            if pwd_actual or pwd_nueva:
                credentials = self._config_repo.get_admin_credentials()
                if credentials and pwd_actual == credentials[1]:
                    self._config_repo.set_admin_password(pwd_nueva)
                else:
                    QMessageBox.warning(self, "Contraseña incorrecta", "La contraseña actual es incorrecta.")
                    return

            QMessageBox.information(self, "Datos guardados", "Los datos se han guardado correctamente.")

        except Exception:
            logger.exception("Error al guardar datos admin")
            QMessageBox.critical(self, "Error", "Ocurrió un error al guardar los datos.")

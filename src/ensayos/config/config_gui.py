"""Configuración de la interfaz gráfica."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class GuiConfig:
    """Configuración de la interfaz PyQt5."""

    theme: str = os.environ.get("GUI_THEME", "dark")
    ui_dir: str = os.environ.get("GUI_UI_DIR", "src/ensayos/gui/resources")


gui_config = GuiConfig()

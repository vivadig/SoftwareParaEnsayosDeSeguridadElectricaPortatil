"""Configuración de la interfaz gráfica."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class GuiConfig:
    """Configuración de la interfaz PyQt5."""

    theme: str = os.environ.get("GUI_THEME", "dark")
    ui_dir: str = os.environ.get(
        "GUI_UI_DIR", str(Path(__file__).resolve().parents[1] / "gui" / "resources")
    )


gui_config = GuiConfig()

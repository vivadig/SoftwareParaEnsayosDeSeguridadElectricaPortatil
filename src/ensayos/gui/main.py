"""Entry point de la aplicación GUI de ensayos de seguridad eléctrica."""

import logging
import sys

from dotenv import load_dotenv


def main() -> None:
    """Inicia la aplicación PyQt5."""
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from PyQt5.QtWidgets import QApplication

    from ensayos.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    window = MainWindow()
    window.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

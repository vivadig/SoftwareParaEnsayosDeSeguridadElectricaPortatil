"""Widget stub para gráficos en vivo (LivePlotWidget)."""

from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt


class LivePlotWidget(QWidget):
    """Widget stub para gráficos en tiempo real."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgb(0, 0, 0); border: 1px solid rgb(58, 58, 58);")

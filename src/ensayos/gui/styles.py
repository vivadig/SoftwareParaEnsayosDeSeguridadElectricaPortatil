"""Estilos CSS para los widgets de la GUI."""

BUTTON_NORMAL = """QPushButton {
    font: 13pt;
    border: 1px solid rgb(160, 160, 160);
    color: white;
    padding: 6px;
    background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.5, y2:0,
    stop:0 rgba(77,77,77,255), stop:1 rgba(97,97,97,255));}
QPushButton:hover {background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.5, y2:0, stop:0 rgba(107,107,107,255), stop:1 rgba(157,157,157,255));}
QPushButton:pressed {background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.5, y2:0, stop:0 rgba(77,77,77,255), stop:1 rgba(97,97,97,255));}
QPushButton:disabled {color: grey; background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.5, y2:0, stop:0 rgba(57,57,57,255), stop:1 rgba(77,77,77,255));}"""

BUTTON_ACTIVE = """QPushButton {
    font: bold 13pt;
    border-style: outset;
    border: 1px solid rgb(160, 160, 160);
    color: black;
    padding: 6px;
    background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.5, y2:0, stop:0 rgba(255, 170, 0, 255), stop:1 rgba(152, 120, 61, 255));}
QPushButton:hover, QPushButton:pressed, QPushButton:disabled {
    border-style: solid;
    border-width: 2px;
    padding: 6px;}
QPushButton:hover {
    border-top-color: qlineargradient(spread:pad, x1:0.5, y1:0.6, x2:0.5, y2:0.4, stop:0 rgba(180, 180, 180, 255), stop:1 rgba(110, 110, 110, 255));
    border-right-color: qlineargradient(spread:pad, x1:0.4, y1:0.5, x2:0.6, y2:0.5, stop:0 rgba(180, 180, 180, 255), stop:1 rgba(110, 110, 110, 255));
    border-left-color: qlineargradient(spread:pad, x1:0.6, y1:0.5, x2:0.4, y2:0.5, stop:0 rgba(180, 180, 180, 255), stop:1 rgba(110, 110, 110, 255));
    border-bottom-color: rgb(115, 115, 115);
    border-bottom-width: 1px;
    background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.5, y2:0, stop:0 rgba(255, 180, 0, 255), stop:1 rgba(182, 150, 61, 255));}
QPushButton:pressed {
    border-top-color: qlineargradient(spread:pad, x1:0.5, y1:0.6, x2:0.5, y2:0.4, stop:0 rgba(62, 62, 62, 255), stop:1 rgba(22, 22, 22, 255));
    border-right-color: qlineargradient(spread:pad, x1:0.4, y1:0.5, x2:0.6, y2:0.5, stop:0 rgba(115, 115, 115, 255), stop:1 rgba(62, 62, 62, 255));
    border-left-color: qlineargradient(spread:pad, x1:0.6, y1:0.5, x2:0.4, y2:0.5, stop:0 rgba(115, 115, 115, 255), stop:1 rgba(62, 62, 62, 255));
    border-bottom-color: rgb(58, 58, 58);
    border-bottom-width: 1px;
    background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.5, y2:0, stop:0 rgba(77, 77, 77, 255), stop:1 rgba(97, 97, 97, 255));}
QPushButton:disabled {
    color: #4d4d4d;
    border-top-color: qlineargradient(spread:pad, x1:0.5, y1:0.6, x2:0.5, y2:0.4, stop:0 rgba(115, 115, 115, 255), stop:1 rgba(62, 62, 62, 255));
    border-right-color: qlineargradient(spread:pad, x1:0.4, y1:0.5, x2:0.6, y2:0.5, stop:0 rgba(115, 115, 115, 255), stop:1 rgba(62, 62, 62, 255));
    border-left-color: qlineargradient(spread:pad, x1:0.6, y1:0.5, x2:0.4, y2:0.5, stop:0 rgba(115, 115, 115, 255), stop:1 rgba(62, 62, 62, 255));
    border-bottom-color: rgb(58, 58, 58);
    border-bottom-width: 1px;
    background-color: qlineargradient(spread:pad, x1:0.5, y1:1, x2:0.5, y2:0, stop:0 rgba(235, 150, 0, 255), stop:1 rgba(132, 100, 41, 255));}"""

PROGRESS_BAR_NORMAL = """QProgressBar {
    border: 2px solid black;
    text-align: top; padding: 1px;
    border-radius: 5px;
    background: QLinearGradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #eeeeee, stop: 1 #bbbbbb);
    width: 15px;
}
QProgressBar::chunk {
    background: QLinearGradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #0b00ad, stop: 0.5 #101cff, stop: 1 #101cff);
    border-radius: 4px;
    border: 1px solid black;
}"""

PROGRESS_BAR_GREEN = """QProgressBar {
    border: 2px solid black;
    text-align: top; padding: 1px;
    border-radius: 5px;
    background: QLinearGradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #eeeeee, stop: 1 #bbbbbb);
    width: 15px;
}
QProgressBar::chunk {
    background: QLinearGradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #0bad00, stop: 0.5 #22bc00, stop: 1 #22bc00);
    border-radius: 4px;
    border: 1px solid black;
}"""

PROGRESS_BAR_RED = """QProgressBar {
    border: 2px solid black;
    text-align: top; padding: 1px;
    border-radius: 5px;
    background: QLinearGradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #eeeeee, stop: 1 #bbbbbb);
    width: 15px;
}
QProgressBar::chunk {
    background: QLinearGradient(x1: 0, y1: 0, x2: 1, y2: 0, stop: 0 #ad0000, stop: 0.5 #ff0000, stop: 1 #ff0000);
    border-radius: 4px;
    border: 1px solid black;
}"""

INPUT_ERROR = "border: 1px solid red;"

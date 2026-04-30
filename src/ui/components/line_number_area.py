from PySide6.QtCore import QSize
from PySide6.QtWidgets import QWidget


class LineNumberArea(QWidget):
    """Widget lateral que desenha os números das linhas."""

    def __init__(self, editor):
        super().__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.codeEditor.line_number_area_paint_event(event)

import os
from PySide6.QtWidgets import QFrame, QVBoxLayout, QStackedWidget, QLabel, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QColor

class PreviewPanel(QFrame):
    """Painel para pré-visualização de arquivos."""
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewPanel")
        self.setMinimumWidth(200)
        self.current_pixmap = None # Armazena a pixmap original para re-escalonamento
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)
        
        # Page 0: Placeholder
        self.placeholder = QLabel("Selecione um arquivo para pré-visualizar")
        self.placeholder.setAlignment(Qt.AlignCenter)
        
        # Page 1: Text Preview
        self.text_preview = QTextEdit()
        self.text_preview.setReadOnly(True)
        
        # Page 2: Image Preview
        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        
        self.stack.addWidget(self.placeholder)
        self.stack.addWidget(self.text_preview)
        self.stack.addWidget(self.image_preview)
        
        self.apply_theme(theme)

    def apply_theme(self, theme):
        bg = theme.get("background", "#1e1e1e")
        fg = theme.get("foreground", "#cccccc")
        border = theme.get("border_color", "#454545")
        
        self.setStyleSheet(f"#PreviewPanel {{ background-color: {bg}; border-left: 1px solid {border}; }}")
        self.placeholder.setStyleSheet(f"color: {QColor(fg).darker(130).name()};")
        self.text_preview.setStyleSheet(f"background-color: {bg}; color: {fg}; border: none;")
        
    def show_preview(self, path):
        self.current_pixmap = None
        if not path or os.path.isdir(path):
            self.stack.setCurrentWidget(self.placeholder)
            return

        ext = os.path.splitext(path)[1].lower()
        
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp']:
            self.current_pixmap = QPixmap(path)
            if not self.current_pixmap.isNull():
                self.image_preview.setPixmap(self.current_pixmap.scaled(self.image_preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                self.stack.setCurrentWidget(self.image_preview)
                return
        
        try:
            if os.path.getsize(path) < 2 * 1024 * 1024: # 2MB limit
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(10000)
                    self.text_preview.setPlainText(content)
                    self.stack.setCurrentWidget(self.text_preview)
                    return
        except Exception:
            pass

        self.stack.setCurrentWidget(self.placeholder)

    def resizeEvent(self, event):
        if self.stack.currentWidget() == self.image_preview and self.current_pixmap:
            self.image_preview.setPixmap(self.current_pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        super().resizeEvent(event)
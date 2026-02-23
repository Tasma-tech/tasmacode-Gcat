from PySide6.QtWidgets import QStatusBar, QLabel, QPushButton, QWidget, QHBoxLayout, QStyle, QMenu
from PySide6.QtCore import Qt, QTimer, QSize

class StatusBar(QStatusBar):
    """Barra de status customizada."""
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Remove a alça de redimensionamento padrão para visual mais limpo
        self.setSizeGripEnabled(False)
        
        # Container para widgets da direita
        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(10)
        
        # Widgets
        self.lbl_cursor = self._create_label("Ln 1, Col 1", min_width=100)
        self.lbl_indent = self._create_label("Spaces: 4", min_width=80)
        self.lbl_encoding = self._create_label("UTF-8", min_width=60)
        
        # Botão de Linguagem (Interativo)
        self.btn_lang = QPushButton("Python")
        self.btn_lang.setFlat(True)
        self.btn_lang.setStyleSheet("color: white; border: none; padding: 0 5px; text-align: left;")
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setMinimumWidth(80)
        
        # Menu de Linguagens
        self.lang_menu = QMenu(self)
        self.lang_menu.setStyleSheet("QMenu { background-color: #252526; color: #cccccc; } QMenu::item:selected { background-color: #007acc; }")
        for lang in ["Python", "JavaScript", "HTML", "CSS", "C++", "Rust", "Plain Text"]:
            self.lang_menu.addAction(lang, lambda l=lang: self.update_lang(l))
        self.btn_lang.setMenu(self.lang_menu)
        
        self.btn_bell = QPushButton()
        self.btn_bell.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.btn_bell.setFlat(True)
        self.btn_bell.setFixedSize(20, 20)
        self.btn_bell.setStyleSheet("border: none;")
        self.btn_bell.setCursor(Qt.CursorShape.PointingHandCursor)

        # Adiciona ao layout
        self.right_layout.addWidget(self.lbl_cursor)
        self.right_layout.addWidget(self.lbl_indent)
        self.right_layout.addWidget(self.lbl_encoding)
        self.right_layout.addWidget(self.btn_lang)
        self.right_layout.addWidget(self.btn_bell)

        self.addPermanentWidget(self.right_container)
        
        # Timer para restaurar estilo após flash
        self.flash_timer = QTimer(self)
        self.flash_timer.setSingleShot(True)
        self.flash_timer.timeout.connect(self._reset_style)
        
        self._default_style = "background-color: #007acc; color: white;"
        self.setStyleSheet(self._default_style)
        self.showMessage("Pronto")

    def _create_label(self, text, min_width=0):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: white; padding: 0 5px;")
        if min_width > 0:
            lbl.setMinimumWidth(min_width)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def update_cursor_info(self, line, col):
        self.lbl_cursor.setText(f"Ln {line+1}, Col {col+1}")

    def update_filename(self, filename: str):
        self.showMessage(filename)

    def update_lang(self, lang):
        self.btn_lang.setText(lang)

    def flash_message(self, text, color="#28a745", duration=2000):
        """Exibe uma mensagem com cor de fundo temporária (Feedback Visual)."""
        self.showMessage(text)
        self.setStyleSheet(f"background-color: {color}; color: white;")
        self.flash_timer.start(duration)

    def _reset_style(self):
        self.setStyleSheet(self._default_style)
        self.clearMessage()
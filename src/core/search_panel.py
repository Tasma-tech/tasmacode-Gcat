from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QCheckBox
from PySide6.QtCore import Signal

class SearchPanel(QWidget):
    """A panel for find and replace operations."""
    
    # Signals
    find_next = Signal(str, bool, bool) # text, case_sensitive, whole_word
    replace_one = Signal(str, str, bool, bool)
    replace_all = Signal(str, str, bool, bool)
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SearchPanel")
        self.setFixedHeight(40)
        self.setStyleSheet("""
            QWidget#SearchPanel {
                background-color: #252526;
                border-bottom: 1px solid #3e3e42;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #313131;
                color: #cccccc;
                padding: 2px;
            }
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #313131;
                color: #cccccc;
                width: 80px;
                height: 24px;
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
            QCheckBox {
                color: #cccccc;
                spacing: 5px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(5)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find")
        
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace")

        self.check_whole_word = QCheckBox("Whole Word")
        
        self.btn_find_next = QPushButton("Find Next")
        self.btn_replace = QPushButton("Replace")
        self.btn_replace_all = QPushButton("Replace All")
        
        self.btn_close = QPushButton("X")
        self.btn_close.setFixedWidth(24)

        layout.addWidget(self.find_input)
        layout.addWidget(self.btn_find_next)
        layout.addWidget(self.replace_input)
        layout.addWidget(self.btn_replace)
        layout.addWidget(self.btn_replace_all)
        layout.addWidget(self.check_whole_word)
        layout.addStretch()
        layout.addWidget(self.btn_close)
        
        # Connections
        self.btn_close.clicked.connect(self.closed.emit)
        self.btn_find_next.clicked.connect(self._on_find_next)
        self.btn_replace.clicked.connect(self._on_replace_one)
        self.btn_replace_all.clicked.connect(self._on_replace_all)
        self.find_input.textChanged.connect(self._on_find_text_changed)
        
        self.hide()

    def _on_find_text_changed(self, text):
        self.find_next.emit(text, False, self.check_whole_word.isChecked())

    def _on_find_next(self):
        self.find_next.emit(self.find_input.text(), False, self.check_whole_word.isChecked())

    def _on_replace_one(self):
        self.replace_one.emit(self.find_input.text(), self.replace_input.text(), False, self.check_whole_word.isChecked())

    def _on_replace_all(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        self.replace_all.emit(find_text, replace_text, False, self.check_whole_word.isChecked())

    def show_panel(self):
        self.show()
        self.find_input.setFocus()
        self.find_input.selectAll()
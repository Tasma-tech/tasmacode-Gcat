from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QToolBar, QStyle)
from PySide6.QtCore import Qt
from src.core.logic_motor_pdf import PdfEngine, PdfSurface

class PdfViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = PdfEngine(self)
        self.surface = PdfSurface(self)
        
        self.current_page = 0
        self.total_pages = 0
        
        self._setup_ui()
        
        # Conectar sinais do motor à UI
        self.engine.document_loaded.connect(self._on_document_loaded)
        self.engine.page_rendered.connect(self._on_page_rendered)
        self.engine.error_occurred.connect(self._on_error)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Toolbar de navegação
        toolbar = QToolBar()
        toolbar.setStyleSheet("QToolBar { background-color: #252526; border-bottom: 1px solid #3e3e42; } QPushButton { background-color: transparent; border: none; color: white; }")
        
        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.btn_prev.setToolTip("Página Anterior")
        self.btn_prev.clicked.connect(self.show_previous_page)
        self.btn_prev.setEnabled(False)

        self.btn_next = QPushButton()
        self.btn_next.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.btn_next.setToolTip("Próxima Página")
        self.btn_next.clicked.connect(self.show_next_page)
        self.btn_next.setEnabled(False)

        self.lbl_page_info = QLabel("Página 0 de 0")
        self.lbl_page_info.setStyleSheet("padding: 0 10px;")

        toolbar.addWidget(self.btn_prev)
        toolbar.addWidget(self.btn_next)
        toolbar.addWidget(self.lbl_page_info)
        
        main_layout.addWidget(toolbar)
        main_layout.addWidget(self.surface)

    def load_file(self, path):
        """Inicia o carregamento do documento PDF."""
        if self.engine.load_document(path):
            self.engine.render_page(0)

    def show_page(self, page_number):
        if 0 <= page_number < self.total_pages:
            self.engine.render_page(page_number)

    def show_next_page(self):
        self.show_page(self.current_page + 1)

    def show_previous_page(self):
        self.show_page(self.current_page - 1)

    def _on_document_loaded(self, page_count):
        self.total_pages = page_count
        self.show_page(0)

    def _on_page_rendered(self, page_index, page_image):
        self.surface.display_page(page_image)
        self.current_page = page_index
        self.lbl_page_info.setText(f"Página {self.current_page + 1} de {self.total_pages}")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(self.current_page < self.total_pages - 1)

    def _on_error(self, error_message):
        self.lbl_page_info.setText(f"Erro: {error_message}")

    def closeEvent(self, event):
        self.engine.close_document()
        super().closeEvent(event)
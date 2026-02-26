import os
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtSvgWidgets import QSvgWidget

class AboutWindow(QDialog):
    """Janela de diálogo 'Sobre'."""
    
    def __init__(self, about_info, root_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Sobre {about_info.app_name}")
        self.setFixedSize(400, 380)
        self.setStyleSheet("background-color: #252526; color: #cccccc;")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        
        # Ícone (SVG)
        icon_full_path = os.path.join(root_path, about_info.icon_relative_path)
        if os.path.exists(icon_full_path):
            svg_widget = QSvgWidget(icon_full_path)
            svg_widget.setFixedSize(100, 100)
            layout.addWidget(svg_widget, 0, Qt.AlignmentFlag.AlignCenter)
        else:
            # Fallback caso o ícone não exista
            lbl_missing = QLabel("[Ícone não encontrado]")
            layout.addWidget(lbl_missing, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Título
        lbl_title = QLabel(about_info.app_name)
        lbl_title.setStyleSheet("font-size: 26px; font-weight: bold; color: white; margin-top: 10px;")
        layout.addWidget(lbl_title, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Versão
        lbl_ver = QLabel(f"Versão {about_info.version}")
        lbl_ver.setStyleSheet("font-size: 14px; color: #858585;")
        layout.addWidget(lbl_ver, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Descrição
        lbl_desc = QLabel(about_info.description)
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setStyleSheet("padding: 10px;")
        layout.addWidget(lbl_desc, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Criador (Link)
        link_text = f"Criado por: <a href='{about_info.creator_url}' style='color: #007acc; text-decoration: none;'>{about_info.creator_name}</a>"
        lbl_creator = QLabel(link_text)
        lbl_creator.setOpenExternalLinks(True)
        lbl_creator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_creator, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addSpacing(20)
        
        # Botão Fechar
        btn_close = QPushButton("Fechar")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton { background-color: #3c3c3c; border: 1px solid #454545; padding: 8px 25px; color: white; border-radius: 4px; }
            QPushButton:hover { background-color: #4f4f4f; }
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignCenter)
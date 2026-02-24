from PySide6.QtWidgets import QWidget, QVBoxLayout
from src.core.logic_motor_imgs import ImageEngine, ImageSurface

class ImageViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = ImageEngine(self)
        self.surface = ImageSurface(self)
        
        self._setup_ui()
        
        # Conecta o sinal de carregamento do motor à superfície de exibição
        self.engine.image_loaded.connect(self.surface.display_content)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.surface)

    def load_file(self, path):
        """Inicia o carregamento da imagem via motor."""
        self.engine.load_source(path)
import os
from PySide6.QtCore import QObject, Signal, QFileInfo
from PySide6.QtGui import QImageReader, QPixmap, QMovie

class ImageEngine(QObject):
    """
    Responsável exclusivamente pela lógica de carregamento de imagens.
    Identifica se a imagem é estática ou animada e prepara o objeto Qt adequado.
    """
    
    # Emite (objeto_imagem, is_animated)
    # objeto_imagem pode ser QPixmap ou QMovie
    image_loaded = Signal(object, bool)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def load_source(self, file_path: str):
        """Carrega a imagem do caminho especificado."""
        if not os.path.exists(file_path):
            self.error_occurred.emit(f"Arquivo não encontrado: {file_path}")
            return

        info = QFileInfo(file_path)
        suffix = info.suffix().lower()
        
        # Formatos que o Qt geralmente suporta como animação
        animated_formats = ['gif', 'webp'] 
        
        if suffix in animated_formats:
            self._load_animated(file_path)
        else:
            self._load_static(file_path)

    def _load_animated(self, path):
        movie = QMovie(path)
        if movie.isValid():
            # Pula para o primeiro frame para garantir que tem dados
            movie.jumpToFrame(0)
            self.image_loaded.emit(movie, True)
        else:
            # Fallback: tenta carregar como estático se o QMovie falhar
            self._load_static(path)

    def _load_static(self, path):
        reader = QImageReader(path)
        reader.setAutoTransform(True) # Aplica rotação EXIF automaticamente
        image = reader.read()
        
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.image_loaded.emit(pixmap, False)
        else:
            self.error_occurred.emit(f"Falha ao decodificar imagem: {reader.errorString()}")
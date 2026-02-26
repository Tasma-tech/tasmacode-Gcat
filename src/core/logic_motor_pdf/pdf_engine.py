import logging
import sys
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage

try:
    import fitz  # PyMuPDF - (pip install PyMuPDF)
except ImportError:
    fitz = None

logger = logging.getLogger("PdfEngine")

class PdfEngine(QObject):
    """
    Manipula a lógica de carregar e renderizar documentos PDF usando PyMuPDF.
    Esta classe é independente de qualquer representação de UI.
    """
    document_loaded = Signal(int)  # Emite a contagem de páginas no carregamento bem-sucedido
    page_rendered = Signal(int, QImage) # Emite (índice_da_página, página_como_qimage)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.doc = None
        self.file_path = None

    def load_document(self, file_path: str) -> bool:
        """Carrega um documento PDF do caminho fornecido."""
        if fitz is None:
            msg = f"PyMuPDF não encontrado no Python: {sys.executable}\nInstale com: pip install PyMuPDF"
            logger.error(msg)
            self.error_occurred.emit(msg)
            return False
            
        try:
            if self.doc:
                self.close_document()
            
            self.doc = fitz.open(file_path)
            self.file_path = file_path
            
            if self.doc.is_encrypted and not self.doc.authenticate(""):
                self.error_occurred.emit("O documento está criptografado e requer uma senha.")
                self.doc = None
                return False

            logger.info(f"Documento PDF carregado: {file_path} ({self.doc.page_count} páginas)")
            self.document_loaded.emit(self.doc.page_count)
            return True
        except Exception as e:
            logger.error(f"Falha ao carregar PDF {file_path}: {e}")
            self.error_occurred.emit(str(e))
            self.doc = None
            return False

    def render_page(self, page_index: int, zoom_factor: float = 2.0):
        """
        Renderiza uma única página para uma QImage com um determinado fator de zoom.
        Um fator de zoom maior resulta em uma imagem de maior resolução.
        """
        if not self.doc or not (0 <= page_index < self.doc.page_count):
            return

        try:
            page = self.doc.load_page(page_index)
            
            matrix = fitz.Matrix(zoom_factor, zoom_factor)
            
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            
            if pix.alpha:
                image_format = QImage.Format_RGBA8888
            else:
                image_format = QImage.Format_RGB888

            qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, image_format)
            
            self.page_rendered.emit(page_index, qimage.copy())
            
        except Exception as e:
            logger.error(f"Falha ao renderizar página {page_index}: {e}")
            self.error_occurred.emit(f"Erro ao renderizar página {page_index}: {e}")

    def get_page_count(self) -> int:
        """Retorna o número de páginas no documento carregado."""
        return self.doc.page_count if self.doc else 0

    def close_document(self):
        """Fecha o documento e libera recursos."""
        if self.doc:
            self.doc.close()
            self.doc = None
            self.file_path = None
            logger.info("Documento PDF fechado.")
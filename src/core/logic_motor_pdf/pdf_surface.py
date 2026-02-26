from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QBrush, QColor, QImage

class PdfSurface(QGraphicsView):
    """
    Um widget baseado em QGraphicsView para exibir uma página de PDF renderizada.
    Lida com interações do usuário como zoom e pan.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        
        # Configurações de UI e renderização
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        
        self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        
        self._pixmap_item = None

    def display_page(self, page_image: QImage):
        """
        Limpa a cena e exibe a nova imagem da página.
        """
        self._scene.clear()
        pixmap = QPixmap.fromImage(page_image)
        self._pixmap_item = self._scene.addPixmap(pixmap)
        self.fit_in_view_if_needed()

    def fit_in_view_if_needed(self):
        """Ajusta o conteúdo à visualização, mantendo a proporção."""
        if self._pixmap_item:
            self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent):
        """Lida com eventos da roda do mouse para zoom."""
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
            
    def resizeEvent(self, event):
        """Lida com o redimensionamento para ajustar o conteúdo."""
        super().resizeEvent(event)
        self.fit_in_view_if_needed()
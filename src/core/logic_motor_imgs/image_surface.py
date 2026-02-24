from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QMovie, QPainter, QWheelEvent, QBrush, QColor

class ImageSurface(QGraphicsView):
    """
    Widget de visualização baseado em QGraphicsView.
    Suporta Zoom (Roda do Mouse) e Pan (Arrastar).
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        
        # Configurações para performance e qualidade
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag) # Permite arrastar a imagem
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse) # Zoom foca no mouse
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        
        # Remove barras de rolagem (opcional, para visual mais limpo)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Fundo escuro
        self.setBackgroundBrush(QBrush(QColor("#1e1e1e")))
        
        self._current_movie = None # Referência para manter o GIF vivo

    def display_content(self, data, is_animated: bool):
        """
        Exibe o conteúdo na cena.
        Args:
            data: QPixmap ou QMovie
            is_animated: Booleano indicando o tipo
        """
        self._scene.clear()
        self._current_movie = None
        
        if is_animated and isinstance(data, QMovie):
            self._display_animated(data)
        elif isinstance(data, QPixmap):
            self._display_static(data)
            
        # Ajusta a imagem à vista inicial
        self._fit_to_view()

    def _display_static(self, pixmap: QPixmap):
        self._scene.addPixmap(pixmap)

    def _display_animated(self, movie: QMovie):
        self._current_movie = movie
        # QGraphicsView não anima QMovie nativamente, usamos um QLabel via Proxy
        label = QLabel()
        label.setAttribute(Qt.WA_TranslucentBackground)
        label.setMovie(movie)
        movie.start()
        
        self._scene.addWidget(label)

    def _fit_to_view(self):
        """Reseta o zoom para caber na janela."""
        self.resetTransform()
        if self._scene.itemsBoundingRect().isValid():
            self.fitInView(self._scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event: QWheelEvent):
        """Implementa Zoom com a roda do mouse."""
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)
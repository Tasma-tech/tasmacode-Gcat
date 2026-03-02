"""
Sistema de Renderização
Responsabilidade: Desenhar o efeito visual usando QPainter
"""
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF
from PySide6.QtCore import QPointF
from typing import List

class SmearRenderer:
    def __init__(self):
        self.cursor_color = QColor(0, 255, 0)
        
    def render_smear(self, painter: QPainter, corners: List[List[float]]):
        """Renderiza o smear cursor usando QPainter"""
        if not corners or len(corners) < 4:
            return
            
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Converte cantos para pontos Qt
        points = [QPointF(corner[0], corner[1]) for corner in corners]
        
        # Cria efeito de fade com múltiplas camadas
        for i in range(5):
            alpha = 255 - (i * 40)
            color = QColor(self.cursor_color)
            color.setAlpha(alpha)
            
            pen = QPen(color, 2)
            painter.setPen(pen)
            brush = QBrush(color)
            painter.setBrush(brush)
            
            # Desenha polígono escalonado
            scaled_points = self._scale_points(points, 1 - i * 0.1)
            polygon = QPolygonF(scaled_points)
            painter.drawPolygon(polygon)
            
    def _scale_points(self, points: List[QPointF], factor: float) -> List[QPointF]:
        """Escala pontos em relação ao centro"""
        if not points:
            return []
            
        center = QPointF(sum(p.x() for p in points) / len(points), sum(p.y() for p in points) / len(points))
        
        scaled = [center + (point - center) * factor for point in points]
            
        return scaled
"""
Sistema de Renderização
Responsabilidade: Desenhar o efeito visual usando QPainter
"""
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QPolygonF, QRadialGradient
from PySide6.QtCore import QPointF, Qt
from typing import List
import random

class SmearRenderer:
    def __init__(self):
        self.cursor_color = QColor(0, 255, 0)
        self.mode = 'solid'
        
    def set_color(self, color: QColor):
        self.cursor_color = color
        
    def set_mode(self, mode: str):
        self.mode = mode
        
    def render_smear(self, painter: QPainter, corners: List[List[float]]):
        """Renderiza o smear cursor usando QPainter"""
        if not corners or len(corners) < 4:
            return
            
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.mode == 'particles':
            self._render_particles(painter, corners)
        else:
            self._render_solid(painter, corners)
            
    def _render_solid(self, painter: QPainter, corners: List[List[float]]):
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
            
    def _render_particles(self, painter: QPainter, corners: List[List[float]]):
        points = [QPointF(corner[0], corner[1]) for corner in corners]
        center = QPointF(sum(p.x() for p in points) / len(points), sum(p.y() for p in points) / len(points))
        
        # Efeito de Glow (Brilho)
        radius = 40
        gradient = QRadialGradient(center, radius)
        glow_color = QColor(self.cursor_color)
        glow_color.setAlpha(100) # Centro semi-transparente
        gradient.setColorAt(0, glow_color)
        gradient.setColorAt(1, QColor(0, 0, 0, 0)) # Borda transparente
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(center, radius, radius)
        
        # Desenha partículas aleatórias dentro da área do rastro
        # Cria um efeito de "poeira" mágica seguindo o cursor
        for i in range(15):
            alpha = random.randint(50, 200)
            color = QColor(self.cursor_color)
            color.setAlpha(alpha)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(color))
            
            # Interpolação aleatória entre centro e cantos para espalhar as partículas
            corner_idx = random.randint(0, 3)
            factor = random.random()
            pt = center + (points[corner_idx] - center) * factor
            
            # Adiciona um pouco de caos (jitter)
            jitter_x = random.uniform(-2, 2)
            jitter_y = random.uniform(-2, 2)
            
            size = random.uniform(1, 4)
            painter.drawEllipse(pt + QPointF(jitter_x, jitter_y), size, size)
            
    def _scale_points(self, points: List[QPointF], factor: float) -> List[QPointF]:
        """Escala pontos em relação ao centro"""
        if not points:
            return []
            
        center = QPointF(sum(p.x() for p in points) / len(points), sum(p.y() for p in points) / len(points))
        
        scaled = [center + (point - center) * factor for point in points]
            
        return scaled
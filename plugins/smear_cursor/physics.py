"""
Sistema de Física de Molas
Responsabilidade: Calcular animação elástica baseada no sistema original
"""
import math
from typing import List, Tuple
from PySide6.QtCore import QRect

class SpringPhysics:
    def __init__(self):
        self.current_corners: List[List[float]] = [[0, 0], [0, 0], [0, 0], [0, 0]]
        self.target_corners: List[List[float]] = [[0, 0], [0, 0], [0, 0], [0, 0]]
        self.stiffnesses: List[float] = [0.6, 0.4, 0.3, 0.2]
        self.base_stiffness = 0.6
        
    def set_base_stiffness(self, value: float):
        self.base_stiffness = max(0.01, min(1.0, value))
        
    def update_physics(self):
        """Atualiza posições usando física de molas - baseado no original"""
        for i in range(4):
            for j in range(2):
                self.current_corners[i][j] += (
                    self.target_corners[i][j] - self.current_corners[i][j]
                ) * self.stiffnesses[i]

    def set_target(self, rect: QRect):
        """Define os cantos alvo com base em um QRect."""
        self.target_corners = [
            [rect.left(), rect.top()],
            [rect.right(), rect.top()],
            [rect.right(), rect.bottom()],
            [rect.left(), rect.bottom()],
        ]
                
    def _get_center(self, corners: List[List[float]]) -> Tuple[float, float]:
        """Calcula o ponto central de uma lista de cantos."""
        if not corners:
            return 0, 0
        x = sum(c[0] for c in corners) / len(corners)
        y = sum(c[1] for c in corners) / len(corners)
        return x, y

    def set_stiffnesses(self):
        """Calcula rigidez variável"""
        target_center = self._get_center(self.target_corners)
        distances = []
        
        for i in range(4):
            dist = math.sqrt(
                (self.current_corners[i][0] - target_center[0])**2 + 
                (self.current_corners[i][1] - target_center[1])**2
            )
            distances.append(dist)
            
        min_dist = min(distances) if distances else 0
        max_dist = max(distances) if distances else 1
        
        if max_dist == min_dist:
            self.stiffnesses = [self.base_stiffness] * 4
            return
            
        for i in range(4):
            if max_dist > min_dist:
                x = (distances[i] - min_dist) / (max_dist - min_dist)
                stiffness = self.base_stiffness + (0.4 - self.base_stiffness) * x ** 2.0
                self.stiffnesses[i] = min(1, stiffness)
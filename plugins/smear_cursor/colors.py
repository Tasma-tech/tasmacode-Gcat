"""
Sistema de Cores e Gradientes
Responsabilidade: Gerenciar interpolação de cores
"""
from PySide6.QtGui import QColor
from typing import Optional

class ColorManager:
    def __init__(self):
        self.cursor_color = QColor(0, 255, 0)
        self.background_color = QColor(0, 0, 0)
        self.color_cache = {}
        
    def interpolate_color(self, level: int, max_levels: int = 10) -> QColor:
        """Interpola cor baseada no nível - similar ao sistema original"""
        if level in self.color_cache:
            return self.color_cache[level]
            
        # Calcula opacidade com correção gamma
        opacity = (level / max_levels) ** (1 / 2.2)  # gamma = 2.2
        
        # Interpola entre background e cursor
        r = int(self.background_color.red() + 
                (self.cursor_color.red() - self.background_color.red()) * opacity)
        g = int(self.background_color.green() + 
                (self.cursor_color.green() - self.background_color.green()) * opacity)
        b = int(self.background_color.blue() + 
                (self.cursor_color.blue() - self.background_color.blue()) * opacity)
        
        color = QColor(r, g, b)
        self.color_cache[level] = color
        return color
        
    def update_theme_colors(self, cursor_hex: str, bg_hex: str):
        """Atualiza cores do tema"""
        self.cursor_color = QColor(cursor_hex)
        self.background_color = QColor(bg_hex)
        self.color_cache.clear()
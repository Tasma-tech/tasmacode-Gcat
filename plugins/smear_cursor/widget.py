"""
Widget Qt Integrado
Responsabilidade: Integrar o smear cursor com QTextEdit
"""
from PySide6.QtWidgets import QTextEdit, QWidget
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import QPainter
from .physics import SpringPhysics
from .renderer import SmearRenderer
from .colors import ColorManager
from .config import SmearConfig

class SmearCursorWidget(QWidget):
    def __init__(self, parent_editor):
        super().__init__(parent_editor)
        self.editor = parent_editor
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Componentes SRP
        self.physics = SpringPhysics()
        self.renderer = SmearRenderer()
        self.color_manager = ColorManager()
        self.config = SmearConfig()
        
        # Timer de animação
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(self.config.time_interval)
        
        # Conecta ao sinal de movimento do cursor do editor
        self.editor.cursor_moved.connect(self._on_cursor_moved)
        
        self.animating = False
        
    def move_cursor_to(self, rect: QRect):
        """Inicia animação para nova posição"""
        # Ajusta o rect para coordenadas locais do widget
        self.physics.set_target(rect) 
        self.physics.set_stiffnesses()
        self.animating = True
        
    def _update_animation(self):
        """Loop de animação"""
        if self.animating:
            self.physics.update_physics()
            self.update() # Agenda um paint event
            
            # Verifica se animação terminou
            max_dist = max(
                ((self.physics.current_corners[i][0] - self.physics.target_corners[i][0])**2 +
                 (self.physics.current_corners[i][1] - self.physics.target_corners[i][1])**2)**0.5
                for i in range(4)
            ) if self.physics.current_corners else 0
            
            if max_dist < 1:
                self.animating = False
                
    def paintEvent(self, event):
        """Renderiza o smear cursor"""
        if not self.animating:
            return
            
        painter = QPainter(self)
        self.renderer.render_smear(painter, self.physics.current_corners)

    def _on_cursor_moved(self):
        """Calcula a posição do cursor no CodeEditor e atualiza o efeito."""
        if not self.editor.buffer or not self.editor.buffer.cursors:
            return
            
        cursor = self.editor.buffer.cursors[-1]
        
        # Cálculos baseados na geometria do CodeEditor
        scroll_y = self.editor.verticalScrollBar().value()
        x = (cursor.col * self.editor.char_width) + self.editor.line_number_area_width()
        y = (cursor.line * self.editor.line_height) - scroll_y
        
        # Cria um QRect representando o cursor (largura de 2px padrão)
        cursor_rect = QRect(int(x), int(y), 2, int(self.editor.line_height))
        
        self.move_cursor_to(cursor_rect)
        
        # Garante que o widget cubra todo o editor
        self.resize(self.editor.size())
        
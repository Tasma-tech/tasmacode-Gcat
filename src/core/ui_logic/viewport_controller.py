from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QAbstractScrollArea
from src.core.editor_logic.buffer import DocumentBuffer

class ViewportController(QObject):
    """Controla a área visível e o scroll do editor.
    
    Responsável por calcular quais linhas estão visíveis para otimizar
    renderização e realce de sintaxe.
    """
    
    # Sinal emitido quando a área visível muda (scroll ou resize)
    # Envia (primeira_linha_visivel, ultima_linha_visivel)
    visible_lines_changed = Signal(int, int)

    def __init__(self):
        super().__init__()
        self._editor = None

    def attach_to(self, editor: QAbstractScrollArea):
        """Conecta o controlador a uma instância do editor."""
        self._editor = editor
        
        # Conecta ao scrollbar vertical
        v_scrollbar = self._editor.verticalScrollBar()
        v_scrollbar.valueChanged.connect(self._calculate_visible_area)

    def update_scrollbar(self, buffer: DocumentBuffer):
        """Atualiza os limites da barra de rolagem com base no buffer."""
        if not self._editor: return
        
        line_height = self._editor.line_height
        total_height = buffer.line_count * line_height
        
        # Define o range do scrollbar (em pixels)
        max_scroll = max(0, total_height - self._editor.viewport().height())
        self._editor.verticalScrollBar().setRange(0, max_scroll)
        self._editor.verticalScrollBar().setSingleStep(line_height)

    def _calculate_visible_area(self):
        """Calcula o intervalo de linhas visíveis."""
        if not self._editor:
            return

        scroll_y = self._editor.verticalScrollBar().value()
        line_height = self._editor.line_height
        viewport_height = self._editor.viewport().height()
        
        first_line = scroll_y // line_height
        lines_on_screen = viewport_height // line_height
        last_line = first_line + lines_on_screen
        
        self.visible_lines_changed.emit(first_line, last_line)

    def get_visible_content(self, buffer: DocumentBuffer) -> str:
        pass
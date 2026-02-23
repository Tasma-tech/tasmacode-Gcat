from PySide6.QtWidgets import QAbstractScrollArea
from PySide6.QtCore import Signal, Qt, QTimer, QRect, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen
from plugins.line_number_area import LineNumberArea

class CodeEditor(QAbstractScrollArea):
    """Canvas de edição de código com renderização customizada.
    
    Herda de QAbstractScrollArea para controle total do desenho.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Dependências (injetadas via setters)
        self.buffer = None
        self.theme = None
        self.highlighter = None
        self.input_mapper = None
        
        # Configuração de Fonte e Métricas
        # Tenta usar fontes modernas, fallback para Monospace genérico
        self.font = QFont("JetBrains Mono")
        self.font.setStyleHint(QFont.StyleHint.Monospace)
        if not self.font.exactMatch():
            self.font = QFont("Consolas")
            if not self.font.exactMatch():
                self.font = QFont("Monospace")
        
        self.font.setPointSize(12)
        self.font_metrics = QFontMetrics(self.font)
        self.line_height = self.font_metrics.height()
        self.char_width = self.font_metrics.horizontalAdvance(' ')
        
        # Estado interno
        self.blink_state = True
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._toggle_blink)
        self.blink_timer.start(500)
        
        # Smooth Scrolling setup
        self.verticalScrollBar().setSingleStep(20) # Rolagem mais suave por pixel
        # Para kinetic scrolling real, usariamos QScroller.grabGesture(self.viewport(), ...)
        
        # Padding visual (Margens internas)
        self.setViewportMargins(10, 10, 10, 10)
        
        # Estado de interação
        self._is_dragging = False
        self._last_click_was_double = False
        
        # Destaques da busca
        self.search_highlights = []
        
        # Gutter de Linhas
        self.line_number_area = LineNumberArea(self)
        self._update_line_number_area_width()

    def set_dependencies(self, buffer, theme_manager, highlighter):
        self.buffer = buffer
        self.theme = theme_manager
        self.highlighter = highlighter

    def set_input_mapper(self, mapper):
        self.input_mapper = mapper

    def keyPressEvent(self, event):
        """Delega eventos de teclado para o InputMapper."""
        if self.input_mapper and self.input_mapper.handle_key(event):
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """Trata o clique do mouse para posicionar o cursor."""
        if self._last_click_was_double:
            self._last_click_was_double = False
            # É um clique triplo
            if not self.buffer: return
            pos = event.position()
            scroll_y = self.verticalScrollBar().value()
            target_line = int((pos.y() + scroll_y) // self.line_height)
            
            self.buffer.clear_cursors()
            self.buffer.select_line_at(target_line)
            self._is_dragging = True
            self.viewport().update()
            event.accept()
            return

        self._last_click_was_double = False
        if not self.buffer: return
        
        pos = event.position()
        x, y = pos.x(), pos.y()
        scroll_y = self.verticalScrollBar().value()
        target_line = int((y + scroll_y) // self.line_height)
        target_col = int((x / self.char_width) + 0.5)
        
        modifiers = event.modifiers()
        keep_anchor = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        is_multi = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        
        if not is_multi:
            self.buffer.clear_cursors()
        
        self.buffer.update_last_cursor(target_line, target_col, keep_anchor=keep_anchor)
            
        self._is_dragging = True
        self.viewport().update()

    def _toggle_blink(self):
        self.blink_state = not self.blink_state
        self.viewport().update() # Solicita repaint

    def mouseDoubleClickEvent(self, event):
        """Trata o clique duplo para selecionar uma palavra."""
        self._last_click_was_double = True
        if not self.buffer: return

        pos = event.position()
        scroll_y = self.verticalScrollBar().value()
        target_line = int((pos.y() + scroll_y) // self.line_height)
        target_col = int((pos.x() / self.char_width) + 0.5)

        self.buffer.clear_cursors()
        self.buffer.select_word_at(target_line, target_col)
        self._is_dragging = True
        self.viewport().update()
        event.accept()

    def mouseMoveEvent(self, event):
        """Trata o arrasto do mouse para seleção de texto."""
        if not self.buffer or not self._is_dragging: return
        
        pos = event.position()
        scroll_y = self.verticalScrollBar().value()
        
        target_line = int((pos.y() + scroll_y) // self.line_height)
        target_col = int((pos.x() / self.char_width) + 0.5)
        
        # Atualiza o cursor mantendo a âncora original (seleção)
        self.buffer.update_last_cursor(target_line, target_col, keep_anchor=True)
        
        # Auto-scroll se arrastar para fora da área visível
        if pos.y() < 0:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - self.line_height)
        elif pos.y() > self.viewport().height():
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + self.line_height)
        
        self.viewport().update()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False

    # --- Lógica do Gutter de Linhas ---
    def line_number_area_width(self):
        """Calcula a largura necessária para exibir os números das linhas."""
        digits = 1
        if self.buffer:
            digits = len(str(max(1, self.buffer.line_count)))
        
        space = 15 + self.char_width * digits
        return space

    def _update_line_number_area_width(self):
        """Atualiza as margens do viewport para acomodar o gutter."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def line_number_area_paint_event(self, event):
        """Desenha os números das linhas."""
        if not self.buffer or not self.theme: return

        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(self.theme.get_color("gutter_bg")))

        scroll_y = self.verticalScrollBar().value()
        viewport_h = self.viewport().height()
        
        first_line = scroll_y // self.line_height
        lines_visible = (viewport_h // self.line_height) + 2
        
        # Itera sobre as linhas visíveis
        for i in range(lines_visible):
            line_idx = first_line + i
            if line_idx >= self.buffer.line_count:
                break
                
            y = (line_idx * self.line_height) - scroll_y
            
            # Desenha o número
            painter.setPen(QColor(self.theme.get_color("gutter_fg")))
            painter.setFont(self.font)
            painter.drawText(0, y, self.line_number_area.width() - 5, self.line_height, Qt.AlignmentFlag.AlignRight, str(line_idx + 1))

    def paintEvent(self, event):
        """Renderiza o texto e os cursores."""
        if not self.buffer or not self.theme:
            return

        painter = QPainter(self.viewport())
        painter.setFont(self.font)
        
        
        # Cores do tema
        bg_color = QColor(self.theme.get_color("background"))
        fg_color = QColor(self.theme.get_color("foreground"))
        hl_line_color = QColor(self.theme.get_color("line_highlight"))
        guide_color = QColor(self.theme.get_color("indent_guide"))
        search_hl_color = QColor(self.theme.get_color("accent"))
        search_hl_color.setAlpha(80) # Semi-transparente
        selection_color = QColor(self.theme.get_color("selection"))
        
        # Preenche fundo
        painter.fillRect(event.rect(), bg_color)
        
        # Cálculo de visibilidade (Otimização)
        scroll_y = self.verticalScrollBar().value()
        viewport_h = self.viewport().height()
        
        first_line = scroll_y // self.line_height
        lines_visible = (viewport_h // self.line_height) + 2
        
        # Obtém linhas do buffer
        lines = self.buffer.get_lines(first_line, first_line + lines_visible)
        
        # Posições dos cursores para destaque de linha
        active_lines = {c.line for c in self.buffer.cursors}

        # --- Desenha a Seleção (antes de todo o resto) ---
        for i in range(len(self.buffer.cursors)):
            selection_range = self.buffer.get_selection_range(i)
            if not selection_range:
                continue

            (start_line, start_col), (end_line, end_col) = selection_range

            # Itera apenas sobre as linhas visíveis que estão na seleção
            visible_start = max(start_line, first_line)
            visible_end = min(end_line, first_line + lines_visible)

            for line_idx in range(visible_start, visible_end + 1):
                y = (line_idx * self.line_height) - scroll_y
                
                sel_start_x = start_col * self.char_width if line_idx == start_line else 0
                sel_end_x = end_col * self.char_width if line_idx == end_line else self.viewport().width()
                
                sel_width = sel_end_x - sel_start_x
                if sel_width > 0:
                    painter.fillRect(int(sel_start_x), int(y), int(sel_width), self.line_height, selection_color)
        
        # Desenha Texto
        for i, line_text in enumerate(lines):
            line_idx = first_line + i
            y = (line_idx * self.line_height) - scroll_y
            
            # 1. Active Line Highlight
            if line_idx in active_lines:
                painter.fillRect(0, y, self.viewport().width(), self.line_height, hl_line_color)
            
            # 0. Search Highlights (desenhado antes do texto)
            for hl_line, hl_col, hl_len in self.search_highlights:
                if hl_line == line_idx:
                    hl_x = hl_col * self.char_width
                    hl_w = hl_len * self.char_width
                    painter.fillRect(int(hl_x), int(y), int(hl_w), self.line_height, search_hl_color)
            
            # 2. Indent Guides
            # Desenha linhas verticais a cada 4 espaços (assumindo tab_width=4)
            indent_level = (len(line_text) - len(line_text.lstrip())) // 4
            if indent_level > 0:
                painter.setPen(QPen(guide_color, 1, Qt.PenStyle.DotLine))
                for lvl in range(1, indent_level + 1):
                    gx = lvl * 4 * self.char_width
                    painter.drawLine(gx, y, gx, y + self.line_height)

            # 3. Bracket Match Highlight
            # Verifica se algum cursor está perto de um bracket nesta linha
            # (Simplificação: verifica apenas o último cursor para performance visual)
            if self.buffer.cursors:
                last_cursor = self.buffer.cursors[-1]
                match = self.buffer.get_matching_bracket(last_cursor.line, last_cursor.col)
                if match and match[0] == line_idx:
                    bx = match[1] * self.char_width
                    painter.fillRect(int(bx), int(y), int(self.char_width), int(self.line_height), QColor(self.theme.get_color("bracket_match")))
            
            # Integração com Highlighter
            if self.highlighter:
                tokens = self.highlighter.process_block(line_text)
                # Desenha tokens coloridos (simplificado)
                x_offset = 0
                last_idx = 0
                for token in tokens:
                    # Desenha texto antes do token
                    pre_text = line_text[last_idx:token.start]
                    painter.setPen(fg_color)
                    painter.drawText(x_offset, y, self.char_width * len(pre_text), self.line_height, Qt.AlignmentFlag.AlignLeft, pre_text)
                    x_offset += self.char_width * len(pre_text)
                    
                    # Desenha token
                    token_text = line_text[token.start:token.start+token.length]
                    painter.setPen(QColor(self.theme.get_color("accent"))) # Usa cor de destaque
                    painter.drawText(x_offset, y, self.char_width * len(token_text), self.line_height, Qt.AlignmentFlag.AlignLeft, token_text)
                    x_offset += self.char_width * len(token_text)
                    last_idx = token.start + token.length
                
                # Resto da linha
                painter.setPen(fg_color)
                painter.drawText(x_offset, y, 10000, self.line_height, Qt.AlignmentFlag.AlignLeft, line_text[last_idx:])
            else:
                painter.setPen(fg_color)
                painter.drawText(0, y, 10000, self.line_height, Qt.AlignmentFlag.AlignLeft, line_text)

        # Desenha Cursores
        if self.blink_state:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.theme.get_color("accent")))
            
            for cursor in self.buffer.cursors:
                # Só desenha se estiver visível
                if first_line <= cursor.line <= first_line + lines_visible:
                    cx = cursor.col * self.char_width
                    cy = (cursor.line * self.line_height) - scroll_y
                    painter.drawRect(cx, cy, 2, self.line_height)

    def resizeEvent(self, event):
        """Atualiza scrollbars quando a janela muda de tamanho."""
        super().resizeEvent(event)
        
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
        
        # O ViewportController cuidará dos limites, mas precisamos emitir sinal ou chamar update
        self._setup_font()

    def _setup_font(self):
        pass # Já configurado no init
from PySide6.QtWidgets import QAbstractScrollArea
from PySide6.QtCore import Signal, Qt, QTimer, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen, QFontInfo
from plugins.line_number_area import LineNumberArea
from .autocomplete_widget import AutocompleteWidget, ParameterHintWidget

class CodeEditor(QAbstractScrollArea):
    """Canvas de edição de código com renderização customizada.
    
    Herda de QAbstractScrollArea para controle total do desenho.
    """
    
    text_changed = Signal()
    cursor_moved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Dependências (injetadas via setters)
        self.buffer = None
        self.theme = None
        self.highlighter = None
        self.input_mapper = None
        self.autocomplete_manager = None
        self.word_wrap_enabled = False
        self._visual_lines = []
        self._chars_per_line = 80
        self._max_content_width = 0
        self.autocomplete_widget = None
        self.show_line_numbers = True
        self.auto_indent = True
        self.autocomplete_enabled = False
        
        # Configuração de Fonte e Métricas
        # Tenta usar fontes modernas, fallback para Monospace genérico
        self.font = QFont("JetBrainsMono Nerd Font")
        self.font.setStyleHint(QFont.StyleHint.Monospace)
        self.font.setStyleStrategy(QFont.StyleStrategy.PreferQuality) # Habilita ligaduras por padrão
        if not self.font.exactMatch():
            self.font = QFont("JetBrains Mono")
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
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        # Conecta os sinais de scroll para atualizar a área de números de linha
        self.verticalScrollBar().valueChanged.connect(self.line_number_area.update)
        self.horizontalScrollBar().valueChanged.connect(self.line_number_area.update)
        self._update_line_number_area_width()
        
    def set_buffer(self, buffer):
        self.buffer = buffer
        self.buffer.dirty = False  # Initialize the dirty flag
        self._recalculate_layout()
    def set_dependencies(self, buffer, theme_manager, highlighter, autocomplete_manager):
        self.buffer = buffer
        self.theme = theme_manager
        self.highlighter = highlighter
        self.autocomplete_manager = autocomplete_manager
        if self.autocomplete_manager and not self.autocomplete_widget:
            self.autocomplete_widget = AutocompleteWidget(self)
            self.autocomplete_widget.suggestion_selected.connect(self._on_suggestion_selected)
            
            # Inicializa widget de dicas de parâmetros
            if not hasattr(self, 'parameter_hint_widget'):
                self.parameter_hint_widget = ParameterHintWidget(self)
                
            # Conecta sinais para atualização de dicas
            self.text_changed.connect(self._update_parameter_hint)
            self.cursor_moved.connect(self._update_parameter_hint)
        self._recalculate_layout()

    def set_input_mapper(self, mapper):
        self.input_mapper = mapper

    def set_file_path(self, path: str):
        """Sets the file path and emits the file_path_changed signal."""
        self.setProperty("file_path", path)

    def keyPressEvent(self, event):
        """Delega eventos de teclado para o InputMapper."""
        if self.autocomplete_widget and self.autocomplete_widget.isVisible():
            key = event.key()
            if key in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab, Qt.Key_Escape):
                self.autocomplete_widget.keyPressEvent(event)
                return

        if self.input_mapper and self.input_mapper.handle_key(event):
            event.accept()
            self.text_changed.emit()
        else:
            self.text_changed.emit()
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """Trata o clique do mouse para posicionar o cursor."""
        if self._last_click_was_double:
            self._last_click_was_double = False
            # É um clique triplo
            if not self.buffer: return
            pos = event.position()
            scroll_y = self.verticalScrollBar().value()
            target_line = int((pos.y() + scroll_y) // self.line_height if self.line_height > 0 else 0)
            
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

        if self.word_wrap_enabled:
            visual_line_idx = int((y + scroll_y) // self.line_height) if self.line_height > 0 else 0
            visual_line_idx = min(visual_line_idx, len(self._visual_lines) - 1) if self._visual_lines else 0
            if visual_line_idx < 0: return
            logical_line, start_col = self._visual_lines[visual_line_idx]
            visual_col = int((x / self.char_width) + 0.5) if self.char_width > 0 else 0
            target_line, target_col = logical_line, min(start_col + visual_col, len(self.buffer.lines[logical_line]))
        else:
            scroll_x = self.horizontalScrollBar().value()
            target_line = int((y + scroll_y) // self.line_height if self.line_height > 0 else 0)
            target_col = int(((x + scroll_x) / self.char_width) + 0.5 if self.char_width > 0 else 0)
        
        modifiers = event.modifiers()
        keep_anchor = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        is_multi = bool(modifiers & Qt.KeyboardModifier.ControlModifier)
        
        if not is_multi:
            self.buffer.clear_cursors()
        
        self.buffer.update_last_cursor(target_line, target_col, keep_anchor=keep_anchor)
        self.cursor_moved.emit()
            
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

        if self.word_wrap_enabled:
            visual_line_idx = int((pos.y() + scroll_y) // self.line_height) if self.line_height > 0 else 0
            visual_line_idx = min(visual_line_idx, len(self._visual_lines) - 1) if self._visual_lines else 0
            if visual_line_idx < 0: return
            logical_line, start_col = self._visual_lines[visual_line_idx]
            visual_col = int((pos.x() / self.char_width) + 0.5) if self.char_width > 0 else 0
            target_line, target_col = logical_line, min(start_col + visual_col, len(self.buffer.lines[logical_line]))
        else:
            scroll_x = self.horizontalScrollBar().value()
            target_line = int((pos.y() + scroll_y) // self.line_height if self.line_height > 0 else 0)
            target_col = int(((pos.x() + scroll_x) / self.char_width) + 0.5 if self.char_width > 0 else 0)

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
        
        if self.word_wrap_enabled:
            visual_line_idx = int((pos.y() + scroll_y) // self.line_height) if self.line_height > 0 else 0
            visual_line_idx = min(visual_line_idx, len(self._visual_lines) - 1) if self._visual_lines else 0
            if visual_line_idx < 0: return
            logical_line, start_col = self._visual_lines[visual_line_idx]
            visual_col = int((pos.x() / self.char_width) + 0.5) if self.char_width > 0 else 0
            target_line, target_col = logical_line, min(start_col + visual_col, len(self.buffer.lines[logical_line]))
        else:
            scroll_x = self.horizontalScrollBar().value()
            target_line = int((pos.y() + scroll_y) // self.line_height if self.line_height > 0 else 0)
            target_col = int(((pos.x() + scroll_x) / self.char_width) + 0.5 if self.char_width > 0 else 0)
        
        # Atualiza o cursor mantendo a âncora original (seleção)
        self.buffer.update_last_cursor(target_line, target_col, keep_anchor=True)
        self.cursor_moved.emit()
        
        # Auto-scroll se arrastar para fora da área visível
        if pos.y() < 0:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - self.line_height)
        elif pos.y() > self.viewport().height():
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + self.line_height)
        
        self.viewport().update()

    def mouseReleaseEvent(self, event):
        self._is_dragging = False

    def show_autocomplete(self, suggestions: list):
        """Exibe o widget de autocomplete na posição correta."""
        if not self.autocomplete_widget or not self.buffer:
            return
        
        cursor = self.buffer.cursors[-1]
        
        scroll_y = self.verticalScrollBar().value()

        if self.word_wrap_enabled:
            visual_line, visual_col = self._get_visual_pos_for_cursor(cursor.line, cursor.col)
            x_px = visual_col * self.char_width
            y_px = (visual_line * self.line_height) - scroll_y
        else:
            scroll_x = self.horizontalScrollBar().value()
            x_px = (cursor.col * self.char_width) - scroll_x
            y_px = (cursor.line * self.line_height) - scroll_y
        self.autocomplete_widget.show_suggestions(suggestions)
        
        point = self.viewport().mapTo(self, QPoint(int(x_px), int(y_px + self.line_height)))
        
        widget_height = self.autocomplete_widget.height()
        widget_width = self.autocomplete_widget.width()

        if point.y() + widget_height > self.height():
            point.setY(int(point.y() - widget_height - self.line_height))
        if point.x() + widget_width > self.width():
            point.setX(int(self.width() - widget_width - 20))
        
        self.autocomplete_widget.move(point)

    def _update_parameter_hint(self):
        """Verifica e exibe dicas de parâmetros se estiver dentro de uma função."""
        if not self.buffer or not self.autocomplete_manager: return
        
        cursor = self.buffer.cursors[-1]
        file_path = self.property("file_path") or ""
        
        hint = self.autocomplete_manager.get_parameter_hint(self.buffer, cursor.line, cursor.col, file_path)
        
        if hint:
            # Calcula posição (acima da linha atual)
            scroll_y = self.verticalScrollBar().value()

            if self.word_wrap_enabled:
                visual_line, visual_col = self._get_visual_pos_for_cursor(cursor.line, cursor.col)
                x_px = visual_col * self.char_width
                y_px = (visual_line * self.line_height) - scroll_y
            else:
                scroll_x = self.horizontalScrollBar().value()
                x_px = (cursor.col * self.char_width) - scroll_x
                y_px = (cursor.line * self.line_height) - scroll_y
            # Mapeia para coordenadas do widget
            point = self.viewport().mapTo(self, QPoint(int(x_px), int(y_px)))
            
            # Posiciona um pouco acima da linha
            point.setY(point.y() - 25)
            # Ajusta X para não sair da tela pela esquerda
            point.setX(max(5, point.x()))
            
            # Se o autocomplete estiver visível, move a dica mais para cima
            if self.autocomplete_widget and self.autocomplete_widget.isVisible():
                point.setY(point.y() - self.autocomplete_widget.height() - 5)
            
            self.parameter_hint_widget.show_hint(hint['name'], hint['params'], point, hint.get('active_index', 0))
        else:
            if hasattr(self, 'parameter_hint_widget'):
                self.parameter_hint_widget.hide()

    def _on_suggestion_selected(self, suggestion: dict):
        """Substitui a palavra atual pela sugestão selecionada."""
        if not self.buffer: return
        
        cursor = self.buffer.cursors[-1]
        line_text = self.buffer.get_lines(cursor.line, cursor.line + 1)[0]
        
        # Encontra o início da palavra que está sendo completada
        word_start_col = cursor.col
        while word_start_col > 0 and (line_text[word_start_col - 1].isalnum() or line_text[word_start_col - 1] == '_'):
            word_start_col -= 1
            
        # Seleciona a palavra para substituí-la
        self.buffer.cursors[-1].anchor_col = word_start_col
        self.buffer.cursors[-1].col = cursor.col
        self.buffer.delete_selection()
        
        # Insere o snippet ou o texto da sugestão
        kind = suggestion.get('kind')
        label = suggestion.get('label', '')
        insert_text = suggestion.get('insert_text')
        
        text_to_insert = insert_text if insert_text else label
        
        # Lógica para funções: adicionar () e mover cursor para dentro
        move_back = 0
        if kind == 'function' and not insert_text:
            text_to_insert += "()"
            move_back = 1

        # Lógica de indentação para snippets com múltiplas linhas
        if '\n' in text_to_insert:
            current_indent_spaces = len(line_text) - len(line_text.lstrip(' '))
            indent_str = ' ' * current_indent_spaces
            lines = text_to_insert.split('\n')
            indented_lines = [lines[0]] + [indent_str + line for line in lines[1:]]
            text_to_insert = '\n'.join(indented_lines)
            
        self.buffer.insert_text(text_to_insert)
        
        if move_back > 0:
            self.buffer.move_cursors(0, -move_back)

    def invalidate_line_range(self, start_line: int, end_line: int):
        """Invalida apenas um range de linhas para repintura seletiva."""
        if not self.buffer: return
        
        start_line = max(0, start_line)
        end_line = min(self.buffer.line_count - 1, end_line)
        
        scroll_y = self.verticalScrollBar().value()
        top_y = (start_line * self.line_height) - scroll_y
        height = (end_line - start_line + 1) * self.line_height
        
        rect = QRect(0, int(top_y), self.viewport().width(), int(height))
        self.viewport().update(rect)

    def invalidate_cursor_area(self):
        """Invalida apenas a área dos cursores para performance."""
        if not self.buffer: return
        
        # Invalida a linha de cada cursor
        for cursor in self.buffer.cursors:
            self.invalidate_line_range(cursor.line, cursor.line)

    def _get_visual_pos_for_cursor(self, log_line, log_col):
        if not self.word_wrap_enabled or not self._visual_lines:
            return log_line, log_col

        # Find the visual line index
        for i, (l_line, start_col) in enumerate(self._visual_lines):
            if l_line == log_line:
                line_len = len(self.buffer.lines[l_line])
                end_col = start_col + self._chars_per_line
                if start_col <= log_col < end_col or (log_col == line_len and end_col >= line_len):
                    visual_line_idx = i
                    visual_col = log_col - start_col
                    return visual_line_idx, visual_col
        
        # Fallback if not found (e.g., buffer changed but layout not recalculated)
        return log_line, log_col

    def _recalculate_layout(self):
        """Recalcula a largura e altura total do conteúdo e ajusta as scrollbars."""
        if not self.buffer:
            return

        viewport_width = self.viewport().width()
        total_height = 0

        if self.word_wrap_enabled:
            self._visual_lines.clear()
            self._chars_per_line = (viewport_width - 10) // self.char_width if self.char_width > 0 else 1
            if self._chars_per_line <= 0: self._chars_per_line = 1

            for i, line_text in enumerate(self.buffer.lines):
                if not line_text:
                    self._visual_lines.append((i, 0))
                    continue
                
                start_col = 0
                while start_col < len(line_text):
                    self._visual_lines.append((i, start_col))
                    start_col += self._chars_per_line
            
            total_height = len(self._visual_lines) * self.line_height
            self._max_content_width = viewport_width
            self.horizontalScrollBar().setRange(0, 0)
        else:  # Scroll Horizontal
            self._visual_lines.clear()
            max_line_len_chars = 0
            if self.buffer.line_count > 0:
                # Esta pode ser uma operação lenta para arquivos muito grandes
                max_line_len_chars = max(len(line) for line in self.buffer.lines)
            
            self._max_content_width = (max_line_len_chars * self.char_width) + 20 # Padding
            total_height = self.buffer.line_count * self.line_height
            
            self.horizontalScrollBar().setRange(0, max(0, int(self._max_content_width - viewport_width)))

        self.verticalScrollBar().setRange(0, max(0, int(total_height - self.viewport().height())))
        self.verticalScrollBar().setPageStep(self.viewport().height())
        self.horizontalScrollBar().setPageStep(self.viewport().width())

    # --- Lógica do Gutter de Linhas ---
    def line_number_area_width(self):
        if not self.show_line_numbers:
            return 0
        """Calcula a largura necessária para exibir os números das linhas."""
        digits = 1
        if self.buffer:
            digits = len(str(max(1, self.buffer.line_count)))
        
        space = 15 + self.char_width * digits
        return space

    def _update_line_number_area_width(self):
        """Atualiza as margens do viewport para acomodar o gutter."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_settings(self, settings: dict):
        """Aplica configurações dinâmicas ao editor."""
        # Família e Tamanho da Fonte
        font_family = settings.get("font_family", "JetBrainsMono Nerd Font")
        font_size = settings.get("font_size", 12)
        ligatures = settings.get("font_ligatures", True)
        wrap_mode = settings.get("wrap_mode", "horizontal")

        # Novas configurações de quebra de linha
        self.word_wrap_enabled = (wrap_mode == "wrap")
        
        # Aplica o modo
        if self.word_wrap_enabled:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        if self.font.family() != font_family or self.font.pointSize() != font_size or self.font.styleStrategy() != (QFont.StyleStrategy.PreferQuality if ligatures else QFont.StyleStrategy.PreferDefault):
            new_font = QFont(font_family, font_size)
            new_font.setStyleHint(QFont.StyleHint.Monospace)
            
            if ligatures:
                new_font.setStyleStrategy(QFont.StyleStrategy.PreferQuality)
            
            # Verifica se a fonte foi encontrada, senão usa fallback
            font_info = QFontInfo(new_font)
            if font_info.family().lower() != font_family.lower():
                print(f"Fonte '{font_family}' não encontrada, usando fallback 'Monospace'.")
                new_font = QFont("Monospace", font_size)

            self.font = new_font
            self.font_metrics = QFontMetrics(self.font)
            self.line_height = self.font_metrics.height()
            self.char_width = self.font_metrics.horizontalAdvance(' ')
        # Preferências
        self.show_line_numbers = settings.get("line_numbers", True)
        self.auto_indent = settings.get("auto_indent", True)
        self.autocomplete_enabled = settings.get("enable_autocomplete", False)
        
        # Atualiza configurações do plugin Smear Cursor se estiver ativo
        if hasattr(self, 'smear_widget'):
            self.smear_widget.update_config(settings)
        
        # Recalcula layout
        self._recalculate_layout()
        self.viewport().update()

    def line_number_area_paint_event(self, event):
        """Desenha os números das linhas."""
        if not self.buffer or not self.theme: return

        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor(self.theme.get_color("gutter_bg")))

        scroll_y = self.verticalScrollBar().value()
        viewport_h = self.viewport().height()
        
        if self.word_wrap_enabled and self._visual_lines:
            first_visual_line = scroll_y // self.line_height if self.line_height > 0 else 0
            visual_lines_visible = (viewport_h // self.line_height if self.line_height > 0 else 0) + 2
            
            for i in range(visual_lines_visible):
                visual_line_idx = first_visual_line + i
                if visual_line_idx >= len(self._visual_lines): break
                
                logical_line_idx, start_col = self._visual_lines[visual_line_idx]
                
                if start_col == 0:
                    y = (visual_line_idx * self.line_height) - scroll_y
                    painter.setPen(QColor(self.theme.get_color("gutter_fg")))
                    painter.setFont(self.font)
                    painter.drawText(0, int(y), self.line_number_area.width() - 5, self.line_height, Qt.AlignmentFlag.AlignRight, str(logical_line_idx + 1))
                else:
                    y = (visual_line_idx * self.line_height) - scroll_y
                    painter.setPen(QColor(self.theme.get_color("gutter_fg")))
                    painter.setFont(self.font)
                    painter.drawText(0, int(y), self.line_number_area.width() - 5, self.line_height, Qt.AlignmentFlag.AlignRight, "⤶")
        else:
            first_line = scroll_y // self.line_height if self.line_height > 0 else 0
            lines_visible = (viewport_h // self.line_height if self.line_height > 0 else 0) + 2
            for i in range(lines_visible):
                line_idx = first_line + i
                if line_idx >= self.buffer.line_count: break
                y = (line_idx * self.line_height) - scroll_y
                painter.setPen(QColor(self.theme.get_color("gutter_fg")))
                painter.setFont(self.font)
                painter.drawText(0, int(y), self.line_number_area.width() - 5, self.line_height, Qt.AlignmentFlag.AlignRight, str(line_idx + 1))

    def paintEvent(self, event):
        """Renderiza o texto e os cursores com viewport culling otimizado."""
        if not self.buffer or not self.theme:
            return

        painter = QPainter(self.viewport())
        painter.setFont(self.font)
        
        # Otimização: só processa a região danificada
        damaged_rect = event.rect()
        
        # Cores do tema
        bg_color = QColor(self.theme.get_color("background"))
        fg_color = QColor(self.theme.get_color("foreground"))
        hl_line_color = QColor(self.theme.get_color("line_highlight"))
        guide_color = QColor(self.theme.get_color("indent_guide"))
        search_hl_color = QColor(self.theme.get_color("accent"))
        search_hl_color.setAlpha(80) # Semi-transparente
        selection_color = QColor(self.theme.get_color("selection"))
        
        # Preenche fundo (apenas a região danificada)
        painter.fillRect(damaged_rect, bg_color) # Drawn in viewport coordinates before translation

        scroll_y = self.verticalScrollBar().value()

        if self.word_wrap_enabled:
            self._paint_wrapped(painter, damaged_rect, scroll_y, bg_color, fg_color, hl_line_color, guide_color, search_hl_color, selection_color)
        else:
            self._paint_horizontal_scroll(painter, damaged_rect, scroll_y, bg_color, fg_color, hl_line_color, guide_color, search_hl_color, selection_color)

    def _paint_wrapped(self, painter, damaged_rect, scroll_y, bg_color, fg_color, hl_line_color, guide_color, search_hl_color, selection_color):
        """Lógica de renderização para o modo de quebra de linha."""
        first_visual_line = max(0, scroll_y // self.line_height if self.line_height > 0 else 0)
        visual_lines_on_screen = (damaged_rect.height() // self.line_height if self.line_height > 0 else 0) + 2
        last_visual_line = min(len(self._visual_lines) - 1, first_visual_line + visual_lines_on_screen)

        if first_visual_line > last_visual_line:
            return

        active_lines = {c.line for c in self.buffer.cursors}

        # --- Desenha a Seleção ---
        for i in range(len(self.buffer.cursors)):
            selection_range = self.buffer.get_selection_range(i)
            if not selection_range: continue
            (start_log_line, start_log_col), (end_log_line, end_log_col) = selection_range

            for visual_line_idx in range(first_visual_line, last_visual_line + 1):
                if visual_line_idx >= len(self._visual_lines): break
                log_line, chunk_start_col = self._visual_lines[visual_line_idx]
                chunk_end_col = chunk_start_col + self._chars_per_line
                if log_line < start_log_line or log_line > end_log_line: continue
                
                y = (visual_line_idx * self.line_height) - scroll_y
                sel_start_vis_col = 0
                if log_line == start_log_line: sel_start_vis_col = max(0, start_log_col - chunk_start_col)
                sel_end_vis_col = self._chars_per_line
                if log_line == end_log_line: sel_end_vis_col = min(self._chars_per_line, end_log_col - chunk_start_col)

                if sel_start_vis_col < sel_end_vis_col:
                    sel_start_x = sel_start_vis_col * self.char_width
                    sel_width = (sel_end_vis_col - sel_start_vis_col) * self.char_width
                    painter.fillRect(int(sel_start_x), int(y), int(sel_width), self.line_height, selection_color)

        # --- Desenha Texto e outros elementos ---
        for visual_line_idx in range(first_visual_line, last_visual_line + 1):
            if visual_line_idx >= len(self._visual_lines): break
            
            y = (visual_line_idx * self.line_height) - scroll_y
            logical_line_idx, start_col = self._visual_lines[visual_line_idx]
            
            line_rect = QRect(0, int(y), self.viewport().width(), self.line_height)
            if not line_rect.intersects(damaged_rect): continue

            line_text = self.buffer.lines[logical_line_idx]
            chunk_text = line_text[start_col : start_col + self._chars_per_line]

            if logical_line_idx in active_lines:
                painter.fillRect(0, int(y), self.viewport().width(), self.line_height, hl_line_color)

            # Highlighter
            if self.highlighter:
                tokens = self.highlighter.highlight(line_text)
                tokens.sort(key=lambda t: t.start)
                x_offset = 0
                last_drawn_col_in_chunk = 0
                
                for token in tokens:
                    intersect_start = max(token.start, start_col)
                    intersect_end = min(token.start + token.length, start_col + self._chars_per_line)
                    
                    if intersect_start < intersect_end:
                        pre_text_start_in_chunk = last_drawn_col_in_chunk
                        pre_text_end_in_chunk = intersect_start - start_col
                        if pre_text_start_in_chunk < pre_text_end_in_chunk:
                            pre_text = chunk_text[pre_text_start_in_chunk : pre_text_end_in_chunk]
                            painter.setPen(fg_color)
                            painter.drawText(int(x_offset), int(y), int(self.char_width * len(pre_text)), self.line_height, Qt.AlignmentFlag.AlignLeft, pre_text)
                            x_offset += self.char_width * len(pre_text)

                        token_chunk_text = line_text[intersect_start:intersect_end]
                        token_color = QColor(self.theme.get_color(token.color_key))
                        painter.setPen(token_color)
                        painter.drawText(int(x_offset), int(y), int(self.char_width * len(token_chunk_text)), self.line_height, Qt.AlignmentFlag.AlignLeft, token_chunk_text)
                        x_offset += self.char_width * len(token_chunk_text)
                        last_drawn_col_in_chunk = intersect_end - start_col
                
                if last_drawn_col_in_chunk < len(chunk_text):
                    remaining_text = chunk_text[last_drawn_col_in_chunk:]
                    painter.setPen(fg_color)
                    painter.drawText(int(x_offset), int(y), int(self.char_width * len(remaining_text)), self.line_height, Qt.AlignmentFlag.AlignLeft, remaining_text)
            else:
                painter.setPen(fg_color)
                painter.drawText(0, int(y), 10000, self.line_height, Qt.AlignmentFlag.AlignLeft, chunk_text)

        # --- Desenha Cursores ---
        if self.blink_state:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.theme.get_color("accent")))
            for cursor in self.buffer.cursors:
                visual_line_idx, visual_col = self._get_visual_pos_for_cursor(cursor.line, cursor.col)
                if first_visual_line <= visual_line_idx <= last_visual_line:
                    cx = visual_col * self.char_width
                    cy = (visual_line_idx * self.line_height) - scroll_y
                    painter.drawRect(int(cx), int(cy), 2, self.line_height)

    def _paint_horizontal_scroll(self, painter, damaged_rect, scroll_y, bg_color, fg_color, hl_line_color, guide_color, search_hl_color, selection_color):
        """Lógica de renderização original para o modo de scroll horizontal."""
        scroll_x = self.horizontalScrollBar().value()
        painter.translate(-scroll_x, 0)

        # Cálculo de visibilidade (Otimização)
        first_line = max(0, (damaged_rect.top() + scroll_y) // self.line_height if self.line_height > 0 else 0)
        last_line = min(self.buffer.line_count - 1, 
                       (damaged_rect.bottom() + scroll_y) // self.line_height if self.line_height > 0 else 0)
        
        if first_line > last_line:
            return # Nenhuma linha a ser desenhada na região
        
        # Obtém linhas do buffer
        lines = self.buffer.get_lines(first_line, last_line + 1)
        
        # Posições dos cursores para destaque de linha
        active_lines = {c.line for c in self.buffer.cursors}

        for i in range(len(self.buffer.cursors)):
            selection_range = self.buffer.get_selection_range(i)
            if not selection_range:
                continue

            (start_line, start_col), (end_line, end_col) = selection_range

            visible_start = max(start_line, first_line) # Interseção da seleção com a área danificada
            visible_end = min(end_line, last_line)

            for line_idx in range(visible_start, visible_end + 1):
                y = (line_idx * self.line_height) - scroll_y
                
                # Pula linhas que não estão na região danificada (verificação extra)
                if not QRect(0, int(y), int(self._max_content_width), self.line_height).intersects(damaged_rect.translated(scroll_x, 0)):
                    continue
                
                sel_start_x = start_col * self.char_width if line_idx == start_line else 0
                sel_end_x = end_col * self.char_width if line_idx == end_line else self._max_content_width
                
                sel_width = sel_end_x - sel_start_x
                if sel_width > 0:
                    painter.fillRect(int(sel_start_x), int(y), int(sel_width), self.line_height, selection_color)
        
        for i, line_text in enumerate(lines):
            line_idx = first_line + i
            y = (line_idx * self.line_height) - scroll_y
            
            # Pula linhas fora da região danificada
            if not QRect(0, int(y), int(self._max_content_width), self.line_height).intersects(damaged_rect.translated(scroll_x, 0)):
                continue
            
            # 1. Active Line Highlight
            if line_idx in active_lines:
                painter.fillRect(0, int(y), int(self._max_content_width), self.line_height, hl_line_color)
            
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
                    painter.drawLine(int(gx), int(y), int(gx), int(y + self.line_height))

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
                tokens = self.highlighter.highlight(line_text)
                # Ordena tokens para desenho sequencial correto
                tokens.sort(key=lambda t: t.start)
                
                x_offset = 0
                last_idx = 0
                for token in tokens:
                    # Desenha texto antes do token
                    pre_text = line_text[last_idx:token.start]
                    if pre_text:
                        painter.setPen(fg_color)
                        painter.drawText(int(x_offset), int(y), int(self.char_width * len(pre_text)), self.line_height, Qt.AlignmentFlag.AlignLeft, pre_text)
                        x_offset += self.char_width * len(pre_text)
                    
                    # Desenha token
                    token_text = line_text[token.start:token.start+token.length]
                    
                    token_color = QColor(self.theme.get_color(token.color_key))
                    painter.setPen(token_color)
                    
                    painter.drawText(int(x_offset), int(y), int(self.char_width * len(token_text)), self.line_height, Qt.AlignmentFlag.AlignLeft, token_text)
                    x_offset += self.char_width * len(token_text)
                    last_idx = token.start + token.length
                
                # Resto da linha
                painter.setPen(fg_color)
                painter.drawText(int(x_offset), int(y), 10000, self.line_height, Qt.AlignmentFlag.AlignLeft, line_text[last_idx:])
            else:
                painter.setPen(fg_color)
                painter.drawText(0, int(y), 10000, self.line_height, Qt.AlignmentFlag.AlignLeft, line_text)

        # Desenha Cursores
        if self.blink_state:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(self.theme.get_color("accent")))
            
            for cursor in self.buffer.cursors:
                # Só desenha se estiver visível
                if first_line <= cursor.line <= last_line:
                    cx = cursor.col * self.char_width
                    cy = (cursor.line * self.line_height) - scroll_y
                    painter.drawRect(int(cx), int(cy), 2, self.line_height)

    def resizeEvent(self, event):
        """Atualiza scrollbars quando a janela muda de tamanho."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))
        
        # Recalcula o layout pois a largura do viewport mudou
        self._recalculate_layout()
        
        self.line_number_area.update()

    def _setup_font(self):
        self.verticalScrollBar().valueChanged.connect(self.line_number_area.update)
        self.horizontalScrollBar().valueChanged.connect(self.line_number_area.update)
        self._update_line_number_area_width()
        pass # Já configurado no init
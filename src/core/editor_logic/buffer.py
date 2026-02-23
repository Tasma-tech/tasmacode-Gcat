from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
import logging
import copy

@dataclass
class Cursor:
    """Representa uma posição no texto (linha, coluna)."""
    line: int
    col: int
    anchor_line: Optional[int] = None
    anchor_col: Optional[int] = None

    def __post_init__(self):
        if self.anchor_line is None: self.anchor_line = self.line
        if self.anchor_col is None: self.anchor_col = self.col

    def as_tuple(self) -> Tuple[int, int]:
        return (self.line, self.col)

    def copy(self):
        return Cursor(self.line, self.col, self.anchor_line, self.anchor_col)

@dataclass
class Action:
    """Representa uma ação para o sistema de Undo/Redo."""
    type: str  # 'insert' ou 'delete'
    text: str
    cursors_before: List[Cursor]
    cursors_after: List[Cursor]
    # For full text replacement
    text_before: Optional[str] = None

logger = logging.getLogger("DocumentBuffer")
class DocumentBuffer:
    """Gerencia o documento como uma lista de linhas e múltiplos cursores.
    
    Implementa lógica de inserção/remoção simultânea e histórico de ações.
    """

    def __init__(self, initial_text: str = ""):
        self._lines: List[str] = initial_text.split('\n') if initial_text else [""]
        self.cursors: List[Cursor] = [Cursor(0, 0)]
        self.dirty = False
        
        # Pilhas de Undo/Redo
        self._undo_stack: List[Action] = []
        self._redo_stack: List[Action] = []

    @property
    def lines(self) -> List[str]:
        return list(self._lines)

    @property
    def line_count(self) -> int:
        return len(self._lines)

    def get_text(self) -> str:
        return "\n".join(self._lines)

    def get_lines(self, start: int, end: int) -> List[str]:
        """Retorna um intervalo de linhas (seguro)."""
        start = max(0, start)
        end = min(len(self._lines), end)
        return self._lines[start:end]

    def add_cursor(self, line: int, col: int) -> None:
        """Adiciona um novo cursor na posição especificada."""
        # Validação básica
        line = max(0, min(line, len(self._lines) - 1))
        col = max(0, min(col, len(self._lines[line])))
        
        # Evita duplicatas
        for c in self.cursors:
            if c.line == line and c.col == col:
                return
        self.cursors.append(Cursor(line, col))

    def update_last_cursor(self, line: int, col: int, keep_anchor: bool = False) -> None:
        """Atualiza a posição do último cursor (principal).
        
        Args:
            keep_anchor: Se True, mantém a âncora original (seleção). Se False, reseta a âncora.
        """
        if not self.cursors: return
        
        # Validação de limites (Clamping)
        line = max(0, min(line, len(self._lines) - 1))
        col = max(0, min(col, len(self._lines[line])))
        
        cursor = self.cursors[-1]
        cursor.line = line
        cursor.col = col
        
        if not keep_anchor:
            cursor.anchor_line = line
            cursor.anchor_col = col

    def has_selection(self, cursor_index: int = -1) -> bool:
        """Verifica se um cursor específico tem uma seleção ativa."""
        if not self.cursors or cursor_index >= len(self.cursors): return False
        cursor = self.cursors[cursor_index]
        return (cursor.line, cursor.col) != (cursor.anchor_line, cursor.anchor_col)

    def get_selection_range(self, cursor_index: int = -1) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Retorna o intervalo (início, fim) ordenado da seleção para um cursor."""
        if not self.has_selection(cursor_index): return None
        cursor = self.cursors[cursor_index]

        start_pos = (cursor.anchor_line, cursor.anchor_col)
        end_pos = (cursor.line, cursor.col)

        return (start_pos, end_pos) if start_pos <= end_pos else (end_pos, start_pos)

    def get_selected_text(self, cursor_index: int = -1) -> str:
        """Retorna o texto selecionado para um cursor específico."""
        range_ = self.get_selection_range(cursor_index)
        if not range_: return ""

        (start_line, start_col), (end_line, end_col) = range_

        if start_line == end_line:
            return self._lines[start_line][start_col:end_col]
        else:
            selected_lines = [self._lines[start_line][start_col:]]
            selected_lines.extend(self._lines[start_line + 1:end_line])
            selected_lines.append(self._lines[end_line][:end_col])
            return "\n".join(selected_lines)

    def clear_cursors(self) -> None:
        """Remove todos os cursores extras, mantendo apenas o principal (último)."""
        if self.cursors:
            self.cursors = [self.cursors[-1]]

    def insert_text(self, text: str) -> None:
        """Insere texto em todos os cursores. Se houver seleção, ela é substituída."""
        if any(self.has_selection(i) for i in range(len(self.cursors))):
            self.delete_selection()

        # Salva estado para Undo (simplificado)
        cursors_snapshot = copy.deepcopy(self.cursors)
        
        # Ordena cursores de baixo para cima, direita para esquerda
        # Isso evita que a inserção em uma linha afete os índices dos cursores anteriores
        sorted_cursors = sorted(
            self.cursors, 
            key=lambda c: (c.line, c.col), 
            reverse=True
        )

        for cursor in sorted_cursors:
            self._insert_at_single_cursor(cursor, text)

        # Registra ação (TODO: Implementar lógica completa de diff)
        self._undo_stack.append(Action('insert', text, cursors_snapshot, copy.deepcopy(self.cursors)))
        self._redo_stack.clear()
        self.dirty = True

    def insert_paired_text(self, pair: str) -> None:
        """Inserts a pair of characters (e.g., "()") and places the cursor in the middle."""
        if len(pair) != 2:
            self.insert_text(pair)
            return

        open_char, close_char = pair[0], pair[1]
        cursors_snapshot = copy.deepcopy(self.cursors)

        sorted_cursors = sorted(
            self.cursors,
            key=lambda c: (c.line, c.col),
            reverse=True
        )

        for cursor in sorted_cursors:
            self._insert_at_single_cursor(cursor, open_char + close_char)
            cursor.col -= len(close_char)
            cursor.anchor_line = cursor.line
            cursor.anchor_col = cursor.col

        self.dirty = True

    def replace_full_text(self, text_before: str, text_after: str, cursors_before: List[Cursor]):
        """Replaces the entire buffer content, creating a single undo action."""
        self._lines = text_after.split('\n')
        # Reset cursor to a safe position
        self.cursors = [Cursor(0, 0)]
        
        action = Action('replace_all', text_after, cursors_before, self.cursors, text_before=text_before)
        self._undo_stack.append(action)
        self._redo_stack.clear()
        self.dirty = True

    def _insert_at_single_cursor(self, cursor: Cursor, text: str) -> None:
        """Lógica interna de inserção para um único cursor."""
        line_idx = cursor.line
        col_idx = cursor.col
        current_line = self._lines[line_idx]
        
        insert_lines = text.split('\n')
        
        prefix = current_line[:col_idx]
        suffix = current_line[col_idx:]

        if len(insert_lines) == 1:
            # Caso simples: mesma linha
            self._lines[line_idx] = prefix + insert_lines[0] + suffix
            cursor.col += len(insert_lines[0])
            
            # Ajusta outros cursores na MESMA linha que estavam à direita
            for other in self.cursors:
                if other is not cursor and other.line == line_idx and other.col >= col_idx:
                    other.col += len(insert_lines[0])
        else:
            # Caso complexo: quebra de linha
            self._lines[line_idx] = prefix + insert_lines[0]
            
            # Insere linhas intermediárias
            for i in range(1, len(insert_lines) - 1):
                self._lines.insert(line_idx + i, insert_lines[i])
            
            # Última linha fundida com sufixo
            last_line_content = insert_lines[-1] + suffix
            self._lines.insert(line_idx + len(insert_lines) - 1, last_line_content)
            
            # Atualiza o cursor atual
            cursor.line += len(insert_lines) - 1
            cursor.col = len(insert_lines[-1])
            
            # Ajusta cursores abaixo (shift vertical)
            lines_added = len(insert_lines) - 1
            for other in self.cursors:
                if other is not cursor and other.line > line_idx:
                    other.line += lines_added

    def move_cursors(self, d_line: int, d_col: int) -> None:
        """Move todos os cursores por um deslocamento (delta)."""
        for cursor in self.cursors:
            new_line = cursor.line + d_line
            new_col = cursor.col + d_col
            
            # Clamping vertical
            new_line = max(0, min(new_line, len(self._lines) - 1))
            
            # Lógica horizontal simples (sem wrap de linha por enquanto)
            line_len = len(self._lines[new_line])
            new_col = max(0, min(new_col, line_len))
            
            cursor.line = new_line
            cursor.col = new_col
            
        # Remove cursores sobrepostos após o movimento
        self._merge_cursors()

    def add_cursor_relative(self, d_line: int) -> None:
        """Adiciona um novo cursor relativo ao último cursor ativo (ex: Alt+Down)."""
        if not self.cursors:
            return
            
        base_cursor = self.cursors[-1]
        target_line = base_cursor.line + d_line
        
        if 0 <= target_line < len(self._lines):
            # Tenta manter a mesma coluna, ajustando ao comprimento da nova linha
            target_col = min(base_cursor.col, len(self._lines[target_line]))
            self.add_cursor(target_line, target_col)

    def _merge_cursors(self):
        """Remove cursores duplicados (mesma posição)."""
        unique = set()
        new_cursors = []
        for c in self.cursors:
            pos = (c.line, c.col)
            if pos not in unique:
                unique.add(pos)
                new_cursors.append(c)
        self.cursors = new_cursors

    def delete_backspace(self) -> None:
        """Executa backspace. Se houver seleção, deleta a seleção."""
        if any(self.has_selection(i) for i in range(len(self.cursors))):
            self.delete_selection()
            self.dirty = True
            self._redo_stack.clear()
            return

        # Ordena reverso para não invalidar índices
        sorted_cursors = sorted(
            self.cursors, 
            key=lambda c: (c.line, c.col), 
            reverse=True
        )
        
        for cursor in sorted_cursors:
            self._delete_char_at(cursor)
        
        # TODO: Store deleted text for undo
        self.dirty = True
        self._redo_stack.clear()

    def delete_selection(self) -> None:
        """Deleta a seleção para todos os cursores."""
        sorted_indices = sorted(
            range(len(self.cursors)),
            key=lambda i: self.get_selection_range(i) or ((0,0),(0,0)),
            reverse=True
        )

        for i in sorted_indices:
            self._delete_single_selection(i)
        
        self._merge_cursors()

    def _delete_single_selection(self, cursor_index: int):
        """Lógica interna para deletar a seleção de um único cursor."""
        range_ = self.get_selection_range(cursor_index)
        if not range_: return

        (start_line, start_col), (end_line, end_col) = range_

        first_line_content = self._lines[start_line]
        last_line_content = self._lines[end_line]

        # Junta o início da primeira linha com o fim da última
        self._lines[start_line] = first_line_content[:start_col] + last_line_content[end_col:]

        # Deleta linhas intermediárias
        lines_deleted = end_line - start_line
        if lines_deleted > 0:
            del self._lines[start_line + 1 : end_line + 1]

        # Reposiciona e limpa a seleção do cursor
        cursor = self.cursors[cursor_index]
        cursor.line, cursor.col = start_line, start_col
        cursor.anchor_line, cursor.anchor_col = start_line, start_col

    def _delete_char_at(self, cursor: Cursor) -> None:
        line = cursor.line
        col = cursor.col
        
        if col > 0:
            # Remove char na mesma linha
            txt = self._lines[line]
            self._lines[line] = txt[:col-1] + txt[col:]
            cursor.col -= 1
            # TODO: Ajustar cursores vizinhos na mesma linha
        elif line > 0:
            # Merge com linha de cima
            prev_line_len = len(self._lines[line-1])
            self._lines[line-1] += self._lines[line]
            del self._lines[line]
            cursor.line -= 1
            cursor.col = prev_line_len
            # TODO: Ajustar cursores abaixo (shift vertical negativo)

    def get_matching_bracket(self, line: int, col: int) -> Optional[Tuple[int, int]]:
        """Encontra a posição do bracket correspondente (simples)."""
        if line >= len(self._lines): return None
        
        text = self._lines[line]
        # Verifica se há um bracket à esquerda ou na posição atual
        char = text[col] if col < len(text) else None
        if char is None or char not in "()[]{}":
            if col > 0 and text[col-1] in "()[]{}":
                col -= 1
                char = text[col]
            else:
                return None

        pairs = {'(': ')', '[': ']', '{': '}', ')': '(', ']': '[', '}': '{'}
        target = pairs.get(char)
        direction = 1 if char in "([{" else -1
        
        # Busca simplificada (limitada a +/- 1000 linhas para performance)
        balance = 0
        current_line = line
        current_col = col
        
        while 0 <= current_line < len(self._lines):
            line_txt = self._lines[current_line]
            start_search = current_col + direction if current_line == line else (0 if direction == 1 else len(line_txt) - 1)
            
            range_iter = range(start_search, len(line_txt)) if direction == 1 else range(start_search, -1, -1)
            
            for i in range_iter:
                c = line_txt[i]
                if c == char: balance += 1
                elif c == target:
                    if balance == 0: return (current_line, i)
                    balance -= 1
            
            current_line += direction
            if abs(current_line - line) > 1000: break
            
        return None

    def select_word_at(self, line: int, col: int):
        """Seleciona a palavra na posição do cursor."""
        if line >= len(self._lines): return
        line_text = self._lines[line]
        if col > len(line_text): return

        separators = " \t\n\r.,:;()[]{}<>'\"`~-="

        start = col
        while start > 0 and line_text[start - 1] not in separators:
            start -= 1

        end = col
        while end < len(line_text) and line_text[end] not in separators:
            end += 1

        self.update_last_cursor(line, end)
        self.cursors[-1].anchor_col = start

    def select_line_at(self, line: int):
        """Seleciona a linha inteira."""
        if line >= len(self._lines): return
        self.update_last_cursor(line, len(self._lines[line]))
        self.cursors[-1].anchor_col = 0

    def undo(self):
        """Desfaz a última ação."""
        if not self._undo_stack:
            return

        action = self._undo_stack.pop()
        
        if action.type == 'insert':
            # This requires a proper 'delete' implementation which is complex.
            logger.warning("Undo for simple insertion is not fully implemented.")
            self._undo_stack.append(action) # Put it back
            return
        elif action.type == 'replace_all':
            self._lines = action.text_before.split('\n')
            self.cursors = action.cursors_before
            
        self._redo_stack.append(action)
        self.dirty = True

    def redo(self):
        """Refaz a última ação desfeita."""
        if not self._redo_stack:
            return

        action = self._redo_stack.pop()
        self._lines = action.text.split('\n')
        self.cursors = action.cursors_after
        self._undo_stack.append(action)
        self.dirty = True
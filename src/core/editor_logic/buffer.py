from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict
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

@dataclass
class Action:
    """Representa uma ação para o sistema de Undo/Redo."""
    type: str  # 'insert' ou 'delete'
    text: str
    cursors_before: List[Cursor]
    cursors_after: List[Cursor]

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

    def clear_cursors(self) -> None:
        """Remove todos os cursores extras, mantendo apenas o principal (último)."""
        if self.cursors:
            self.cursors = [self.cursors[-1]]

    def insert_text(self, text: str) -> None:
        """Insere texto em TODOS os cursores ativos simultaneamente."""
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
        """Executa backspace em todos os cursores."""
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

    def undo(self):
        """Desfaz a última ação."""
        # TODO: Implementar lógica de Undo
        logger.warning("Funcionalidade 'Undo' não implementada.")

    def redo(self):
        """Refaz a última ação desfeita."""
        # TODO: Implementar lógica de Redo
        logger.warning("Funcionalidade 'Redo' não implementada.")
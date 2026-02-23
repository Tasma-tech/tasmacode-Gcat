from src.core.editor_logic.buffer import DocumentBuffer
from typing import List, Tuple
from collections import defaultdict
import re

class SearchManager:
    """Manages search and replace operations within a DocumentBuffer."""

    def __init__(self):
        self.highlights = []
        self.root_path = None

    def set_root_path(self, path: str):
        self.root_path = path

    def find_all(self, buffer: DocumentBuffer, text: str, case_sensitive: bool = False, whole_word: bool = False) -> List[Tuple[int, int, int]]:
        """
        Finds all occurrences of a text string in the buffer.
        Returns a list of tuples: (line_index, start_col, length).
        """
        if not text:
            self.highlights = []
            return []

        results = []
        
        # Configura Regex
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern_str = re.escape(text)
        if whole_word:
            pattern_str = r'\b' + pattern_str + r'\b'
        
        try:
            regex = re.compile(pattern_str, flags)
        except re.error:
            return [] # Regex inválido (embora re.escape deva prevenir)
        
        for i, line in enumerate(buffer.lines):
            for match in regex.finditer(line):
                start, end = match.span()
                results.append((i, start, end - start))
        
        self.highlights = results
        return results

    def clear_highlights(self):
        self.highlights = []

    def replace_all(self, buffer: DocumentBuffer, find_text: str, replace_text: str, case_sensitive: bool = False, whole_word: bool = False) -> int:
        """
        Performs a replace-all operation and makes it undoable as a single block.
        Returns the number of replacements made.
        """
        if not find_text:
            return 0

        occurrences = self.find_all(buffer, find_text, case_sensitive, whole_word)
        if not occurrences:
            return 0

        text_before = buffer.get_text()
        cursors_before = [c.copy() for c in buffer.cursors]
        
        new_lines = list(buffer.lines)
        line_changes = defaultdict(list)
        for line_idx, col, length in occurrences:
            line_changes[line_idx].append((col, length))

        for line_idx in sorted(line_changes.keys(), reverse=True):
            line = new_lines[line_idx]
            for col, length in sorted(line_changes[line_idx], reverse=True, key=lambda x: x[0]):
                line = line[:col] + replace_text + line[col+length:]
            new_lines[line_idx] = line
        
        buffer.replace_full_text(text_before, "\n".join(new_lines), cursors_before)
        self.clear_highlights()
        return len(occurrences)
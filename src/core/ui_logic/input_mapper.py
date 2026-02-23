from PySide6.QtCore import Qt, QObject
from PySide6.QtGui import QKeyEvent
from typing import Dict, Optional
import logging

logger = logging.getLogger("InputMapper")

class InputMapper(QObject):
    """Mapeia eventos de teclado para comandos registrados."""

    def __init__(self, command_registry):
        super().__init__()
        self.registry = command_registry
        self.key_bindings: Dict[str, str] = {}
        self.pending_chord = ""
        
        # Carrega bindings padrão (futuramente virá de um JSON)
        self._load_defaults()

    def _load_defaults(self):
        self.key_bindings = {
            "Up": "cursor.move_up",
            "Down": "cursor.move_down",
            "Left": "cursor.move_left",
            "Right": "cursor.move_right",
            "Shift+Up": "cursor.select_up",
            "Shift+Down": "cursor.select_down",
            "Shift+Left": "cursor.select_left",
            "Shift+Right": "cursor.select_right",
            "Alt+Up": "cursor.add_up",
            "Alt+Down": "cursor.add_down",
            "Backspace": "edit.backspace",
            "Return": "edit.new_line",
            "Tab": "edit.indent",
            # Exemplo de Chord
            "Ctrl+K, Ctrl+C": "editor.comment_line",
            # Undo / Redo
            "Ctrl+Z": "edit.undo",
            "Ctrl+Y": "edit.redo",
            "Ctrl+Shift+Z": "edit.redo",
            # Rename
            "F2": "edit.rename"
        }

    def handle_key(self, event: QKeyEvent) -> bool:
        """Processa o evento de tecla. Retorna True se consumiu o evento."""
        key_sequence = self._event_to_string(event)
        
        if not key_sequence:
            return False

        # Lógica de Chord (Sequência de teclas)
        check_sequence = key_sequence
        if self.pending_chord:
            check_sequence = f"{self.pending_chord}, {key_sequence}"

        # 1. Verifica correspondência exata de comando
        if check_sequence in self.key_bindings:
            cmd_id = self.key_bindings[check_sequence]
            self.registry.execute(cmd_id)
            self.pending_chord = "" # Reset após execução
            return True

        # 2. Verifica se é o início de um chord (prefixo)
        # Ex: Se digitei "Ctrl+K", e existe "Ctrl+K, Ctrl+C", aguarda.
        if any(k.startswith(check_sequence + ",") for k in self.key_bindings):
            self.pending_chord = check_sequence
            logger.info(f"Aguardando sequência de chord: {self.pending_chord}...")
            return True
        
        # Se não casou chord nem prefixo, reseta estado
        self.pending_chord = ""

        # 3. Tratamento de Digitação (Texto)
        # Ignora se tiver modificadores de controle (exceto Shift)
        modifiers = event.modifiers()
        has_ctrl = bool(modifiers & Qt.ControlModifier)
        has_alt = bool(modifiers & Qt.AltModifier)
        
        text = event.text()
        if text and text.isprintable() and not (has_ctrl or has_alt):
            # Auto-pairing logic
            pairing_map = {'(': '()', '[': '[]', '{': '{}', '"': '""', "'": "''"}
            if text in pairing_map:
                # TODO: Add logic to wrap selection if it exists
                self.registry.execute("edit.insert_pair", pairing_map[text])
                return True

            # Default character typing
            self.registry.execute("type_char", text)
            return True

        return False

    def _event_to_string(self, event: QKeyEvent) -> str:
        """Converte QKeyEvent para string no formato 'Ctrl+Shift+A'."""
        key = event.key()
        modifiers = event.modifiers()
        
        # Ignora teclas modificadoras sozinhas
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            return ""

        parts = []
        if modifiers & Qt.ControlModifier: parts.append("Ctrl")
        if modifiers & Qt.AltModifier: parts.append("Alt")
        if modifiers & Qt.ShiftModifier: parts.append("Shift")
        
        # Mapeamento de teclas especiais
        key_map = {
            Qt.Key_Backspace: "Backspace", Qt.Key_Return: "Return", Qt.Key_Enter: "Return",
            Qt.Key_Tab: "Tab", Qt.Key_Space: "Space",
            Qt.Key_Left: "Left", Qt.Key_Right: "Right", Qt.Key_Up: "Up", Qt.Key_Down: "Down",
            Qt.Key_Escape: "Escape", Qt.Key_Delete: "Delete"
        }
        
        if key in key_map:
            parts.append(key_map[key])
        elif 0x20 <= key <= 0x7e: # ASCII imprimível
            parts.append(chr(key).upper())
        else:
            # Fallback para nome da tecla do Qt ou ignorar
            return ""
            
        return "+".join(parts)
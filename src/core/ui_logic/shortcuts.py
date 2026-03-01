from PySide6.QtGui import QKeySequence

class Shortcuts:
    """Definições centralizadas de atalhos de teclado."""
    
    # Gestão de Arquivos
    NEW_FILE = "Ctrl+N"
    NEW_FOLDER = "Ctrl+Shift+N"
    OPEN_FILE = "Ctrl+O"
    OPEN_FOLDER = "Ctrl+K, Ctrl+O" # Exemplo de chord
    SAVE_FILE = QKeySequence.StandardKey.Save
    SAVE_AS = "Ctrl+Shift+S"
    CLOSE_TAB = "Ctrl+W"
    
    # Edição
    UNDO = QKeySequence.StandardKey.Undo
    REDO = QKeySequence.StandardKey.Redo
    CUT = QKeySequence.StandardKey.Cut
    COPY = QKeySequence.StandardKey.Copy
    PASTE = QKeySequence.StandardKey.Paste
    FIND = QKeySequence.StandardKey.Find
    RENAME = "F2"
    
    # Interface e Navegação
    TOGGLE_SIDEBAR = "Ctrl+B"
    REFRESH_EXPLORER = "F5"
    FOCUS_SIDEBAR_SEARCH = "Ctrl+Shift+F"
    NEXT_TAB = "Ctrl+Tab"
    PREV_TAB = "Ctrl+Shift+Tab"
    COMMAND_PALETTE = "Ctrl+Shift+P"
    SWITCH_PROJECT = "Ctrl+R"
    
    # Ajuda
    HELP = "F1"
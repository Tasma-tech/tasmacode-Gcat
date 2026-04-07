from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel, QHBoxLayout
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtCore import Qt, Signal
from .editor import CodeEditor
import os

class EditorGroup(QWidget):
    """
    A container that manages multiple CodeEditor widgets in a tabbed interface.
    """
    active_editor_changed = Signal(object) # Emits the new active CodeEditor or None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_accent = "#007acc"
        self.icon_labels = []
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        self.layout.addWidget(self.tab_widget)
        
        self._show_placeholder()

    def _show_placeholder(self):
        """Exibe um placeholder com um ícone e texto de boas-vindas."""
        self.icon_labels = []
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.setSpacing(20)

        # --- Ícone SVG ---
        icon_path = 'icon/JCODE.svg'

        if os.path.exists(icon_path):
            svg_widget = QSvgWidget(icon_path)
            svg_widget.setFixedSize(650, 510)
            placeholder_layout.addWidget(svg_widget)
        else:
            icon_missing_label = QLabel(f"[Ícone não encontrado: {icon_path}]")
            icon_missing_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder_layout.addWidget(icon_missing_label)

        # --- Título ---
        titulo_label = QLabel(" ")
        titulo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_layout.addWidget(titulo_label)

        # --- Dicas ---
        dicas_title = QLabel("Atalhos Essenciais")
        dicas_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dicas_title.setStyleSheet("font-size: 16px; color: #858585; margin-bottom: 15px;")
        placeholder_layout.addWidget(dicas_title)

        dicas_container = QWidget()
        dicas_container.setFixedWidth(500)
        dicas_v_layout = QVBoxLayout(dicas_container)
        dicas_v_layout.setContentsMargins(0, 0, 0, 0)
        dicas_v_layout.setSpacing(8)

        dicas_data = [
            {'icon': '', 'shortcut': 'Ctrl + B', 'description': 'Mostrar/Ocultar barra lateral'},
            {'icon': '', 'shortcut': 'Ctrl + S', 'description': 'Salvar arquivo atual'},
            {'icon': '', 'shortcut': 'Ctrl + Alt + B', 'description': 'Abrir painel de controle Git'},
            {'icon': '', 'shortcut': 'Ctrl + Shift + P', 'description': 'Abrir Paleta de Comandos'},
            {'icon': '', 'shortcut': 'F1', 'description': 'Exibir guia de atalhos'},
        ]

        for dica in dicas_data:
            dica_widget = QWidget()
            dica_h_layout = QHBoxLayout(dica_widget)
            dica_h_layout.setContentsMargins(10, 5, 10, 5)
            dica_h_layout.setSpacing(15)

            icon_label = QLabel(dica['icon'])
            icon_label.setStyleSheet(f"color: {self.current_accent}; font-size: 16px; font-weight: bold;")
            self.icon_labels.append(icon_label)

            shortcut_label = QLabel(dica['shortcut'])
            shortcut_label.setMinimumWidth(140)
            shortcut_label.setStyleSheet("color: #cccccc; font-size: 13px; font-family: 'Consolas', 'Monospace';")

            desc_label = QLabel(dica['description'])
            desc_label.setStyleSheet("color: #858585; font-size: 13px;")

            dica_h_layout.addWidget(icon_label)
            dica_h_layout.addWidget(shortcut_label)
            dica_h_layout.addWidget(desc_label)
            dica_h_layout.addStretch()

            dicas_v_layout.addWidget(dica_widget)

        placeholder_layout.addWidget(dicas_container, 0, Qt.AlignmentFlag.AlignCenter)
        self.placeholder = placeholder_widget
        self.tab_widget.addTab(self.placeholder, "")
        self.tab_widget.setTabsClosable(False)

    def apply_theme(self, theme):
        self.current_accent = theme.get("accent", "#007acc")
        for label in self.icon_labels:
            try:
                label.setStyleSheet(f"color: {self.current_accent}; font-size: 16px; font-weight: bold;")
            except RuntimeError:
                pass # Ignora se o widget já foi deletado

    def add_editor(self, editor_widget: CodeEditor, file_path: str) -> None:
        """Adds a new editor to a tab."""
        if self.tab_widget.widget(0) == self.placeholder:
            self.tab_widget.removeTab(0)
            self.tab_widget.setTabsClosable(True)
            
        file_name = os.path.basename(file_path)
        index = self.tab_widget.addTab(editor_widget, file_name)
        self.tab_widget.setCurrentIndex(index)

    def close_tab(self, index: int) -> None:
        # TODO: Check for unsaved changes before closing
        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        if widget:
            widget.deleteLater()
        
        if self.tab_widget.count() == 0:
            self._show_placeholder()
            self.active_editor_changed.emit(None)

    def get_active_editor(self) -> CodeEditor | None:
        widget = self.tab_widget.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None

    def _on_tab_changed(self, index: int) -> None:
        editor = self.tab_widget.widget(index)
        if isinstance(editor, CodeEditor):
            self.active_editor_changed.emit(editor)
        else:
            self.active_editor_changed.emit(None)
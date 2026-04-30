from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QMenu, QInputDialog, QFileDialog
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QColor
import os

class TasmaSidebar(QWidget):
    """Barra lateral do TasmaFile."""
    
    category_selected = Signal(str, str) # tipo, dados (caminho ou id)

    def __init__(self, provider, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.setFixedWidth(200)
        self.theme = {}
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        
        # Context Menu
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.list_widget)
        self._populate()

    def apply_theme(self, theme):
        self.theme = theme
        bg = theme.get("sidebar_bg", "#252526")
        fg = theme.get("foreground", "#cccccc")
        border = theme.get("border_color", "#3e3e42")
        hover = theme.get("selection", "#37373d")
        
        self.setStyleSheet(f"background-color: {bg}; border-right: 1px solid {border};")
        
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ border: none; background-color: transparent; color: {fg}; font-size: 13px; outline: none; }}
            QListWidget::item {{ padding: 8px; border-radius: 4px; margin: 2px 5px; }}
            QListWidget::item:selected {{ background-color: {hover}; color: white; border-left: 3px solid {theme.get('accent', '#007acc')}; }}
            QListWidget::item:hover {{ background-color: {border}; }}
        """)

    def _populate(self):
        self.list_widget.clear()
        # Seção: Navegação
        
        # Seção: Favoritos (Custom)
        custom = self.provider.get_custom_categories()
        if custom:
            self._add_header("FAVORITOS")
            for name, path in custom.items():
                self._add_item(name, "custom", path)

        self._add_header("NAVEGAÇÃO")
        self._add_item("Este Computador", "root", self.provider.get_root_dir())
        self._add_item("Pasta de Usuário", "home", self.provider.get_home_dir())
        
        # Seção: Projetos
        self._add_header("PROJETOS")
        recents = self.provider.get_recent_projects()
        for path in recents:
            self._add_item(path.split("/")[-1], "recent", path)
            
        # Seção: Sistema JCode
        self._add_header("JCODE SYSTEM")
        self._add_item("Código Fonte", "source", self.provider.get_editor_source())
        self._add_item("Plugins", "plugins_root", "plugins_virtual_root") # Placeholder logic

    def _add_header(self, text):
        item = QListWidgetItem(text)
        item.setFlags(Qt.NoItemFlags) # Não selecionável
        item.setForeground(QColor("#808080"))
        font = item.font()
        font.setBold(True)
        font.setPointSize(10)
        item.setFont(font)
        self.list_widget.addItem(item)

    def _add_item(self, label, type_id, data):
        item = QListWidgetItem(f"  {label}")
        item.setData(Qt.UserRole, {"type": type_id, "data": data})
        self.list_widget.addItem(item)

    def _on_item_clicked(self, item):
        data = item.data(Qt.UserRole)
        if data:
            self.category_selected.emit(data["type"], data["data"])

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        
        # Apply theme
        bg = self.theme.get("sidebar_bg", "#252526")
        fg = self.theme.get("foreground", "#cccccc")
        accent = self.theme.get("accent", "#007acc")
        menu.setStyleSheet(f"QMenu {{ background-color: {bg}; color: {fg}; }} QMenu::item:selected {{ background-color: {accent}; }}")
        
        add_action = menu.addAction("Adicionar aos Favoritos")
        add_action.triggered.connect(self._add_category_dialog)
        
        item = self.list_widget.itemAt(pos)
        if item:
            data = item.data(Qt.UserRole)
            if data and data.get("type") == "custom":
                name = item.text().strip()
                remove_action = menu.addAction(f"Remover '{name}'")
                remove_action.triggered.connect(lambda: self.provider.remove_custom_category(name) or self._populate())

        menu.exec(self.list_widget.mapToGlobal(pos))

    def _add_category_dialog(self):
        path = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Favoritos")
        if path:
            name, ok = QInputDialog.getText(self, "Adicionar Favorito", "Nome:", text=os.path.basename(path))
            if ok and name:
                self.provider.add_custom_category(name, path)
                self._populate()
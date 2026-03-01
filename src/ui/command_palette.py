from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt

class CommandPalette(QDialog):
    """Janela flutuante para busca e execução de comandos (Ctrl+Shift+P)."""
    
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.resize(500, 300)
        self.setStyleSheet("background-color: #252526; border: 1px solid #454545; color: #cccccc;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type a command...")
        self.search_input.setStyleSheet("background-color: #3c3c3c; border: none; padding: 5px; color: white;")
        self.search_input.textChanged.connect(self._filter_commands)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background-color: #252526; border: none; color: #cccccc; }
            QListWidget::item:selected { background-color: #007acc; color: white; }
            QListWidget::item:hover { background-color: #2a2d2e; }
        """)
        self.list_widget.itemActivated.connect(self._execute_command)
        
        layout.addWidget(self.search_input)
        layout.addWidget(self.list_widget)
        
        self.commands = [] # Lista de dicionários: {'name': str, 'callback': callable, 'tags': list}

    def register_command(self, name: str, callback, search_tags: list = None):
        """Registra um comando com um nome, uma função de callback e tags de busca opcionais."""
        if search_tags is None:
            search_tags = []
        self.commands.append({'name': name, 'callback': callback, 'tags': search_tags})

    def show_palette(self):
        self.search_input.clear()
        self._populate_list()
        self.list_widget.setCurrentRow(0)
        # Centraliza na janela pai
        if self.parent():
            geo = self.parent().geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + 50 # Um pouco abaixo do topo
            self.move(x, y)
        self.show()
        self.search_input.setFocus()

    def _populate_list(self):
        self.list_widget.clear()
        # Ordena comandos por nome para consistência
        self.commands.sort(key=lambda c: c['name'])
        for cmd_data in self.commands:
            self.list_widget.addItem(cmd_data['name'])

    def _filter_commands(self, text):
        lower_text = text.lower()
        if not lower_text:
            # Se o campo de busca estiver vazio, mostra tudo
            for i in range(self.list_widget.count()):
                self.list_widget.item(i).setHidden(False)
            return

        for i, cmd_data in enumerate(self.commands):
            item = self.list_widget.item(i)
            
            name = cmd_data['name'].lower()
            
            # Lógica Fuzzy: verifica se os caracteres de busca aparecem na ordem correta
            it = iter(name)
            is_match = all(char in it for char in lower_text)
            
            # Busca nas tags se não encontrou no nome
            if not is_match:
                for tag in cmd_data.get('tags', []):
                    if lower_text in str(tag).lower():
                        is_match = True
                        break
            
            item.setHidden(not is_match)

    def _execute_command(self, item):
        cmd_name = item.text()
        for cmd_data in self.commands:
            if cmd_data['name'] == cmd_name:
                cmd_data['callback']()
                self.close()
                return
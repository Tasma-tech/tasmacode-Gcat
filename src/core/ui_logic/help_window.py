from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QLineEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QColor
from src.core.ui_logic.shortcuts import Shortcuts

class HelpWindow(QDialog):
    """Janela de ajuda aprimorada com busca e lista organizada de atalhos."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Atalhos")
        self.resize(650, 550)
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(25, 25, 25, 25)
        
        # Header e Busca
        title = QLabel("Atalhos do Teclado")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        self.layout.addWidget(title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Filtrar comandos...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._filter_content)
        
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 8px;
                padding: 10px 15px;
                color: #e0e0e0;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
                background-color: #333336;
            }
        """)
        self.layout.addWidget(self.search_input)
        
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: transparent;
                border: none;
            }
            QTableWidget::item {
                padding: 8px 0;
                border-bottom: 1px solid #333333;
            }
        """)
        
        self.layout.addWidget(self.table)
        
        # Dados
        self.all_data = []
        self._load_shortcuts_data()
        self._populate_table()
        
    def _load_shortcuts_data(self):
        """Carrega os dados de atalhos em uma estrutura pesquisável."""
        sections = {
            "Arquivos": [
                ("Novo Arquivo", Shortcuts.NEW_FILE),
                ("Nova Pasta", Shortcuts.NEW_FOLDER),
                ("Abrir Arquivo", Shortcuts.OPEN_FILE),
                ("Salvar", Shortcuts.SAVE_FILE),
                ("Salvar Como", Shortcuts.SAVE_AS),
                ("Fechar Aba", Shortcuts.CLOSE_TAB),
            ],
            "Edição": [
                ("Desfazer", Shortcuts.UNDO),
                ("Refazer", Shortcuts.REDO),
                ("Copiar", Shortcuts.COPY),
                ("Colar", Shortcuts.PASTE),
                ("Recortar", Shortcuts.CUT),
                ("Localizar", Shortcuts.FIND),
                ("Renomear Variável", Shortcuts.RENAME),
            ],
            "Interface & Navegação": [
                ("Alternar Sidebar", Shortcuts.TOGGLE_SIDEBAR),
                ("Alternar Git Sidebar", Shortcuts.TOGGLE_RIGHT_SIDEBAR),
                ("Focar Busca Sidebar", Shortcuts.FOCUS_SIDEBAR_SEARCH),
                ("Atualizar Explorer", Shortcuts.REFRESH_EXPLORER),
                ("Próxima Aba", Shortcuts.NEXT_TAB),
                ("Aba Anterior", Shortcuts.PREV_TAB),
                ("Paleta de Comandos", Shortcuts.COMMAND_PALETTE),
                ("Alternar Projeto", Shortcuts.SWITCH_PROJECT),
            ],
            "Geral & Zoom": [
                ("Ajuda", Shortcuts.HELP),
                ("Zoom Aumentar", Shortcuts.ZOOM_IN),
                ("Zoom Diminuir", Shortcuts.ZOOM_OUT),
                ("Easter Egg", Shortcuts.BATATA),
            ]
        }
        
        for section, items in sections.items():
            self.all_data.append({"type": "header", "text": section})
            for label, shortcut in items:
                # Converte shortcut para string legível
                if not isinstance(shortcut, QKeySequence):
                    shortcut = QKeySequence(shortcut)
                shortcut_str = shortcut.toString(QKeySequence.NativeText)
                
                self.all_data.append({
                    "type": "item",
                    "label": label,
                    "shortcut": shortcut_str
                })

    def _filter_content(self, text):
        self._populate_table(filter_text=text)

    def _populate_table(self, filter_text=""):
        self.table.setRowCount(0)
        filter_text = filter_text.lower()
        
        rows = []
        # Filtra os dados
        for item in self.all_data:
            if item["type"] == "header":
                if not filter_text: # Só mostra headers se não estiver filtrando
                    rows.append(item)
            else:
                if filter_text in item["label"].lower() or filter_text in item["shortcut"].lower():
                    rows.append(item)
        
        self.table.setRowCount(len(rows))
        
        font_header = self.font()
        font_header.setBold(True)
        font_header.setPointSize(11)
        
        font_mono = QFont("Consolas")
        font_mono.setStyleHint(QFont.Monospace)
        font_mono.setPointSize(10)

        for i, row_data in enumerate(rows):
            if row_data["type"] == "header":
                item = QTableWidgetItem(row_data['text'])
                item.setFlags(Qt.NoItemFlags)
                item.setFont(font_header)
                item.setForeground(QColor("#007acc"))
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
                self.table.setItem(i, 0, item)
                self.table.setSpan(i, 0, 1, 2) # Ocupa toda a linha
            else:
                label_item = QTableWidgetItem(row_data["label"])
                label_item.setForeground(QColor("#e0e0e0"))
                
                shortcut_item = QTableWidgetItem(row_data["shortcut"])
                shortcut_item.setFont(font_mono)
                shortcut_item.setTextAlignment(Qt.AlignCenter)
                shortcut_item.setForeground(QColor("#a0a0a0"))
                
                self.table.setItem(i, 0, label_item)
                self.table.setItem(i, 1, shortcut_item)
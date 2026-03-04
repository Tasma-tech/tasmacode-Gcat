import sys
import os
import json
import requests
import re
import uuid
import difflib
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                               QHBoxLayout, QSplitter, QInputDialog, QToolButton, QLabel, 
                               QDialog, QFormLayout, QComboBox, QDialogButtonBox, QMessageBox,
                               QTextBrowser, QListWidget, QListWidgetItem, QFileDialog, QStyle, QTreeView, QFileSystemModel, QMenu)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QUrl, QDir, QSortFilterProxyModel
from PySide6.QtGui import QFont, QTextCursor, QDesktopServices, QColor, QCursor, QSyntaxHighlighter, QTextCharFormat

class AIWorker(QThread):
    chunk_received = Signal(str)
    finished_signal = Signal()
    error_occurred = Signal(str)

    def __init__(self, api_key, model, prompt, context="", system_message=""):
        super().__init__()
        self.api_key = api_key
        self.model = model
        self.prompt = prompt
        self.context = context
        self.system_message = system_message

    def run(self):
        try:
            # Exemplo com API Groq
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # Combina contexto e mensagem do sistema (regras/personalidade)
            full_system_msg = self.context
            if self.system_message:
                full_system_msg += "\n\n" + self.system_message

            # Adiciona anexos ao contexto se houver
            # (A lógica de anexos é tratada antes de chamar o worker, passando no 'prompt' ou 'context')
            # Aqui assumimos que o 'prompt' ou 'context' já contém os dados necessários.

            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.context},
                    {"role": "user", "content": self.prompt}
                ],
                "stream": True
            }

            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60,
                stream=True
            )

            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        if self.isInterruptionRequested():
                            break
                            
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith("data: "):
                            if decoded_line.strip() == "data: [DONE]":
                                break
                            try:
                                json_data = json.loads(decoded_line[6:])
                                delta = json_data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    self.chunk_received.emit(content)
                            except:
                                pass
                self.finished_signal.emit()
            else:
                try:
                    error_msg = response.json().get("error", {}).get("message", response.text)
                except:
                    error_msg = response.text
                self.error_occurred.emit(f"Erro {response.status_code}: {error_msg}")

        except Exception as e:
            self.error_occurred.emit(f"Erro de conexão: {str(e)}")

class FileEditorDialog(QDialog):
    """Diálogo simples para editar arquivos de texto (regras/personalidade)."""
    def __init__(self, title, file_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 400)
        self.file_path = file_path
        
        layout = QVBoxLayout(self)
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        
        # Carrega conteúdo
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                self.editor.setPlainText(f.read())
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.save_and_close)
        btns.rejected.connect(self.reject)
        
        layout.addWidget(self.editor)
        layout.addWidget(btns)
        
    def save_and_close(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao salvar arquivo: {e}")

class AISettingsDialog(QDialog):
    """Diálogo de configurações do plugin."""
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Configurações da IA")
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        # API Key
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setText(self.api.get_config("groq_api_key", ""))
        form.addRow("API Key (Groq):", self.key_input)
        
        # Model Selector
        self.model_combo = QComboBox()
        models = ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma-7b-it"]
        self.model_combo.addItems(models)
        current_model = self.api.get_config("groq_model", "llama-3.3-70b-versatile")
        self.model_combo.setCurrentText(current_model)
        form.addRow("Modelo:", self.model_combo)
        
        layout.addLayout(form)
        
        # Botões de Arquivos
        btn_rules = QPushButton("Editar Regras")
        btn_rules.clicked.connect(lambda: self._open_file_editor("Regras", "regras.txt"))
        layout.addWidget(btn_rules)
        
        btn_persona = QPushButton("Editar Personalidade")
        btn_persona.clicked.connect(lambda: self._open_file_editor("Personalidade", "perssonalidade.txt"))
        layout.addWidget(btn_persona)
        
        layout.addStretch()
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save_settings)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def _open_file_editor(self, title, filename):
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(plugin_dir, filename)
        FileEditorDialog(title, path, self).exec()
        
    def _save_settings(self):
        self.api.update_config("groq_api_key", self.key_input.text().strip())
        self.api.update_config("groq_model", self.model_combo.currentText())
        self.accept()

class FileFilterProxy(QSortFilterProxyModel):
    """Filtra arquivos e pastas indesejados como .git."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ignored_names = {'.git', '__pycache__', '.vscode', '.idea', '.DS_Store'}

    def filterAcceptsRow(self, source_row, source_parent):
        source_index = self.sourceModel().index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False

        file_name = self.sourceModel().fileName(source_index)
        if file_name in self.ignored_names:
            return False

        return super().filterAcceptsRow(source_row, source_parent)

class ProjectFilesDialog(QDialog):
    """Diálogo para selecionar arquivos do projeto."""
    def __init__(self, root_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Anexar Arquivos do Projeto")
        self.resize(400, 500)
        self.setStyleSheet("""
            QDialog { background-color: #252526; color: #cccccc; }
            QTreeView { background-color: #1e1e1e; color: #cccccc; border: 1px solid #3e3e42; outline: none; }
            QTreeView::item { padding: 4px; }
            QTreeView::item:hover { background-color: #2a2d2e; }
            QTreeView::item:selected { background-color: #094771; color: white; }
            QPushButton { background-color: #0e639c; color: white; border: none; padding: 6px 12px; border-radius: 2px; }
            QPushButton:hover { background-color: #1177bb; }
            QPushButton[text="Cancel"] { background-color: #3c3c3c; }
        """)

        layout = QVBoxLayout(self)

        self.source_model = QFileSystemModel()
        self.source_model.setRootPath(root_path)
        self.source_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self.proxy_model = FileFilterProxy()
        self.proxy_model.setSourceModel(self.source_model)

        self.tree = QTreeView()
        self.tree.setModel(self.proxy_model)
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.source_model.index(root_path)))
        self.tree.setSelectionMode(QTreeView.SelectionMode.MultiSelection)
        self.tree.setColumnHidden(1, True)
        self.tree.setColumnHidden(2, True)
        self.tree.setColumnHidden(3, True)
        self.tree.setHeaderHidden(True)
        self.tree.setStyleSheet("border: 1px solid #3e3e42;")

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Anexar")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        layout.addWidget(self.tree)
        layout.addWidget(btns)

    def get_selected_files(self):
        proxy_indexes = self.tree.selectionModel().selectedIndexes()
        source_indexes = [self.proxy_model.mapToSource(idx) for idx in proxy_indexes]
        files = {self.source_model.filePath(index) for index in source_indexes if index.column() == 0 and not self.source_model.isDir(index)}
        return list(files)

class CodeDiffDialog(QDialog):
    def __init__(self, old_code, new_code, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Revisar Alterações")
        self.resize(1000, 700)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; border: 1px solid #333; }
            QLabel { color: #ccc; font-size: 12px; font-weight: bold; }
            QTextEdit { background-color: #1e1e1e; color: #d4d4d4; border: none; font-family: 'Consolas', 'Monospace'; font-size: 11px; }
            QPushButton { background-color: #3c3c3c; color: white; border: none; padding: 8px 16px; border-radius: 4px; font-weight: bold; }
            QPushButton:hover { background-color: #4c4c4c; }
            QPushButton#Accept { background-color: #2da44e; }
            QPushButton#Accept:hover { background-color: #2c974b; }
            QPushButton#Reject { background-color: #d73a49; }
            QPushButton#Reject:hover { background-color: #cb2431; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.addWidget(QLabel("Original"))
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Sugestão"))
        header.setStyleSheet("background-color: #252526; border-bottom: 1px solid #333; padding: 5px 10px;")
        layout.addWidget(header)

        splitter = QSplitter(Qt.Horizontal)
        self.left_view = QTextEdit()
        self.left_view.setReadOnly(True)
        self.left_view.setLineWrapMode(QTextEdit.NoWrap)

        self.right_view = QTextEdit()
        self.right_view.setReadOnly(True)
        self.right_view.setLineWrapMode(QTextEdit.NoWrap)

        splitter.addWidget(self.left_view)
        splitter.addWidget(self.right_view)
        layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(15, 15, 15, 15)
        btn_layout.addStretch()

        btn_reject = QPushButton("Rejeitar")
        btn_reject.setObjectName("Reject")
        btn_reject.clicked.connect(self.reject)

        btn_accept = QPushButton("Aceitar")
        btn_accept.setObjectName("Accept")
        btn_accept.clicked.connect(self.accept)

        btn_layout.addWidget(btn_reject)
        btn_layout.addWidget(btn_accept)
        layout.addLayout(btn_layout)

        self._populate_views(old_code, new_code)
        self._sync_scrollbars()

    def _populate_views(self, old_code, new_code):
        old_lines = old_code.splitlines()
        new_lines = new_code.splitlines()
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)

        fmt_add = QTextCharFormat(); fmt_add.setBackground(QColor("#233923"))
        fmt_remove = QTextCharFormat(); fmt_remove.setBackground(QColor("#402525"))

        left_cursor, right_cursor = self.left_view.textCursor(), self.right_view.textCursor()

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            old_chunk, new_chunk = old_lines[i1:i2], new_lines[j1:j2]
            max_len = max(len(old_chunk), len(new_chunk))

            for i in range(max_len):
                if i < len(old_chunk):
                    left_cursor.insertText(old_chunk[i] + '\n', fmt_remove if tag != 'insert' else QTextCharFormat())
                else:
                    self.left_view.append("")

                if i < len(new_chunk):
                    right_cursor.insertText(new_chunk[i] + '\n', fmt_add if tag != 'delete' else QTextCharFormat())
                else:
                    self.right_view.append("")

    def _sync_scrollbars(self):
        self.left_scroll = self.left_view.verticalScrollBar()
        self.right_scroll = self.right_view.verticalScrollBar()
        self.left_scroll.valueChanged.connect(lambda v: self.right_scroll.setValue(v))
        self.right_scroll.valueChanged.connect(lambda v: self.left_scroll.setValue(v))

class ChatHistoryManager:
    """Gerencia o armazenamento local dos chats."""
    def __init__(self):
        self.history_dir = os.path.join(os.path.expanduser("~"), ".jcode", "code_ia")
        os.makedirs(self.history_dir, exist_ok=True)
        self.history_file = os.path.join(self.history_dir, "chats.json")
        self.chats = self._load()

    def _load(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def save(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.chats, f, indent=2)

    def create_chat(self):
        chat = {"id": str(uuid.uuid4()), "title": "Novo Chat", "messages": [], "pinned": False}
        self.chats.insert(0, chat)
        self.save()
        return chat

    def delete_chat(self, chat_id):
        self.chats = [c for c in self.chats if c["id"] != chat_id]
        self.save()

    def toggle_pin(self, chat_id):
        for chat in self.chats:
            if chat["id"] == chat_id:
                chat["pinned"] = not chat.get("pinned", False)
                break
        self.save()

    def rename_chat(self, chat_id, new_title):
        for chat in self.chats:
            if chat["id"] == chat_id:
                chat["title"] = new_title
                break
        self.save()

class AIChatWidget(QWidget):
    def __init__(self, api, parent=None):
        super().__init__(parent)
        self.api = api
        self.api_key = self.api.get_config("groq_api_key", "") if self.api else ""
        self.model = self.api.get_config("groq_model", "llama-3.3-70b-versatile") if self.api else "llama-3.3-70b-versatile"
        self.history_manager = ChatHistoryManager()
        self.current_chat = None
        self.code_snippets = {} # Armazena snippets para aplicação posterior
        self.setup_ui()
        self.setAcceptDrops(True)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Header com Botão de Configuração
        header_layout = QHBoxLayout()
        title = QLabel("Assistente IA")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #cccccc;")
        
        self.btn_history = QToolButton()
        self.btn_history.setText("Histórico")
        self.btn_history.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_history.clicked.connect(self.toggle_history)
        
        self.btn_new_chat = QToolButton()
        self.btn_new_chat.setText("+")
        self.btn_new_chat.setToolTip("Novo Chat")
        self.btn_new_chat.clicked.connect(self.create_new_chat)
        
        self.btn_undo = QToolButton()
        self.btn_undo.setText("↩️")
        self.btn_undo.setToolTip("Desfazer última ação no editor")
        self.btn_undo.clicked.connect(self.api.undo)
        
        self.btn_clear = QToolButton()
        self.btn_clear.setText("🗑")
        self.btn_clear.setToolTip("Limpar Chat Atual")
        self.btn_clear.clicked.connect(self.clear_history)
        
        btn_settings = QToolButton()
        btn_settings.setText("⚙")
        btn_settings.setToolTip("Configurações")
        btn_settings.clicked.connect(self.show_settings)
        
        header_layout.addWidget(self.btn_history)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_undo)
        header_layout.addWidget(self.btn_clear)
        header_layout.addWidget(self.btn_new_chat)
        header_layout.addWidget(btn_settings)
        layout.addLayout(header_layout)

        # Área Central (Stack para Chat e Histórico)
        self.content_area = QWidget()
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.content_area)

        # Busca no Histórico
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Buscar no histórico...")
        self.history_search.setStyleSheet("background-color: #2d2d30; color: #cccccc; border: 1px solid #3e3e42; padding: 4px; border-radius: 4px; margin: 2px;")
        self.history_search.textChanged.connect(self.filter_history)
        self.history_search.hide()
        content_layout.addWidget(self.history_search)

        # Histórico (Overlay ou Lista)
        self.history_list = QListWidget()
        self.history_list.setStyleSheet("background-color: #252526; color: #cccccc; border: 1px solid #3e3e42;")
        self.history_list.itemClicked.connect(self.load_chat_from_item)
        self.history_list.hide()
        self.history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list.customContextMenuRequested.connect(self._show_history_context_menu)
        content_layout.addWidget(self.history_list)

        # Área de chat
        self.chat_area = QTextBrowser()
        self.chat_area.setReadOnly(True)
        self.chat_area.setOpenExternalLinks(False) # Controlamos os links manualmente
        self.chat_area.setFont(QFont("Consolas", 10))
        self.chat_area.anchorClicked.connect(self._on_link_clicked)
        content_layout.addWidget(self.chat_area)

        # Área de Anexos
        self.attachments_list = QListWidget()
        self.attachments_list.setMaximumHeight(80)
        self.attachments_list.setStyleSheet("background-color: #2d2d30; border: 1px solid #3e3e42; color: #cccccc; font-size: 11px; border-radius: 4px;")
        self.attachments_list.hide()
        layout.addWidget(self.attachments_list)
        self.attached_files = []

        # Campo de entrada
        input_layout = QVBoxLayout()

        input_row = QHBoxLayout()
        
        self.btn_attach = QToolButton()
        self.btn_attach.setText("📎")
        self.btn_attach.setToolTip("Anexar Arquivos")
        self.btn_attach.clicked.connect(self.attach_files)
        
        self.input_field = QLineEdit() 
        self.input_field.setPlaceholderText("Digite seu comando...")
        self.input_field.returnPressed.connect(self.send_message)
        
        input_row.addWidget(self.btn_attach)
        input_row.addWidget(self.input_field)
        
        input_layout.addLayout(input_row)

        # Botões de ação
        button_layout = QHBoxLayout()

        self.send_btn = QPushButton("Enviar")
        self.send_btn.clicked.connect(self.send_message)
        
        self.stop_btn = QPushButton("Parar")
        self.stop_btn.setStyleSheet("background-color: #d73a49; color: white;")
        self.stop_btn.clicked.connect(self.stop_generation)
        self.stop_btn.hide()
        
        button_layout.addWidget(self.send_btn)
        button_layout.addWidget(self.stop_btn)

        input_layout.addLayout(button_layout)
        layout.addLayout(input_layout)

        self.worker = None
        
        # Carrega último chat ou cria novo
        if self.history_manager.chats:
            self.load_chat(self.history_manager.chats[0])
        else:
            self.create_new_chat()

    def toggle_history(self):
        if self.history_list.isVisible():
            self.history_list.hide()
            self.history_search.hide()
            self.chat_area.show()
        else:
            self.refresh_history_list()
            self.chat_area.hide()
            self.history_search.show()
            self.history_list.show()
            self.history_search.setFocus()

    def refresh_history_list(self):
        self.history_list.clear()
        # Ordena: Fixados primeiro, depois pela ordem original (que é cronológica inversa)
        sorted_chats = sorted(self.history_manager.chats, key=lambda c: c.get("pinned", False), reverse=True)
        
        for chat in sorted_chats:
            title = chat["title"]
            if chat.get("pinned", False):
                title = "📌 " + title
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, chat)
            self.history_list.addItem(item)
            
    def filter_history(self, text):
        """Filtra o histórico com base no texto digitado."""
        text = text.lower()
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            chat = item.data(Qt.UserRole)
            # Busca no título e no conteúdo das mensagens
            match = text in chat["title"].lower()
            if not match:
                for msg in chat["messages"]:
                    if text in msg["content"].lower():
                        match = True
                        break
            item.setHidden(not match)

    def load_chat_from_item(self, item):
        chat = item.data(Qt.UserRole)
        self.load_chat(chat)
        self.toggle_history() # Volta para o chat

    def _show_history_context_menu(self, pos):
        item = self.history_list.itemAt(pos)
        if not item: return
        
        chat = item.data(Qt.UserRole)
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #252526; color: #cccccc; } QMenu::item:selected { background-color: #007acc; }")
        
        is_pinned = chat.get("pinned", False)
        action_pin = menu.addAction("Desafixar Chat" if is_pinned else "Fixar Chat")
        action_pin.triggered.connect(lambda: self._toggle_pin_chat_from_history(chat))
        
        action_rename = menu.addAction("Renomear Chat")
        action_rename.triggered.connect(lambda: self._rename_chat_from_history(chat))
        
        menu.addSeparator()
        action_delete = menu.addAction("Excluir Chat")
        action_delete.triggered.connect(lambda: self._delete_chat_from_history(chat))
        
        menu.exec(self.history_list.mapToGlobal(pos))

    def _delete_chat_from_history(self, chat):
        chat_id = chat["id"]
        self.history_manager.delete_chat(chat_id)
        self.refresh_history_list()
        
        # Se o chat deletado era o atual, carrega outro ou cria novo
        if self.current_chat and self.current_chat["id"] == chat_id:
            if self.history_manager.chats:
                self.load_chat(self.history_manager.chats[0])
            else:
                self.create_new_chat()

    def _toggle_pin_chat_from_history(self, chat):
        self.history_manager.toggle_pin(chat["id"])
        self.refresh_history_list()

    def _rename_chat_from_history(self, chat):
        new_title, ok = QInputDialog.getText(self, "Renomear Chat", "Novo título:", text=chat["title"])
        if ok and new_title:
            self.history_manager.rename_chat(chat["id"], new_title)
            self.refresh_history_list()
            if self.current_chat and self.current_chat["id"] == chat["id"]:
                self.current_chat["title"] = new_title

    def load_chat(self, chat):
        self.current_chat = chat
        self.chat_area.clear()
        self.code_snippets = {}
        
        for msg in chat["messages"]:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                self.chat_area.append(f"<b>Você:</b> {content}")
            else:
                # Re-formata para incluir botões de aplicar se houver código
                formatted = self.format_response(content)
                self.chat_area.append(f"<b>IA:</b> {formatted}")

    def create_new_chat(self):
        self.current_chat = self.history_manager.create_chat()
        self.load_chat(self.current_chat)

    def attach_files(self):
        root_path = self.api.get_project_root()
        if not root_path:
            # Fallback para diálogo padrão se não houver projeto aberto
            files, _ = QFileDialog.getOpenFileNames(self, "Anexar Arquivos")
            if files:
                self.attached_files.extend(files)
                self.update_attachments_label()
            return

        dlg = ProjectFilesDialog(root_path, self)
        if dlg.exec():
            files = dlg.get_selected_files()
            if files:
                self.attached_files.extend(files)
                self.update_attachments_label()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(url.toLocalFile())
        
        if files:
            self.attached_files.extend(files)
            self.update_attachments_label()
            event.acceptProposedAction()

    def update_attachments_label(self):
        self.attachments_list.clear()
        if not self.attached_files:
            self.attachments_list.hide()
            return
        
        self.attachments_list.show()
        for f in self.attached_files:
            item = QListWidgetItem(os.path.basename(f))
            item.setToolTip(f)
            self.attachments_list.addItem(item)

    def clear_history(self):
        self.chat_area.clear()
        if self.current_chat:
            self.current_chat["messages"] = []
            self.history_manager.save()

    def stop_generation(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.chat_area.append("<i>[Gerado interrompida pelo usuário]</i>")
            self.on_finished() # Força finalização da UI

    def send_message(self):
        message = self.input_field.text().strip()
        if not message:
            return
            
        # Recarrega configs (caso tenham mudado)
        self.api_key = self.api.get_config("groq_api_key", "")
        self.model = self.api.get_config("groq_model", "llama-3.3-70b-versatile")
            
        if not self.api_key:
            self.chat_area.append("<b>Sistema:</b> API Key não configurada. Por favor, configure a chave da API.")
            return

        # Adiciona mensagem do usuário ao chat
        self.chat_area.append(f"<b>Você:</b> {message}")
        if self.current_chat:
            self.current_chat["messages"].append({"role": "user", "content": message})
            # Atualiza título se for o primeiro
            if len(self.current_chat["messages"]) == 1:
                self.current_chat["title"] = message[:30] + "..."
            self.history_manager.save()
            
        self.input_field.clear()

        # Obtém contexto do editor
        context = self.api.get_full_text()
        
        # Processa anexos
        attachments_content = ""
        if self.attached_files:
            attachments_content = "\n\n--- Arquivos Anexados ---\n"
            for path in self.attached_files:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        attachments_content += f"\nArquivo: {os.path.basename(path)}\n```\n{f.read()}\n```\n"
                except Exception as e:
                    attachments_content += f"\nErro ao ler {os.path.basename(path)}: {e}\n"
            self.attached_files = [] # Limpa após envio
            self.update_attachments_label()

        # Carrega arquivos de sistema
        system_msg = self._load_system_files()
        
        # Instruções de Capacidades
        system_msg += "\n\n[SYSTEM: Capabilities]\n"
        system_msg += "Você é um especialista em edição de código cirúrgica. Ao editar código existente:\n"
        system_msg += "1. ANALISE o código fornecido no contexto.\n"
        system_msg += "2. IDENTIFIQUE as linhas exatas (classes, funções, variáveis) que precisam mudar.\n"
        system_msg += "3. USE o formato SEARCH/REPLACE para alterar APENAS o necessário. NÃO reescreva o arquivo todo a menos que solicitado.\n\n"
        system_msg += "Formato para Edição Parcial (Search & Replace):\n"
        system_msg += "<<<<<<< SEARCH\n"
        system_msg += "    # Copie aqui EXATAMENTE as linhas do código original que serão alteradas\n"
        system_msg += "    # Inclua indentação correta e contexto suficiente para ser único\n"
        system_msg += "=======\n"
        system_msg += "    # Seu novo código aqui\n"
        system_msg += ">>>>>>> REPLACE\n\n"
        system_msg += "Formato para Criar Arquivos ou Substituição Total:\n"
        system_msg += "# file: path/to/file.ext\n"
        system_msg += "conteudo completo do arquivo...\n"
        
        # Combina prompt com anexos
        full_prompt = message + attachments_content

        self.worker = AIWorker(self.api_key, self.model, full_prompt, context, system_msg)
        self.worker.chunk_received.connect(self.on_chunk)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.error_occurred.connect(self.on_error)
        
        # Prepara UI para streaming
        self.chat_area.append("<b>IA:</b> ")
        self.current_stream_text = ""
        
        self.send_btn.hide()
        self.stop_btn.show()
        self.worker.start()

    def _load_system_files(self):
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        content = ""
        
        # Regras
        rules_path = os.path.join(plugin_dir, "regras.txt")
        if os.path.exists(rules_path):
            with open(rules_path, 'r', encoding='utf-8') as f:
                content += "Regras:\n" + f.read() + "\n\n"
                
        # Personalidade
        persona_path = os.path.join(plugin_dir, "perssonalidade.txt")
        if os.path.exists(persona_path):
            with open(persona_path, 'r', encoding='utf-8') as f:
                content += "Personalidade:\n" + f.read()
                
        return content

    def on_chunk(self, text):
        """Recebe pedaços de texto e adiciona ao chat."""
        self.current_stream_text += text
        self.chat_area.moveCursor(QTextCursor.End)
        self.chat_area.insertPlainText(text)
        self.chat_area.verticalScrollBar().setValue(self.chat_area.verticalScrollBar().maximum())

    def on_finished(self):
        """Chamado quando o streaming termina para formatar o markdown."""
        self.stop_btn.hide()
        self.send_btn.show()
        
        # Salva resposta no histórico
        if self.current_chat and self.current_stream_text:
            self.current_chat["messages"].append({"role": "assistant", "content": self.current_stream_text})
            self.history_manager.save()

        # Substitui o texto bruto pelo formatado (com botões de aplicar)
        # Como QTextBrowser não facilita substituir o último bloco facilmente sem limpar tudo,
        # vamos apenas re-renderizar a última mensagem formatada.
        # Uma estratégia simples é limpar e recarregar o chat, mas isso pisca.
        # Vamos apenas adicionar a versão formatada e o usuário verá o texto "bruto" virar "bonito" se implementarmos replace.
        # Por simplicidade, vamos apenas processar os snippets para o dicionário e deixar o texto como está, 
        # mas o ideal é formatar. Vamos tentar formatar a última mensagem.
        
        # Hack: Remove o texto streamado (que é plain) e insere o HTML formatado
        cursor = self.chat_area.textCursor()
        cursor.movePosition(QTextCursor.End)
        # Seleciona para trás o comprimento do texto streamado
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, len(self.current_stream_text))
        cursor.removeSelectedText()
        
        formatted = self.format_response(self.current_stream_text)
        self.chat_area.append(formatted)
            
    def on_error(self, msg):
        self.stop_btn.hide()
        self.send_btn.show()
        self.chat_area.append(f"<br><b style='color:red'>Erro:</b> {msg}")

    def format_response(self, text):
        """Formata a resposta com syntax highlighting básico para blocos de código."""
        parts = re.split(r'(```\w*?\n.*?\n```)', text, flags=re.DOTALL)
        html_parts = []
        for part in parts:
            if part.startswith("```"):
                match = re.match(r'```(\w+)?\n(.*?)\n```', part, re.DOTALL)
                if match:
                    lang = match.group(1) or "text"
                    code = match.group(2)
                    highlighted = self.highlight_code(code, lang)
                    
                    # Gera ID para o snippet
                    snippet_id = str(uuid.uuid4())
                    self.code_snippets[snippet_id] = code.strip()
                    
                    # Botão/Link de Aplicar
                    apply_link = f"<br><a href='apply:{snippet_id}' style='color: #4caf50; text-decoration: none; font-weight: bold;'>[ ✔ Aplicar no Editor ]</a>"
                    
                    html_parts.append(f"<br><pre style='background-color: #2d2d2d; color: #cccccc; padding: 10px;'>{highlighted}</pre>{apply_link}<br>")
            else:
                # Texto normal: escape HTML e converte quebras de linha
                escaped = part.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                html_parts.append(escaped.replace("\n", "<br>"))
        return "".join(html_parts)

    def highlight_code(self, code, lang):
        """Aplica cores básicas a palavras-chave."""
        code = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if lang in ["python", "py"]:
            code = re.sub(r'(#.*)', r"<span style='color: #6a9955;'>\1</span>", code)
            code = re.sub(r'\b(def)\s+([a-zA-Z_][a-zA-Z0-9_]*)', r"<span style='color: #c586c0;'>\1</span> <span style='color: #dcdcaa;'>\2</span>", code)
            code = re.sub(r'\b(class)\s+([A-Z][a-zA-Z0-9_]*)', r"<span style='color: #c586c0;'>\1</span> <span style='color: #4ec9b0;'>\2</span>", code)
            code = re.sub(r'(@[a-zA-Z0-9_.]+)', r"<span style='color: #d7ba7d;'>\1</span>", code)
            keywords = ["import", "from", "return", "if", "else", "elif", "for", "while", "try", "except", "finally", "with", "as", "lambda", "pass", "break", "continue", "in", "is", "not", "and", "or", "yield", "async", "await"]
            for kw in keywords:
                code = re.sub(r'\b(' + kw + r')\b', r"<span style='color: #c586c0;'>\1</span>", code)
            builtins = ["True", "False", "None", "self", "super", "print", "len", "range", "str", "int", "list", "dict", "set", "open"]
            for bi in builtins:
                code = re.sub(r'\b(' + bi + r')\b', r"<span style='color: #569cd6;'>\1</span>", code)
            code = re.sub(r'(".*?")', r"<span style='color: #ce9178;'>\1</span>", code)
            code = re.sub(r"('.*?')", r"<span style='color: #ce9178;'>\1</span>", code)
            code = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()', r"<span style='color: #dcdcaa;'>\1</span>", code)
            code = re.sub(r'\b(\d+\.?\d*)\b', r"<span style='color: #b5cea8;'>\1</span>", code)
        elif lang in ["js", "javascript", "css", "html"]:
            code = re.sub(r'(//.*|/\*.*?\*/)', r"<span style='color: #6a9955;'>\1</span>", code)
            keywords = ["function", "const", "let", "var", "return", "if", "else", "for", "while", "class", "import", "export", "default", "async", "await", "new", "this", "switch", "case", "break", "continue"]
            for kw in keywords:
                code = re.sub(r'\b(' + kw + r')\b', r"<span style='color: #c586c0;'>\1</span>", code)
            builtins = ["true", "false", "null", "undefined", "console", "document", "window", "Math", "JSON", "Promise", "fetch"]
            for bi in builtins:
                code = re.sub(r'\b(' + bi + r')\b', r"<span style='color: #569cd6;'>\1</span>", code)
            code = re.sub(r'\b([A-Z][a-zA-Z0-9_]*)\b', r"<span style='color: #4ec9b0;'>\1</span>", code)
            code = re.sub(r'(".*?")', r"<span style='color: #ce9178;'>\1</span>", code)
            code = re.sub(r"('.*?')", r"<span style='color: #ce9178;'>\1</span>", code)
            code = re.sub(r"(`.*?`)", r"<span style='color: #ce9178;'>\1</span>", code)
            code = re.sub(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*(?=\()', r"<span style='color: #dcdcaa;'>\1</span>", code)
            code = re.sub(r'\b(\d+\.?\d*)\b', r"<span style='color: #b5cea8;'>\1</span>", code)

        return code

    def _on_link_clicked(self, url: QUrl):
        scheme = url.scheme()
        if scheme == 'apply':
            snippet_id = url.path()
            new_code = self.code_snippets.get(snippet_id)
            if new_code:
                self._process_apply_code(new_code)
        else:
            QDesktopServices.openUrl(url)
            
    def _process_apply_code(self, code):
        # 1. Detecta cabeçalho de arquivo: # file: path/to/file.ext
        file_path = None
        clean_code = code
        
        header_match = re.match(r'^[\s#/\*!-]*file:\s*([^\n]+)', code, re.IGNORECASE)
        if header_match:
            raw_path = header_match.group(1).strip().strip("'\"")
            root = self.api.get_project_root()
            if root:
                file_path = os.path.join(root, raw_path)
            else:
                file_path = raw_path
            clean_code = code[header_match.end():].lstrip()

        # 2. Verifica padrão Search/Replace
        if "<<<<<<< SEARCH" in clean_code and ">>>>>>> REPLACE" in clean_code:
            self._apply_patch(file_path, clean_code)
        elif file_path:
            self._apply_file_creation(file_path, clean_code)
        else:
            self._apply_to_active_editor(clean_code)

    def _apply_to_active_editor(self, new_code):
        old_code = ""
        try:
            editor = self.api.get_active_editor()
            if editor and editor.buffer:
                if any(editor.buffer.has_selection(i) for i in range(len(editor.buffer.cursors))):
                    old_code = editor.buffer.get_selected_text()
        except:
            pass

        dlg = CodeDiffDialog(old_code, new_code, self)
        if dlg.exec():
            self.api.insert_text(new_code)
            self.api.log("Código aplicado.")

    def _apply_file_creation(self, path, content):
        old_code = ""
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    old_code = f.read()
            except:
                pass
        
        dlg = CodeDiffDialog(old_code, content, self)
        dlg.setWindowTitle(f"Confirmar: {os.path.basename(path)}")
        
        if dlg.exec():
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.api.log(f"Arquivo salvo: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao salvar arquivo: {e}")

    def _apply_patch(self, file_path, patch_text):
        target_text = ""
        editor = None
        
        if file_path and os.path.exists(file_path):
             with open(file_path, 'r', encoding='utf-8') as f:
                target_text = f.read()
        else:
            editor = self.api.get_active_editor()
            if editor and editor.buffer:
                target_text = editor.buffer.get_text()
            else:
                QMessageBox.warning(self, "Erro", "Nenhum alvo encontrado para aplicar o patch.")
                return

        # Regex mais flexível com espaços e newlines
        pattern = r'<<<<<<< SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n>>>>>>> REPLACE'
        matches = re.findall(pattern, patch_text, re.DOTALL)
        
        if not matches:
            QMessageBox.warning(self, "Erro", "Formato de patch inválido.")
            return

        new_text = target_text
        for search_block, replace_block in matches:
            if search_block in new_text:
                # Se replace_block for vazio (apenas newline do regex), remove o bloco
                if not replace_block.strip() and replace_block.count('\n') <= 1:
                    replace_block = ""
                new_text = new_text.replace(search_block, replace_block, 1)
            else:
                QMessageBox.warning(self, "Erro", "Bloco de código original não encontrado.")
                return

        dlg = CodeDiffDialog(target_text, new_text, self)
        if dlg.exec():
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_text)
                self.api.log(f"Patch aplicado em {file_path}")
            elif editor:
                # Usa cursores atuais para manter posição se possível, ou reseta
                editor.buffer.replace_full_text(target_text, new_text, editor.buffer.cursors)
                editor.viewport().update()
                self.api.log("Patch aplicado no editor.")

    def show_settings(self):
        dlg = AISettingsDialog(self.api, self)
        dlg.exec()


# Função principal do plugin
def plugin_main(api):
    """Função chamada pelo ExtensionBridge para ativar o plugin."""

    # Cria o widget de chat
    chat_widget = AIChatWidget(api)

    # Adiciona ao menu de plugins
    api.add_menu_action("Assistente de IA", lambda: show_chat(api, chat_widget))

    # Registra atalho Ctrl+H (precisa ser adicionado ao InputMapper)
    api.log("Plugin AI Assistant ativado. Use Ctrl+H para abrir.")


def show_chat(api, widget):
    """Função para exibir o widget de chat."""
    # Esta função precisa ser integrada com a UI principal
    #api.show_widget(widget)
    widget.show()
    widget.raise_()
    widget.activateWindow()


if __name__ == '__main__':
     # Para testar o Widget
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = QWidget()
    layout = QVBoxLayout(window)
    chat_widget = AIChatWidget(None)  # EditorAPI não é necessário para testar
    layout.addWidget(chat_widget)
    window.show()
    sys.exit(app.exec())
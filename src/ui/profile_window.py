from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QHBoxLayout, QMessageBox, QFrame, QApplication, QListWidget, QListWidgetItem, QWidget, QProgressBar, QFileDialog, QComboBox, QMenu, QStyle, QCheckBox)
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QPixmap, QColor
from src.core.git_logic import GitLogic
import requests
import webbrowser


class RepoLoaderThread(QThread):
    loaded = Signal(list)
    def __init__(self, auth_logic):
        super().__init__()
        self.auth_logic = auth_logic
    def run(self):
        self.loaded.emit(self.auth_logic.get_user_repos())

class NewRepoDialog(QDialog):
    """Diálogo para criar um novo repositório."""
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Novo Repositório")
        self.resize(400, 250)
        
        bg = theme.get("background", "#252526")
        fg = theme.get("foreground", "#cccccc")
        input_bg = theme.get("sidebar_bg", "#3c3c3c")
        border = theme.get("border_color", "#454545")
        accent = theme.get("accent", "#007acc")
        
        self.setStyleSheet(f"background-color: {bg}; color: {fg};")
        
        layout = QVBoxLayout(self)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome do Repositório")
        self.name_input.setStyleSheet(f"background-color: {input_bg}; border: 1px solid {border}; padding: 6px; color: {fg}; border-radius: 4px;")
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Descrição (Opcional)")
        self.desc_input.setStyleSheet(f"background-color: {input_bg}; border: 1px solid {border}; padding: 6px; color: {fg}; border-radius: 4px;")
        
        self.chk_private = QCheckBox("Privado")
        self.chk_private.setStyleSheet(f"color: {fg}; spacing: 5px;")
        
        btn_create = QPushButton("Criar Repositório")
        btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_create.setStyleSheet(f"background-color: {accent}; color: white; padding: 8px; border: none; border-radius: 4px; font-weight: bold;")
        btn_create.clicked.connect(self.accept)
        
        layout.addWidget(QLabel("Nome:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Descrição:"))
        layout.addWidget(self.desc_input)
        layout.addWidget(self.chk_private)
        layout.addStretch()
        layout.addWidget(btn_create)
        
    def get_data(self):
        return self.name_input.text().strip(), self.desc_input.text().strip(), self.chk_private.isChecked()

class RepoItemWidget(QWidget):
    """Widget retangular para exibir informações do repositório."""
    def __init__(self, repo_data, theme, parent=None):
        super().__init__(parent)
        self.setObjectName("RepoItemWidget")
        
        main_bg = theme.get("background", "#252526")
        bg_color = QColor(main_bg).darker(110)
        bg = bg_color.name()
        hover_bg = bg_color.lighter(105).name()
        
        fg = theme.get("foreground", "#cccccc")
        accent = theme.get("accent", "#007acc")
        border = theme.get("border_color", "#454545")
        
        self.setStyleSheet(f"""
            #RepoItemWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
            #RepoItemWidget:hover {{
                background-color: {hover_bg};
                border: 1px solid {accent};
            }}
            QLabel {{
                background-color: transparent;
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Header (Nome + Ícone Privado)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        name_lbl = QLabel(repo_data.get("name", "Unknown"))
        name_lbl.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {accent};")
        header_layout.addWidget(name_lbl)

        if repo_data.get("private"):
            lock_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserSecure)
            lock_lbl = QLabel()
            lock_lbl.setPixmap(lock_icon.pixmap(12, 12))
            lock_lbl.setToolTip("Privado")
            header_layout.addWidget(lock_lbl)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        desc_text = repo_data.get("description") or "Sem descrição"
        if len(desc_text) > 60: desc_text = desc_text[:57] + "..."
        desc_lbl = QLabel(desc_text)
        desc_lbl.setStyleSheet(f"color: {fg}; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        
        layout.addWidget(desc_lbl)

class ProfileWindow(QDialog):
    """Janela para login e visualização de perfil do GitHub."""
    
    def __init__(self, auth_logic, theme_manager, parent=None):
        super().__init__(parent)
        self.auth_logic = auth_logic
        self.theme_manager = theme_manager
        self.theme = theme_manager.current_theme
        self.git_logic = GitLogic()
        self.repos = []
        
        self.setWindowTitle("Perfil GitHub")
        self.resize(600, 500)
        
        # Aplica cores do tema
        bg = self.theme.get("background", "#252526")
        fg = self.theme.get("foreground", "#cccccc")
        self.setStyleSheet(f"background-color: {bg}; color: {fg};")
        
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(20, 20, 20, 20)

        if self.auth_logic.is_logged_in():
            self._setup_logged_in_ui()
        else:
            self._setup_login_ui()

    def _setup_login_ui(self):
        fg = self.theme.get("foreground", "#cccccc")
        input_bg = self.theme.get("sidebar_bg", "#3c3c3c")
        border = self.theme.get("border_color", "#454545")
        
        lbl_title = QLabel("Login com GitHub")
        lbl_title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {fg}; margin-bottom: 10px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_title)

        lbl_info = QLabel("Insira seu Personal Access Token (PAT) para habilitar operações de Git (Push/Pull) sem senha.")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet(f"color: {fg}; margin-bottom: 10px; opacity: 0.8;")
        lbl_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_info)

        token_layout = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("ghp_...")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setStyleSheet(f"background-color: {input_bg}; border: 1px solid {border}; padding: 10px; color: {fg}; border-radius: 4px;")
        
        btn_paste = QPushButton("Colar")
        btn_paste.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_paste.setStyleSheet(f"background-color: {input_bg}; color: {fg}; padding: 10px; border: 1px solid {border}; border-radius: 4px;")
        btn_paste.clicked.connect(lambda: self.token_input.setText(QApplication.clipboard().text()))
        
        token_layout.addWidget(self.token_input)
        token_layout.addWidget(btn_paste)
        self.layout.addLayout(token_layout)

        btn_login = QPushButton("Entrar")
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.setStyleSheet("background-color: #2ea043; color: white; padding: 10px; border: none; border-radius: 4px; font-weight: bold; font-size: 14px;")
        btn_login.clicked.connect(self._handle_login)
        self.layout.addWidget(btn_login)
        
        self.layout.addStretch()

    def _setup_logged_in_ui(self):
        user_data = self.auth_logic.get_user_data()
        fg = self.theme.get("foreground", "#cccccc")
        sidebar_bg = self.theme.get("sidebar_bg", "#3c3c3c")
        border = self.theme.get("border_color", "#454545")
        
        # Avatar
        avatar_url = user_data.get("avatar_url")
        lbl_avatar = QLabel()
        lbl_avatar.setFixedSize(120, 120)
        lbl_avatar.setStyleSheet(f"border-radius: 60px; background-color: {sidebar_bg}; border: 2px solid {border};")
        lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if avatar_url:
            try:
                # Download simples da imagem para exibição
                data = requests.get(avatar_url, timeout=5).content
                pixmap = QPixmap()
                pixmap.loadFromData(data)
                lbl_avatar.setPixmap(pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            except:
                lbl_avatar.setText("Sem Imagem")
        
        # Container centralizado para avatar
        h_avatar = QHBoxLayout()
        h_avatar.addStretch()
        h_avatar.addWidget(lbl_avatar)
        h_avatar.addStretch()
        self.layout.addLayout(h_avatar)

        # Info
        name = user_data.get("name") or user_data.get("login")
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {fg}; margin-top: 10px;")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_name)

        lbl_login = QLabel(f"@{user_data.get('login')}")
        lbl_login.setStyleSheet(f"color: {fg}; font-size: 14px; opacity: 0.7;")
        lbl_login.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(lbl_login)

        # Repositórios
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.layout.addWidget(line)

        # Header Repositórios (Label + Sort)
        repo_header_layout = QHBoxLayout()
        
        lbl_repos = QLabel("Repositórios Recentes:")
        lbl_repos.setStyleSheet(f"font-weight: bold; color: {fg};")
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Atualização (Recente)", "Nome (A-Z)"])
        self.sort_combo.setStyleSheet(f"background-color: {sidebar_bg}; color: {fg}; border: 1px solid {border}; padding: 2px; min-width: 100px;")
        self.sort_combo.currentIndexChanged.connect(self._update_repo_list)
        
        btn_new_repo = QPushButton("+ Novo")
        btn_new_repo.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new_repo.setStyleSheet(f"background-color: {self.theme.get('accent', '#007acc')}; color: white; border: none; border-radius: 4px; padding: 4px 10px;")
        btn_new_repo.clicked.connect(self._show_new_repo_dialog)
        
        repo_header_layout.addWidget(lbl_repos)
        repo_header_layout.addStretch()
        repo_header_layout.addWidget(btn_new_repo)
        repo_header_layout.addWidget(QLabel("Ordenar:"))
        repo_header_layout.addWidget(self.sort_combo)
        
        self.layout.addLayout(repo_header_layout)

        # Filtro de Busca
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar repositórios...")
        self.search_input.setStyleSheet(f"background-color: {sidebar_bg}; border: 1px solid {border}; padding: 6px; color: {fg}; border-radius: 4px;")
        self.search_input.textChanged.connect(self._filter_repos)
        self.layout.addWidget(self.search_input)

        # Loading Indicator
        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0) # Indeterminate
        self.loading_bar.setStyleSheet(f"QProgressBar {{ border: none; background-color: {sidebar_bg}; height: 4px; }} QProgressBar::chunk {{ background-color: {self.theme.get('accent', '#007acc')}; }}")
        self.layout.addWidget(self.loading_bar)

        self.repo_list = QListWidget()
        self.repo_list.setSpacing(10)
        self.repo_list.setViewMode(QListWidget.IconMode)
        self.repo_list.setResizeMode(QListWidget.Adjust)
        self.repo_list.setMovement(QListWidget.Static)
        self.repo_list.setStyleSheet("background-color: transparent; border: none;")
        self.repo_list.itemDoubleClicked.connect(self._on_repo_double_clicked)
        self.repo_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.repo_list.customContextMenuRequested.connect(self._show_repo_context_menu)
        self.layout.addWidget(self.repo_list)
        
        self._load_repos()

        # Logout
        btn_logout = QPushButton("Sair")
        btn_logout.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_logout.setStyleSheet("background-color: #d73a49; color: white; padding: 8px 20px; border: none; border-radius: 4px; margin-top: 30px;")
        btn_logout.clicked.connect(self._handle_logout)
        
        h_btn = QHBoxLayout()
        h_btn.addStretch()
        h_btn.addWidget(btn_logout)
        h_btn.addStretch()
        self.layout.addLayout(h_btn)
        
        self.layout.addStretch()

    def _load_repos(self):
        self.repo_list.hide()
        self.loading_bar.show()
        
        self.loader_thread = RepoLoaderThread(self.auth_logic)
        self.loader_thread.loaded.connect(self._on_repos_loaded)
        self.loader_thread.start()

    def _on_repos_loaded(self, repos):
        self.loading_bar.hide()
        self.repo_list.show()
        self.repos = repos
        self._update_repo_list()

    def _update_repo_list(self):
        self.repo_list.clear()
        
        # Ordenação
        if self.sort_combo.currentIndex() == 0: # Atualização
            sorted_repos = sorted(self.repos, key=lambda r: r.get("updated_at", ""), reverse=True)
        else: # Nome
            sorted_repos = sorted(self.repos, key=lambda r: r.get("name", "").lower())
        
        # Calcula largura para 2 colunas (largura total / 2 - espaçamento)
        item_width = (self.repo_list.width() // 2) - 20
        if item_width < 200: item_width = 250

        for repo in sorted_repos:
            item = QListWidgetItem(self.repo_list)
            item.setData(Qt.UserRole, repo)
            widget = RepoItemWidget(repo, self.theme)
            item.setSizeHint(QSize(item_width, 100))
            self.repo_list.addItem(item)
            self.repo_list.setItemWidget(item, widget)
            
        # Re-aplica filtro se houver texto
        if self.search_input.text():
            self._filter_repos(self.search_input.text())

    def _filter_repos(self, text):
        text = text.lower()
        for i in range(self.repo_list.count()):
            item = self.repo_list.item(i)
            repo = item.data(Qt.UserRole)
            if repo:
                name = repo.get("name", "").lower()
                item.setHidden(text not in name)

    def _on_repo_double_clicked(self, item):
        repo = item.data(Qt.UserRole)
        if not repo: return
        
        clone_url = repo.get("clone_url")
        name = repo.get("name")
        
        dest_folder = QFileDialog.getExistingDirectory(self, f"Clonar {name} em...")
        if dest_folder:
            success, msg = self.git_logic.clone_repository(clone_url, dest_folder)
            if success:
                QMessageBox.information(self, "Sucesso", msg)
            else:
                QMessageBox.critical(self, "Erro", msg)

    def _show_repo_context_menu(self, pos):
        item = self.repo_list.itemAt(pos)
        if not item: return
        
        repo = item.data(Qt.UserRole)
        if not repo: return

        menu = QMenu(self)
        menu.setStyleSheet(f"QMenu {{ background-color: {self.theme.get('sidebar_bg')}; color: {self.theme.get('foreground')}; }} QMenu::item:selected {{ background-color: {self.theme.get('accent')}; }}")
        
        action_open = menu.addAction("Abrir no Navegador (GitHub)")
        action_open.triggered.connect(lambda: webbrowser.open(repo.get("html_url", "")))
        
        menu.exec(self.repo_list.mapToGlobal(pos))

    def _show_new_repo_dialog(self):
        dlg = NewRepoDialog(self.theme, self)
        if dlg.exec():
            name, desc, private = dlg.get_data()
            if name:
                success, msg = self.auth_logic.create_repository(name, desc, private)
                if success:
                    QMessageBox.information(self, "Sucesso", msg)
                    self._load_repos() # Recarrega a lista
                else:
                    QMessageBox.critical(self, "Erro", msg)

    def _handle_login(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Erro", "Por favor, insira um token.")
            return
            
        success, msg = self.auth_logic.login(token)
        if success:
            QMessageBox.information(self, "Sucesso", msg)
            self.close()
        else:
            QMessageBox.critical(self, "Erro", msg)

    def _handle_logout(self):
        self.auth_logic.logout()
        self.close()
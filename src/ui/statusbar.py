from PySide6.QtWidgets import QStatusBar, QLabel, QPushButton, QWidget, QHBoxLayout, QStyle, QMenu
from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QPixmap, QIcon
import os
import json

class ClickableLabel(QLabel):
    """Label que emite sinal ao ser clicado."""
    clicked = Signal()
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class StatusBar(QStatusBar):
    """Barra de status customizada."""

    live_server_toggle_requested = Signal(bool)
    avatar_clicked = Signal()

    WIDGET_DEFAULTS = {
        "avatar": True, "cursor_info": True, "indent": True,
        "encoding": True, "language": True, "live_server": True,
        "live_link": True, "notifications": True
    }

    def __init__(self, parent=None):
        self.theme = None
        super().__init__(parent)
        
        # Configuração de visibilidade
        self.config_dir = os.path.join(os.path.expanduser("~"), ".jcode")
        self.config_file = os.path.join(self.config_dir, "statusbar.json")
        self.widget_visibility = {}
        
        # Remove a alça de redimensionamento padrão para visual mais limpo
        self.setSizeGripEnabled(False)
        
        # Container para widgets da direita
        self.right_container = QWidget()
        self.right_layout = QHBoxLayout(self.right_container)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(10)
        
        # Widgets
        self.lbl_avatar = ClickableLabel()
        self.lbl_avatar.setFixedSize(20, 20)
        self.lbl_avatar.setStyleSheet("border-radius: 10px; background-color: #444;")
        self.lbl_avatar.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lbl_avatar.clicked.connect(self.avatar_clicked.emit)
        self.lbl_avatar.hide()

        self.lbl_cursor = self._create_label("Ln 1, Col 1", min_width=100)
        self.lbl_indent = self._create_label("Spaces: 4", min_width=80)
        self.lbl_encoding = self._create_label("UTF-8", min_width=60)
        
        # Botão de Linguagem (Interativo)
        self.btn_lang = QPushButton("Python")
        self.btn_lang.setFlat(True)
        self.btn_lang.setStyleSheet("color: white; border: none; padding: 0 5px; text-align: left;")
        self.btn_lang.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lang.setMinimumWidth(80)
        
        # Menu de Linguagens
        self.lang_menu = QMenu(self)
        self.lang_menu.setStyleSheet("QMenu { background-color: #252526; color: #cccccc; } QMenu::item:selected { background-color: #007acc; }")
        for lang in ["Python", "JavaScript", "HTML", "CSS", "C++", "Rust", "Plain Text"]:
            self.lang_menu.addAction(lang, lambda l=lang: self.update_lang(l))
        self.btn_lang.setMenu(self.lang_menu)
        
        self.btn_bell = QPushButton()
        self.btn_bell.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.btn_bell.setFlat(True)
        self.btn_bell.setFixedSize(20, 20)
        self.btn_bell.setStyleSheet("border: none;")
        self.btn_bell.setCursor(Qt.CursorShape.PointingHandCursor)

        # Botão do Live Server
        self.btn_live_server = QPushButton("Live Server")
        self.btn_live_server.setFlat(True)
        self.btn_live_server.setCheckable(True)
        self.btn_live_server.setStyleSheet("color: white; border: none; padding: 0 5px;")
        self.btn_live_server.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_live_server.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.btn_live_server.toggled.connect(self.live_server_toggle_requested.emit)

        # Link do Live Server
        self.lbl_live_link = QLabel("")
        self.lbl_live_link.setOpenExternalLinks(True)
        self.lbl_live_link.hide()

        # Adiciona ao layout
        self.right_layout.addWidget(self.lbl_avatar)
        self.right_layout.addWidget(self.lbl_cursor)
        self.right_layout.addWidget(self.lbl_indent)
        self.right_layout.addWidget(self.lbl_encoding)
        self.right_layout.addWidget(self.btn_lang)
        self.right_layout.addWidget(self.lbl_live_link)
        self.right_layout.addWidget(self.btn_live_server)
        self.right_layout.addWidget(self.btn_bell)

        self.addPermanentWidget(self.right_container)
        
        # Mapeamento de widgets para configuração
        self.widgets_map = {
            "avatar": self.lbl_avatar,
            "cursor_info": self.lbl_cursor,
            "indent": self.lbl_indent,
            "encoding": self.lbl_encoding,
            "language": self.btn_lang,
            "live_server": self.btn_live_server,
            "live_link": self.lbl_live_link,
            "notifications": self.btn_bell
        }
        
        # Carrega e aplica configurações de visibilidade
        self._load_visibility_config()
        self._apply_visibility()
        
        # Timer para restaurar estilo após flash
        self.flash_timer = QTimer(self)
        self.flash_timer.setSingleShot(True)
        self.flash_timer.timeout.connect(self._reset_style)
        
        self._default_style = "background-color: #333; color: white;"
        self.setStyleSheet(self._default_style)
        self.showMessage("Pronto")

    def _load_visibility_config(self):
        # Começa com uma cópia nova dos padrões
        config = self.WIDGET_DEFAULTS.copy()

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    # Garante que o arquivo não esteja vazio antes de tentar carregar
                    if os.path.getsize(self.config_file) > 0:
                        user_config = json.load(f)
                        if isinstance(user_config, dict):
                            config.update(user_config) # Sobrescreve padrões com as configs do usuário
            except (json.JSONDecodeError, IOError) as e:
                # Se o arquivo estiver corrompido ou ilegível, usa os padrões.
                print(f"Aviso: '{self.config_file}' corrompido. Usando padrões. Erro: {e}")
        
        self.widget_visibility = config

    def _save_visibility_config(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.widget_visibility, f, indent=4)
        except IOError as e:
            print(f"Erro ao salvar configuração da statusbar: {e}")

    def _apply_visibility(self):
        for name, widget in self.widgets_map.items():
            is_visible = self.widget_visibility.get(name, True)
            # O link do live server tem uma lógica especial
            if name == 'live_link':
                if self.btn_live_server.isChecked():
                    widget.setVisible(is_visible)
                else:
                    widget.setVisible(False)
            else:
                widget.setVisible(is_visible)

    def _create_label(self, text, min_width=0):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: white; padding: 0 5px;")
        if min_width > 0:
            lbl.setMinimumWidth(min_width)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    def update_cursor_info(self, line, col):
        self.lbl_cursor.setText(f"Ln {line+1}, Col {col+1}")

    def update_filename(self, filename: str):
        self.showMessage(filename)

    def _get_language_from_path(self, path: str) -> str:
        """Determina a linguagem de programação com base na extensão do arquivo."""
        ext_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.jsx': 'JavaScript (React)',
            '.ts': 'TypeScript',
            '.tsx': 'TypeScript (React)',
            '.html': 'HTML',
            '.htm': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.json': 'JSON',
            '.xml': 'XML',
            '.md': 'Markdown',
            '.c': 'C',
            '.cpp': 'C++',
            '.h': 'C/C++ Header',
            '.java': 'Java',
            '.rs': 'Rust',
        }
        _, ext = os.path.splitext(path)
        return ext_map.get(ext.lower(), "Plain Text")

    def update_language_display(self, file_path: str | None, is_code_editor: bool):
        """Atualiza o display de linguagem com base no editor e caminho."""
        if not is_code_editor:
            self.update_lang("") # Limpa para visualizadores
            return
        
        if file_path:
            lang = self._get_language_from_path(file_path)
            self.update_lang(lang)
        else:
            # É um CodeEditor, mas sem caminho (arquivo novo)
            self.update_lang("Plain Text")

    def _get_icon_for_lang(self, lang):
        """Retorna um ícone apropriado para a linguagem."""
        if not lang:
            return QIcon()
        
        # Mapeamento para ícones de tema do sistema (padrão Freedesktop)
        mime_map = {
            "Python": "text-x-python",
            "JavaScript": "text-javascript",
            "HTML": "text-html",
            "CSS": "text-css",
            "C++": "text-x-c++src",
            "Rust": "text-rust",
            "Java": "text-x-java",
            "Plain Text": "text-plain"
        }
        
        icon_name = mime_map.get(lang, "text-plain")
        icon = QIcon.fromTheme(icon_name)
        
        # Fallback para ícone genérico se o tema não tiver o ícone específico
        if icon.isNull():
            return self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        return icon

    def update_lang(self, lang):
        self.btn_lang.setText(lang)
        self.btn_lang.setIcon(self._get_icon_for_lang(lang))

    def set_live_server_state(self, running: bool, host: str = "", port: int = 0):
        """Atualiza a aparência do botão do live server."""
        self.btn_live_server.blockSignals(True)
        self.btn_live_server.setChecked(running)
        if running:
            self.btn_live_server.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.btn_live_server.setToolTip(f"Servidor rodando em http://{host}:{port}")
            
            url = f"http://{host}:{port}"
            self.lbl_live_link.setText(f"<a href='{url}' style='color: #4da6ff; text-decoration: none;'>{url}</a>")
            
            # Apenas mostra se a configuração permitir
            if self.widget_visibility.get("live_link", True):
                self.lbl_live_link.show()
        else:
            self.btn_live_server.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
            self.btn_live_server.setToolTip("Iniciar Live Server")
            self.lbl_live_link.hide()
        self.btn_live_server.blockSignals(False)

    def flash_message(self, text, color="#28a745", duration=2000):
        """Exibe uma mensagem com cor de fundo temporária (Feedback Visual)."""
        self.showMessage(text)
        self.setStyleSheet(f"background-color: {color}; color: white;")
        self.flash_timer.start(duration)

    def set_avatar(self, image_bytes):
        if image_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(image_bytes)
            scaled = pixmap.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.lbl_avatar.setPixmap(scaled)
            self.lbl_avatar.show()
        else:
            self.lbl_avatar.hide()

    def apply_theme(self, theme):
        """Aplica o tema visual à barra de status."""
        bg = theme.get("statusbar_bg")
        fg = theme.get("foreground")
        
        if bg and fg:
            style = f"""
            QStatusBar {{
                background-color: {bg};
                color: {fg};
                border: none;
            }}
            QStatusBar QLabel {{
                color: {fg};
                border: none;
            }}
            """
            self.setStyleSheet(style)
        self.theme = theme

    def _reset_style(self):
        if self.theme:
            self.apply_theme(self.theme)
        self.clearMessage()

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if self.theme:
            bg = self.theme.get("sidebar_bg", "#252526")
            fg = self.theme.get("foreground", "#cccccc")
            accent = self.theme.get("accent", "#007acc")
            menu.setStyleSheet(f"QMenu {{ background-color: {bg}; color: {fg}; }} QMenu::item:selected {{ background-color: {accent}; }}")

        menu.addSection("Exibir na Barra de Status")

        name_map = {
            "avatar": "Avatar do Perfil", "cursor_info": "Posição do Cursor",
            "indent": "Indentação", "encoding": "Codificação",
            "language": "Linguagem", "live_server": "Botão Live Server",
            "live_link": "Link do Live Server", "notifications": "Notificações"
        }

        for key, name in name_map.items():
            action = menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(self.widget_visibility.get(key, True))
            action.triggered.connect(lambda checked, k=key: self._toggle_widget_visibility(k, checked))

        menu.exec(event.globalPos())

    def _toggle_widget_visibility(self, key, visible):
        self.widget_visibility[key] = visible
        if key in self.widgets_map:
            self.widgets_map[key].setVisible(visible)
        self._save_visibility_config()
import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog, QInputDialog, QMessageBox, QMenu, QMenuBar
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTextCursor, QAction, QKeySequence, QCursor
from PySide6.QtCore import QDir
# Ajuste de Path para garantir que imports funcionem a partir da raiz
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.core.editor_logic.buffer import DocumentBuffer
from src.core.editor_logic.file_manager import FileManager
from src.core.ui_logic.extension_bridge import ExtensionBridge, EditorAPI
from src.core.editor_logic.clipboard_manager import ClipboardManager
from src.core.editor_logic.autocomplete_manager import AutocompleteManager
from src.core.editor_logic.search_manager import SearchManager
from src.core.syntax_highlighter import SyntaxHighlighter
from src.core.ui_logic.theme_manager import ThemeManager
from src.core.session_manager import SessionManager
from src.core.editor_logic.commands import CommandRegistry
from src.core.ui_logic.input_mapper import InputMapper
from src.core.ui_logic.event_handler import EventHandler
from src.core.ui_logic.viewport_controller import ViewportController
from src.core.search_panel import SearchPanel
from src.core.project_launcher import ProjectLauncher
from src.core.config_manager import ConfigManager
from src.ui.settings_dialog import SettingsDialog
from src.ui.editor import CodeEditor
from src.ui.sidebar import Sidebar
from src.ui.right_sidebar import RightSidebar
from src.ui.statusbar import StatusBar
from src.ui.editor_group import EditorGroup
from src.ui.command_palette import CommandPalette
from src.ui.video_player import VideoPlayer
from src.ui.pdf_viewer import PdfViewer
from src.ui.image_viewer import ImageViewer
from src.core.ui_logic.help_window import HelpWindow
from src.core.ui_logic.shortcuts import Shortcuts
from src.core.ui_logic.about_info import AboutInfo
from src.ui.about_window import AboutWindow
from src.ui.store_window import StoreWindow
from src.ui.theme_editor_dialog import ThemeEditorDialog
from src.serv_live.live_server_manager import LiveServerManager
from src.core.github_auth import GithubAuth
from src.ui.profile_window import ProfileWindow
from src.ui.custom_title_bar import CustomTitleBar
from src.core.ui_logic.font_manager import FontManager
from src.ui.batata_window import BatataWindow
from src.core.editor_logic.marker_manager import MarkerManager
from src.ui.tasmafile.tf_window import TasmaFileWindow

class JCodeMainWindow(QMainWindow):
    """Janela principal do editor JCODE.
    
    Responsável por orquestrar a inicialização dos subsistemas Core  e UI.
    """

    def __init__(self):
        super().__init__()
        
        # Gerenciamento de múltiplos documentos
        self.active_editor = None
        
        # --- 2. Inicialização dos Subsistemas de UI Logic ---
        self.config_manager = ConfigManager()
        self.highlighter = SyntaxHighlighter()
        self.search_manager = SearchManager()
        self.extension_bridge = ExtensionBridge()
        self.autocomplete_manager = AutocompleteManager()
        self.clipboard_manager = ClipboardManager(self)
        
        themes_path = os.path.join(root_dir, "themes")
        self.theme_manager = ThemeManager(themes_path)
        
        # Gerenciador de Fontes
        user_fonts_path = os.path.join(self.config_manager.config_dir, "fonts")
        self.font_manager = FontManager(user_fonts_path)
        
        self.command_registry = CommandRegistry()
        self.session_manager = SessionManager()
        self.input_mapper = InputMapper(self.command_registry)
        self.github_auth = GithubAuth(self.config_manager.config_dir)
        self.github_auth.auth_changed.connect(self._update_user_avatar)
        
        self.live_server_manager = LiveServerManager()
        self.event_handler = EventHandler(self.extension_bridge, None) # Buffer será definido dinamicamente
        self.viewport_controller = ViewportController()
        self.cache_dir = os.path.join(root_dir, "cache")
        
        # --- 3. Configuração da UI ---
        self.setWindowTitle("JCode - Modular Editor")
        self.resize(1024, 768)
        
        # Configuração da Barra de Título
        self.use_custom_title = self.config_manager.get("use_custom_title_bar") or False
        if self.use_custom_title:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        self._setup_ui()
        self._create_actions()
        self._setup_commands()
        self._register_core_commands()
        self._create_menu_bar()
        self._setup_logic_connections()
        
        # Conecta sinal de configuração
        self.config_manager.config_changed.connect(self._apply_config_globally)
        
        # Carrega tema e extensões
        # Aplica configurações iniciais (incluindo tema e sessão)
        self._apply_config_globally(self.config_manager.config)
        
        if self.config_manager.get("restore_session"):
            self._load_session()
        self._load_extensions()
        
        # Hook de inicialização
        self.extension_bridge.trigger_hook("on_app_start")
        self._update_user_avatar()

        self.autocomplete_timer = QTimer()
        self.autocomplete_timer.setSingleShot(True)
        self.autocomplete_timer.timeout.connect(self._perform_autocomplete)

    def closeEvent(self, event):
        """Salva a sessão ao fechar."""
        self._save_session()
        event.accept()

    def _setup_ui(self):
        """Configura os widgets da interface."""
        # Componentes principais
        self.sidebar = Sidebar()
        self.right_sidebar = RightSidebar()
        self.right_sidebar.set_auth_logic(self.github_auth) # Injeta lógica de auth
        self.editor_group = EditorGroup()
        
        self.custom_statusbar = StatusBar()
        self.setStatusBar(self.custom_statusbar)
        if self.use_custom_title:
            self.custom_statusbar.setSizeGripEnabled(True)
        
        self.command_palette = CommandPalette(self)
        
        # Layout de Conteúdo (Vertical: SearchPanel | EditorGroup)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.search_panel = SearchPanel(self)
        content_layout.addWidget(self.search_panel)
        content_layout.addWidget(self.editor_group)
        
        # Layout Principal (Horizontal: Sidebar | Conteúdo)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.sidebar)
        self.main_splitter.addWidget(content_widget)
        self.main_splitter.addWidget(self.right_sidebar)
        
        # Define proporção inicial (20% Sidebar, 80% Editor)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 4)
        self.main_splitter.setStretchFactor(2, 0) # Right sidebar começa oculta/pequena
        
        self.right_sidebar.hide() # Começa oculta
        
        if self.use_custom_title:
            # Container principal para suportar TitleBar customizada
            self.main_container = QWidget()
            self.main_layout = QVBoxLayout(self.main_container)
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(0)
            
            self.custom_title_bar = CustomTitleBar(self)
            self.custom_title_bar.settings_clicked.connect(self._show_settings_dialog)
            self.custom_title_bar.profile_clicked.connect(self._show_profile_window)
            self.main_layout.addWidget(self.custom_title_bar)
            
            self.menu_bar_instance = QMenuBar()
            self.main_layout.addWidget(self.menu_bar_instance)
            
            self.main_layout.addWidget(self.main_splitter)
            
            self.setCentralWidget(self.main_container)
        else:
            self.menu_bar_instance = self.menuBar()
            self.setCentralWidget(self.main_splitter)

    def _create_menu_bar(self):
        """Cria e popula a barra de menu global."""
        menu_bar = self.menu_bar_instance


        def _create_new_session():
            print("Criar nova sessão")

        # --- Menu Arquivo ---
        file_menu = menu_bar.addMenu("&Arquivo")
        file_menu.addAction(self.new_file_action)
        open_file_action = QAction("Abrir Arquivo...", self)
        open_file_action.setEnabled(False) # Placeholder
        file_menu.addAction(open_file_action)
        file_menu.addAction(self.open_project_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()


        exit_action = QAction("Sair", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(exit_action)

        # --- Menu Editar ---
        edit_menu = menu_bar.addMenu("&Editar")
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
        edit_menu.addAction(self.cut_action)
        edit_menu.addAction(self.copy_action)
        edit_menu.addAction(self.paste_action)

        # --- Menu Exibir ---
        view_menu = menu_bar.addMenu("&Exibir")
        view_menu.addAction(self.toggle_sidebar_action)
        view_menu.addAction(self.toggle_fullscreen_action)

        # --- Menu Sessões ---
        session_menu = menu_bar.addMenu("&Sessões")
        create_new_session_action = QAction("Criar nova sessão", self)
        create_new_session_action.triggered.connect(self._new_session)
        session_menu.addAction(create_new_session_action)
        save_session_action = QAction("Salvar Sessão Atual", self)
        save_session_action.triggered.connect(self._save_session)
        session_menu.addAction(self.switch_project_action)
        session_menu.addAction(save_session_action)
        
        # --- Menu Perfil ---
        profile_menu = menu_bar.addMenu("&Perfil")
        profile_action = QAction("Login / Perfil GitHub", self)
        profile_action.triggered.connect(self._show_profile_window)
        profile_menu.addAction(profile_action)

        # --- Outros Menus (Placeholders) ---

        tools_menu = menu_bar.addMenu("&Ferramentas")
        self.store_action = QAction("Store", self)
        self.store_action.triggered.connect(self._show_store_dialog)
        self.theme_editor_action = QAction("Editor de Temas", self)
        self.theme_editor_action.triggered.connect(self._show_theme_editor)
        tools_menu.addAction(self.theme_editor_action)
        tools_menu.addAction(self.store_action)
        help_menu = menu_bar.addMenu("&Ajuda")
        help_menu.addAction("Configurações", self._show_settings_dialog)
        help_menu.addSeparator()
        help_menu.addAction(self.show_help_action)
        help_menu.addAction(self.about_action)

        # --- Menu Plugins (Dinâmico) ---
        self.plugins_menu = menu_bar.addMenu("&Plugins")

    def _create_actions(self):
        """Cria todas as QActions globais para centralizar a lógica."""
        # --- File Actions ---
        self.new_file_action = QAction("Novo Arquivo", self) 
        self.new_file_action.setShortcut(Shortcuts.NEW_FILE)
        self.new_file_action.triggered.connect(self._create_new_file)

        self.open_project_action = QAction("Abrir Pasta de Projeto...", self)
        self.open_project_action.triggered.connect(self._open_project_dialog)

        self.save_action = QAction("Salvar", self)
        self.save_action.setShortcut(Shortcuts.SAVE_FILE)
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(lambda: self.command_registry.execute("file.save"))

        self.save_as_action = QAction("Salvar Como...", self)
        self.save_as_action.setShortcut(Shortcuts.SAVE_AS)
        self.save_as_action.triggered.connect(lambda: self.command_registry.execute("file.save_as"))
        
        self.close_tab_action = QAction("Fechar Aba", self)
        self.close_tab_action.setShortcut(Shortcuts.CLOSE_TAB)
        self.close_tab_action.triggered.connect(self._close_current_tab)

        # --- Edit Actions ---
        self.undo_action = QAction("Desfazer", self)
        self.undo_action.setShortcut(Shortcuts.UNDO)
        self.undo_action.triggered.connect(lambda: self.command_registry.execute("edit.undo"))

        self.redo_action = QAction("Refazer", self)
        self.redo_action.setShortcut(Shortcuts.REDO)
        self.redo_action.triggered.connect(lambda: self.command_registry.execute("edit.redo"))

        self.cut_action = QAction("Recortar", self)
        self.cut_action.setShortcut(Shortcuts.CUT)
        self.cut_action.triggered.connect(lambda: self.command_registry.execute("edit.cut"))

        self.copy_action = QAction("Copiar", self)
        self.copy_action.setShortcut(Shortcuts.COPY)
        self.copy_action.triggered.connect(lambda: self.command_registry.execute("edit.copy"))

        self.paste_action = QAction("Colar", self)
        self.paste_action.setShortcut(Shortcuts.PASTE)
        self.paste_action.triggered.connect(lambda: self.command_registry.execute("edit.paste"))

        self.find_action = QAction("Localizar", self)
        self.find_action.setShortcut(Shortcuts.FIND)
        self.find_action.triggered.connect(self._show_search_panel)

        self.rename_action = QAction("Renomear Variável", self)
        self.rename_action.setShortcut(Shortcuts.RENAME)
        self.rename_action.triggered.connect(self._quick_rename)

        self.switch_project_action = QAction("Alternar Projeto...", self)
        self.switch_project_action.setShortcut(Shortcuts.SWITCH_PROJECT)
        self.switch_project_action.triggered.connect(self._show_project_launcher)

        # --- View Actions ---
        self.toggle_sidebar_action = QAction("Alternar Barra Lateral", self)
        self.toggle_sidebar_action.setShortcut(Shortcuts.TOGGLE_SIDEBAR)
        self.toggle_sidebar_action.triggered.connect(self._toggle_sidebar)

        self.toggle_right_sidebar_action = QAction("Alternar Barra Direita (Git)", self)
        self.toggle_right_sidebar_action.setShortcut(Shortcuts.TOGGLE_RIGHT_SIDEBAR)
        self.toggle_right_sidebar_action.triggered.connect(self._toggle_right_sidebar)

        self.focus_sidebar_search_action = QAction("Focar Busca na Sidebar", self)
        self.focus_sidebar_search_action.setShortcut(Shortcuts.FOCUS_SIDEBAR_SEARCH)
        self.focus_sidebar_search_action.triggered.connect(self._focus_sidebar_search)

        self.toggle_fullscreen_action = QAction("Tela Cheia", self)
        self.toggle_fullscreen_action.setCheckable(True)
        self.toggle_fullscreen_action.triggered.connect(lambda checked: self.showFullScreen() if checked else self.showNormal())
        
        self.refresh_explorer_action = QAction("Atualizar Explorer", self)
        self.refresh_explorer_action.setShortcut(Shortcuts.REFRESH_EXPLORER)
        self.refresh_explorer_action.triggered.connect(self._refresh_explorer)
        
        self.next_tab_action = QAction("Próxima Aba", self)
        self.next_tab_action.setShortcut(Shortcuts.NEXT_TAB)
        self.next_tab_action.triggered.connect(self._next_tab)
        
        self.prev_tab_action = QAction("Aba Anterior", self)
        self.prev_tab_action.setShortcut(Shortcuts.PREV_TAB)
        self.prev_tab_action.triggered.connect(self._prev_tab)

        # --- Zoom Actions ---
        self.zoom_in_action = QAction("Aumentar Zoom", self)
        self.zoom_in_action.setShortcut(Shortcuts.ZOOM_IN)
        self.zoom_in_action.triggered.connect(self._zoom_in)

        self.zoom_out_action = QAction("Diminuir Zoom", self)
        self.zoom_out_action.setShortcut(Shortcuts.ZOOM_OUT)
        self.zoom_out_action.triggered.connect(self._zoom_out)

        # --- Batata Action ---
        self.show_batata_action = QAction("Mostrar Batata", self)
        self.show_batata_action.setShortcut(Shortcuts.BATATA)
        self.show_batata_action.triggered.connect(self._show_batata_window)

        # --- Diagram Action ---
        self.diagram_action = QAction("Abrir Gerador de Diagramas", self)
        self.diagram_action.setShortcut("F6")
        self.diagram_action.triggered.connect(self._show_diagram_window)

        # --- Help Actions ---
        self.show_help_action = QAction("Guia de Atalhos", self)
        self.show_help_action.setShortcut(Shortcuts.HELP)
        self.show_help_action.triggered.connect(self._show_help_window)

        self.about_action = QAction("Sobre o JCode", self)
        self.about_action.triggered.connect(self._show_about_dialog)

        # Adiciona ações à janela para que os atalhos sejam globais
        self.addActions([
            self.new_file_action, self.save_action, self.undo_action, self.redo_action,
            self.cut_action, self.copy_action, self.paste_action, self.find_action, self.rename_action, self.switch_project_action,
            self.toggle_sidebar_action, self.toggle_right_sidebar_action, self.focus_sidebar_search_action, self.show_help_action, self.close_tab_action, self.refresh_explorer_action, self.next_tab_action, self.prev_tab_action,
            self.zoom_in_action, self.zoom_out_action,
            self.show_batata_action,
            self.diagram_action
        ])

    def _register_core_commands(self):
        """Registra os comandos fundamentais do editor."""
        def get_active_buffer_and_execute(func_name, *args, **kwargs):
            """Wrapper para executar um comando no buffer ativo."""
            if self.active_editor and self.active_editor.buffer:
                buffer = self.active_editor.buffer
                func = getattr(buffer, func_name)
                func(*args, **kwargs)
                self._on_buffer_modified()

        r = self.command_registry
        
        # Comandos de Edição
        r.register("type_char", self._handle_type_char)
        r.register("edit.insert_pair", lambda p: get_active_buffer_and_execute("insert_paired_text", p))
        r.register("edit.backspace", lambda: get_active_buffer_and_execute("delete_backspace"))
        r.register("edit.new_line", lambda: get_active_buffer_and_execute("insert_text", "\n"))
        r.register("edit.indent", lambda: get_active_buffer_and_execute("insert_text", "    "))
        
        # Comandos de Cursor
        r.register("cursor.move_up", lambda: get_active_buffer_and_execute("move_cursors", -1, 0))
        r.register("cursor.move_down", lambda: get_active_buffer_and_execute("move_cursors", 1, 0))
        r.register("cursor.move_left", lambda: get_active_buffer_and_execute("move_cursors", 0, -1))
        r.register("cursor.move_right", lambda: get_active_buffer_and_execute("move_cursors", 0, 1))
        r.register("cursor.select_up", lambda: get_active_buffer_and_execute("move_cursors", -1, 0, True))
        r.register("cursor.select_down", lambda: get_active_buffer_and_execute("move_cursors", 1, 0, True))
        r.register("cursor.select_left", lambda: get_active_buffer_and_execute("move_cursors", 0, -1, True))
        r.register("cursor.select_right", lambda: get_active_buffer_and_execute("move_cursors", 0, 1, True))
        r.register("cursor.add_up", lambda: get_active_buffer_and_execute("add_cursor_relative", -1))
        r.register("cursor.add_down", lambda: get_active_buffer_and_execute("add_cursor_relative", 1))
        
        # Comandos de Marcadores
        r.register("editor.next_marker", lambda: self.active_editor.go_to_next_marker() if self.active_editor else None)
        r.register("editor.prev_marker", lambda: self.active_editor.go_to_prev_marker() if self.active_editor else None)
        
        # Comandos de Histórico
        def safe_undo():
            if self.active_editor and self.active_editor.buffer and self.active_editor.buffer.can_undo:
                get_active_buffer_and_execute("undo")
        
        def safe_redo():
            if self.active_editor and self.active_editor.buffer and self.active_editor.buffer.can_redo:
                get_active_buffer_and_execute("redo")

        r.register("edit.undo", safe_undo)
        r.register("edit.redo", safe_redo)

        # Comandos de Área de Transferência
        r.register("edit.cut", self._cut_selection)
        r.register("edit.copy", self._copy_selection)
        r.register("edit.paste", self._paste_from_clipboard)
        
        r.register("view.command_palette", self.command_palette.show_palette)
        r.register("view.find", self._show_search_panel)
        r.register("view.switch_project", self._show_project_launcher)
        r.register("edit.rename", self._quick_rename)
        r.register("view.toggle_ai_chat", self._toggle_ai_chat)
        r.register("file.save", self._save_file)
        r.register("file.save_as", self._save_file_as)

    def _handle_type_char(self, text):
        """Trata a digitação de caracteres, incluindo lógica de auto-close tag."""
        if not self.active_editor or not self.active_editor.buffer: return
        
        buffer = self.active_editor.buffer
        buffer.insert_text(text)
        self._on_buffer_modified()
        
        # Lógica de Fechamento Automático de Tags HTML
        if text == ">":
            self._check_auto_close_tag(buffer)

    def _check_auto_close_tag(self, buffer):
        """Verifica e insere tag de fechamento HTML se necessário."""
        file_path = self.active_editor.property("file_path")
        if not file_path: return
        
        # Verifica extensões relevantes
        valid_exts = ('.html', '.htm', '.xml', '.js', '.jsx', '.ts', '.tsx', '.vue', '.php')
        if not file_path.lower().endswith(valid_exts):
            return

        cursor = buffer.cursors[-1]
        line_content = buffer.get_lines(cursor.line, cursor.line + 1)[0]
        before_cursor = line_content[:cursor.col]
        
        # Encontra a última abertura de tag '<'
        open_bracket_index = before_cursor.rfind('<')
        if open_bracket_index == -1: return
        
        # Extrai conteúdo da tag (ex: "div class='foo'")
        tag_content = before_cursor[open_bracket_index+1:-1] # Remove o '>' final
        
        parts = tag_content.split()
        if not parts: return
        tag_name = parts[0]
        
        # Ignora tags de fechamento (/div) ou self-closing (br, img, etc)
        if tag_name.startswith('/') or tag_content.endswith('/'): return
        
        void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr", "!doctype"}
        if tag_name.lower() in void_tags: return
        
        # Insere fechamento e move cursor para o meio
        closing_tag = f"</{tag_name}>"
        buffer.insert_text(closing_tag)
        buffer.move_cursors(0, -len(closing_tag)) # Volta o cursor para entre as tags
        self._on_buffer_modified()

    def _new_session(self):
        """Cria uma nova sessão, fechando todos os arquivos e limpando o projeto."""
        if self._close_all_files():
            # Limpa o projeto atual
            self.sidebar.set_root_path(QDir.homePath())
            self._open_project_dialog()
            self.setWindowTitle("JCode - Nova Sessão")

            # Limpa a sessão
            self.session_manager.save_session(None, [], None)
            self.custom_statusbar.showMessage("Nova sessão iniciada.", 3000)
        else:
            # Cancelado pelo usuário
            self.custom_statusbar.showMessage("Ação de nova sessão cancelada.", 3000)

    def _setup_commands(self):
        """Registra comandos e atalhos."""
        # Atalho para Paleta de Comandos
        action = QAction("Command Palette", self)
        action.setShortcut(Shortcuts.COMMAND_PALETTE)
        action.triggered.connect(self.command_palette.show_palette)
        self.addAction(action)
        
        self._register_palette_commands()

    def _register_palette_commands(self):
        """Registra todos os comandos disponíveis na paleta de comandos."""
        # Registra comandos básicos
        self.command_palette.register_command("Exibir: Alternar Barra Lateral", self.toggle_sidebar_action.trigger)
        self.command_palette.register_command("Exibir: Alternar Barra Direita (Git)", self.toggle_right_sidebar_action.trigger)
        self.command_palette.register_command("Exibir: Focar Busca na Sidebar", self._focus_sidebar_search)
        self.command_palette.register_command("Arquivo: Salvar", self._save_file)
        self.command_palette.register_command("File: New File", self._create_new_file)
        self.command_palette.register_command("File: New Folder", self._create_new_folder)
        self.command_palette.register_command("File: Open Folder", self._open_project_dialog)
        self.command_palette.register_command("Preferences: Settings", self._show_settings_dialog)
        
        # Registra as configurações para busca global
        setting_descriptions = {
            "font_size": "Tamanho da Fonte",
            "line_numbers": "Exibir Números de Linha",
            "auto_indent": "Auto-indentação",
            "theme": "Tema Visual",
            "restore_session": "Restaurar Sessão Anterior",
            "server_address": "Endereço do Servidor Local",
            "live_server_port": "Porta do Live Server",
            "live_server_open_browser": "Abrir Navegador (Live Server)",
            "enable_autocomplete": "Habilitar Autocomplete (Beta)",
            "autocomplete_delay": "Atraso do Autocomplete"
        }

        for key, desc in setting_descriptions.items():
            command_name = f"Config: {desc}"
            current_value = self.config_manager.get(key)
            tags = [key, str(current_value)]
            self.command_palette.register_command(command_name, self._show_settings_dialog, search_tags=tags)

    def _setup_logic_connections(self):
        """Conecta a lógica de UI aos widgets."""
        # Instala o filtro de eventos no editor
        # self.event_handler.install_on(self.editor_group) # O filtro agora é por editor
        
        # Conecta o controlador de viewport ao editor
        # self.viewport_controller.attach_to(self.editor) # Será conectado por aba
        
        # Exemplo de conexão de sinal: Atualizar statusbar ao scrollar
        self.viewport_controller.visible_lines_changed.connect(
            lambda first, last: self.custom_statusbar.showMessage(f"Linhas visíveis: {first} - {last}")
        )
        
        # CONEXÃO BIDIRECIONAL:
        # Conecta o sinal de modificação do buffer a um slot que atualiza a UI
        # self.event_handler.buffer_modified.connect(self._on_buffer_modified) # Não mais global
        
        # Conexões da Sidebar
        self.sidebar.open_folder_clicked.connect(self._open_project_dialog)
        self.sidebar.open_project_clicked.connect(self._open_project_dialog)
        self.sidebar.file_clicked.connect(self._open_file)
        self.sidebar.file_created.connect(self._open_file)
        self.sidebar.status_message.connect(self.custom_statusbar.showMessage)
        self.sidebar.marker_clicked.connect(self._on_sidebar_marker_clicked)

        # Conexão do EditorGroup
        self.editor_group.active_editor_changed.connect(self._on_active_editor_changed)

        # Conexões do Painel de Busca
        self.search_panel.closed.connect(self._hide_search_panel)
        self.search_panel.find_next.connect(self._on_find)
        self.search_panel.replace_one.connect(self._on_replace_one)
        self.search_panel.replace_all.connect(self._on_replace_all)

        # Conexões do Live Server
        self.custom_statusbar.live_server_toggle_requested.connect(self._on_live_server_toggle)
        self.live_server_manager.server_started.connect(self._on_live_server_started)
        self.live_server_manager.server_stopped.connect(self._on_live_server_stopped)
        self.live_server_manager.error.connect(lambda msg: self.custom_statusbar.flash_message(msg, color="#dc3545"))
        self.custom_statusbar.avatar_clicked.connect(self._on_avatar_clicked)

    def _on_active_editor_changed(self, editor_widget):
        """Chamado quando a aba ativa muda."""
        # Desconecta sinais do editor anterior se necessário (opcional, mas boa prática)
        if self.active_editor and isinstance(self.active_editor, CodeEditor):
            try:
                self.active_editor.markers_changed.disconnect(self._update_sidebar_markers)
            except:
                pass

        self.active_editor = editor_widget
        if editor_widget:
            self.event_handler.buffer = editor_widget.buffer
            self.viewport_controller.attach_to(editor_widget)
            
            # Conecta sinais do novo editor
            if isinstance(editor_widget, CodeEditor):
                editor_widget.markers_changed.connect(self._update_sidebar_markers)
                self._update_sidebar_markers() # Atualiza inicial
        else:
            self.event_handler.buffer = None
            self.sidebar.update_markers([]) # Limpa marcadores
            
        self._on_buffer_modified()
        # Limpa os highlights de busca ao trocar de aba
        self._hide_search_panel()
        if self.active_editor and hasattr(self.active_editor, 'autocomplete_widget'):
            self.active_editor.autocomplete_widget.hide()

    def _update_sidebar_markers(self):
        """Atualiza a sidebar com os marcadores globais do projeto."""
        # Garante que os marcadores atuais foram salvos no cache antes de ler
        if self.active_editor and isinstance(self.active_editor, CodeEditor):
             self.active_editor._save_markers()
             
        markers = MarkerManager.get_global_markers(self.cache_dir)
        self.sidebar.update_markers(markers)

    def _on_sidebar_marker_clicked(self, file_path, line):
        """Navega para a linha do marcador clicado na sidebar."""
        self._open_file(file_path)
        
        if self.active_editor and isinstance(self.active_editor, CodeEditor):
            if self.active_editor.property("file_path") == file_path:
                self.active_editor.buffer.update_last_cursor(line, 0)
                self.active_editor._ensure_cursor_visible()
                self.active_editor.viewport().update()

    def _check_autocomplete_trigger(self):
        """Verifica se o autocomplete deve ser acionado."""
        editor = self.sender()
        if not editor or editor is not self.active_editor:
            return

        if not getattr(editor, "autocomplete_enabled", False):
            return

        delay = self.config_manager.get("autocomplete_delay")
        self.autocomplete_timer.start(delay)

    def _perform_autocomplete(self):
        editor = self.active_editor
        if not editor:
            return

        if not editor.buffer or not editor.autocomplete_manager:
            return

        buffer = editor.buffer
        cursor = buffer.cursors[-1]

        if cursor.col == 0:
            editor.autocomplete_widget.hide()
            return

        line_text = buffer.get_lines(cursor.line, cursor.line + 1)[0]
        if cursor.col > len(line_text):
            return

        char = line_text[cursor.col - 1]
        if editor.autocomplete_manager.should_trigger(char):
            file_path = editor.property("file_path") or ""
            suggestions = editor.autocomplete_manager.get_suggestions(buffer, cursor.line, cursor.col, file_path)
            if suggestions:
                editor.show_autocomplete(suggestions)
            else:
                editor.autocomplete_widget.hide()

    def _hide_autocomplete(self):
        if self.active_editor and hasattr(self.active_editor, 'autocomplete_widget'):
            self.active_editor.autocomplete_widget.hide()

    def _on_avatar_clicked(self):
        """Mostra menu de opções ao clicar no avatar."""
        menu = QMenu(self)
        menu.addAction("Ver Perfil", self._show_profile_window)
        menu.addAction("Sair (Logout)", self.github_auth.logout)
        menu.exec(QCursor.pos())

    def _apply_theme_to_dialog(self, dialog):
        """Aplica o tema atual a um diálogo injetando stylesheet."""
        if not self.theme_manager or not self.theme_manager.current_theme:
            return
            
        theme = self.theme_manager.current_theme
        bg = theme.get("background", "#252526")
        fg = theme.get("foreground", "#cccccc")
        border = theme.get("border_color", "#3e3e42")
        sidebar_bg = theme.get("sidebar_bg", "#252526")
        accent = theme.get("accent", "#007acc")
        
        # Estilo genérico para dialogs que cobre a maioria dos widgets padrão
        style = f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QWidget {{
                color: {fg};
            }}
            QLabel {{
                color: {fg};
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {sidebar_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {border};
            }}
            QPushButton:pressed {{
                background-color: {accent};
                color: white;
            }}
            QLineEdit, QTextEdit, QPlainTextEdit, QScrollArea {{
                background-color: {sidebar_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QListWidget, QTableWidget, QTreeWidget {{
                background-color: {sidebar_bg};
                color: {fg};
                border: 1px solid {border};
            }}
            QTabWidget::pane {{
                border: 1px solid {border};
            }}
            QTabBar::tab {{
                background: {sidebar_bg};
                color: {fg};
                padding: 5px 10px;
                border: 1px solid {border};
            }}
            QTabBar::tab:selected {{
                background: {bg};
            }}
        """
        dialog.setStyleSheet(style)

    def _show_settings_dialog(self):
        dlg = SettingsDialog(self.config_manager, self.theme_manager, self.font_manager, self)
        self._apply_theme_to_dialog(dlg)
        dlg.exec()

    def _apply_config_globally(self, config):
        """Aplica as configurações em toda a aplicação."""
        # 1. Tema
        theme_name = config.get("theme", "dark_default")
        print(f"[Config] Loading theme: {theme_name}")
        self.theme_manager.load_theme(theme_name)
        self.theme_manager.apply_theme(QApplication.instance())
        
        # 2. Fonte Global da UI (afetada pelo zoom)
        # O tamanho da fonte do editor é usado como base para o zoom global.
        font_size = config.get("font_size", 12)
        app_font = QApplication.instance().font()
        # Ajusta o tamanho da fonte padrão da aplicação. Widgets específicos podem sobrescrever.
        app_font.setPointSize(font_size)
        QApplication.instance().setFont(app_font)
        
        self.custom_statusbar.apply_theme(self.theme_manager.current_theme)
        self.right_sidebar.apply_theme(self.theme_manager.current_theme)
        
        if hasattr(self, 'custom_title_bar'):
            self.custom_title_bar.apply_theme(self.theme_manager.current_theme)
            
        # 3. Editor (Propaga para todas as abas)
        for i in range(self.editor_group.tab_widget.count()):
            editor = self.editor_group.tab_widget.widget(i)
            if isinstance(editor, CodeEditor):
                editor.update_settings(config)

    def _toggle_ai_chat(self):
        """Abre/fecha o painel de chat IA."""
        if not hasattr(self, 'ai_chat_widget'):
            # Cria o widget na primeira chamada
            from plugins.code_ia.ai_assistant import AIChatWidget
            # Aqui, _create_editor_api é chamado SEM argumentos
            self.ai_chat_widget = AIChatWidget(self._create_editor_api())

            # Adiciona ao layout principal (como uma nova sidebar)
            self.ai_splitter = QSplitter(Qt.Orientation.Horizontal)
            self.ai_splitter.addWidget(self.main_splitter)
            self.ai_splitter.addWidget(self.ai_chat_widget)
            self.ai_splitter.setStretchFactor(0, 4)
            self.ai_splitter.setStretchFactor(1, 1)
            
            if self.use_custom_title:
                self.main_layout.addWidget(self.ai_splitter)
            else:
                self.setCentralWidget(self.ai_splitter)

            # Começa oculto
            self.ai_chat_widget.hide()

        # Alterna visibilidade
        self.ai_chat_widget.setVisible(not self.ai_chat_widget.isVisible())
        if self.ai_chat_widget.isVisible():
            self.ai_chat_widget.input_field.setFocus()

    def _create_editor_api(self):
        """Cria uma instância da API para uso interno (ex: Chat IA)."""
        def update_config_wrapper(key, value):
            self.config_manager.config[key] = value
            self.config_manager.save_config(self.config_manager.config)

        def get_config_wrapper(key, default=None):
            return self.config_manager.get(key) or default

        def get_project_root_wrapper():
            if self.sidebar and self.sidebar.stack.currentWidget() == self.sidebar.tree:
                return self.sidebar.file_model.rootPath()
            return None

        return EditorAPI(
            insert_fn=self._api_insert_text,
            get_text_fn=self._api_get_text,
            add_menu_fn=self._api_add_menu,
            log_fn=self._api_log,
            get_editor_fn=lambda: self.active_editor,
            update_config_fn=update_config_wrapper,
            get_config_fn=get_config_wrapper,
            get_project_root_fn=get_project_root_wrapper,
            undo_fn=lambda: self.command_registry.execute("edit.undo")
        )

    def _toggle_sidebar(self):
        print("DEBUG: Atalho Ctrl+B acionado, alternando sidebar.")
        if self.sidebar is not None:
            self.sidebar.setVisible(not self.sidebar.isVisible())

    def _toggle_right_sidebar(self):
        if self.right_sidebar is not None:
            self.right_sidebar.setVisible(not self.right_sidebar.isVisible())

    def _focus_sidebar_search(self):
        if self.sidebar:
            if not self.sidebar.isVisible():
                self.sidebar.setVisible(True)
            self.sidebar.focus_search()

    def _create_new_file(self):
        print("DEBUG: Atalho Ctrl+N acionado, novo arquivo.")
        if self.sidebar is not None:
            self.sidebar._start_creation(is_folder=False)

    def _create_new_folder(self):
        print("DEBUG: Atalho Ctrl+Shift+N acionado, nova pasta.")
        if self.sidebar is not None:
            self.sidebar._start_creation(is_folder=True)

    def _show_help_window(self):
        """Exibe a janela de ajuda sólida."""
        help_win = HelpWindow(self)
        self._apply_theme_to_dialog(help_win)
        help_win.exec()

    def _show_store_dialog(self):
        """Abre a janela da loja de plugins."""
        dialog = StoreWindow(root_dir, self.theme_manager, self)
        dialog.exec()

    def _show_about_dialog(self):
        info = AboutInfo()
        dlg = AboutWindow(info, root_dir, self)
        self._apply_theme_to_dialog(dlg)
        dlg.exec()

    def _show_theme_editor(self):
        """Abre o editor de temas visual."""
        dialog = ThemeEditorDialog(self.theme_manager, self)
        # Conecta o sinal para o preview ao vivo
        dialog.theme_updated.connect(self._apply_config_globally)
        dialog.exec()
        # Restaura o tema salvo após fechar o diálogo
        self._apply_config_globally(self.config_manager.config)

    def _show_batata_window(self):
        """Exibe a janela da batata."""
        dlg = BatataWindow(self)
        self._apply_theme_to_dialog(dlg)
        dlg.exec()

    def _show_diagram_window(self):
        """Abre a janela do plugin dIAgram."""
        try:
            # Importa o plugin
            from plugins.dIAgram.diagram import DiagramWindow

            # Cria e mostra a janela
            # Mantém referência para não ser coletado pelo GC
            self.diagram_window = DiagramWindow(self)
            self.diagram_window.show()

            self.custom_statusbar.showMessage("Gerador de Diagramas aberto", 3000)
        except ImportError as e:
            QMessageBox.critical(
                self,
                "Plugin Não Encontrado",
                f"O plugin dIAgram não foi encontrado: {e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro",
                f"Erro ao abrir o plugin: {e}"
            )

    def _show_profile_window(self):
        """Abre a janela de perfil do GitHub."""
        dlg = ProfileWindow(self.github_auth, self.theme_manager, self)
        dlg.exec()

    def _close_current_tab(self):
        """Fecha a aba atual com segurança."""
        current_idx = self.editor_group.tab_widget.currentIndex()
        if current_idx != -1:
            self.editor_group.close_tab(current_idx)

    def _refresh_explorer(self):
        """Atualiza a árvore de arquivos na sidebar."""
        if self.sidebar:
            self.sidebar._refresh_tree()
            self.custom_statusbar.showMessage("Explorer atualizado.", 3000)
            
    def _next_tab(self):
        idx = self.editor_group.tab_widget.currentIndex()
        count = self.editor_group.tab_widget.count()
        if count > 1:
            self.editor_group.tab_widget.setCurrentIndex((idx + 1) % count)

    def _prev_tab(self):
        idx = self.editor_group.tab_widget.currentIndex()
        count = self.editor_group.tab_widget.count()
        if count > 1:
            self.editor_group.tab_widget.setCurrentIndex((idx - 1) % count)

    def _open_project_dialog(self):
        """Abre diálogo para selecionar pasta de projeto."""
        if self.config_manager.get("use_tasmafile"):
            dlg = TasmaFileWindow(self.config_manager, self.session_manager, root_dir, self.theme_manager, self)
            if dlg.exec():
                folder = dlg.selected_path
            else:
                folder = None
        else:
            folder = QFileDialog.getExistingDirectory(self, "Abrir Pasta de Projeto")
            
        if folder:
            self._load_project(folder)

    def _show_search_panel(self):
        if self.active_editor:
            self.search_panel.show_panel()

    def _hide_search_panel(self):
        self.search_panel.hide()
        if self.active_editor:
            self.active_editor.search_highlights = []
            self.active_editor.viewport().update()

    def _show_project_launcher(self):
        """Exibe o diálogo de troca rápida de projetos."""
        session = self.session_manager.load_session()
        recent = session.get("recent_projects", [])
        
        launcher = ProjectLauncher(recent, self)
        launcher.project_selected.connect(self._load_project)
        
        # Centraliza na janela
        geo = self.geometry()
        x = geo.x() + (geo.width() - launcher.width()) // 2
        y = geo.y() + 100
        launcher.move(x, y)
        launcher.exec()

    def _on_live_server_toggle(self, start: bool):
        """Inicia ou para o live server baseado no clique do botão."""
        if start:
            root_path = self.sidebar.file_model.rootPath()
            if not root_path or root_path == QDir.homePath():
                self.custom_statusbar.flash_message("Abra uma pasta de projeto para iniciar o servidor.", color="#dc3545")
                self.custom_statusbar.set_live_server_state(False)
                return
            
            port = self.config_manager.get("live_server_port")
            open_browser = self.config_manager.get("live_server_open_browser")
            self.live_server_manager.start(root_path, port=port, open_browser=open_browser)
        else:
            self.live_server_manager.stop()

    def _on_live_server_started(self, host: str, port: int):
        """Callback para quando o servidor é iniciado com sucesso."""
        self.custom_statusbar.set_live_server_state(True, host, port)
        self.custom_statusbar.flash_message(f"Live Server iniciado em http://{host}:{port}", color="#28a745")

    def _on_live_server_stopped(self):
        """Callback para quando o servidor é parado."""
        self.custom_statusbar.set_live_server_state(False)
        self.custom_statusbar.flash_message("Live Server parado.", color="#007acc")



    def _close_all_files(self):
        """Fecha todos os arquivos abertos, perguntando se deseja salvar."""
        count = self.editor_group.tab_widget.count()
        # Itera de trás para frente para evitar problemas de índice ao fechar
        for i in range(count - 1, -1, -1):
            self.editor_group.tab_widget.setCurrentIndex(i)
            editor = self.editor_group.tab_widget.widget(i)
            
            if isinstance(editor, CodeEditor) and editor.buffer and editor.buffer.dirty:
                file_name = os.path.basename(editor.property("file_path") or "Untitled")
                reply = QMessageBox.question(
                    self, "Salvar Alterações?",
                    f"O arquivo '{file_name}' tem alterações não salvas.\nDeseja salvar?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
                )
                
                if reply == QMessageBox.StandardButton.Cancel:
                    return False
                elif reply == QMessageBox.StandardButton.Yes:
                    self._save_file()
            
            self.editor_group.close_tab(i)
        return True

    def _load_project(self, path):
        """Carrega um projeto e atualiza a sessão."""
        if not self._close_all_files():
            return

        self.sidebar.set_root_path(path)
        self.search_manager.set_root_path(path)
        self.right_sidebar.load_repo(path) # Atualiza a sidebar direita (Git)
        self.setWindowTitle(f"JCode - {os.path.basename(path)}")
        if hasattr(self, 'custom_title_bar'):
            self.custom_title_bar.set_title(f"JCode - {os.path.basename(path)}")
        
        self.session_manager.add_to_history(path)
        # Salva sessão com o novo root e lista de arquivos vazia (pois fechamos tudo)
        self.session_manager.save_session(path, [], None)
        self.custom_statusbar.showMessage(f"Projeto carregado: {path}", 3000)

    def _on_find(self, text, case_sensitive, whole_word):
        if not self.active_editor or not text:
            self._hide_search_panel()
            return
        highlights = self.search_manager.find_all(self.active_editor.buffer, text, case_sensitive, whole_word)
        self.active_editor.search_highlights = highlights
        self.active_editor.viewport().update()
        
        # Feedback se não encontrar nada
        if not highlights:
            self.custom_statusbar.flash_message("Nenhum resultado encontrado.", color="#dc3545")

    def _on_replace_one(self, find_text, replace_text, case_sensitive, whole_word):
        """Substitui a seleção atual se corresponder, ou busca a próxima."""
        if not self.active_editor or not find_text: return
        
        buffer = self.active_editor.buffer
        # Verifica se o texto selecionado é o que queremos substituir
        current_selection = buffer.get_selected_text()
        
        if current_selection == find_text:
            # Substitui
            buffer.insert_text(replace_text)
            self._on_buffer_modified()
            # Busca o próximo
            self._on_find(find_text, case_sensitive, whole_word)
        else:
            # Apenas busca o próximo (o usuário precisa clicar de novo para substituir)
            # TODO: Implementar navegação de cursor para o próximo match
            self._on_find(find_text, case_sensitive, whole_word)
            self.custom_statusbar.flash_message("Próxima ocorrência localizada. Clique novamente para substituir.", color="#007acc")

    def _on_replace_all(self, find_text, replace_text, case_sensitive, whole_word):
        if self.active_editor and find_text:
            count = self.search_manager.replace_all(self.active_editor.buffer, find_text, replace_text, case_sensitive, whole_word)
            self._on_buffer_modified()
            self.custom_statusbar.flash_message(f"{count} ocorrências substituídas.", color="#28a745")

    def _quick_rename(self):
        """Atalho F2: Renomeia a variável sob o cursor em todo o arquivo."""
        if not self.active_editor or not self.active_editor.buffer: return
        
        buffer = self.active_editor.buffer
        
        # Tenta pegar seleção ou palavra sob cursor
        initial_text = buffer.get_selected_text()
        if not initial_text:
            # Seleciona palavra sob cursor se não houver seleção
            cursor = buffer.cursors[-1]
            buffer.select_word_at(cursor.line, cursor.col)
            initial_text = buffer.get_selected_text()
            self.active_editor.viewport().update()
            
        if not initial_text:
            self.custom_statusbar.flash_message("Nenhuma palavra selecionada para renomear.", color="#dc3545")
            return

        new_text, ok = QInputDialog.getText(self, "Renomear Variável", f"Renomear '{initial_text}' para:", text=initial_text)
        
        if ok and new_text and new_text != initial_text:
            # Executa substituição global com limite de palavra (Whole Word)
            count = self.search_manager.replace_all(buffer, initial_text, new_text, case_sensitive=True, whole_word=True)
            self._on_buffer_modified()
            self.custom_statusbar.flash_message(f"Renomeado '{initial_text}' para '{new_text}' em {count} lugares.", color="#28a745")

    def _copy_selection(self):
        """Copia o texto selecionado para a área de transferência."""
        if self.active_editor and self.active_editor.buffer:
            buffer = self.active_editor.buffer
            selected_texts = [buffer.get_selected_text(i) for i in range(len(buffer.cursors))]
            non_empty = [text for text in selected_texts if text]
            if non_empty:
                QApplication.clipboard().setText("\n".join(non_empty))

    def _cut_selection(self):
        """Recorta o texto selecionado."""
        if self.active_editor and self.active_editor.buffer:
            self._copy_selection()
            self.active_editor.buffer.delete_selection()
            self._on_buffer_modified()

    def _paste_from_clipboard(self):
        """Cola o texto da área de transferência."""
        if self.active_editor and self.active_editor.buffer:
            text = QApplication.clipboard().text()
            if text:
                self.active_editor.buffer.insert_text(text)
                self._on_buffer_modified()

    def _save_file(self):
        if not self.active_editor:
            return

        file_path = self.active_editor.property("file_path")
        if not file_path:
            self._save_file_as()
            return
        
        content = self.active_editor.buffer.get_text()
        # Usando a versão síncrona do FileManager para simplicidade
        FileManager._write_sync(file_path, content)
        self.active_editor.buffer.dirty = False
        self._on_buffer_modified()
        self.custom_statusbar.flash_message(f"Arquivo salvo: {os.path.basename(file_path)}", color="#28a745")

    def _save_file_as(self):
        if not self.active_editor:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Salvar Como...")
        if path:
            self.active_editor.set_file_path(path)
            self._save_file()

    def _open_file(self, path):
        """Abre um arquivo selecionado na sidebar."""
        # Verifica se o arquivo já está aberto
        for i in range(self.editor_group.tab_widget.count()):
            editor = self.editor_group.tab_widget.widget(i)
            if editor.property("file_path") == path:
                self.editor_group.tab_widget.setCurrentIndex(i)
                return

        # Verifica se é arquivo de mídia
        _, ext = os.path.splitext(path)
        ext = ext.lower()
        if ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.mp3']:
            self._open_media_file(path)
            return
            
        if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.ico', '.svg', '.tif', '.tiff']:
            self._open_image_file(path)
            return

        if ext == '.pdf':
            self._open_pdf_file(path)
            return

        # Usando a versão síncrona do FileManager para simplicidade na UI
        try:
            content = FileManager._read_sync(path, 'utf-8')
            buffer = DocumentBuffer(content)
            buffer.dirty = False

            editor = CodeEditor()
            editor.set_cache_dir(self.cache_dir)
            editor.set_file_path(path)
            editor.set_dependencies(buffer, self.theme_manager, self.highlighter, self.autocomplete_manager, self.clipboard_manager)
            editor.set_input_mapper(self.input_mapper)
            # Aplica configurações atuais ao novo editor
            editor.update_settings(self.config_manager.config)
           
            handler = EventHandler(self.extension_bridge, buffer)
            
            def on_editor_text_changed():
                buffer.dirty = True
                self._on_buffer_modified()

            editor.text_changed.connect(on_editor_text_changed)
            editor.text_changed.connect(self._check_autocomplete_trigger)
            editor.cursor_moved.connect(self._hide_autocomplete)
            
            # Conecta sinais do menu de contexto
            editor.save_requested.connect(self._save_file)
            editor.close_requested.connect(self._close_current_tab)

            # Conecta o sinal de modificação deste buffer específico
            editor.setProperty("event_handler", handler)

            self.editor_group.add_editor(editor, path)
            self.custom_statusbar.flash_message(f"Arquivo aberto: {os.path.basename(path)}", color="#007acc")
        except Exception as e:
            self.custom_statusbar.flash_message(f"Erro ao abrir: {e}", color="#dc3545")

    def _open_media_file(self, path):
        try:
            player = VideoPlayer()
            player.load_file(path)
            player.setProperty("file_path", path)
            
            self.editor_group.add_editor(player, path)
            self.custom_statusbar.flash_message(f"Mídia aberta: {os.path.basename(path)}", color="#007acc")
        except Exception as e:
            self.custom_statusbar.flash_message(f"Erro ao abrir mídia: {e}", color="#dc3545")

    def _open_image_file(self, path):
        try:
            viewer = ImageViewer()
            viewer.load_file(path)
            viewer.setProperty("file_path", path)
            
            self.editor_group.add_editor(viewer, path)
            self.custom_statusbar.flash_message(f"Imagem aberta: {os.path.basename(path)}", color="#007acc")
        except Exception as e:
            self.custom_statusbar.flash_message(f"Erro ao abrir imagem: {e}", color="#dc3545")

    def _open_pdf_file(self, path):
        try:
            viewer = PdfViewer()
            viewer.load_file(path)
            viewer.setProperty("file_path", path)
            
            self.editor_group.add_editor(viewer, path)
            self.custom_statusbar.flash_message(f"PDF aberto: {os.path.basename(path)}", color="#007acc")
        except Exception as e:
            self.custom_statusbar.flash_message(f"Erro ao abrir PDF: {e}", color="#dc3545")

    def _on_buffer_modified(self):

        """Atualiza o widget CodeEditor com o conteúdo do DocumentBuffer."""
        self._update_tab_title()

        if not self.active_editor or not self.active_editor.buffer:
            self.setWindowTitle("JCode")
            self.save_action.setEnabled(False)
            self.find_action.setEnabled(False)
            return

        buffer = self.active_editor.buffer
        file_path = self.active_editor.property("file_path")
        
        base_name = os.path.basename(file_path) if file_path else "Novo Arquivo"

        # Atualiza scrollbar caso o número de linhas tenha mudado
        self.viewport_controller.update_scrollbar(buffer)
        
        # Solicita repaint
        self.active_editor.viewport().update()
        
        # Atualiza largura do gutter se necessário (ex: passou de 99 para 100 linhas)
        self.active_editor._update_line_number_area_width()

        # Atualiza título da janela para indicar modificações
        title = "JCode - "
        title += base_name
        if buffer.dirty:
            title += "*"
        self.setWindowTitle(title)
        if hasattr(self, 'custom_title_bar'):
            self.custom_title_bar.set_title(title)
        
        # Atualiza Status Bar
        if buffer.cursors:
            c = buffer.cursors[-1]
            self.custom_statusbar.update_cursor_info(c.line, c.col)
        
        # Atualiza estado da ação 'Salvar'
        if hasattr(self, 'save_action'):
            self.save_action.setEnabled(buffer.dirty)
        
        # Atualiza nome do arquivo na barra de status
        if file_path:
            filename = os.path.basename(file_path)
            self.custom_statusbar.update_filename(filename)
        else:
            # Mostra "Novo Arquivo" ou similar se não tiver arquivo
            self.custom_statusbar.update_filename("Novo Arquivo")
            
    def _update_tab_title(self):


        """Atualiza o título da aba para reflectir o estado 'dirty'."""
        if not self.active_editor:
            return

        file_path = self.active_editor.property("file_path")
        base_name = os.path.basename(file_path) if file_path else "Novo Arquivo"
        buffer = self.active_editor.buffer
        index = self.editor_group.tab_widget.currentIndex()
        title = base_name + (" ●" if buffer.dirty else "")  # Use a bullet
        self.editor_group.tab_widget.setTabText(index, title)
        
    def _close_current_tab(self):
        """Closes the current tab with save/discard/cancel logic."""
        current_idx = self.editor_group.tab_widget.currentIndex()
        if current_idx == -1:
            return

        editor = self.editor_group.tab_widget.widget(current_idx)
        if not isinstance(editor, CodeEditor):
            self.editor_group.close_tab(current_idx)  # Close placeholder or other non-editor tabs
            return

        if editor.buffer.dirty:
            file_path = editor.property("file_path")
            file_name = os.path.basename(file_path) if file_path else "Untitled"

            reply = QMessageBox.question(
                self, "Salvar Alterações?",
                f"Deseja salvar as alterações em '{file_name}'?",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save  # Default button
            )

            if reply == QMessageBox.StandardButton.Save:
                # Save the file and then close the tab
                self._save_file()
                if not editor.buffer.dirty:  # Only close if save was successful
                    self.editor_group.close_tab(current_idx)
            elif reply == QMessageBox.StandardButton.Discard:
                # Discard changes and close the tab
                self.editor_group.close_tab(current_idx)
            else:
                # Cancel: Do nothing, just return
                return
        else:
            # If not dirty, just close the tab
            self.editor_group.close_tab(current_idx)


        self.find_action.setEnabled(True)
        
    def _load_extensions(self):
        """Carrega plugins e conecta sinais."""
        plugins_path = os.path.join(root_dir, "plugins")
        
        # Cria pasta de plugins se não existir
        if not os.path.exists(plugins_path):
            os.makedirs(plugins_path)
            
        # Conecta sinal da bridge para atualizar a UI
        self.extension_bridge.plugin_loaded.connect(
            lambda name: self.custom_statusbar.showMessage(f"Plugin carregado: {name}", 3000)
        )
        self.extension_bridge.plugin_error.connect(
            lambda name, err: self.custom_statusbar.flash_message(f"Erro no plugin {name}: {err}", color="#dc3545")
        )
        
        # Fase 1: Load (Importação)
        self.extension_bridge.load_plugins(plugins_path)
        
        # Fase 2: Activate (Execução com API)
        def update_config_wrapper(key, value):
            # Atualiza a configuração e salva no disco
            self.config_manager.config[key] = value
            self.config_manager.save_config(self.config_manager.config)
            
        def get_config_wrapper(key, default=None):
            return self.config_manager.get(key) or default

        def get_project_root_wrapper():
            if self.sidebar and self.sidebar.stack.currentWidget() == self.sidebar.tree:
                return self.sidebar.file_model.rootPath()
            return None

        self.extension_bridge.activate_plugins(
            insert_fn=self._api_insert_text,
            get_text_fn=self._api_get_text,
            add_menu_fn=self._api_add_menu,
            log_fn=self._api_log,
            get_editor_fn=lambda: self.active_editor,
            update_config_fn=update_config_wrapper,
            get_config_fn=get_config_wrapper,
            get_project_root_fn=get_project_root_wrapper,
            undo_fn=lambda: self.command_registry.execute("edit.undo")
        )

    # --- Implementação da EditorAPI ---
    def _api_insert_text(self, text):
        if self.active_editor and self.active_editor.buffer:
            self.active_editor.buffer.insert_text(text)
            self._on_buffer_modified()

    def _api_get_text(self):
        if self.active_editor and self.active_editor.buffer:
            return self.active_editor.buffer.get_text()
        return ""

    def _api_add_menu(self, label, callback):
        """Adiciona uma ação ao menu de Plugins."""
        action = QAction(label, self)
        # O callback já vem envolvido pelo EditorAPI para não precisar de args
        action.triggered.connect(callback)
        self.plugins_menu.addAction(action)

    def _api_log(self, message):
        self.custom_statusbar.showMessage(f"[Plugin] {message}", 5000)

    def _load_session(self):
        """Carrega a lista de arquivos da sessão anterior."""
        session_data = self.session_manager.load_session()
        
        # 1. Recupera e valida o diretório de trabalho
        root_path = session_data.get("last_directory")
        if root_path and os.path.exists(root_path) and os.path.isdir(root_path):
            self.sidebar.set_root_path(root_path)
            self.search_manager.set_root_path(root_path)
            self.setWindowTitle(f"JCode - {os.path.basename(root_path)}")
        else:
            root_path = None

        # 2. Abre os arquivos e restaura cursores
        files_to_open = session_data.get("open_files", [])
        for file_data in files_to_open:
            path = file_data.get("path")
            if path:
                # Reconstrói caminho absoluto se necessário
                if root_path and not os.path.isabs(path):
                    path = os.path.join(root_path, path)
                
                if os.path.exists(path):
                    self._open_file(path)
                    
                    # Restaura posição do cursor
                    cursor_info = file_data.get("cursor")
                    if cursor_info and self.active_editor:
                        self.active_editor.buffer.update_last_cursor(
                            cursor_info.get("line", 0), 
                            cursor_info.get("col", 0)
                        )
                        self.active_editor.viewport().update()

        # 3. Restaura a aba ativa
        active_file = session_data.get("active_file")
        if active_file:
            if root_path and not os.path.isabs(active_file):
                active_file = os.path.join(root_path, active_file)
            
            for i in range(self.editor_group.tab_widget.count()):
                editor = self.editor_group.tab_widget.widget(i)   
                if isinstance(editor, CodeEditor) and editor.property("file_path") == active_file:
                    self.editor_group.tab_widget.setCurrentIndex(i)
                    break

    def _save_session(self):
        """Salva a lista de arquivos abertos."""
        open_files = []

        for i in range(self.editor_group.tab_widget.count()):
            editor = self.editor_group.tab_widget.widget(i)
            if isinstance(editor, CodeEditor):
                file_path = editor.property("file_path")
                if file_path:
                    cursor = editor.buffer.cursors[-1]
                    open_files.append({
                        'path': file_path, 
                        'cursor': {'line': cursor.line, 'col': cursor.col}
                    })

        # Determina o root_path baseado no estado da Sidebar
        root_path = None
        if self.sidebar.stack.currentWidget() == self.sidebar.tree:
            root_path = self.sidebar.file_model.rootPath()
            


        active_path = self.active_editor.property("file_path") if self.active_editor else None
        
        self.session_manager.save_session(root_path, open_files, active_path)

    def _zoom_in(self):
        """Aumenta o tamanho da fonte global."""
        current_size_val = self.config_manager.get("font_size")
        current_size = current_size_val if current_size_val is not None else 12
        new_size = min(current_size + 1, 72) # Limite máximo de 72
        if new_size != current_size:
            self.config_manager.config["font_size"] = new_size
            self._apply_config_globally(self.config_manager.config)
            self.custom_statusbar.showMessage(f"Zoom: {int((new_size/12)*100)}%", 1000)

    def _zoom_out(self):
        """Diminui o tamanho da fonte global."""
        current_size_val = self.config_manager.get("font_size")
        current_size = current_size_val if current_size_val is not None else 12
        new_size = max(current_size - 1, 6) # Limite mínimo de 6
        if new_size != current_size:
            self.config_manager.config["font_size"] = new_size
            self._apply_config_globally(self.config_manager.config)
            self.custom_statusbar.showMessage(f"Zoom: {int((new_size/12)*100)}%", 1000)

    def _update_user_avatar(self):
        """Atualiza o avatar na barra de status."""
        if self.github_auth.is_logged_in():
            avatar_bytes = self.github_auth.get_avatar_bytes()
            self.custom_statusbar.set_avatar(avatar_bytes)
        else:
            self.custom_statusbar.set_avatar(None)


def main():
    """Ponto de entrada da aplicação."""
    app = QApplication(sys.argv)
    app.setApplicationName("JCode")
    
    window = JCodeMainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

import sys
import os
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QSplitter, QFileDialog
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QAction, QKeySequence

# Ajuste de Path para garantir que imports funcionem a partir da raiz
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.core.editor_logic.buffer import DocumentBuffer
from src.core.editor_logic.file_manager import FileManager
from src.core.ui_logic.extension_bridge import ExtensionBridge
from src.core.editor_logic.highlighter_engine import HighlighterEngine
from src.core.ui_logic.theme_manager import ThemeManager
from src.core.editor_logic.commands import CommandRegistry
from src.core.ui_logic.input_mapper import InputMapper
from src.core.ui_logic.event_handler import EventHandler
from src.core.ui_logic.viewport_controller import ViewportController
from src.ui.editor import CodeEditor
from src.ui.sidebar import Sidebar
from src.ui.statusbar import StatusBar
from src.ui.editor_group import EditorGroup
from src.ui.command_palette import CommandPalette
from src.ui.help_overlay import HelpOverlay

class JCodeMainWindow(QMainWindow):
    """Janela principal do editor JCODE.
    
    Responsável por orquestrar a inicialização dos subsistemas Core e UI.
    """

    def __init__(self):
        super().__init__()
        
        # Gerenciamento de múltiplos documentos
        self.active_editor = None
        
        # --- 2. Inicialização dos Subsistemas de UI Logic ---
        self.highlighter = HighlighterEngine()
        self.extension_bridge = ExtensionBridge()
        
        themes_path = os.path.join(root_dir, "themes")
        self.theme_manager = ThemeManager(themes_path)
        
        self.command_registry = CommandRegistry()
        self.input_mapper = InputMapper(self.command_registry)
        
        self.event_handler = EventHandler(self.extension_bridge, None) # Buffer será definido dinamicamente
        self.viewport_controller = ViewportController()
        
        # --- 3. Configuração da UI ---
        self.setWindowTitle("JCode - Modular Editor")
        self.resize(1024, 768)
        
        self._setup_ui()
        self._create_actions()
        self._create_menu_bar()
        self._setup_logic_connections()
        
        # Carrega tema e extensões
        self.theme_manager.load_theme("dark_default") # Tenta carregar tema
        self.theme_manager.apply_theme(QApplication.instance())
        self._load_extensions()
        self._load_session()
        
        # Hook de inicialização
        self.extension_bridge.trigger_hook("on_app_start")

    def closeEvent(self, event):
        """Salva a sessão ao fechar."""
        self._save_session()
        event.accept()

    def _setup_ui(self):
        """Configura os widgets da interface."""
        # Componentes principais
        self.sidebar = Sidebar()
        self.editor_group = EditorGroup()
        
        self.custom_statusbar = StatusBar()
        self.setStatusBar(self.custom_statusbar)
        
        self.command_palette = CommandPalette(self)
        self._setup_commands()
        self._register_core_commands()
        
        # Layout Principal (Horizontal: Sidebar | Conteúdo)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(self.sidebar)

        # Layout de Conteúdo (Apenas Editor agora)
        self.main_splitter.addWidget(self.editor_group)
        
        # Define proporção inicial (20% Sidebar, 80% Editor)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 4)
        
        self.setCentralWidget(self.main_splitter)

    def _create_menu_bar(self):
        """Cria e popula a barra de menu global."""
        menu_bar = self.menuBar()

        # --- Menu Arquivo ---
        file_menu = menu_bar.addMenu("&Arquivo")
        file_menu.addAction(self.new_file_action)
        open_file_action = QAction("Abrir Arquivo...", self)
        open_file_action.setEnabled(False) # Placeholder
        file_menu.addAction(open_file_action)
        file_menu.addAction(self.open_folder_action)
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
        # Placeholders para funcionalidades futuras
        for name in ["Recortar", "Copiar", "Colar", "Localizar"]:
            action = QAction(name, self)
            action.setEnabled(False)
            edit_menu.addAction(action)

        # --- Menu Exibir ---
        view_menu = menu_bar.addMenu("&Exibir")
        view_menu.addAction(self.toggle_sidebar_action)
        view_menu.addAction(self.toggle_fullscreen_action)

        # --- Outros Menus (Placeholders) ---
        menu_bar.addMenu("&Ferramentas")
        help_menu = menu_bar.addMenu("&Ajuda")
        help_menu.addAction(self.show_help_action)

        # --- Menu Plugins (Dinâmico) ---
        self.plugins_menu = menu_bar.addMenu("&Plugins")

    def _create_actions(self):
        """Cria todas as QActions globais para centralizar a lógica."""
        # --- File Actions ---
        self.new_file_action = QAction("Novo Arquivo", self)
        self.new_file_action.setShortcut(QKeySequence("Ctrl+N"))
        self.new_file_action.triggered.connect(self._create_new_file)

        self.open_folder_action = QAction("Abrir Pasta...", self)
        self.open_folder_action.triggered.connect(self._open_folder_dialog)

        self.save_action = QAction("Salvar", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.setEnabled(False)
        self.save_action.triggered.connect(lambda: self.command_registry.execute("file.save"))

        self.save_as_action = QAction("Salvar Como...", self)
        self.save_as_action.triggered.connect(lambda: self.command_registry.execute("file.save_as"))

        # --- Edit Actions ---
        self.undo_action = QAction("Desfazer", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(lambda: self.command_registry.execute("edit.undo"))

        self.redo_action = QAction("Refazer", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(lambda: self.command_registry.execute("edit.redo"))

        # --- View Actions ---
        self.toggle_sidebar_action = QAction("Alternar Barra Lateral", self)
        self.toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+B"))
        self.toggle_sidebar_action.triggered.connect(self._toggle_sidebar)

        self.toggle_fullscreen_action = QAction("Tela Cheia", self)
        self.toggle_fullscreen_action.setCheckable(True)
        self.toggle_fullscreen_action.triggered.connect(lambda checked: self.showFullScreen() if checked else self.showNormal())

        # --- Help Actions ---
        self.show_help_action = QAction("Guia de Atalhos", self)
        self.show_help_action.setShortcut(QKeySequence("F1"))
        self.show_help_action.triggered.connect(self._show_help_overlay)

        # Adiciona ações à janela para que os atalhos sejam globais
        self.addActions([
            self.new_file_action, self.save_action, self.undo_action, self.redo_action,
            self.toggle_sidebar_action, self.show_help_action
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
        r.register("type_char", lambda t: get_active_buffer_and_execute("insert_text", t))
        r.register("edit.insert_pair", lambda p: get_active_buffer_and_execute("insert_paired_text", p))
        r.register("edit.backspace", lambda: get_active_buffer_and_execute("delete_backspace"))
        r.register("edit.new_line", lambda: get_active_buffer_and_execute("insert_text", "\n"))
        r.register("edit.indent", lambda: get_active_buffer_and_execute("insert_text", "    "))
        
        # Comandos de Cursor
        r.register("cursor.move_up", lambda: get_active_buffer_and_execute("move_cursors", -1, 0))
        r.register("cursor.move_down", lambda: get_active_buffer_and_execute("move_cursors", 1, 0))
        r.register("cursor.move_left", lambda: get_active_buffer_and_execute("move_cursors", 0, -1))
        r.register("cursor.move_right", lambda: get_active_buffer_and_execute("move_cursors", 0, 1))
        r.register("cursor.add_up", lambda: get_active_buffer_and_execute("add_cursor_relative", -1))
        r.register("cursor.add_down", lambda: get_active_buffer_and_execute("add_cursor_relative", 1))
        
        # Comandos de Histórico
        r.register("edit.undo", lambda: get_active_buffer_and_execute("undo"))
        r.register("edit.redo", lambda: get_active_buffer_and_execute("redo"))
        
        r.register("view.command_palette", self.command_palette.show_palette)
        r.register("file.save", self._save_file)
        r.register("file.save_as", self._save_file_as)

    def _setup_commands(self):
        """Registra comandos e atalhos."""
        # Atalho para Paleta de Comandos
        action = QAction("Command Palette", self)
        action.setShortcut(QKeySequence("Ctrl+Shift+P"))
        action.triggered.connect(self.command_palette.show_palette)
        self.addAction(action)
        
        # Registra comandos básicos
        self.command_palette.register_command("Editor: Toggle Sidebar", lambda: self.sidebar.setVisible(not self.sidebar.isVisible()))
        self.command_palette.register_command("File: Save", lambda: print("Save triggered"))
        self.command_palette.register_command("File: New File", self._create_new_file)
        self.command_palette.register_command("File: New Folder", self._create_new_folder)
        self.command_palette.register_command("File: Open Folder", self._open_folder_dialog)

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
        self.sidebar.open_folder_clicked.connect(self._open_folder_dialog)
        self.sidebar.file_clicked.connect(self._open_file)
        self.sidebar.file_created.connect(self._open_file)
        self.sidebar.status_message.connect(self.custom_statusbar.showMessage)

        # Conexão do EditorGroup
        self.editor_group.active_editor_changed.connect(self._on_active_editor_changed)

    def _on_active_editor_changed(self, editor_widget):
        self.active_editor = editor_widget
        if editor_widget:
            self.event_handler.buffer = editor_widget.buffer
            self.viewport_controller.attach_to(editor_widget)
        self._on_buffer_modified()

    def _toggle_sidebar(self):
        print("DEBUG: Atalho Ctrl+B acionado, alternando sidebar.")
        if self.sidebar is not None:
            self.sidebar.setVisible(not self.sidebar.isVisible())

    def _create_new_file(self):
        print("DEBUG: Atalho Ctrl+N acionado, novo arquivo.")
        if self.sidebar is not None:
            self.sidebar._start_creation(is_folder=False)

    def _create_new_folder(self):
        print("DEBUG: Atalho Ctrl+Shift+N acionado, nova pasta.")
        if self.sidebar is not None:
            self.sidebar._start_creation(is_folder=True)

    def _show_help_overlay(self):
        """Exibe a janela de ajuda com os atalhos."""
        print("DEBUG: Atalho F1 acionado, mostrando ajuda.")
        all_bindings = self.input_mapper.key_bindings.copy()
        # TODO: Adicionar atalhos globais (QAction) a este dicionário para uma lista completa.
        help_dialog = HelpOverlay(all_bindings, self)
        help_dialog.show()

    def _open_folder_dialog(self):
        """Abre diálogo para selecionar pasta."""
        folder = QFileDialog.getExistingDirectory(self, "Abrir Pasta")
        if folder:
            self.sidebar.set_root_path(folder)

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
        self.custom_statusbar.showMessage(f"Arquivo salvo: {file_path}", 3000)

    def _save_file_as(self):
        if not self.active_editor:
            return

        path, _ = QFileDialog.getSaveFileName(self, "Salvar Como...")
        if path:
            self.active_editor.setProperty("file_path", path)
            self._save_file()

    def _open_file(self, path):
        """Abre um arquivo selecionado na sidebar."""
        # Verifica se o arquivo já está aberto
        for i in range(self.editor_group.tab_widget.count()):
            editor = self.editor_group.tab_widget.widget(i)
            if isinstance(editor, CodeEditor) and editor.property("file_path") == path:
                self.editor_group.tab_widget.setCurrentIndex(i)
                return

        # Usando a versão síncrona do FileManager para simplicidade na UI
        try:
            content = FileManager._read_sync(path, 'utf-8')
            buffer = DocumentBuffer(content)
            buffer.dirty = False

            editor = CodeEditor()
            editor.setProperty("file_path", path)
            editor.set_dependencies(buffer, self.theme_manager, self.highlighter)
            editor.set_input_mapper(self.input_mapper)
            
            # Conecta o sinal de modificação deste buffer específico
            handler = EventHandler(self.extension_bridge, buffer)
            handler.buffer_modified.connect(self._on_buffer_modified)
            editor.setProperty("event_handler", handler) # Mantém referência

            self.editor_group.add_editor(editor, path)
            self.custom_statusbar.showMessage(f"Arquivo aberto: {os.path.basename(path)}", 5000)
        except Exception as e:
            self.custom_statusbar.showMessage(f"Erro ao abrir o arquivo: {e}", 5000)

    def _on_buffer_modified(self):
        """Atualiza o widget CodeEditor com o conteúdo do DocumentBuffer."""
        if not self.active_editor or not self.active_editor.buffer:
            self.setWindowTitle("JCode")
            self.save_action.setEnabled(False)
            return

        buffer = self.active_editor.buffer
        file_path = self.active_editor.property("file_path")

        # Atualiza scrollbar caso o número de linhas tenha mudado
        self.viewport_controller.update_scrollbar(buffer)
        
        # Solicita repaint
        self.active_editor.viewport().update()
        
        # Atualiza largura do gutter se necessário (ex: passou de 99 para 100 linhas)
        self.active_editor._update_line_number_area_width()

        # Atualiza título da janela para indicar modificações
        title = "JCode - "
        base_name = os.path.basename(file_path) if file_path else "Novo Arquivo"
        title += base_name
        if buffer.dirty:
            title += "*"
        self.setWindowTitle(title)
        
        # Atualiza Status Bar
        if buffer.cursors:
            c = buffer.cursors[-1]
            self.custom_statusbar.update_cursor_info(c.line, c.col)
        
        # Atualiza estado da ação 'Salvar'
        if hasattr(self, 'save_action'):
            self.save_action.setEnabled(buffer.dirty)
        
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
            lambda name, err: self.custom_statusbar.showMessage(f"Erro no plugin {name}: {err}", 10000)
        )
        
        # Fase 1: Load (Importação)
        self.extension_bridge.load_plugins(plugins_path)
        
        # Fase 2: Activate (Execução com API)
        self.extension_bridge.activate_plugins(
            insert_fn=self._api_insert_text,
            get_text_fn=self._api_get_text,
            add_menu_fn=self._api_add_menu,
            log_fn=self._api_log
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
        session_file = os.path.join(os.path.expanduser("~"), ".jcode_session")
        if not os.path.exists(session_file):
            return
        with open(session_file, 'r') as f:
            files_to_open = [line.strip() for line in f if line.strip() and os.path.exists(line.strip())]
        
        for file_path in files_to_open:
            self._open_file(file_path)

    def _save_session(self):
        """Salva a lista de arquivos abertos."""
        session_file = os.path.join(os.path.expanduser("~"), ".jcode_session")
        open_files = []
        for i in range(self.editor_group.tab_widget.count()):
            editor = self.editor_group.tab_widget.widget(i)
            if isinstance(editor, CodeEditor):
                file_path = editor.property("file_path")
                if file_path:
                    open_files.append(file_path)
        with open(session_file, 'w') as f:
            f.write('\n'.join(open_files))

def main():
    """Ponto de entrada da aplicação."""
    app = QApplication(sys.argv)
    app.setApplicationName("JCode")
    
    window = JCodeMainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
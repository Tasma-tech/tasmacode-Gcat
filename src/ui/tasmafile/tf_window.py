from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QPushButton, QFrame, QLabel, QStyle, QSplitter
from PySide6.QtCore import Qt
from src.core.tasmafile.data_provider import TasmaDataProvider
from src.ui.tasmafile.tf_sidebar import TasmaSidebar
from src.ui.tasmafile.tf_file_view import TasmaFileView
from src.ui.tasmafile.tf_preview_panel import PreviewPanel
import os

class TasmaFileWindow(QDialog):
    """Janela Principal do Gerenciador de Arquivos TasmaFile."""
    
    def __init__(self, config_manager, session_manager, root_dir, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.setWindowTitle("TasmaFile - Gerenciador de Arquivos")
        self.resize(1000, 700)
        self.selected_path = None
        
        # Lógica
        self.provider = TasmaDataProvider(session_manager, root_dir)
        
        # Layout Principal
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = TasmaSidebar(self.provider)
        self.sidebar.category_selected.connect(self._on_category_selected)
        
        # Conteúdo (File View + Botões de Ação)
        content_widget = QFrame()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        self.file_view = TasmaFileView()
        self.file_view.path_confirmed.connect(self._on_path_confirmed)
        self.file_view.path_selected.connect(self._on_path_selected)
        self.file_view.status_updated.connect(self._update_status)
        self.file_view.preview_toggled.connect(self._on_preview_toggled)
        
        # Botões Inferiores
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 10, 10, 10)
        btn_layout.addStretch()
        
        self.btn_select = QPushButton("Selecionar / Abrir")
        self.btn_select.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOkButton))
        self.btn_select.setCursor(Qt.PointingHandCursor)
        self.btn_select.clicked.connect(lambda: self._on_path_confirmed(self.selected_path))
        
        self.lbl_status = QLabel("Pronto")
        self.lbl_status.setStyleSheet("color: #808080; font-size: 11px; padding-left: 5px;")
        
        btn_layout.addWidget(self.lbl_status)
        btn_layout.addWidget(self.btn_select)
        
        content_layout.addWidget(self.file_view)
        content_layout.addLayout(btn_layout)
        
        # Preview Panel
        self.preview_panel = PreviewPanel(self.theme_manager.current_theme)
        
        # Splitter para File View e Preview
        view_splitter = QSplitter(Qt.Horizontal)
        view_splitter.addWidget(content_widget)
        view_splitter.addWidget(self.preview_panel)
        view_splitter.setStretchFactor(0, 2) # File view é maior
        view_splitter.setStretchFactor(1, 1) # Preview é menor
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(view_splitter)
        
        # Aplica o tema
        self._apply_theme()
        
        # Conecta e carrega favoritos
        self.provider.favorites_changed.connect(self._refresh_favorites)
        self._refresh_favorites()
        
        # Define caminho inicial (Projetos recentes ou Home)
        recents = self.provider.get_recent_projects()
        if recents:
            self.file_view.set_path(recents[0])
        else:
            self.file_view.set_path(self.provider.get_home_dir())

    def _apply_theme(self):
        theme = self.theme_manager.current_theme
        bg = theme.get("background", "#1e1e1e")
        fg = theme.get("foreground", "#cccccc")
        accent = theme.get("accent", "#007acc")
        
        self.setStyleSheet(f"background-color: {bg}; color: {fg};")
        self.sidebar.apply_theme(theme)
        self.file_view.apply_theme(theme)
        self.preview_panel.apply_theme(theme)
        self.btn_select.setStyleSheet(f"background-color: {accent}; color: white; padding: 8px 16px; border: none; border-radius: 4px; font-weight: bold;")

    def _refresh_favorites(self):
        favs = self.provider.get_custom_categories()
        self.file_view.update_favorites(favs)

    def _on_category_selected(self, type_id, data):
        self.file_view.set_path(data)

    def _on_path_selected(self, path):
        self.selected_path = path
        self.preview_panel.show_preview(path)

    def _on_path_confirmed(self, path):
        if path:
            # Se um arquivo for confirmado, o projeto é a pasta pai.
            if os.path.isfile(path):
                self.selected_path = os.path.dirname(path)
            else:
                self.selected_path = path
            self.accept()

    def _update_status(self, msg):
        self.lbl_status.setText(msg)

    def _on_preview_toggled(self, visible):
        self.preview_panel.setVisible(visible)
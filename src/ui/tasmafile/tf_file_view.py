from PySide6.QtWidgets import (QWidget, QVBoxLayout, QListView, QFileSystemModel, QLineEdit, 
                               QAbstractItemView, QHBoxLayout, QPushButton, QStyle, QMenu, QListWidget, QListWidgetItem,
                               QInputDialog, QMessageBox, QToolTip, QScrollArea, QFrame, 
                               QSlider, QComboBox, QLabel, QSpinBox, QStackedWidget)
from PySide6.QtCore import Qt, Signal, QDir, QSize, QEvent, QThread, QDateTime, QSortFilterProxyModel
from PySide6.QtGui import QKeySequence, QCursor
from src.core.editor_logic.file_manager import FileManager
from src.core.tasmafile.search_engine import FileSearchEngine
import os
import shutil

class AdvancedFileFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._extension = ""
        self._size_limit = -1
        self._size_op = ">"
        self._date_limit = QDateTime()

    def set_extension_filter(self, ext: str):
        self._extension = ext.lower().strip()
        if self._extension and not self._extension.startswith('.'):
            self._extension = '.' + self._extension
        self.invalidateFilter()

    def set_size_filter(self, op: str, size: int, unit: str):
        self._size_op = op
        multiplier = {"KB": 1024, "MB": 1024**2, "GB": 1024**3}
        self._size_limit = size * multiplier.get(unit, 1)
        self.invalidateFilter()

    def set_date_filter(self, period: str):
        now = QDateTime.currentDateTime()
        if period == "Last 24h":
            self._date_limit = now.addDays(-1)
        elif period == "Last 7 days":
            self._date_limit = now.addDays(-7)
        elif period == "Last 30 days":
            self._date_limit = now.addDays(-30)
        else:
            self._date_limit = QDateTime()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        source_index = self.sourceModel().index(source_row, 0, source_parent)
        if not source_index.isValid():
            return False

        file_info = self.sourceModel().fileInfo(source_index)

        if file_info.isDir():
            return True

        if self._extension and not file_info.fileName().lower().endswith(self._extension):
            return False

        if self._size_limit > 0:
            file_size = file_info.size()
            if self._size_op == '>' and file_size <= self._size_limit:
                return False
            if self._size_op == '<' and file_size >= self._size_limit:
                return False
        
        if self._date_limit.isValid() and file_info.lastModified() < self._date_limit:
            return False

        return True

class FolderStatsThread(QThread):
    """Thread para calcular tamanho de pasta sem travar a UI."""
    stats_ready = Signal(str, int, float) # path, count, size_gb

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._is_running = True

    def run(self):
        total_size = 0
        file_count = 0
        try:
            for dirpath, _, filenames in os.walk(self.path):
                if not self._is_running: return
                file_count += len(filenames)
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except:
            pass
        
        size_gb = total_size / (1024 * 1024 * 1024)
        self.stats_ready.emit(self.path, file_count, size_gb)

    def stop(self):
        self._is_running = False

class TasmaFileView(QWidget):
    """Área principal de visualização de arquivos."""
    
    path_selected = Signal(str)
    path_confirmed = Signal(str) # Double click ou Enter
    status_updated = Signal(str) # Envia texto para a barra de status
    preview_toggled = Signal(bool)
    

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = {}
        self._clipboard_path = None
        self._stats_thread = None
        self._history = []
        self._future = []
        self._is_navigating_history = False
        self._search_thread = None
        self._is_search_mode = False
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Barra Superior ---
        top_bar_widget = QWidget()
        top_bar_layout = QVBoxLayout(top_bar_widget)
        top_bar_layout.setContentsMargins(10, 10, 10, 5)
        top_bar_layout.setSpacing(8)

        # Linha 1: Navegação e Endereço
        nav_layout = QHBoxLayout()
        self.btn_back = QPushButton()
        self.btn_back.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        self.btn_back.setFixedSize(32, 32)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setToolTip("Voltar")
        self.btn_back.clicked.connect(self.go_back)
        self.btn_back.setEnabled(False)

        self.btn_forward = QPushButton()
        self.btn_forward.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowForward))
        self.btn_forward.setFixedSize(32, 32)
        self.btn_forward.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forward.setToolTip("Avançar")
        self.btn_forward.clicked.connect(self.go_forward)
        self.btn_forward.setEnabled(False)

        self.address_bar = QLineEdit()
        self.address_bar.setReadOnly(True)
        self.address_bar.setFixedHeight(32)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar no conteúdo...")
        self.search_input.setFixedHeight(32)
        self.search_input.returnPressed.connect(self._start_content_search)

        self.btn_clear_search = QPushButton()
        self.btn_clear_search.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        self.btn_clear_search.setFixedSize(32, 32)
        self.btn_clear_search.setToolTip("Limpar busca e voltar à navegação")
        self.btn_clear_search.clicked.connect(self._clear_search)
        self.btn_clear_search.hide()

        nav_layout.addWidget(self.btn_back)
        nav_layout.addWidget(self.btn_forward)
        nav_layout.addWidget(self.address_bar, 1)
        nav_layout.addWidget(self.search_input, 1)
        nav_layout.addWidget(self.btn_clear_search)
        top_bar_layout.addLayout(nav_layout)

        # Linha 2: Controles de Visualização
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 5, 0, 0)

        self.btn_toggle_view = QPushButton()
        self.btn_toggle_view.setFixedSize(32, 32)
        self.btn_toggle_view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_view.clicked.connect(self._toggle_view_mode)

        self.btn_toggle_filters = QPushButton()
        self.btn_toggle_filters.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView))
        self.btn_toggle_filters.setFixedSize(32, 32)
        self.btn_toggle_filters.setCheckable(True)
        self.btn_toggle_filters.setToolTip("Mostrar/Ocultar Filtros Avançados")
        self.btn_toggle_filters.clicked.connect(self._toggle_filters_panel)

        self.btn_toggle_preview = QPushButton()
        self.btn_toggle_preview.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))
        self.btn_toggle_preview.setFixedSize(32, 32)
        self.btn_toggle_preview.setCheckable(True)
        self.btn_toggle_preview.setChecked(True)
        self.btn_toggle_preview.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_preview.setToolTip("Alternar Painel de Pré-visualização")
        self.btn_toggle_preview.clicked.connect(self.preview_toggled.emit)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Nome", "Tamanho", "Data de Modificação"])
        self.sort_combo.currentIndexChanged.connect(self._on_sort_changed)

        self.btn_sort_order = QPushButton()
        self.btn_sort_order.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        self.btn_sort_order.setFixedSize(32, 32)
        self.btn_sort_order.setCheckable(True)
        self.btn_sort_order.setToolTip("Ordem Ascendente/Descendente")
        self.btn_sort_order.clicked.connect(self._on_sort_changed)

        controls_layout.addWidget(self.btn_toggle_view)
        controls_layout.addWidget(self.btn_toggle_filters)
        controls_layout.addWidget(self.btn_toggle_preview)
        controls_layout.addWidget(QLabel("Ordenar por:"))
        controls_layout.addWidget(self.sort_combo)
        controls_layout.addWidget(self.btn_sort_order)
        controls_layout.addStretch()

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(32, 128) # Tamanho do ícone
        self.zoom_slider.setValue(48)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self._on_zoom_changed)
        
        controls_layout.addWidget(QLabel("Zoom:"))
        controls_layout.addWidget(self.zoom_slider)
        top_bar_layout.addLayout(controls_layout)

        layout.addWidget(top_bar_widget)

        # --- Painel de Filtros Avançados ---
        self.filters_widget = QFrame()
        self.filters_widget.setObjectName("FiltersFrame")
        filters_layout = QHBoxLayout(self.filters_widget)
        filters_layout.setContentsMargins(10, 5, 10, 5)
        filters_layout.setSpacing(10)

        filters_layout.addWidget(QLabel("Extensão:"))
        self.filter_ext_input = QLineEdit()
        self.filter_ext_input.setPlaceholderText(".py")
        self.filter_ext_input.setFixedWidth(80)
        filters_layout.addWidget(self.filter_ext_input)

        filters_layout.addWidget(QLabel("Tamanho:"))
        self.filter_size_op = QComboBox()
        self.filter_size_op.addItems([">", "<"])
        self.filter_size_op.setFixedWidth(50)
        filters_layout.addWidget(self.filter_size_op)
        self.filter_size_val = QSpinBox()
        self.filter_size_val.setRange(0, 9999)
        filters_layout.addWidget(self.filter_size_val)
        self.filter_size_unit = QComboBox()
        self.filter_size_unit.addItems(["KB", "MB", "GB"])
        filters_layout.addWidget(self.filter_size_unit)

        filters_layout.addWidget(QLabel("Data Modif.:"))
        self.filter_date_combo = QComboBox()
        self.filter_date_combo.addItems(["Qualquer", "Últimas 24h", "Últimos 7 dias", "Últimos 30 dias"])
        filters_layout.addWidget(self.filter_date_combo)

        filters_layout.addStretch()
        layout.addWidget(self.filters_widget)
        self.filters_widget.hide()

        # --- Barra de Favoritos Rápidos ---
        self.favorites_container = QWidget()
        self.favorites_container.setFixedHeight(45)
        fav_layout_outer = QHBoxLayout(self.favorites_container)
        fav_layout_outer.setContentsMargins(10, 0, 10, 5)
        
        self.favorites_scroll = QScrollArea()
        self.favorites_scroll.setWidgetResizable(True)
        self.favorites_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.favorites_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.favorites_scroll.setStyleSheet("background: transparent; border: none;")
        self.favorites_scroll.setFixedHeight(40)
        
        self.favorites_content = QWidget()
        self.favorites_layout = QHBoxLayout(self.favorites_content)
        self.favorites_layout.setContentsMargins(0, 0, 0, 0)
        self.favorites_layout.setSpacing(8)
        self.favorites_layout.setAlignment(Qt.AlignLeft)
        
        self.favorites_scroll.setWidget(self.favorites_content)
        fav_layout_outer.addWidget(self.favorites_scroll)
        
        layout.addWidget(self.favorites_container)
        self.favorites_container.hide() # Oculta se não houver favoritos

        # Modelo de Arquivos
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot)
        self.model.setRootPath(QDir.rootPath())
        self.model.setReadOnly(False) # Habilita operações de arquivo (Drag & Drop)
        self.model.directoryLoaded.connect(self._on_directory_loaded)
        
        self.proxy_model = AdvancedFileFilterProxyModel(self)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        self.proxy_model.setSourceModel(self.model)
        
        # List View (Modo Ícones / Grid)
        self.list_view = QListView()
        self.list_view.setModel(self.proxy_model)
        self.list_view.setRootIndex(self.proxy_model.mapFromSource(self.model.index(QDir.homePath())))
        
        # Context Menu
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self._show_context_menu)
        
        # Configuração de Drag & Drop
        self.list_view.setDragEnabled(True)
        self.list_view.setAcceptDrops(True)
        self.list_view.setDropIndicatorShown(True)
        self.list_view.setDragDropMode(QAbstractItemView.DragDrop)
        self.list_view.setDefaultDropAction(Qt.MoveAction)
        
        # Tooltips e Mouse Tracking
        self.list_view.setMouseTracking(True)
        self.list_view.entered.connect(self._on_item_entered)
        self.list_view.installEventFilter(self) # Para atalhos de teclado
        
        # Inicia no modo Grade
        self._set_icon_mode()
        
        self.list_view.doubleClicked.connect(self._on_double_click)
        self.list_view.clicked.connect(self._on_click)
        
        # Conexões dos filtros
        self.filter_ext_input.textChanged.connect(self._apply_filters)
        self.filter_size_op.currentIndexChanged.connect(self._apply_filters)
        self.filter_size_val.valueChanged.connect(self._apply_filters)
        self.filter_size_unit.currentIndexChanged.connect(self._apply_filters)
        self.filter_date_combo.currentIndexChanged.connect(self._apply_filters)
        
        # Stack para alternar entre Navegador e Busca
        self.view_stack = QStackedWidget()
        self.search_results_view = QListWidget()
        self.search_results_view.itemDoubleClicked.connect(self._on_search_result_activated)

        self.view_stack.addWidget(self.list_view)
        self.view_stack.addWidget(self.search_results_view)

        layout.addWidget(self.view_stack)

    def _set_icon_mode(self):
        """Configura visualização em grade (ícones grandes)."""
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setGridSize(QSize(100, 100))
        self.list_view.setIconSize(QSize(48, 48))
        self.list_view.setUniformItemSizes(True)
        self.list_view.setWordWrap(True)
        self.list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.zoom_slider.show()
        self.btn_toggle_view.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView))
        self.btn_toggle_view.setToolTip("Mudar para Lista")

    def _set_list_mode(self):
        """Configura visualização em lista (detalhes compactos)."""
        self.list_view.setViewMode(QListView.ListMode)
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setGridSize(QSize()) # Reseta grid
        self.list_view.setIconSize(QSize(16, 16))
        self.list_view.setUniformItemSizes(False)
        self.list_view.setWordWrap(False)
        self.zoom_slider.hide()
        self.btn_toggle_view.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        self.btn_toggle_view.setToolTip("Mudar para Grade")

    def _toggle_view_mode(self):
        if self.list_view.viewMode() == QListView.IconMode:
            self._set_list_mode()
        else:
            self._set_icon_mode()

    def go_back(self):
        if not self._history:
            return
        self._is_navigating_history = True
        current_path = self.model.rootPath()
        self._future.append(current_path)
        self.set_path(self._history.pop())
        self._is_navigating_history = False

    def go_forward(self):
        if not self._future:
            return
        self._is_navigating_history = True
        current_path = self.model.rootPath()
        self._history.append(current_path)
        self.set_path(self._future.pop())
        self._is_navigating_history = False

    def _on_sort_changed(self):
        sort_map = {0: 0, 1: 1, 2: 3} # Nome, Tamanho, Data
        column = sort_map.get(self.sort_combo.currentIndex(), 0) # Padrão para Nome
        
        is_descending = self.btn_sort_order.isChecked()
        order = Qt.SortOrder.DescendingOrder if is_descending else Qt.SortOrder.AscendingOrder
        self.btn_sort_order.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp if is_descending else QStyle.StandardPixmap.SP_ArrowDown))
        
        self.proxy_model.sort(column, order)
        if self._is_search_mode:
            self._clear_search()

    def _on_zoom_changed(self, value):
        if self.list_view.viewMode() == QListView.IconMode:
            self.list_view.setIconSize(QSize(value, value))
            self.list_view.setGridSize(QSize(value + 20, value + 40))

    def _toggle_filters_panel(self, checked):
        self.filters_widget.setVisible(checked)

    def _apply_filters(self):
        if self._is_search_mode: self._clear_search()

        if not hasattr(self, 'proxy_model'): return

        self.proxy_model.set_extension_filter(self.filter_ext_input.text())

        if self.filter_size_val.value() > 0:
            self.proxy_model.set_size_filter(
                self.filter_size_op.currentText(),
                self.filter_size_val.value(),
                self.filter_size_unit.currentText()
            )
        else:
            self.proxy_model.set_size_filter(">", -1, "B")

        date_map = {"Qualquer": "Any", "Últimas 24h": "Last 24h", "Últimos 7 dias": "Last 7 days", "Últimos 30 dias": "Last 30 days"}
        self.proxy_model.set_date_filter(date_map[self.filter_date_combo.currentText()])

    def update_favorites(self, favorites):
        """Atualiza a barra de favoritos rápidos."""
        # Limpa itens existentes
        while self.favorites_layout.count():
            child = self.favorites_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not favorites:
            self.favorites_container.hide()
            return
            
        self.favorites_container.show()
        
        for name, path in favorites.items():
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(path)
            btn.clicked.connect(lambda checked=False, p=path: self.set_path(p))
            self.favorites_layout.addWidget(btn)
            
        if self.theme:
            self.apply_theme(self.theme)

    def apply_theme(self, theme):
        self.theme = theme
        bg = theme.get("background", "#1e1e1e")
        fg = theme.get("foreground", "#cccccc")
        input_bg = theme.get("sidebar_bg", "#3c3c3c")
        border = theme.get("border_color", "#454545")
        selection = theme.get("selection", "#094771")
        accent = theme.get("accent", "#007acc")
        
        self.address_bar.setStyleSheet(f"background-color: {input_bg}; color: {fg}; padding: 8px; border: 1px solid {border}; border-radius: 4px;")
        
        tool_button_style = f"""QPushButton {{ 
            background-color: transparent; 
            border: 1px solid transparent; 
            border-radius: 4px; 
        }}
            QPushButton:hover {{ background-color: {border}; }}
            QPushButton:checked {{ background-color: {selection}; border: 1px solid {accent}; }}
            QPushButton:disabled {{ color: #555; }}"""
        self.btn_back.setStyleSheet(tool_button_style)
        self.btn_forward.setStyleSheet(tool_button_style)
        self.btn_toggle_view.setStyleSheet(tool_button_style)
        self.btn_toggle_filters.setStyleSheet(tool_button_style)
        self.btn_toggle_preview.setStyleSheet(tool_button_style)
        self.btn_sort_order.setStyleSheet(tool_button_style)
        self.btn_clear_search.setStyleSheet(tool_button_style)

        self.filters_widget.setStyleSheet(f"QFrame#FiltersFrame {{ background-color: {input_bg}; border-top: 1px solid {border}; }}")
        filter_input_style = f"background-color: {bg}; color: {fg}; border: 1px solid {border}; padding: 4px; border-radius: 4px;"
        self.filter_ext_input.setStyleSheet(filter_input_style)
        self.filter_size_op.setStyleSheet(filter_input_style)
        self.filter_size_val.setStyleSheet(filter_input_style)
        self.filter_size_unit.setStyleSheet(filter_input_style)
        self.filter_date_combo.setStyleSheet(filter_input_style)
        
        self.search_input.setStyleSheet(f"background-color: {input_bg}; color: {fg}; padding: 8px; border: 1px solid {border}; border-radius: 4px;")

        self.sort_combo.setStyleSheet(f"QComboBox {{ background-color: {input_bg}; color: {fg}; border: 1px solid {border}; padding: 4px; border-radius: 4px; }}")
        self.zoom_slider.setStyleSheet("QSlider::groove:horizontal { border: 1px solid #bbb; background: white; height: 10px; border-radius: 4px; } QSlider::handle:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #eee, stop:1 #ccc); border: 1px solid #777; width: 18px; margin: -2px 0; border-radius: 4px; }")
        
        # Estilo dos botões de favoritos (Chips)
        fav_btn_style = f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {border};
                border-radius: 14px;
                padding: 4px 12px;
                color: {fg};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: white;
                border: 1px solid {accent};
            }}
        """
        for i in range(self.favorites_layout.count()):
            widget = self.favorites_layout.itemAt(i).widget()
            if widget:
                widget.setStyleSheet(fav_btn_style)
        
        self.list_view.setStyleSheet(f"""
            QListView {{ background-color: {bg}; color: {fg}; border: none; outline: none; }}
            QListView::item {{ padding: 5px; border-radius: 4px; margin: 2px; }}
            QListView::item:selected {{ background-color: {selection}; color: white; border: 1px solid {accent}; }}
            QListView::item:hover {{ background-color: {border}; }}
        """)
        
        self.search_results_view.setStyleSheet(f"""
            QListWidget {{ background-color: {bg}; color: {fg}; border: none; outline: none; }}
            QListWidget::item {{ border-bottom: 1px solid {border}; }}
            QListWidget::item:selected {{ background-color: {selection}; border-left: 2px solid {accent}; }}
            QListWidget::item:hover {{ background-color: {border}; }}
        """)

    def set_path(self, path):
        # Ao navegar, sempre cancela o modo de busca
        if self._is_search_mode:
            self._clear_search()

        if path == "plugins_virtual_root":
            path = QDir.homePath()
            
        # History management
        if not self._is_navigating_history:
            old_path = self.model.rootPath()
            if old_path != path and os.path.exists(old_path):
                self._history.append(old_path)
                self._future.clear() # Clear forward history on new navigation
        
        self.btn_back.setEnabled(bool(self._history))
        self.btn_forward.setEnabled(bool(self._future))
        
        self.address_bar.setText(path)
        source_idx = self.model.setRootPath(path)
        proxy_idx = self.proxy_model.mapFromSource(source_idx)
        self.list_view.setRootIndex(proxy_idx)

    def _on_click(self, index):
        source_index = self.proxy_model.mapToSource(index)
        path = self.model.filePath(source_index)
        self.path_selected.emit(path)

    def _on_double_click(self, index):
        source_index = self.proxy_model.mapToSource(index)
        path = self.model.filePath(source_index)
        if self.model.isDir(source_index):
            self.set_path(path)
        else:
            self.path_confirmed.emit(path)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        proxy_index = self.list_view.indexAt(pos)
        
        # Apply theme
        bg = self.theme.get("background", "#1e1e1e")
        fg = self.theme.get("foreground", "#cccccc")
        accent = self.theme.get("accent", "#007acc")
        menu.setStyleSheet(f"QMenu {{ background-color: {bg}; color: {fg}; }} QMenu::item:selected {{ background-color: {accent}; }}")
        
        if proxy_index.isValid():
            source_index = self.proxy_model.mapToSource(proxy_index)
            path = self.model.filePath(source_index)
            
            rename_action = menu.addAction("Renomear")
            rename_action.triggered.connect(lambda: self._rename_item(path))
            
            delete_action = menu.addAction("Excluir")
            delete_action.triggered.connect(lambda: self._delete_item(path))
            
            menu.addSeparator()
            
            copy_action = menu.addAction("Copiar (Ctrl+C)")
            copy_action.triggered.connect(self._copy_selection)
        
        new_file = menu.addAction("Novo Arquivo")
        new_file.triggered.connect(lambda: self._create_item(is_folder=False))
        
        new_folder = menu.addAction("Nova Pasta")
        new_folder.triggered.connect(lambda: self._create_item(is_folder=True))
        
        if self._clipboard_path and os.path.exists(self._clipboard_path):
            menu.addSeparator()
            paste_action = menu.addAction("Colar (Ctrl+V)")
            paste_action.triggered.connect(self._paste_to_current)
        
        menu.exec(self.list_view.mapToGlobal(pos))

    def _create_item(self, is_folder):
        current_dir = self.model.rootPath()
        type_str = "Pasta" if is_folder else "Arquivo"
        name, ok = QInputDialog.getText(self, f"Nova {type_str}", f"Nome da {type_str}:")
        if ok and name:
            try:
                if is_folder: FileManager.create_directory(current_dir, name)
                else: FileManager.create_file(current_dir, name)
            except Exception as e:
                QMessageBox.critical(self, "Erro", str(e))

    def _rename_item(self, path):
        old_name = os.path.basename(path)
        dir_path = os.path.dirname(path)
        
        name, ok = QInputDialog.getText(self, "Renomear", "Novo nome:", text=old_name)
        if ok and name and name != old_name:
            new_path = os.path.join(dir_path, name)
            try:
                os.rename(path, new_path)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao renomear: {e}")

    def _delete_item(self, path):
        name = os.path.basename(path)
        reply = QMessageBox.question(self, "Excluir", f"Tem certeza que deseja excluir '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao excluir: {e}")

    def _copy_selection(self):
        proxy_index = self.list_view.currentIndex()
        if proxy_index.isValid():
            source_index = self.proxy_model.mapToSource(proxy_index)
            self._clipboard_path = self.model.filePath(source_index)
            self.status_updated.emit(f"Copiado: {os.path.basename(self._clipboard_path)}")

    def _paste_to_current(self):
        if not self._clipboard_path or not os.path.exists(self._clipboard_path):
            return
            
        dest_dir = self.proxy_model.rootPath()
        src_name = os.path.basename(self._clipboard_path)
        dest_path = os.path.join(dest_dir, src_name)

        # Evita sobrescrever
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(src_name)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_dir, f"{base}_copy{counter}{ext}")
                counter += 1

        try:
            if os.path.isdir(self._clipboard_path):
                shutil.copytree(self._clipboard_path, dest_path)
            else:
                shutil.copy2(self._clipboard_path, dest_path)
            self.status_updated.emit(f"Colado: {os.path.basename(dest_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao colar: {e}")

    def _delete_selection(self):
        proxy_index = self.list_view.currentIndex()
        if proxy_index.isValid():
            source_index = self.proxy_model.mapToSource(proxy_index)
            self._delete_item(self.model.filePath(source_index))

    def eventFilter(self, obj, event):
        if obj == self.list_view and event.type() == QEvent.Type.KeyPress:
            if event.matches(QKeySequence.Copy):
                self._copy_selection()
                return True
            elif event.matches(QKeySequence.Paste):
                self._paste_to_current()
                return True
            elif event.key() == Qt.Key.Key_Delete:
                self._delete_selection()
                return True
        return super().eventFilter(obj, event)

    def _on_directory_loaded(self, path):
        """Atualiza a barra de status com contagem e espaço em disco."""
        source_index = self.model.index(path)
        proxy_index = self.proxy_model.mapFromSource(source_index)
        count = self.proxy_model.rowCount(proxy_index)
        try:
            total, used, free = shutil.disk_usage(path)
            free_gb = free / (1024**3)
            self.status_updated.emit(f"{count} itens | Livre: {free_gb:.2f} GB")
        except:
            self.status_updated.emit(f"{count} itens")

    def _on_item_entered(self, index):
        """Mostra tooltip com informações da pasta."""
        if not index.isValid(): return
        source_index = self.proxy_model.mapToSource(index)
        
        if self.model.isDir(source_index):
            path = self.model.filePath(source_index)
            
            # Cancela thread anterior se existir
            if self._stats_thread and self._stats_thread.isRunning():
                self._stats_thread.stop()
                self._stats_thread.wait()
            
            self._stats_thread = FolderStatsThread(path)
            self._stats_thread.stats_ready.connect(self._show_folder_tooltip)
            self._stats_thread.start()
            
            QToolTip.showText(QCursor.pos(), "Calculando...", self.list_view)

    def _show_folder_tooltip(self, path, count, size_gb):
        text = f"<b>{os.path.basename(path)}</b><br>Arquivos: {count}<br>Tamanho: {size_gb:.2f} GB"
        # Verifica se o mouse ainda está sobre o item (opcional, mas bom para UX)
        QToolTip.showText(QCursor.pos(), text, self.list_view)

    def _start_content_search(self):
        query = self.search_input.text()
        if not query:
            self._clear_search()
            return

        if self._search_thread and self._search_thread.isRunning():
            self._search_thread.stop()
            self._search_thread.wait()

        self.status_updated.emit(f"Buscando por '{query}'...")
        self.search_results_view.clear()
        self.view_stack.setCurrentWidget(self.search_results_view)
        self._is_search_mode = True
        self.btn_clear_search.show()
        
        current_dir = self.model.rootPath()
        self._search_thread = FileSearchEngine(current_dir, query)
        self._search_thread.match_found.connect(self._add_search_result)
        self._search_thread.progress_updated.connect(self.status_updated)
        self._search_thread.search_finished.connect(self._finish_search)
        self._search_thread.start()

    def _clear_search(self):
        if self._search_thread and self._search_thread.isRunning():
            self._search_thread.stop()
        
        self.search_input.clear()
        self.view_stack.setCurrentWidget(self.list_view)
        self._is_search_mode = False
        self.btn_clear_search.hide()
        self._on_directory_loaded(self.model.rootPath())

    def _add_search_result(self, filepath, line_num, line_content):
        item = QListWidgetItem()
        item.setData(Qt.UserRole, (filepath, line_num))
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 3, 5, 3)
        
        filename = os.path.basename(filepath)
        relative_path = os.path.relpath(os.path.dirname(filepath), self.model.rootPath())
        path_text = filename if relative_path == '.' else os.path.join(relative_path, filename)

        lbl_path = QLabel(path_text)
        lbl_path.setStyleSheet("font-weight: bold; background: transparent;")
        
        lbl_content = QLabel(f"<span style='color:#888;'>{line_num}: </span>{line_content}")
        lbl_content.setStyleSheet("background: transparent;")
        
        layout.addWidget(lbl_path)
        layout.addWidget(lbl_content)
        
        item.setSizeHint(widget.sizeHint())
        self.search_results_view.addItem(item)
        self.search_results_view.setItemWidget(item, widget)

    def _finish_search(self, match_count):
        self.status_updated.emit(f"Busca concluída. {match_count} resultados encontrados.")

    def _on_search_result_activated(self, item):
        filepath, line_num = item.data(Qt.UserRole)
        self.path_confirmed.emit(filepath)
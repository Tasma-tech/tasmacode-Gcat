from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit,
                               QTreeView, QFileSystemModel, QHBoxLayout, 
                               QStackedWidget, QFrame, QStyle, QMenu, QMessageBox, QInputDialog, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal, QDir, QEvent, QSortFilterProxyModel, QRegularExpression
from PySide6.QtGui import QIcon
import os
import shutil
from src.core.editor_logic.file_manager import FileManager

class FileFilterProxyModel(QSortFilterProxyModel):
    """Proxy model to ignore specific files/folders and filter by text."""
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

class Sidebar(QWidget):
    """Barra lateral para explorador de arquivos e ferramentas."""
    
    # Sinais para desacoplar a lógica
    open_folder_clicked = Signal()
    open_project_clicked = Signal()
    file_clicked = Signal(str) # Envia o caminho do arquivo
    file_created = Signal(str) # Novo arquivo criado
    status_message = Signal(str, int) # Mensagem para statusbar (msg, timeout)
    marker_clicked = Signal(str, int) # Envia caminho do arquivo e número da linha

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar") # Para estilização via QSS
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # --- Toolbar de Ações Rápidas ---
        self.toolbar = QFrame()
        self.toolbar.setFixedHeight(30)
        tb_layout = QHBoxLayout(self.toolbar)
        tb_layout.setContentsMargins(5, 0, 5, 0)
        
        # Botões simples (ícones padrão do Qt para garantir compatibilidade)
        self.btn_new_file = self._create_action_btn(QStyle.StandardPixmap.SP_FileIcon, "Novo Arquivo")
        self.btn_new_folder = self._create_action_btn(QStyle.StandardPixmap.SP_DirIcon, "Nova Pasta")
        self.btn_refresh = self._create_action_btn(QStyle.StandardPixmap.SP_BrowserReload, "Recarregar")
        self.btn_open_project = self._create_action_btn(QStyle.StandardPixmap.SP_FileDialogNewFolder, "Abrir Projeto")
        self.btn_toggle_view = self._create_action_btn(QStyle.StandardPixmap.SP_FileDialogDetailedView, "Alternar Marcadores")
        
        self.btn_new_file.clicked.connect(lambda: self._start_creation(is_folder=False))
        self.btn_new_folder.clicked.connect(lambda: self._start_creation(is_folder=True))
        self.btn_refresh.clicked.connect(self._refresh_tree)
        self.btn_open_project.clicked.connect(self.open_project_clicked.emit)
        self.btn_toggle_view.clicked.connect(self._toggle_view_mode)

        self.lbl_title = QLabel("EXPLORER")
        tb_layout.addWidget(self.lbl_title)
        tb_layout.addStretch()
        tb_layout.addWidget(self.btn_toggle_view)
        tb_layout.addWidget(self.btn_open_project)
        tb_layout.addWidget(self.btn_new_file)
        tb_layout.addWidget(self.btn_new_folder)
        tb_layout.addWidget(self.btn_refresh)
        
        self.layout.addWidget(self.toolbar)

        # --- Filtro de Busca ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar arquivos (Ctrl+Shift+F)")
        self.search_input.setStyleSheet("padding: 4px; background-color: #3c3c3c; border: none; margin: 0 5px 5px 5px;")
        self.search_input.textChanged.connect(self._on_filter_text_changed)
        self.search_input.installEventFilter(self)
        self.layout.addWidget(self.search_input)

        # --- Área Principal (Stack) ---
        self.stack = QStackedWidget()
        self.layout.addWidget(self.stack)

        # Estado 1: Vazio
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_open = QPushButton("Abrir Pasta")
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.setStyleSheet("background-color: #007acc; color: white; padding: 8px 16px; border-radius: 4px; border: none;")
        self.btn_open.clicked.connect(self.open_folder_clicked.emit)
        
        empty_layout.addWidget(QLabel("Nenhuma pasta aberta"))
        empty_layout.addWidget(self.btn_open)
        self.stack.addWidget(self.empty_state)

        # Estado 2: Árvore de Arquivos
        self.file_model = QFileSystemModel()
        self.file_model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.file_model.setRootPath(QDir.homePath())
        self.file_model.setReadOnly(False) # Permite operações de escrita (Drag & Drop)
        
        # Modelo de proxy para filtragem
        self.filter_proxy_model = FileFilterProxyModel()
        self.filter_proxy_model.setSourceModel(self.file_model)
        self.filter_proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.filter_proxy_model.setRecursiveFilteringEnabled(True)
        
        self.tree = QTreeView()
        self.tree.setModel(self.filter_proxy_model)
        self.tree.setRootIndex(self.filter_proxy_model.mapFromSource(self.file_model.index(QDir.homePath())))
        self.tree.setHeaderHidden(True)
        self.tree.setColumnHidden(1, True) # Size
        self.tree.setColumnHidden(2, True) # Type
        self.tree.setColumnHidden(3, True) # Date
        
        # Configuração de Drag and Drop
        self.tree.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QTreeView.DragDropMode.DragDrop)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.tree.setAnimated(True)
        
        self.tree.doubleClicked.connect(self._on_tree_double_click)
        
        # Menu de Contexto
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        
        self.stack.addWidget(self.tree)
        
        # Estado 3: Lista de Marcadores
        self.markers_list = QListWidget()
        self.markers_list.setStyleSheet("background-color: #252526; color: #cccccc; border: none;")
        self.markers_list.itemClicked.connect(self._on_marker_item_clicked)
        self.markers_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.markers_list.customContextMenuRequested.connect(self._show_marker_context_menu)
        self.stack.addWidget(self.markers_list)
        
        # --- Inline Input para Criação ---
        self.input_edit = QLineEdit(self.tree)
        self.input_edit.hide()
        self.input_edit.returnPressed.connect(self._on_input_return)
        self.input_edit.installEventFilter(self)
        self.input_edit.setStyleSheet("background-color: #3c3c3c; color: white; border: 1px solid #007acc;")
        
        # Estado interno
        self._creating_folder = False
        self._creation_base_path = ""
        
        # Clipboard interno para arquivos
        self._clipboard_path = None

    def _create_action_btn(self, icon_std, tooltip):
        btn = QPushButton()
        btn.setIcon(self.style().standardIcon(icon_std))
        btn.setToolTip(tooltip)
        btn.setObjectName("SidebarAction")
        btn.setFixedSize(24, 24)
        return btn

    def _toggle_view_mode(self):
        """Alterna entre a árvore de arquivos e a lista de marcadores."""
        if self.stack.currentWidget() == self.markers_list:
            self.stack.setCurrentWidget(self.tree)
            self.lbl_title.setText("EXPLORER")
            self.search_input.setPlaceholderText("Filtrar arquivos (Ctrl+Shift+F)")
            self.search_input.show()
        else:
            self.stack.setCurrentWidget(self.markers_list)
            self.lbl_title.setText("MARCADORES")
            self.search_input.setPlaceholderText("Filtrar marcadores...")
            self.search_input.show()
            self.search_input.clear()

    def update_markers(self, global_markers):
        """Atualiza a lista de marcadores globais.
        Args:
            global_markers: lista de tuplas (file_path, line, marker)
        """
        self.markers_list.clear()
        if not global_markers:
            return
            
        # Ordena por caminho do arquivo e depois por linha
        sorted_markers = sorted(global_markers, key=lambda x: (x[0], x[1]))
        
        for file_path, line, marker in sorted_markers:
            file_name = os.path.basename(file_path)
            label = f"{file_name} : {line + 1}"
            if marker.label:
                label += f" - {marker.label}"
            
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, (file_path, line))
            item.setToolTip(file_path)
            self.markers_list.addItem(item)
            
        if self.search_input.text():
            self._filter_markers(self.search_input.text())

    def _on_marker_item_clicked(self, item):
        data = item.data(Qt.UserRole)
        if data:
            file_path, line = data
            self.marker_clicked.emit(file_path, line)

    def _show_marker_context_menu(self, pos):
        item = self.markers_list.itemAt(pos)
        if not item: return
        
        file_path, line = item.data(Qt.UserRole)
        
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #252526; color: #cccccc; border: 1px solid #454545; } QMenu::item:selected { background-color: #007acc; }")
        
        action_go = menu.addAction("Ir para Linha")
        action_go.triggered.connect(lambda: self.marker_clicked.emit(file_path, line))
        
        menu.exec(self.markers_list.mapToGlobal(pos))

    def set_root_path(self, path: str):
        """Define a pasta raiz da árvore."""
        self.stack.setCurrentWidget(self.tree)
        source_index = self.file_model.setRootPath(path)
        proxy_index = self.filter_proxy_model.mapFromSource(source_index)
        self.tree.setRootIndex(proxy_index)

    def focus_search(self):
        """Foca na barra de busca da sidebar."""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _on_tree_double_click(self, index):
        source_index = self.filter_proxy_model.mapToSource(index)
        path = self.file_model.filePath(source_index)
        if not self.file_model.isDir(source_index):
            self.file_clicked.emit(path)

    def _get_current_path(self):
        """Retorna o diretório base para criação (pasta selecionada ou pai do arquivo)."""
        proxy_index = self.tree.currentIndex()
        source_index = self.filter_proxy_model.mapToSource(proxy_index)
        root = self.file_model.rootPath()
        
        if not source_index.isValid():
            return root
            
        path = self.file_model.filePath(source_index)
        if self.file_model.isDir(source_index):
            return path
        else:
            return os.path.dirname(path)

    def _on_filter_text_changed(self, text: str):
        if self.stack.currentWidget() == self.tree:
            self.filter_proxy_model.setFilterWildcard(f"*{text}*")
        elif self.stack.currentWidget() == self.markers_list:
            self._filter_markers(text)

    def _filter_markers(self, text: str):
        text = text.lower()
        for i in range(self.markers_list.count()):
            item = self.markers_list.item(i)
            # Filtra pelo texto do item (que contém linha e tag)
            item.setHidden(text not in item.text().lower())

    def _start_creation(self, is_folder: bool):
        """Inicia o processo de criação mostrando o input."""
        if self.stack.currentWidget() != self.tree:
            return # Não faz nada se estiver no estado vazio
            
        self._creating_folder = is_folder
        self._creation_base_path = self._get_current_path()
        
        # Posicionamento do Input
        proxy_index = self.tree.currentIndex()
        rect = self.tree.visualRect(proxy_index)
        
        # Se não houver seleção ou rect inválido, posiciona no topo
        if not rect.isValid():
            rect = self.tree.viewport().rect()
            rect.setHeight(24)
            y_pos = 0
        else:
            # Posiciona logo abaixo do item selecionado
            y_pos = rect.bottom()
            
        self.input_edit.move(0, y_pos)
        self.input_edit.setFixedSize(self.tree.width(), 24)
        self.input_edit.setPlaceholderText(f"Nome do {'Diretório' if is_folder else 'Arquivo'} (Enter para criar)")
        self.input_edit.clear()
        self.input_edit.show()
        self.input_edit.setFocus()

    def _on_input_return(self):
        """Processa a criação quando Enter é pressionado."""
        name = self.input_edit.text().strip()
        if not name:
            self.input_edit.hide()
            return
            
        try:
            if self._creating_folder:
                FileManager.create_directory(self._creation_base_path, name)
                self.status_message.emit(f"Pasta criada: {name}", 3000)
            else:
                full_path = FileManager.create_file(self._creation_base_path, name)
                self.status_message.emit(f"Arquivo criado: {name}", 3000)
                self.file_created.emit(full_path)
        except PermissionError:
            self.status_message.emit("Erro de Permissão: Acesso negado ao criar neste local.", 5000)
        except Exception as e:
            self.status_message.emit(f"Erro: {str(e)}", 5000)
        
        self.input_edit.hide()

    def _refresh_tree(self):
        # QFileSystemModel atualiza automaticamente, mas podemos forçar re-scan se necessário
        pass

    def eventFilter(self, obj, event):
        if hasattr(self, 'input_edit') and obj == self.input_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.input_edit.hide()
                return True
        if obj == self.search_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.search_input.clear()
                return True
        return super().eventFilter(obj, event)

    def _show_context_menu(self, position):
        proxy_index = self.tree.indexAt(position)
        if not proxy_index.isValid():
            return

        source_index = self.filter_proxy_model.mapToSource(proxy_index)
        path = self.file_model.filePath(source_index)
        menu = QMenu()

        # Ações de Arquivo
        rename_action = menu.addAction("Renomear")
        rename_action.triggered.connect(lambda: self._rename_item(path))

        delete_action = menu.addAction("Excluir")
        delete_action.triggered.connect(lambda: self._delete_item(path))

        menu.addSeparator()

        copy_action = menu.addAction("Copiar")
        copy_action.triggered.connect(lambda: self._copy_item(path))

        paste_action = menu.addAction("Colar")
        # Habilita colar apenas se houver algo na área de transferência e o destino for válido
        paste_action.setEnabled(bool(self._clipboard_path and os.path.exists(self._clipboard_path)))
        paste_action.triggered.connect(lambda: self._paste_item(path))

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _rename_item(self, path):
        old_name = os.path.basename(path)
        dir_path = os.path.dirname(path)
        
        new_name, ok = QInputDialog.getText(self, "Renomear", "Novo nome:", text=old_name)
        if ok and new_name and new_name != old_name:
            new_path = os.path.join(dir_path, new_name)
            try:
                os.rename(path, new_path)
                self.status_message.emit(f"Renomeado para: {new_name}", 3000)
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
                self.status_message.emit(f"Excluído: {name}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Erro ao excluir: {e}")

    def _copy_item(self, path):
        self._clipboard_path = path
        self.status_message.emit(f"Copiado: {os.path.basename(path)}", 2000)

    def _paste_item(self, target_path):
        if not self._clipboard_path or not os.path.exists(self._clipboard_path):
            return

        # Se o alvo for um arquivo, cola na pasta pai
        if os.path.isfile(target_path):
            dest_dir = os.path.dirname(target_path)
        else:
            dest_dir = target_path

        src_name = os.path.basename(self._clipboard_path)
        dest_path = os.path.join(dest_dir, src_name)

        # Evita sobrescrever: adiciona sufixo se necessário
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
            self.status_message.emit(f"Colado: {os.path.basename(dest_path)}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Erro ao colar: {e}")
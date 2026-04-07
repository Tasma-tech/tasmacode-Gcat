from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QFileDialog, QMessageBox, QFrame, QStackedWidget, QScrollArea, QMenu, 
                               QInputDialog, QApplication, QStyle, QComboBox, QDialog, QListWidget, QTextEdit, QToolButton, QSizePolicy, QListWidgetItem)
from PySide6.QtCore import Qt, QRect, QPointF, Signal, QPoint
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QFont, QPainterPath,
                           QFontMetrics, QCursor, QSyntaxHighlighter, QTextCharFormat, QPixmap)
from PySide6.QtCore import QThread, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from src.core.git_logic import GitLogic

class CommitStatsThread(QThread):
    """Thread para buscar estatísticas de um commit."""
    stats_ready = Signal(dict) # Emits {'hash': str, 'stats': dict}

    def __init__(self, git_logic, repo_path, commit_hash, parent=None):
        super().__init__(parent)
        self.git_logic = git_logic
        self.repo_path = repo_path
        self.commit_hash = commit_hash

    def run(self):
        stats = self.git_logic.get_commit_stats(self.repo_path, self.commit_hash)
        if stats:
            self.stats_ready.emit({'hash': self.commit_hash, 'stats': stats})

class LineCounterThread(QThread):
    """Thread para contar as linhas do projeto sem congelar a UI."""
    count_ready = Signal(int, int) # file_count, line_count

    def __init__(self, git_logic, repo_path, parent=None):
        super().__init__(parent)
        self.git_logic = git_logic
        self.repo_path = repo_path

    def run(self):
        file_count, line_count = self.git_logic.count_project_lines(self.repo_path)
        self.count_ready.emit(file_count, line_count)

class CommitTooltip(QLabel):
    """Tooltip customizado flutuante para commits."""
    def __init__(self):
        super().__init__(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("""
            background-color: #1e1e1e;
            color: #cccccc;
            border: 1px solid #454545;
            border-radius: 4px;
            padding: 8px;
        """)
        self.setWordWrap(True)
        self.setMaximumWidth(300)

    def show_data(self, commit, pos):
        content = (f"<b style='color: #ffffff'>Hash:</b> {commit['hash'][:8]}<br>"
                   f"<b style='color: #ffffff'>Autor:</b> {commit['author']}<br>")

        # Adiciona stats se disponíveis
        if 'files' in commit:
            files = commit['files']
            insertions = commit.get('insertions', 0)
            deletions = commit.get('deletions', 0)
            
            if files >= 0: # Verifica se não houve erro (-1)
                stats_parts = [f"{files} arquivo(s) alterado(s)"]
                if insertions > 0:
                    stats_parts.append(f"<span style='color: #a6e22e;'>+{insertions}</span>")
                if deletions > 0:
                    stats_parts.append(f"<span style='color: #f92672;'>-{deletions}</span>")
                content += f"<b style='color: #ffffff'>Stats:</b> {', '.join(stats_parts)}<br>"
            else:
                content += f"<b style='color: #ffffff'>Stats:</b> <i>Erro ao carregar</i><br>"
        elif commit.get('loading_stats'):
             content += f"<b style='color: #ffffff'>Stats:</b> <i>Carregando...</i><br>"

        content += (f"<hr style='background-color: #454545; height: 1px; border: none;'>{commit['message'].replace(chr(10), '<br>')}")
        self.setText(content)
        self.adjustSize()
        self.move(pos)
        self.show()

class DiffHighlighter(QSyntaxHighlighter):
    """Realce de sintaxe básico para Diffs."""
    def __init__(self, document):
        super().__init__(document)
        self.added_fmt = QTextCharFormat()
        self.added_fmt.setForeground(QColor("#a6e22e")) # Verde
        
        self.removed_fmt = QTextCharFormat()
        self.removed_fmt.setForeground(QColor("#f92672")) # Rosa/Vermelho
        
        self.header_fmt = QTextCharFormat()
        self.header_fmt.setForeground(QColor("#66d9ef")) # Azul

    def highlightBlock(self, text):
        if text.startswith('+'): self.setFormat(0, len(text), self.added_fmt)
        elif text.startswith('-'): self.setFormat(0, len(text), self.removed_fmt)
        elif text.startswith('@@') or text.startswith('diff'): self.setFormat(0, len(text), self.header_fmt)

class FileListItemWidget(QWidget):
    """Widget customizado para item de arquivo com stats coloridos."""
    def __init__(self, icon, text, added, removed, text_color, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)
        
        lbl_icon = QLabel()
        lbl_icon.setPixmap(icon.pixmap(16, 16))
        lbl_icon.setFixedSize(16, 16)
        layout.addWidget(lbl_icon)
        
        lbl_name = QLabel(text)
        lbl_name.setStyleSheet(f"color: {text_color}; background-color: transparent;")
        layout.addWidget(lbl_name)
        
        layout.addStretch()
        
        if added > 0:
            lbl_added = QLabel(f"+{added}")
            lbl_added.setStyleSheet("color: #a6e22e; font-weight: bold; background-color: transparent;")
            layout.addWidget(lbl_added)
            
        if removed > 0:
            lbl_removed = QLabel(f"-{removed}")
            lbl_removed.setStyleSheet("color: #f92672; font-weight: bold; background-color: transparent;")
            layout.addWidget(lbl_removed)
            
        # Garante que o widget seja transparente para ver a seleção do QListWidget
        self.setStyleSheet("background-color: transparent;")

class DiffViewer(QDialog):
    """Janela para visualizar o diff de um arquivo."""
    def __init__(self, diff_text, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Diff: {title}")
        self.resize(800, 600)
        self.setStyleSheet("background-color: #1e1e1e; color: #cccccc;")
        
        layout = QVBoxLayout(self)
        text_edit = QTextEdit()
        text_edit.setPlainText(diff_text)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Monospace", 10))
        text_edit.setStyleSheet("border: none; background-color: #1e1e1e; color: #cccccc;")
        self.highlighter = DiffHighlighter(text_edit.document())
        layout.addWidget(text_edit)

class CommitDetailsDialog(QDialog):
    """Janela com detalhes do commit e lista de arquivos modificados."""
    def __init__(self, repo_path, commit_data, git_logic, parent=None):
        super().__init__(parent)
        self.repo_path = repo_path
        self.commit_data = commit_data
        self.git_logic = git_logic
        self.setWindowTitle(f"Commit {commit_data['hash'][:8]}")
        self.resize(500, 400)
        self.setStyleSheet("background-color: #252526; color: #cccccc;")
        
        layout = QVBoxLayout(self)
        
        # Metadata
        meta = QLabel(f"<b>Autor:</b> {commit_data['author']}<br><b>Data:</b> {commit_data['date']}<br><br>{commit_data['message']}")
        meta.setWordWrap(True)
        layout.addWidget(meta)
        
        layout.addWidget(QLabel("<b>Arquivos Modificados (Clique para ver Diff):</b>"))
        
        self.files_list = QListWidget()
        self.files_list.setStyleSheet("background-color: #3c3c3c; border: none;")
        files = self.git_logic.get_commit_files(self.repo_path, self.commit_data['hash'])
        self.files_list.addItems(files)
        self.files_list.itemClicked.connect(self._show_diff)
        layout.addWidget(self.files_list)
        
    def _show_diff(self, item):
        file_path = item.text()
        diff = self.git_logic.get_diff(self.repo_path, self.commit_data['hash'], file_path)
        DiffViewer(diff, file_path, self).exec()

class CredentialsDialog(QDialog):
    """Diálogo para solicitar credenciais do Git."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Autenticação Git")
        self.resize(350, 180)
        self.setStyleSheet("background-color: #252526; color: #cccccc;")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        layout.addWidget(QLabel("Falha na autenticação. Por favor, insira suas credenciais:"))
        
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Username")
        self.user_input.setStyleSheet("background-color: #3c3c3c; border: 1px solid #454545; padding: 6px; color: white;")
        
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password / Personal Access Token")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet("background-color: #3c3c3c; border: 1px solid #454545; padding: 6px; color: white;")
        
        btn_box = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_ok.setStyleSheet("background-color: #007acc; color: white; padding: 6px 12px; border: none; border-radius: 4px;")
        btn_ok.clicked.connect(self.accept)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setStyleSheet("background-color: #3c3c3c; color: white; padding: 6px 12px; border: 1px solid #454545; border-radius: 4px;")
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        
        layout.addWidget(self.user_input)
        layout.addWidget(self.pass_input)
        layout.addLayout(btn_box)

    def get_credentials(self):
        return self.user_input.text().strip(), self.pass_input.text().strip()

class GitGraphWidget(QWidget):
    """Widget customizado para desenhar o grafo de commits."""
    
    commit_clicked = Signal(dict)
    copy_hash_requested = Signal(str)

    def __init__(self, git_logic, parent=None):
        super().__init__(parent)
        self.git_logic = git_logic
        self.repo_path = None
        self.commits = []
        self.row_height = 36 # Altura aumentada para melhor espaçamento
        self.node_radius = 6
        self.lane_width = 24 # Largura aumentada para evitar aglomeração
        self.setMinimumHeight(400)
        self.hit_areas = [] # Armazena áreas clicáveis: (QRect, commit_data)
        self.setMouseTracking(True) # Habilita rastreamento do mouse para hover
        self.hovered_commit = None
        self.hover_pos = QPoint(0, 0)
        self.bg_color = QColor("#1e1e1e")
        self.text_color = QColor("#cccccc")
        self.font_metrics_msg = QFontMetrics(self.font())
        self.stats_thread = None
        self.stats_cache = {}
        # Cores para os branches
        self.colors = [
            QColor("#40c463"), QColor("#f38ba8"), QColor("#89b4fa"), 
            QColor("#fab387"), QColor("#cba6f7"), QColor("#f9e2af"), 
            QColor("#94e2d5")
        ]
        self.tooltip_widget = CommitTooltip()

    def set_data(self, commits):
        self.commits = commits
        self.setMinimumHeight(len(commits) * self.row_height + 20)
        self.font_metrics_msg = QFontMetrics(self.font()) # Recalculate on data change if font can change
        self.update()

    def set_theme_colors(self, bg, fg):
        self.bg_color = QColor(bg)
        self.text_color = QColor(fg)
        self.update()

    def mousePressEvent(self, event):
        pos = event.position().toPoint()
        for rect, commit in self.hit_areas:
            if rect.adjusted(-5, -5, 5, 5).contains(pos):
                self.commit_clicked.emit(commit)
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Detecta hover sobre os commits."""
        pos = event.position().toPoint()
        self.hover_pos = pos
        found_commit = None
        for rect, commit in self.hit_areas:
            if rect.adjusted(-5, -5, 5, 5).contains(pos):
                found_commit = commit
                break
        
        # Se o mouse saiu de um commit, esconde o tooltip
        if not found_commit and self.hovered_commit:
            self.tooltip_widget.hide()
            self.hovered_commit = None
            return

        # Se o mouse está sobre um commit
        if found_commit:
            # Se é o mesmo commit, não faz nada
            if self.hovered_commit and self.hovered_commit['hash'] == found_commit['hash']:
                return

            # É um novo commit para hover
            self.hovered_commit = found_commit
            global_pos = self.mapToGlobal(pos) + QPoint(15, 15)

            # Verifica o cache
            if found_commit['hash'] in self.stats_cache:
                found_commit.update(self.stats_cache[found_commit['hash']])
                self.tooltip_widget.show_data(found_commit, global_pos)
            else:
                # Mostra tooltip com info básica e "Carregando..."
                found_commit['loading_stats'] = True
                self.tooltip_widget.show_data(found_commit, global_pos)
                
                # Inicia thread para buscar os stats
                if self.stats_thread and self.stats_thread.isRunning():
                    self.stats_thread.terminate() # Cancela a anterior
                
                self.stats_thread = CommitStatsThread(self.git_logic, self.repo_path, found_commit['hash'])
                self.stats_thread.stats_ready.connect(self._on_stats_ready)
                self.stats_thread.start()
        
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hovered_commit = None
        self.tooltip_widget.hide()
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        """Menu de contexto ao clicar com botão direito."""
        if self.hovered_commit:
            menu = QMenu(self)
            menu.setStyleSheet("QMenu { background-color: #252526; color: #cccccc; } QMenu::item:selected { background-color: #007acc; }")
            menu.addAction("Copiar Hash", lambda: self.copy_hash_requested.emit(self.hovered_commit['hash']))
            menu.addAction("Copiar Mensagem", lambda: QApplication.clipboard().setText(self.hovered_commit['message']))
            menu.exec(event.globalPos())

    def _on_stats_ready(self, stats_data):
        commit_hash = stats_data['hash']
        stats = stats_data['stats']
        
        # Salva no cache
        self.stats_cache[commit_hash] = stats
        
        # Se o mouse ainda estiver sobre o mesmo commit, atualiza o tooltip
        if self.hovered_commit and self.hovered_commit['hash'] == commit_hash:
            self.hovered_commit.update(stats)
            if 'loading_stats' in self.hovered_commit:
                del self.hovered_commit['loading_stats']
            
            global_pos = self.mapToGlobal(self.hover_pos) + QPoint(15, 15)
            self.tooltip_widget.show_data(self.hovered_commit, global_pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        self.hit_areas = [] # Reinicia áreas de clique

        # Fontes
        font_refs = self.font()
        font_refs.setPointSize(9)
        font_refs.setBold(True)
        
        font_msg = self.font() # Use font from widget
        font_msg.setPointSize(10) # Slightly larger for readability
        self.font_metrics_msg = QFontMetrics(font_msg)

        # Estado para o desenho do grafo
        # lanes: lista de hashes de commit esperados na próxima linha.
        # O índice na lista representa a 'trilha' visual (coluna)
        lanes = [] 
        
        # Posições Y
        y = self.row_height // 2

        for commit in self.commits:
            commit_hash = commit['hash']
            is_hovered = self.hovered_commit and self.hovered_commit['hash'] == commit_hash
            
            # Determina a lane deste commit
            if commit_hash in lanes:
                node_lane_idx = lanes.index(commit_hash)
            else:
                # Nova ponta de branch, encontra uma lane livre (None) ou adiciona nova
                try:
                    node_lane_idx = lanes.index(None)
                except ValueError:
                    node_lane_idx = len(lanes)
                    lanes.append(None)
            
            # Prepara next_lanes (estado da próxima linha)
            next_lanes = list(lanes)
            
            # O commit atual consome sua posição na lane (será substituído pelos pais)
            if node_lane_idx < len(next_lanes):
                next_lanes[node_lane_idx] = None

            # Atribui pais às lanes na próxima linha
            parent_positions = []
            for i, parent_hash in enumerate(commit['parents']):
                if parent_hash in next_lanes:
                    # Pai já esperado (merge), reutiliza a lane existente
                    idx = next_lanes.index(parent_hash)
                    parent_positions.append(idx)
                else:
                    # Atribui a uma lane
                    if i == 0:
                        # Primeiro pai tenta herdar a lane do nó atual
                        if node_lane_idx < len(next_lanes) and next_lanes[node_lane_idx] is None:
                            next_lanes[node_lane_idx] = parent_hash
                            parent_positions.append(node_lane_idx)
                        else:
                            # Lane ocupada, busca livre
                            try:
                                idx = next_lanes.index(None)
                                next_lanes[idx] = parent_hash
                                parent_positions.append(idx)
                            except ValueError:
                                idx = len(next_lanes)
                                next_lanes.append(parent_hash)
                                parent_positions.append(idx)
                    else:
                        # Outros pais (bifurcação) buscam slots livres
                        try:
                            idx = next_lanes.index(None)
                            next_lanes[idx] = parent_hash
                            parent_positions.append(idx)
                        except ValueError:
                            idx = len(next_lanes)
                            next_lanes.append(parent_hash)
                            parent_positions.append(idx)

            # --- DESENHO ---
            
            # 1. Desenha linhas verticais para branches que apenas passam por aqui (Pass-through)
            for i in range(len(lanes)):
                if lanes[i] is not None and lanes[i] != commit_hash:
                    # Verifica se continua na próxima linha (deve continuar se não foi modificado)
                    if i < len(next_lanes) and next_lanes[i] == lanes[i]:
                        line_x = 20 + (i * self.lane_width)
                        color = self.colors[i % len(self.colors)]
                        painter.setPen(QPen(color, 2))
                        painter.drawLine(line_x, y, line_x, y + self.row_height)

            # 2. Desenha conexões do Nó atual para os Pais
            node_x = 20 + (node_lane_idx * self.lane_width)
            node_color = self.colors[node_lane_idx % len(self.colors)]
            
            for p_idx in parent_positions:
                target_x = 20 + (p_idx * self.lane_width)
                target_y = y + self.row_height

                pen_width = 3 if is_hovered else 2
                painter.setPen(QPen(node_color, pen_width))
                painter.setBrush(Qt.NoBrush)
                
                path = QPainterPath()
                path.moveTo(node_x, y)
                
                if p_idx == node_lane_idx:
                    # Linha reta para o pai direto
                    path.lineTo(target_x, target_y)
                else:
                    # Curva suave para merges ou branches
                    ctrl1 = QPointF(node_x, y + self.row_height * 0.6)
                    ctrl2 = QPointF(target_x, target_y - self.row_height * 0.6)
                    path.cubicTo(ctrl1, ctrl2, QPointF(target_x, target_y))
                
                painter.drawPath(path)

            # 3. Desenha o Nó do commit
            radius = self.node_radius + (2 if is_hovered else 0)
            pen_width = 3 if is_hovered else 2
            painter.setPen(QPen(node_color, pen_width))
            painter.setBrush(QBrush(self.bg_color))
            node_rect = QRect(node_x - radius, y - radius, radius*2, radius*2)
            painter.drawEllipse(node_rect)
            
            self.hit_areas.append((node_rect, commit))

            # 4. Desenha Texto (Mensagem e Refs)
            # Posiciona o texto à direita de todas as lanes ativas (usando len(next_lanes) ou len(lanes))
            max_lane_idx = max(len(lanes), len(next_lanes))
            text_x = 20 + (max_lane_idx * self.lane_width) + 10
            
            # Refs (Branches/Tags)
            if commit['refs']:
                painter.setFont(font_refs)
                painter.setPen(QColor("#ffcc00"))
                painter.drawText(text_x, y + 4, commit['refs']) # y+4 para alinhar verticalmente
                text_x += QFontMetrics(font_refs).horizontalAdvance(commit['refs']) + 8

            # Mensagem
            painter.setFont(font_msg)
            painter.setPen(self.text_color)
            # Elide text se for muito longo
            elided_msg = self.font_metrics_msg.elidedText(commit['message'], Qt.TextElideMode.ElideRight, self.width() - text_x - 10)
            painter.drawText(text_x, y + 4, elided_msg)

            # Atualiza estado para a próxima iteração
            lanes = next_lanes
            y += self.row_height

class RightSidebar(QWidget):
    """Barra lateral direita focada em ferramentas Git."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.git_logic = GitLogic()
        self.auth_logic = None
        self.theme = {}
        self.line_counter_thread = None
        self.setObjectName("RightSidebar")
        self.setMinimumWidth(200)
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.stack = QStackedWidget()
        
        # --- Página 1: Clone (Default) ---
        self.page_clone = QWidget()
        clone_layout = QVBoxLayout(self.page_clone)
        clone_layout.setContentsMargins(10, 10, 10, 10)
        clone_layout.setSpacing(10)

        # Título
        lbl_title = QLabel("Git Clone")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        clone_layout.addWidget(lbl_title)

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        clone_layout.addWidget(line)

        # Input URL
        lbl_url = QLabel("URL do Repositório:")
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("https://github.com/user/repo.git")
        
        clone_layout.addWidget(lbl_url)
        clone_layout.addWidget(self.input_url)

        # Botão Clonar
        self.btn_clone = QPushButton("Clonar Repositório")
        self.btn_clone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clone.clicked.connect(self._handle_clone_click)
        
        clone_layout.addWidget(self.btn_clone)
        clone_layout.addStretch()

        # --- Página 2: Controle Git (Visual) ---
        self.page_git = QWidget()
        git_layout = QVBoxLayout(self.page_git)
        git_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header Git
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame) # Adiciona margens para respiro
        header_layout.setContentsMargins(5, 5, 5, 5)
        
        self.branch_selector = QComboBox()
        self.branch_selector.currentIndexChanged.connect(self._switch_branch)

        btn_new_branch = QPushButton()
        btn_new_branch.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        btn_new_branch.setToolTip("Criar Nova Branch")
        btn_new_branch.setFixedSize(28, 28)
        btn_new_branch.clicked.connect(self._create_branch)
        
        btn_commit = QPushButton()
        btn_commit.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        btn_commit.setToolTip("Commit")
        btn_commit.setFixedSize(28, 28)
        btn_commit.clicked.connect(self._perform_commit)

        btn_pull = QPushButton()
        btn_pull.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))
        btn_pull.setToolTip("Pull")
        btn_pull.setFixedSize(28, 28)
        btn_pull.clicked.connect(self._perform_pull)

        btn_push = QPushButton()
        btn_push.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        btn_push.setToolTip("Push")
        btn_push.setFixedSize(28, 28)
        btn_push.clicked.connect(self._perform_push)

        btn_refresh = QPushButton()
        btn_refresh.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        btn_refresh.setToolTip("Atualizar")
        btn_refresh.setFixedSize(28, 28)
        btn_refresh.clicked.connect(self._refresh_graph)
        
        header_layout.addWidget(self.branch_selector, 1)
        
        self.lbl_line_count = QLabel("...")
        self.lbl_line_count.setToolTip("Linhas de Código (rastreadas pelo Git)")
        header_layout.addWidget(self.lbl_line_count)
        
        header_layout.addStretch()
        header_layout.addWidget(btn_new_branch)
        header_layout.addWidget(btn_commit)
        header_layout.addWidget(btn_pull)
        header_layout.addWidget(btn_push)
        header_layout.addWidget(btn_refresh)
        
        git_layout.addWidget(header_frame)
        
        # --- Seção de Staged Changes (Collapsible) ---
        self.staged_section = QWidget()
        staged_layout = QVBoxLayout(self.staged_section)
        staged_layout.setContentsMargins(5, 5, 5, 5)
        staged_layout.setSpacing(5)
        
        self.btn_toggle_staged = QToolButton()
        self.btn_toggle_staged.setText(" Staged Changes (0)")
        self.btn_toggle_staged.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_toggle_staged.setArrowType(Qt.DownArrow)
        self.btn_toggle_staged.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_toggle_staged.clicked.connect(lambda: self._toggle_section(self.staged_list, self.btn_toggle_staged))
        
        self.staged_list = QListWidget()
        self.staged_list.setMaximumHeight(150)
        self.staged_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.staged_list.customContextMenuRequested.connect(lambda pos: self._show_file_context_menu(pos, is_staged=True))
        self.staged_list.itemDoubleClicked.connect(lambda item: self._view_diff(item.data(Qt.UserRole), is_staged=True))
        
        staged_layout.addWidget(self.btn_toggle_staged)
        staged_layout.addWidget(self.staged_list)
        
        git_layout.addWidget(self.staged_section)

        # --- Seção de Unstaged Changes (Collapsible) ---
        self.unstaged_section = QWidget()
        unstaged_layout = QVBoxLayout(self.unstaged_section)
        unstaged_layout.setContentsMargins(5, 5, 5, 5)
        unstaged_layout.setSpacing(5)
        
        self.btn_toggle_unstaged = QToolButton()
        self.btn_toggle_unstaged.setText(" Changes (0)")
        self.btn_toggle_unstaged.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.btn_toggle_unstaged.setArrowType(Qt.DownArrow)
        self.btn_toggle_unstaged.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_toggle_unstaged.clicked.connect(lambda: self._toggle_section(self.unstaged_list, self.btn_toggle_unstaged))
        
        self.unstaged_list = QListWidget()
        self.unstaged_list.setMaximumHeight(200)
        self.unstaged_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.unstaged_list.customContextMenuRequested.connect(lambda pos: self._show_file_context_menu(pos, is_staged=False))
        self.unstaged_list.itemDoubleClicked.connect(lambda item: self._view_diff(item.data(Qt.UserRole), is_staged=False))
        
        unstaged_layout.addWidget(self.btn_toggle_unstaged)
        unstaged_layout.addWidget(self.unstaged_list)
        
        git_layout.addWidget(self.unstaged_section)
        
        # Área do Gráfico (Scrollável)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.graph_widget = GitGraphWidget(self.git_logic)
        self.graph_widget.copy_hash_requested.connect(self._copy_hash)
        self.graph_widget.commit_clicked.connect(self._open_commit_details)
        scroll.setWidget(self.graph_widget)
        
        git_layout.addWidget(scroll)
        
        # Adiciona páginas ao stack
        self.stack.addWidget(self.page_clone)
        self.stack.addWidget(self.page_git)
        
        layout.addWidget(self.stack)
        
        self.current_repo = None

    def set_auth_logic(self, auth_logic):
        self.auth_logic = auth_logic

    def apply_theme(self, theme):
        """Aplica o tema visual à barra lateral direita."""
        self.theme = theme
        bg = theme.get("sidebar_bg", "#252526")
        fg = theme.get("foreground", "#cccccc")
        border = theme.get("border_color", "#3e3e42")
        accent = theme.get("accent", "#007acc")
        input_bg = theme.get("background", "#1e1e1e")
        selection_bg = theme.get("selection", "#094771")
        
        self.setStyleSheet(f"""
            QWidget#RightSidebar {{
                background-color: {bg};
                border-left: 1px solid {border};
                color: {fg};
            }}
            QLabel {{ color: {fg}; }}
            QLineEdit {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 5px;
                border-radius: 4px;
            }}
            QComboBox {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 2px;
            }}
            QToolButton {{
                border: none;
                background-color: {bg};
                color: {fg};
                padding: 6px;
                text-align: left;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: {border};
            }}
        """)
        
        self.btn_clone.setStyleSheet(f"background-color: {accent}; color: white; padding: 8px; border: none; border-radius: 4px;")
        self.graph_widget.set_theme_colors(bg, fg)
        self._refresh_files() # Re-renderiza a lista para aplicar cores

    def load_repo(self, path):
        """Chamado quando um projeto é aberto."""
        if self.git_logic.is_repo(path):
            self.current_repo = path
            self.graph_widget.repo_path = path # Define o caminho do repo no widget
            self.stack.setCurrentWidget(self.page_git)
            self._refresh_graph()
            self._update_project_stats()
        else:
            self.current_repo = None
            self.stack.setCurrentWidget(self.page_clone)

    def _refresh_graph(self):
        if not self.current_repo: return
        
        branch = self.git_logic.get_current_branch(self.current_repo)
        branches = self.git_logic.get_branches(self.current_repo)
        
        self.branch_selector.blockSignals(True)
        self.branch_selector.clear()
        self.branch_selector.addItems(branches)
        self.branch_selector.setCurrentText(branch)
        self.branch_selector.blockSignals(False)

        commits = self.git_logic.get_graph_data(self.current_repo)
        self.graph_widget.set_data(commits)
        self._refresh_files()
        self._update_project_stats()

    def _perform_commit(self):
        if not self.current_repo: return
        msg, ok = QInputDialog.getMultiLineText(self, "Commit", "Mensagem do Commit:")
        if ok and msg.strip():
            success, info = self.git_logic.commit(self.current_repo, msg.strip())
            if success:
                self._refresh_graph()
                QMessageBox.information(self, "Git", info)
            else:
                QMessageBox.warning(self, "Erro no Commit", info)

    def _perform_push(self):
        if not self.current_repo: return
        success, info = self.git_logic.push(self.current_repo)
        
        # Tenta usar credenciais salvas se falhar
        if not success and self.auth_logic and self.auth_logic.is_logged_in():
            user_data = self.auth_logic.get_user_data()
            token = self.auth_logic.get_token()
            success, info = self.git_logic.push(self.current_repo, user_data['login'], token)
        
        # Verifica falha de autenticação
        if not success and ("Authentication failed" in info or "could not read" in info):
            dlg = CredentialsDialog(self)
            if dlg.exec():
                user, token = dlg.get_credentials()
                if user and token:
                    success, info = self.git_logic.push(self.current_repo, user, token)

        if success:
            QMessageBox.information(self, "Git Push", info)
        else:
            QMessageBox.warning(self, "Git Push", info)

    def _perform_pull(self):
        if not self.current_repo: return
        success, info = self.git_logic.pull(self.current_repo)
        
        # Tenta usar credenciais salvas se falhar
        if not success and self.auth_logic and self.auth_logic.is_logged_in():
            user_data = self.auth_logic.get_user_data()
            token = self.auth_logic.get_token()
            success, info = self.git_logic.pull(self.current_repo, user_data['login'], token)
        
        # Verifica falha de autenticação
        if not success and ("Authentication failed" in info or "could not read" in info):
            dlg = CredentialsDialog(self)
            if dlg.exec():
                user, token = dlg.get_credentials()
                if user and token:
                    success, info = self.git_logic.pull(self.current_repo, user, token)

        if success:
            self._refresh_graph()
            QMessageBox.information(self, "Git Pull", info)
        else:
            QMessageBox.warning(self, "Git Pull", info)

    def _switch_branch(self):
        branch = self.branch_selector.currentText()
        if branch:
            success, info = self.git_logic.checkout(self.current_repo, branch)
            if success:
                self._refresh_graph()
            else:
                QMessageBox.warning(self, "Checkout", info)
                # Reverte seleção visual
                self._refresh_graph()

    def _create_branch(self):
        if not self.current_repo: return
        name, ok = QInputDialog.getText(self, "Nova Branch", "Nome da Branch:")
        if ok and name:
            # Sanitiza o nome: Git não aceita espaços em nomes de branch
            sanitized_name = name.strip().replace(" ", "-")
            success, info = self.git_logic.create_branch(self.current_repo, sanitized_name)
            if success: self._refresh_graph()
            QMessageBox.information(self, "Git", info)

    def _handle_clone_click(self):
        url = self.input_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Aviso", "Por favor, insira uma URL válida.")
            return

        # Pergunta onde salvar
        dest_folder = QFileDialog.getExistingDirectory(self, "Escolha onde salvar o repositório")
        if not dest_folder:
            return

        # Feedback visual
        self.btn_clone.setText("Clonando...")
        self.btn_clone.setEnabled(False)
        self.repaint() # Força atualização da UI

        # Executa lógica
        success, msg = self.git_logic.clone_repository(url, dest_folder)

        # Restaura UI e mostra resultado
        self.btn_clone.setText("Clonar Repositório")
        self.btn_clone.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Sucesso", msg)
            self.input_url.clear()
        else:
            QMessageBox.critical(self, "Erro", msg)

    def _update_project_stats(self):
        """Inicia a thread de contagem de linhas."""
        if not self.current_repo: return
        if self.line_counter_thread and self.line_counter_thread.isRunning():
            return # Já está calculando
        self.lbl_line_count.setText("Calculando...")
        self.line_counter_thread = LineCounterThread(self.git_logic, self.current_repo)
        self.line_counter_thread.count_ready.connect(lambda f, l: self.lbl_line_count.setText(f"{l:,} LOC"))
        self.line_counter_thread.start()

    def _copy_hash(self, commit_hash):
        QApplication.clipboard().setText(commit_hash)
        # Opcional: Mostrar feedback na statusbar se tivesse acesso

    def _open_commit_details(self, commit_data):
        CommitDetailsDialog(self.current_repo, commit_data, self.git_logic, self).exec()

    def _toggle_section(self, list_widget, button):
        """Expande ou recolhe a lista de arquivos."""
        is_visible = list_widget.isVisible()
        
        if hasattr(list_widget, "_anim") and list_widget._anim.state() == QAbstractAnimation.State.Running:
            return

        target_height = 150 if list_widget == self.staged_list else 200

        if is_visible:
            list_widget._anim = QPropertyAnimation(list_widget, b"maximumHeight")
            list_widget._anim.setDuration(200)
            list_widget._anim.setStartValue(list_widget.height())
            list_widget._anim.setEndValue(0)
            list_widget._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            list_widget._anim.finished.connect(lambda: list_widget.setVisible(False))
            list_widget._anim.finished.connect(lambda: list_widget.setMaximumHeight(target_height))
            button.setArrowType(Qt.RightArrow)
        else:
            list_widget.setMaximumHeight(0)
            list_widget.setVisible(True)
            list_widget._anim = QPropertyAnimation(list_widget, b"maximumHeight")
            list_widget._anim.setDuration(200)
            list_widget._anim.setStartValue(0)
            list_widget._anim.setEndValue(target_height)
            list_widget._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            button.setArrowType(Qt.DownArrow)
            
        list_widget._anim.start()

    def _refresh_files(self):
        """Atualiza a lista de arquivos modificados."""
        if not self.current_repo: return
        
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        text_color = self.theme.get("foreground", "#cccccc")

        # --- Staged Files ---
        staged_files = self.git_logic.get_staged_files(self.current_repo)
        staged_stats = self.git_logic.get_files_stats(self.current_repo, staged=True)
        self.staged_list.clear()
        
        for f in staged_files:
            added, removed = staged_stats.get(f, (0, 0))
            item = QListWidgetItem(self.staged_list)
            item.setData(Qt.UserRole, f)
            widget = FileListItemWidget(icon, f, added, removed, text_color)
            item.setSizeHint(widget.sizeHint())
            self.staged_list.setItemWidget(item, widget)
        self.btn_toggle_staged.setText(f" Staged Changes ({len(staged_files)})")

        # --- Unstaged Files ---
        unstaged_files = self.git_logic.get_unstaged_files(self.current_repo)
        unstaged_stats = self.git_logic.get_files_stats(self.current_repo, staged=False)
        self.unstaged_list.clear()
        
        for f in unstaged_files:
            added, removed = unstaged_stats.get(f, (0, 0))
            item = QListWidgetItem(self.unstaged_list)
            item.setData(Qt.UserRole, f)
            widget = FileListItemWidget(icon, f, added, removed, text_color)
            item.setSizeHint(widget.sizeHint())
            self.unstaged_list.setItemWidget(item, widget)
        self.btn_toggle_unstaged.setText(f" Changes ({len(unstaged_files)})")

    def _show_file_context_menu(self, pos, is_staged):
        list_widget = self.staged_list if is_staged else self.unstaged_list
        item = list_widget.itemAt(pos)
        if not item: return
        file_path = item.data(Qt.UserRole) # Recupera o caminho limpo
        
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #252526; color: #cccccc; } QMenu::item:selected { background-color: #007acc; }")
        
        if is_staged:
            menu.addAction("Ver Diff (Staged)", lambda: self._view_diff(file_path, is_staged=True))
            menu.addAction("Remover do Stage (-)", lambda: self._unstage_file(file_path))
        else:
            menu.addAction("Ver Diff (Working)", lambda: self._view_diff(file_path, is_staged=False))
            menu.addAction("Adicionar ao Stage (+)", lambda: self._stage_file(file_path))
            menu.addSeparator()
            menu.addAction("Descartar Alterações", lambda: self._discard_file_changes(file_path))
        
        menu.exec(list_widget.mapToGlobal(pos))

    def _view_diff(self, file_path, is_staged):
        if not self.current_repo: return
        
        if is_staged:
            diff = self.git_logic.get_staged_diff(self.current_repo, file_path)
            title = f"{file_path} (Staged)"
        else:
            diff = self.git_logic.get_working_diff(self.current_repo, file_path)
            title = f"{file_path} (Working Tree)"
            
        if diff.strip():
            DiffViewer(diff, title, self).exec()
        else:
            QMessageBox.information(self, "Diff", "O arquivo parece não ter diferenças textuais ou é um arquivo binário/novo.")

    def _discard_file_changes(self, file_path):
        if not self.current_repo: return
        reply = QMessageBox.question(self, "Descartar Alterações", f"Tem certeza que deseja descartar as alterações em '{file_path}'?\nEssa ação é irreversível.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.git_logic.discard_changes(self.current_repo, file_path)
            if success:
                self._refresh_files()
            else:
                QMessageBox.warning(self, "Erro", msg)

    def _stage_file(self, file_path):
        if not self.current_repo: return
        success, msg = self.git_logic.stage_file(self.current_repo, file_path)
        if success:
            self._refresh_files()
        else:
            QMessageBox.warning(self, "Erro", msg)

    def _unstage_file(self, file_path):
        if not self.current_repo: return
        success, msg = self.git_logic.unstage_file(self.current_repo, file_path)
        if success:
            self._refresh_files()
        else:
            QMessageBox.warning(self, "Erro", msg)
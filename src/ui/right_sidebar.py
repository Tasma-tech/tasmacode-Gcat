from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                               QFileDialog, QMessageBox, QFrame, QStackedWidget, QScrollArea)
from PySide6.QtCore import Qt, QRect, QPointF, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QFontMetrics
from src.core.git_logic import GitLogic

class GitGraphWidget(QWidget):
    """Widget customizado para desenhar o grafo de commits."""
    
    commit_clicked = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.commits = []
        self.row_height = 36 # Altura aumentada para melhor espaçamento
        self.node_radius = 6
        self.lane_width = 24 # Largura aumentada para evitar aglomeração
        self.setMinimumHeight(400)
        self.hit_areas = [] # Armazena áreas clicáveis: (QRect, commit_data)
        # Cores para os branches
        self.colors = [
            QColor("#40c463"), QColor("#f38ba8"), QColor("#89b4fa"), 
            QColor("#fab387"), QColor("#cba6f7"), QColor("#f9e2af"), 
            QColor("#94e2d5")
        ]

    def set_data(self, commits):
        self.commits = commits
        self.setMinimumHeight(len(commits) * self.row_height + 20)
        self.update()

    def mousePressEvent(self, event):
        """Detecta cliques nos nós dos commits."""
        pos = event.position().toPoint()
        for rect, commit in self.hit_areas:
            # Expande levemente a área de clique para facilitar
            if rect.adjusted(-3, -3, 3, 3).contains(pos):
                self.commit_clicked.emit(commit)
                return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        self.hit_areas = [] # Reinicia áreas de clique

        # Fontes
        font_refs = self.font()
        font_refs.setPointSize(9)
        font_refs.setBold(True)
        
        font_msg = self.font()
        font_msg.setPointSize(9)

        # Estado para o desenho do grafo
        # lanes: lista de hashes de commit esperados na próxima linha
        # O índice na lista representa a 'trilha' visual (coluna)
        lanes = [] 
        
        # Posições Y
        y = self.row_height // 2

        for commit in self.commits:
            commit_hash = commit['hash']
            
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
                
                painter.setPen(QPen(node_color, 2))
                painter.setBrush(Qt.NoBrush)
                
                path = QPainterPath()
                path.moveTo(node_x, y)
                
                if p_idx == node_lane_idx:
                    path.lineTo(target_x, target_y)
                else:
                    ctrl1 = QPointF(node_x, y + self.row_height * 0.5)
                    ctrl2 = QPointF(target_x, target_y - self.row_height * 0.5)
                    path.cubicTo(ctrl1, ctrl2, QPointF(target_x, target_y))
                
                painter.drawPath(path)

            # 3. Desenha o Nó do commit
            painter.setPen(QPen(node_color, 2))
            painter.setBrush(QBrush(QColor("#252526")))
            node_rect = QRect(node_x - self.node_radius, y - self.node_radius, self.node_radius*2, self.node_radius*2)
            painter.drawEllipse(node_rect)
            
            # Ponto central preenchido
            painter.setBrush(QBrush(node_color))
            painter.drawEllipse(node_x - 2, y - 2, 4, 4)
            
            self.hit_areas.append((node_rect, commit))

            # 4. Desenha Texto (Mensagem e Refs)
            # Posiciona o texto à direita de todas as lanes ativas (usando len(next_lanes) ou len(lanes))
            max_lane_idx = max(len(lanes), len(next_lanes))
            text_x = 20 + (max_lane_idx * self.lane_width) + 10
            
            # Refs (Branches/Tags)
            if commit['refs']:
                painter.setFont(font_refs)
                painter.setPen(QColor("#ffcc00"))
                painter.drawText(text_x, y + 4, commit['refs'])
                fm = QFontMetrics(font_refs)
                text_x += fm.horizontalAdvance(commit['refs']) + 8

            # Mensagem
            painter.setFont(font_msg)
            painter.setPen(QColor("#cccccc"))
            # Elide text se for muito longo
            msg = commit['message']
            fm = QFontMetrics(font_msg)
            elided_msg = fm.elidedText(msg, Qt.TextElideMode.ElideRight, self.width() - text_x - 10)
            painter.drawText(text_x, y + 4, elided_msg)

            # Atualiza estado para a próxima iteração
            lanes = next_lanes
            y += self.row_height

class RightSidebar(QWidget):
    """Barra lateral direita focada em ferramentas Git."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.git_logic = GitLogic()
        self.setObjectName("RightSidebar")
        self.setFixedWidth(250)
        self.setStyleSheet("background-color: #252526; border-left: 1px solid #3e3e42;")
        
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
        lbl_title.setStyleSheet("font-weight: bold; color: #cccccc; font-size: 14px;")
        clone_layout.addWidget(lbl_title)

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #3e3e42;")
        clone_layout.addWidget(line)

        # Input URL
        lbl_url = QLabel("URL do Repositório:")
        lbl_url.setStyleSheet("color: #cccccc;")
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("https://github.com/user/repo.git")
        self.input_url.setStyleSheet("background-color: #3c3c3c; color: white; border: 1px solid #454545; padding: 5px;")
        
        clone_layout.addWidget(lbl_url)
        clone_layout.addWidget(self.input_url)

        # Botão Clonar
        self.btn_clone = QPushButton("Clonar Repositório")
        self.btn_clone.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clone.setStyleSheet("""
            QPushButton { background-color: #007acc; color: white; padding: 8px; border: none; border-radius: 4px; }
            QPushButton:hover { background-color: #0098ff; }
        """)
        self.btn_clone.clicked.connect(self._handle_clone_click)
        
        clone_layout.addWidget(self.btn_clone)
        clone_layout.addStretch()

        # --- Página 2: Controle Git (Visual) ---
        self.page_git = QWidget()
        git_layout = QVBoxLayout(self.page_git)
        git_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header Git
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #2d2d30; padding: 5px;")
        header_layout = QVBoxLayout(header_frame)
        
        self.lbl_branch = QLabel("Branch: -")
        self.lbl_branch.setStyleSheet("font-weight: bold; color: #fff;")
        
        btn_refresh = QPushButton("Atualizar")
        btn_refresh.clicked.connect(self._refresh_graph)
        btn_refresh.setStyleSheet("background-color: #3c3c3c; color: white; border: none; padding: 4px;")
        
        header_layout.addWidget(self.lbl_branch)
        header_layout.addWidget(btn_refresh)
        
        git_layout.addWidget(header_frame)
        
        # Área do Gráfico (Scrollável)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #1e1e1e; border: none;")
        
        self.graph_widget = GitGraphWidget()
        self.graph_widget.commit_clicked.connect(self._show_commit_details)
        scroll.setWidget(self.graph_widget)
        
        git_layout.addWidget(scroll)
        
        # Adiciona páginas ao stack
        self.stack.addWidget(self.page_clone)
        self.stack.addWidget(self.page_git)
        
        layout.addWidget(self.stack)
        
        self.current_repo = None

    def load_repo(self, path):
        """Chamado quando um projeto é aberto."""
        if self.git_logic.is_repo(path):
            self.current_repo = path
            self.stack.setCurrentWidget(self.page_git)
            self._refresh_graph()
        else:
            self.current_repo = None
            self.stack.setCurrentWidget(self.page_clone)

    def _refresh_graph(self):
        if not self.current_repo: return
        
        branch = self.git_logic.get_current_branch(self.current_repo)
        self.lbl_branch.setText(f"Branch: {branch}")
        
        commits = self.git_logic.get_graph_data(self.current_repo)
        self.graph_widget.set_data(commits)

    def _show_commit_details(self, commit):
        details = (
            f"Hash: {commit['hash']}\n"
            f"Autor: {commit['author']}\n"
            f"Data: {commit['date']}\n\n"
            f"Mensagem:\n{commit['message']}"
        )
        QMessageBox.information(self, "Detalhes do Commit", details)

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
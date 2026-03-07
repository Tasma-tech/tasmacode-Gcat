import sys
import os
import json
import base64
import hashlib
import requests
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                              QPushButton, QLabel, QComboBox, QMessageBox, 
                              QProgressBar, QSplitter, QWidget, QTabWidget, QScrollArea, QFileDialog, QApplication, QCheckBox, QStyle, QFrame, QLineEdit)
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtGui import QFont, QPixmap, QImage, QPainter, QDesktopServices
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtSvg import QSvgRenderer

# Adiciona o path raiz para imports
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

class AIDiagramThread(QThread):
    """Thread para comunicação com APIs de IA (Groq, OpenAI, Gemini, xAI)."""
    response_ready = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, provider: str, api_key: str, prompt: str, model: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.prompt = prompt
        self.model = model
        
    def run(self):
        try:
            if self.provider == "Google Gemini":
                self._run_google()
            else:
                self._run_openai_compatible()
        except Exception as e:
            self.error_occurred.emit(f"Connection Error: {str(e)}")

    def _run_openai_compatible(self):
        urls = {
            "Groq": "https://api.groq.com/openai/v1/chat/completions",
            "OpenAI": "https://api.openai.com/v1/chat/completions",
            "xAI (Grok)": "https://api.x.ai/v1/chat/completions"
        }
        
        url = urls.get(self.provider)
        if not url:
            self.error_occurred.emit(f"Provider desconhecido: {self.provider}")
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a software architecture expert. Generate detailed diagrams in Mermaid syntax based on the provided code structure. Focus on class relationships, dependencies, and data flow. Output ONLY the mermaid code."
                },
                {
                    "role": "user",
                    "content": self.prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            diagram = result["choices"][0]["message"]["content"]
            self._emit_diagram(diagram)
        else:
            self.error_occurred.emit(f"API Error ({self.provider}): {response.status_code} - {response.text}")

    def _run_google(self):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{"text": f"You are a software architecture expert. Generate detailed diagrams in Mermaid syntax based on the provided code structure. Focus on class relationships, dependencies, and data flow. Output ONLY the mermaid code.\n\nCode:\n{self.prompt}"}]
            }]
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            try:
                diagram = result["candidates"][0]["content"]["parts"][0]["text"]
                self._emit_diagram(diagram)
            except (KeyError, IndexError):
                self.error_occurred.emit(f"API Error (Gemini): Resposta inesperada - {response.text}")
        else:
            self.error_occurred.emit(f"API Error (Gemini): {response.status_code} - {response.text}")

    def _emit_diagram(self, diagram):
        # Limpeza básica
        if "```mermaid" in diagram:
            diagram = diagram.split("```mermaid")[1].split("```")[0].strip()
        elif "```" in diagram:
            diagram = diagram.split("```")[1].split("```")[0].strip()
        self.response_ready.emit(diagram)

class DiagramSettingsDialog(QDialog):
    """Diálogo de configurações do plugin."""
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações dIAgram")
        self.resize(450, 250)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        
        self.config = config.copy()
        self.providers = {
            "Groq": ["llama-3.3-70b-versatile", "llama3-70b-8192", "gemma-7b-it"],
            "OpenAI": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "Google Gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"],
            "xAI (Grok)": ["grok-beta"]
        }
        
        layout = QVBoxLayout(self)
        
        # Provider Selector
        layout.addWidget(QLabel("Provedor de IA:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(self.providers.keys())
        self.provider_combo.setCurrentText(self.config.get("provider", "Groq"))
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        layout.addWidget(self.provider_combo)
        
        # API Key
        layout.addWidget(QLabel("API Key:"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Cole sua chave aqui...")
        self.key_input.textChanged.connect(self._save_current_key_temp)
        layout.addWidget(self.key_input)
        
        # Model Selector
        layout.addWidget(QLabel("Modelo:"))
        self.model_combo = QComboBox()
        self.model_combo.currentTextChanged.connect(self._save_current_model_temp)
        layout.addWidget(self.model_combo)
        
        # Cache
        layout.addSpacing(10)
        btn_clear_cache = QPushButton("Limpar Cache de Diagramas")
        btn_clear_cache.clicked.connect(self._clear_cache)
        layout.addWidget(btn_clear_cache)
        
        layout.addStretch()
        
        # Botões
        btns = QHBoxLayout()
        btn_save = QPushButton("Salvar")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btns.addWidget(btn_cancel)
        btns.addWidget(btn_save)
        layout.addLayout(btns)
        
        # Inicializa campos
        self._on_provider_changed(self.provider_combo.currentText())
        
    def _on_provider_changed(self, provider):
        # Carrega chave salva
        api_keys = self.config.get("api_keys", {})
        self.key_input.setText(api_keys.get(provider, ""))
        
        # Atualiza modelos
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(self.providers.get(provider, []))
        
        # Seleciona modelo salvo
        saved_models = self.config.get("models", {})
        if provider in saved_models:
            self.model_combo.setCurrentText(saved_models[provider])
        self.model_combo.blockSignals(False)
        
        # Atualiza config temporária
        self.config["provider"] = provider

    def _save_current_key_temp(self, text):
        provider = self.provider_combo.currentText()
        if "api_keys" not in self.config: self.config["api_keys"] = {}
        self.config["api_keys"][provider] = text.strip()

    def _save_current_model_temp(self, text):
        provider = self.provider_combo.currentText()
        if "models" not in self.config: self.config["models"] = {}
        self.config["models"][provider] = text

    def get_config(self):
        return self.config
        
    def _clear_cache(self):
        cache_dir = os.path.expanduser("~/.jcode/diagram_cache")
        if os.path.exists(cache_dir):
            try:
                count = 0
                for f in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, f)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        count += 1
                QMessageBox.information(self, "Cache", f"{count} arquivos removidos do cache.")
            except Exception as e:
                QMessageBox.warning(self, "Erro", f"Erro ao limpar cache: {e}")
        else:
            QMessageBox.information(self, "Cache", "Cache já está vazio.")

class DiagramWindow(QDialog):
    """Janela independente para geração de diagramas."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("dIAgram - Gerador de Diagramas")
        self.setGeometry(200, 200, 1200, 800)
        
        self.diagram_config = {
            "provider": "Groq",
            "api_keys": {"Groq": "", "OpenAI": "", "Google Gemini": "", "xAI (Grok)": ""},
            "models": {
                "Groq": "llama-3.3-70b-versatile",
                "OpenAI": "gpt-4o",
                "Google Gemini": "gemini-1.5-flash",
                "xAI (Grok)": "grok-beta"
            }
        }
        
        self.groq_thread = None
        self.image_thread = None
        self.current_svg_data = None
        self.current_cache_path = None
        self.current_url = ""
        self.history = []
        self.history_index = -1
        
        self.live_preview_timer = QTimer()
        self.live_preview_timer.setSingleShot(True)
        self.live_preview_timer.setInterval(1000) # 1 segundo de delay
        self.live_preview_timer.timeout.connect(self._render_diagram)
        
        self._setup_ui()
        self._load_config()
        
        # Aplica tema do usuário se disponível
        if parent and hasattr(parent, 'theme_manager'):
            self.apply_theme(parent.theme_manager.current_theme)
        else:
            self.apply_theme({
                "background": "#1e1e1e", "foreground": "#cccccc",
                "sidebar_bg": "#252526", "border_color": "#3e3e42",
                "accent": "#007acc", "selection": "#094771"
            })
        
    def closeEvent(self, event):
        """Desconecta sinais ao fechar para evitar erros de objeto deletado."""
        if self.groq_thread:
            try:
                self.groq_thread.response_ready.disconnect()
                self.groq_thread.error_occurred.disconnect()
            except: pass
            
        if self.image_thread:
            try:
                self.image_thread.content_ready.disconnect()
                self.image_thread.error_occurred.disconnect()
            except: pass
        super().closeEvent(event)

    def _setup_ui(self):
        # Layout principal sem margens para a statusbar colar no fundo
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Container de conteúdo com margens
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        main_layout.addWidget(content_widget)
        
        # --- Toolbar Superior ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # Grupo Histórico
        self.btn_prev_history = QPushButton()
        self.btn_prev_history.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft))
        self.btn_prev_history.setToolTip("Histórico Anterior")
        self.btn_prev_history.setFixedSize(32, 32)
        self.btn_prev_history.setEnabled(False)
        self.btn_prev_history.clicked.connect(self._go_prev_history)
        
        self.btn_next_history = QPushButton()
        self.btn_next_history.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight))
        self.btn_next_history.setToolTip("Histórico Próximo")
        self.btn_next_history.setFixedSize(32, 32)
        self.btn_next_history.setEnabled(False)
        self.btn_next_history.clicked.connect(self._go_next_history)
        
        header_layout.addWidget(self.btn_prev_history)
        header_layout.addWidget(self.btn_next_history)
        
        # Botão Config (Agora abre Settings Dialog)
        self.config_btn = QPushButton("Config")
        self.config_btn.setToolTip("Configurações (API, Cache)")
        self.config_btn.clicked.connect(self._configure_api)
        header_layout.addWidget(self.config_btn)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        header_layout.addWidget(line)
        
        # Seletores
        header_layout.addWidget(QLabel("Tipo:"))
        self.diagram_type = QComboBox()
        self.diagram_type.addItems([
            "Arquitetura do Projeto",
            "Diagrama de Classes",
            "Fluxo de Dados",
            "Dependências",
            "Módulos e Componentes",
            "Fluxograma Genérico"
        ])
        self.diagram_type.setMinimumWidth(150)
        header_layout.addWidget(self.diagram_type)
        
        self.template_combo = QComboBox()
        self.template_combo.addItems([
            "Templates Rápidos...",
            "CRUD API (Básico)",
            "Microservices (E-commerce)",
            "Arquitetura MVC",
            "Pipeline de Dados (ETL)",
            "Fluxo de Autenticação (OAuth2)"
        ])
        self.template_combo.setToolTip("Selecione um modelo para preencher a descrição automaticamente")
        self.template_combo.currentTextChanged.connect(self._on_template_changed)
        self.template_combo.setMinimumWidth(150)
        header_layout.addWidget(self.template_combo)
        
        header_layout.addStretch()
        
        # Botão Limpar
        self.btn_clear = QPushButton("Limpar")
        self.btn_clear.setToolTip("Limpar tudo para um novo diagrama")
        self.btn_clear.clicked.connect(self._clear_all)
        header_layout.addWidget(self.btn_clear)
        
        # Botão Gerar (Destaque)
        self.generate_btn = QPushButton(" Gerar Diagrama")
        self.generate_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.generate_btn.clicked.connect(self._generate_diagram)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ea043; 
                color: white; 
                font-weight: bold; 
                padding: 6px 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover { background-color: #3fb950; }
            QPushButton:disabled { background-color: #238636; opacity: 0.6; }
        """)
        header_layout.addWidget(self.generate_btn)
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Splitter para input e output
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Área de input - código do projeto
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        
        input_header = QHBoxLayout()
        input_header.addWidget(QLabel("Código do Projeto:"))
        input_header.addStretch()
        
        self.btn_select_files = QPushButton("Selecionar Arquivos")
        self.btn_select_files.setToolTip("Seleciona arquivos e extrai a estrutura para economizar tokens")
        self.btn_select_files.clicked.connect(self._select_files)
        self.btn_select_files.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #3e3e42;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """)
        input_header.addWidget(self.btn_select_files)
        
        input_layout.addLayout(input_header)
        
        self.code_input = QTextEdit()
        self.code_input.setPlaceholderText("Cole aqui o código ou estrutura do projeto...")
        self.code_input.setFont(QFont("Consolas", 10))
        input_layout.addWidget(self.code_input)
        
        # Área de output - diagrama gerado
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        
        self.tabs = QTabWidget()
        
        # Tab 1: Visualização
        self.preview_tab = QWidget()
        preview_layout = QVBoxLayout(self.preview_tab)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background-color: #2b2b2b; border: none;")
        
        self.preview_label = QLabel("Gere um diagrama para visualizar")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.preview_label)
        preview_layout.addWidget(self.scroll_area)
        
        # Botões de ação da visualização
        preview_actions = QHBoxLayout()
        self.btn_open_browser = QPushButton(" Navegador")
        self.btn_open_browser.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton))
        self.btn_open_browser.clicked.connect(self._open_in_browser)
        self.btn_download_svg = QPushButton(" Salvar SVG")
        self.btn_download_svg.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_download_svg.clicked.connect(self._download_svg)
        
        preview_actions.addStretch()
        preview_actions.addWidget(self.btn_open_browser)
        preview_actions.addWidget(self.btn_download_svg)
        preview_layout.addLayout(preview_actions)
        
        # Tab 2: Código
        self.code_tab = QWidget()
        code_layout = QVBoxLayout(self.code_tab)
        code_layout.setContentsMargins(0, 0, 0, 0)
        
        self.diagram_output = QTextEdit()
        self.diagram_output.setPlaceholderText("O código Mermaid aparecerá aqui...")
        self.diagram_output.setFont(QFont("Consolas", 10))
        self.diagram_output.textChanged.connect(self._on_code_changed)
        code_layout.addWidget(self.diagram_output)
        
        self.tabs.addTab(self.preview_tab, "Visualização")
        self.tabs.addTab(self.code_tab, "Código Mermaid")
        
        output_layout.addWidget(self.tabs)
        
        # Controles de Output
        controls_layout = QHBoxLayout()
        
        self.btn_render = QPushButton(" Atualizar Visualização")
        self.btn_render.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_render.clicked.connect(self._render_diagram)
        
        self.chk_live_preview = QCheckBox("Live Preview")
        self.chk_live_preview.setToolTip("Atualiza o diagrama automaticamente ao editar o código")
        
        controls_layout.addWidget(self.btn_render)
        controls_layout.addWidget(self.chk_live_preview)
        controls_layout.addStretch()
        
        output_layout.addLayout(controls_layout)
        
        splitter.addWidget(input_widget)
        splitter.addWidget(output_widget)
        splitter.setSizes([400, 800])
        
        layout.addWidget(splitter)
        
        # Status bar customizada
        self.status_bar_frame = QFrame()
        self.status_bar_frame.setFixedHeight(28)
        sb_layout = QHBoxLayout(self.status_bar_frame)
        sb_layout.setContentsMargins(10, 0, 10, 0)
        
        self.status_label = QLabel("Pronto")
        self.status_label.setStyleSheet("background: transparent; border: none; color: white;")
        sb_layout.addWidget(self.status_label)
        
        sb_layout.addStretch()
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #d73a49; 
                color: white; 
                border: none; 
                border-radius: 3px; 
                padding: 2px 8px; 
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #cb2431; }
        """)
        self.btn_cancel.clicked.connect(self._cancel_generation)
        self.btn_cancel.hide()
        sb_layout.addWidget(self.btn_cancel)
        
        main_layout.addWidget(self.status_bar_frame)
        
    def _on_template_changed(self, text):
        if text == "Templates Rápidos...":
            return
            
        templates = {
            "CRUD API (Básico)": 
                "Sistema de API REST para gerenciamento de Usuários.\n"
                "Entidades: User (id, name, email).\n"
                "Camadas:\n"
                "- UserController: Endpoints HTTP (GET, POST, PUT, DELETE)\n"
                "- UserService: Lógica de negócios e validação\n"
                "- UserRepository: Acesso a dados\n"
                "- Database: PostgreSQL",
                
            "Microservices (E-commerce)":
                "Arquitetura de Microsserviços para Loja Online.\n"
                "Componentes:\n"
                "1. API Gateway (Nginx) - Ponto de entrada\n"
                "2. Auth Service - Gerencia tokens JWT\n"
                "3. Catalog Service - Gerencia produtos (MongoDB)\n"
                "4. Order Service - Gerencia pedidos (PostgreSQL)\n"
                "5. Payment Service - Processa pagamentos\n"
                "6. Notification Service - Envia emails\n"
                "Comunicação: REST (Síncrono) e RabbitMQ (Assíncrono para Pedido Criado -> Notificação)",
                
            "Arquitetura MVC":
                "Padrão Model-View-Controller para Aplicação Web.\n"
                "- View: Interface do usuário (HTML/CSS/JS)\n"
                "- Controller: Recebe input do usuário, interage com Model\n"
                "- Model: Lógica de dados e regras de negócio\n"
                "- Database: Persistência\n"
                "Fluxo: Usuário -> View -> Controller -> Model -> Database",
                
            "Pipeline de Dados (ETL)":
                "Pipeline de processamento de dados Big Data.\n"
                "1. Sources: Logs de Servidor, APIs Externas, Banco Transacional\n"
                "2. Ingestion: Apache Kafka (Buffer)\n"
                "3. Processing: Apache Spark (Limpeza e Agregação)\n"
                "4. Storage: Data Lake (S3 / HDFS)\n"
                "5. Serving: Data Warehouse (Snowflake)\n"
                "6. Visualization: PowerBI / Metabase",
                
            "Fluxo de Autenticação (OAuth2)":
                "Fluxo de Autenticação OAuth2 Authorization Code.\n"
                "Atores: Resource Owner (Usuário), User-Agent (Browser), Client (App), Auth Server, Resource Server.\n"
                "Passos:\n"
                "1. Client redireciona User-Agent para Auth Server.\n"
                "2. Usuário faz login e aprova acesso.\n"
                "3. Auth Server redireciona com Authorization Code.\n"
                "4. Client troca Code por Access Token.\n"
                "5. Client acessa Resource Server com Token."
        }
        
        content = templates.get(text)
        if content:
            self.code_input.setPlainText(content)
            # Ajusta o tipo de diagrama automaticamente para melhor resultado
            if "Fluxo" in text:
                index = self.diagram_type.findText("Fluxo de Dados")
                if index >= 0: self.diagram_type.setCurrentIndex(index)
            elif "Arquitetura" in text or "Microservices" in text:
                index = self.diagram_type.findText("Arquitetura do Projeto")
                if index >= 0: self.diagram_type.setCurrentIndex(index)
            elif "CRUD" in text:
                index = self.diagram_type.findText("Diagrama de Classes")
                if index >= 0: self.diagram_type.setCurrentIndex(index)

    def _on_code_changed(self):
        """Acionado quando o código Mermaid é alterado manualmente."""
        if self.chk_live_preview.isChecked():
            self.live_preview_timer.start()

    def _load_config(self):
        """Carrega configuração do arquivo."""
        config_file = os.path.expanduser("~/.jcode/diagram_config.json")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    loaded = json.load(f)
                    # Migração de config antiga
                    if "groq_api_key" in loaded and "api_keys" not in loaded:
                        self.diagram_config["api_keys"]["Groq"] = loaded["groq_api_key"]
                    else:
                        self.diagram_config.update(loaded)
        except:
            pass
            
    def _save_config(self):
        """Salva configuração no arquivo."""
        config_dir = os.path.expanduser("~/.jcode")
        os.makedirs(config_dir, exist_ok=True)
        config_file = os.path.join(config_dir, "diagram_config.json")
        
        try:
            with open(config_file, 'w') as f:
                json.dump(self.diagram_config, f)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar configurações: {e}")

    def _clear_all(self):
        """Limpa o estado atual para um novo diagrama."""
        self.code_input.clear()
        self.diagram_output.clear()
        
        # Recria o label para garantir que o objeto C++ existe
        self.preview_label = QLabel("Gere um diagrama para visualizar")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.preview_label)
        
        self.current_svg_data = None
        self.current_url = ""
        self.status_label.setText("Limpo.")

    def _select_files(self):
        """Seleciona arquivos e gera um resumo estrutural para economizar tokens."""
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar Arquivos do Projeto")
        if not files:
            return
            
        summary = []
        total_lines = 0
        
        for file_path in files:
            try:
                rel_path = os.path.basename(file_path)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                ext = os.path.splitext(file_path)[1].lower()
                file_summary = self._extract_structure(content, ext)
                
                summary.append(f"# File: {rel_path}\n{file_summary}\n")
                total_lines += len(file_summary.splitlines())
            except Exception as e:
                summary.append(f"# Error reading {rel_path}: {e}\n")
                
        self.code_input.setPlainText("\n".join(summary))
        self.status_label.setText(f"{len(files)} arquivos processados. Resumo gerado com ~{total_lines} linhas.")

    def _extract_structure(self, content, ext):
        """Extrai linhas de definição e documentação para reduzir o tamanho do prompt."""
        lines = content.splitlines()
        structure = []
        
        in_docstring = False
        doc_marker = None
        
        is_py = ext == '.py'
        
        for line in lines:
            l = line.strip()
            if not l: continue
            
            # Extração de Docstrings e Comentários
            if is_py:
                if in_docstring:
                    structure.append(line)
                    if doc_marker in l:
                        in_docstring = False
                        doc_marker = None
                    continue
                
                if l.startswith(('"""', "'''")):
                    structure.append(line)
                    if l.count(l[:3]) == 1: # Começa mas não termina na mesma linha (simplificado)
                        in_docstring = True
                        doc_marker = l[:3]
                    continue
                    
                if l.startswith('#'):
                    structure.append(line)
                    continue
            else:
                # C-style comments (JS, Java, C++, etc)
                if in_docstring:
                    structure.append(line)
                    if '*/' in l:
                        in_docstring = False
                    continue
                
                if l.startswith('/*'):
                    structure.append(line)
                    if '*/' not in l:
                        in_docstring = True
                    continue
                    
                if l.startswith('//'):
                    structure.append(line)
                    continue

            # Definições de estrutura
            if l.startswith(('def ', 'class ', 'import ', 'from ', '@', 'export ', 'interface ', 'type ', 'function ', 'public ', 'private ', 'async ')):
                structure.append(line)
            elif l.endswith(':') or l.endswith('{'):
                structure.append(line)
                    
        return "\n".join(structure)

    def _update_history_buttons(self):
        self.btn_prev_history.setEnabled(self.history_index > 0)
        self.btn_next_history.setEnabled(self.history_index < len(self.history) - 1)
        if self.history:
            self.status_label.setText(f"Histórico: {self.history_index + 1}/{len(self.history)}")

    def _go_prev_history(self):
        if self.history_index > 0:
            self.history_index -= 1
            self._load_history_item()

    def _go_next_history(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._load_history_item()

    def _load_history_item(self):
        item = self.history[self.history_index]
        
        self.code_input.blockSignals(True)
        self.diagram_type.blockSignals(True)
        self.diagram_output.blockSignals(True)
        
        self.code_input.setPlainText(item["input"])
        self.diagram_type.setCurrentText(item["type"])
        self.diagram_output.setPlainText(item["output"])
        
        self.code_input.blockSignals(False)
        self.diagram_type.blockSignals(False)
        self.diagram_output.blockSignals(False)
        
        self._update_history_buttons()
        
        if item.get("svg_data"):
            self.current_svg_data = item["svg_data"]
            self.current_url = item.get("url", "")
            self.svg_widget = QSvgWidget()
            self.svg_widget.load(self.current_svg_data)
            self.scroll_area.setWidget(self.svg_widget)
        else:
            self._render_diagram()
            
    def _configure_api(self):
        """Abre diálogo para configurar API key e Cache."""
        dlg = DiagramSettingsDialog(self.diagram_config, self)
        if dlg.exec():
            self.diagram_config = dlg.get_config()
            self._save_config()
            self.status_label.setText("Configurações salvas!")
            
    def _generate_diagram(self):
        """Inicia geração do diagrama."""
        provider = self.diagram_config.get("provider", "Groq")
        api_key = self.diagram_config.get("api_keys", {}).get(provider, "")
        model = self.diagram_config.get("models", {}).get(provider, "")
        
        if not api_key:
            QMessageBox.warning(self, "API Key", f"Configure a API Key para {provider} primeiro!")
            return
            
        code = self.code_input.toPlainText().strip()
        if not code:
            QMessageBox.warning(self, "Código", "Insira o código do projeto primeiro!")
            return
            
        diagram_type = self.diagram_type.currentText()
        
        # Constrói o prompt baseado no tipo de diagrama
        prompts = {
            "Arquitetura do Projeto": f"Analise este código e gere um diagrama de arquitetura completo em Mermaid. Inclua módulos, camadas, e principais componentes:\n\n{code}",
            "Diagrama de Classes": f"Crie um diagrama de classes UML em Mermaid baseado neste código. Inclua herança, composição e interfaces:\n\n{code}",
            "Fluxo de Dados": f"Gere um diagrama de fluxo de dados em Mermaid mostrando como a informação flui através do sistema:\n\n{code}",
            "Dependências": f"Crie um grafo de dependências em Mermaid mostrando as relações entre os módulos:\n\n{code}",
            "Módulos e Componentes": f"Analise e gere um diagrama mostrando a estrutura de módulos e componentes:\n\n{code}",
            "Fluxograma Genérico": f"Crie um fluxograma (flowchart) detalhado em Mermaid representando a lógica deste código:\n\n{code}"
        }
        
        prompt = prompts.get(diagram_type, prompts["Arquitetura do Projeto"])
        
        # Interrompe thread anterior se existir
        if self.groq_thread and self.groq_thread.isRunning():
            try:
                self.groq_thread.response_ready.disconnect()
                self.groq_thread.error_occurred.disconnect()
            except: pass
            self.groq_thread.quit()

        # Inicia thread para API
        self.groq_thread = AIDiagramThread(provider, api_key, prompt, model)
        self.groq_thread.response_ready.connect(self._on_diagram_ready)
        self.groq_thread.error_occurred.connect(self._on_error)
        
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText(f"Gerando diagrama com {provider}...")
        self.btn_cancel.show()
        
        self.groq_thread.start()
        
    def _on_diagram_ready(self, diagram: str):
        """Recebe diagrama gerado."""
        self.diagram_output.setPlainText(diagram)
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.btn_cancel.hide()
        self.status_label.setText("Diagrama gerado com sucesso!")
        self.tabs.setCurrentWidget(self.preview_tab)
        
        # Adiciona ao histórico
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index+1]
            
        self.history.append({
            "input": self.code_input.toPlainText(),
            "type": self.diagram_type.currentText(),
            "output": diagram,
            "svg_data": None,
            "url": None
        })
        self.history_index = len(self.history) - 1
        self._update_history_buttons()
        
        self._render_diagram()
        
    def _on_error(self, error: str):
        """Trata erros da API."""
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Erro: {error}")
        self.btn_cancel.hide()
        QMessageBox.critical(self, "Erro na API", error)

    def _render_diagram(self):
        """Renderiza o diagrama visualmente usando mermaid.ink."""
        try:
            if not self.isVisible(): return
        except RuntimeError: return

        code = self.diagram_output.toPlainText().strip()
        if not code:
            return
            
        try:
            # Codifica o diagrama em base64 para a URL
            base64_str = base64.b64encode(code.encode("utf-8")).decode("ascii")
            # Adiciona tema escuro para combinar com o editor
            
            # --- Cache System ---
            cache_dir = os.path.expanduser("~/.jcode/diagram_cache")
            os.makedirs(cache_dir, exist_ok=True)
            code_hash = hashlib.md5(code.encode('utf-8')).hexdigest()
            self.current_cache_path = os.path.join(cache_dir, f"{code_hash}.svg")
            
            if os.path.exists(self.current_cache_path):
                with open(self.current_cache_path, 'rb') as f:
                    self._on_content_ready(f.read())
                self.status_label.setText("Diagrama carregado do cache local.")
                return
            # --------------------

            url = f"https://mermaid.ink/svg/{base64_str}?theme=dark&bgColor=2b2b2b"
            self.current_url = url
            
            self.preview_label = QLabel("Carregando imagem...")
            self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.scroll_area.setWidget(self.preview_label)
            self.btn_cancel.show()
            
            # Interrompe download anterior para evitar condições de corrida
            if self.image_thread and self.image_thread.isRunning():
                try:
                    self.image_thread.content_ready.disconnect()
                    self.image_thread.error_occurred.disconnect()
                except: pass
                self.image_thread.quit()

            self.image_thread = ImageDownloadThread(url)
            self.image_thread.content_ready.connect(self._on_content_ready)
            self.image_thread.error_occurred.connect(self._on_image_error)
            self.image_thread.start()
        except RuntimeError:
            pass # Objeto deletado
        except Exception as e:
            self._on_image_error(str(e))
            
    def _on_content_ready(self, data: bytes):
        try:
            self.current_svg_data = data
            
            # Salva no cache se não existir
            if self.current_cache_path and not os.path.exists(self.current_cache_path):
                try:
                    with open(self.current_cache_path, 'wb') as f:
                        f.write(data)
                except: pass
            
            # Atualiza cache do histórico
            if 0 <= self.history_index < len(self.history):
                self.history[self.history_index]["svg_data"] = data
                self.history[self.history_index]["url"] = self.current_url
            
            self.svg_widget = QSvgWidget()
            self.svg_widget.load(data)
            self.scroll_area.setWidget(self.svg_widget)
            self.btn_cancel.hide()
            self.status_label.setText("Pronto")
        except RuntimeError:
            pass
        
    def _on_image_error(self, error):
        self.preview_label = QLabel(f"Erro ao renderizar: {error}\nVerifique sua conexão ou a sintaxe do diagrama.")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidget(self.preview_label)
        self.btn_cancel.hide()

    def _open_in_browser(self):
        """Abre o diagrama atual no navegador padrão."""
        if self.current_url:
            QDesktopServices.openUrl(QUrl(self.current_url))
        else:
            QMessageBox.warning(self, "Aviso", "Gere um diagrama primeiro.")

    def _download_svg(self):
        """Baixa o arquivo SVG diretamente."""
        if not self.current_svg_data:
            QMessageBox.warning(self, "Aviso", "Nenhum diagrama gerado para baixar.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Baixar SVG", "diagrama.svg", "Scalable Vector Graphics (*.svg)")
        if file_path:
            with open(file_path, 'wb') as f:
                f.write(self.current_svg_data)
            self.status_label.setText(f"SVG salvo com sucesso: {os.path.basename(file_path)}")

    def _cancel_generation(self):
        """Cancela a geração ou download em andamento."""
        if self.groq_thread and self.groq_thread.isRunning():
            try: 
                self.groq_thread.response_ready.disconnect()
                self.groq_thread.error_occurred.disconnect()
            except: pass
            # Não usamos wait() para não travar a UI, apenas desconectamos
            
        if self.image_thread and self.image_thread.isRunning():
            try: 
                self.image_thread.content_ready.disconnect()
                self.image_thread.error_occurred.disconnect()
            except: pass
            
        self.status_label.setText("Operação cancelada.")
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        self.btn_cancel.hide()

    def apply_theme(self, theme):
        """Aplica o tema visual à janela."""
        bg = theme.get("background", "#1e1e1e")
        fg = theme.get("foreground", "#cccccc")
        input_bg = theme.get("sidebar_bg", "#252526")
        border = theme.get("border_color", "#3e3e42")
        accent = theme.get("accent", "#007acc")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg};
                color: {fg};
            }}
            QTextEdit {{
                background-color: {input_bg};
                border: 1px solid {border};
                color: {fg};
                padding: 8px;
                font-family: 'Consolas', monospace;
                border-radius: 4px;
            }}
            QTextEdit:focus {{
                border: 1px solid {accent};
            }}
            QPushButton {{
                background-color: {input_bg};
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
            QComboBox {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                padding: 4px;
                border-radius: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QProgressBar {{
                border: none;
                background-color: {input_bg};
                height: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
            }}
            QSplitter::handle {{
                background-color: {border};
            }}
            QTabWidget::pane {{
                border: 1px solid {border};
            }}
            QTabBar::tab {{
                background: {input_bg};
                color: {fg};
                padding: 5px 10px;
                border: 1px solid {border};
            }}
            QTabBar::tab:selected {{
                background: {bg};
                border-bottom: 2px solid {accent};
            }}
        """)
        
        if hasattr(self, 'status_bar_frame'):
            self.status_bar_frame.setStyleSheet(f"background-color: {accent}; color: white;")
            
        if hasattr(self, 'generate_btn'):
             self.generate_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2ea043; 
                    color: white; 
                    font-weight: bold; 
                    padding: 6px 12px;
                    border-radius: 4px;
                    border: none;
                }}
                QPushButton:hover {{ background-color: #3fb950; }}
                QPushButton:disabled {{ background-color: #238636; opacity: 0.6; }}
            """)

# Função principal do plugin - será chamada pelo ExtensionBridge
def create_diagram_window():
    """Cria e retorna a janela do plugin."""
    return DiagramWindow()

# Registro do plugin
PLUGIN_INFO = {
    "name": "dIAgram",
    "version": "1.0.0",
    "description": "Gerador de diagramas usando API Groq",
    "author": "JCode Plugin System"
}

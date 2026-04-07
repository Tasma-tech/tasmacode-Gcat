from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
                               QLabel, QSlider, QCheckBox, QComboBox, QPushButton, QDialogButtonBox, QLineEdit, 
                               QSpinBox, QColorDialog, QFileDialog, QMessageBox, QCompleter, QRadioButton, QListWidget, QStackedWidget, QScrollArea, QStyledItemDelegate, QStyle)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QTextDocument, QAbstractTextDocumentLayout, QPainter

class HighlightDelegate(QStyledItemDelegate):
    """Delegate para desenhar o texto com destaque (highlight) para a busca."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.search_text = ""

    def paint(self, painter, option, index):
        painter.save()
        
        # No PySide6, initStyleOption modifica o objeto 'option' in-place.
        self.initStyleOption(option, index)
        text = index.data(Qt.DisplayRole)
        
        if self.search_text and self.search_text.lower() in text.lower():
            # Escapa o texto e adiciona a tag de destaque na parte correspondente
            start_idx = text.lower().find(self.search_text.lower())
            end_idx = start_idx + len(self.search_text)
            
            highlighted_text = (f"{text[:start_idx]}"
                               f"<span style='background-color: #ffc600; color: #000000;'>{text[start_idx:end_idx]}</span>"
                               f"{text[end_idx:]}")
            
            doc = QTextDocument()
            # Aplica o estilo de cor padrão do item antes do destaque
            color = option.palette.text().color().name()
            doc.setHtml(f"<html><body style='color: {color};'>{highlighted_text}</body></html>")
            
            option.text = "" # Limpa o texto original para não sobrepor
            # Verifica se self.parent() é válido e tem um estilo
            if self.parent() and self.parent().style():
                self.parent().style().drawControl(QStyle.CE_ItemViewItem, option, painter)
            # else: Fallback se o estilo não estiver disponível, o fundo do item não será desenhado corretamente
            
            painter.translate(option.rect.left() + 10, option.rect.top() + 8) # Ajuste de padding
            doc.drawContents(painter)
        else:
            super().paint(painter, option, index)
        
        painter.restore()

class SettingsDialog(QDialog):
    """Janela de preferências do usuário."""

    def __init__(self, config_manager, theme_manager, font_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        self.font_manager = font_manager
        
        # Cópia local das configurações para edição
        self.current_config = config_manager.config.copy()
        
        self.setWindowTitle("Configurações")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: #252526; color: #cccccc;")

        # Layout Principal (Horizontal: Sidebar | Conteúdo)
        self.main_layout = QVBoxLayout(self)
        self.content_h_layout = QHBoxLayout()
        self.content_h_layout.setSpacing(0)
        self.content_h_layout.setContentsMargins(0, 0, 0, 0)

        # --- Coluna da Sidebar (Navegação + Busca) ---
        self.sidebar_container = QWidget()
        self.sidebar_container.setFixedWidth(200)
        self.sidebar_container.setStyleSheet("background-color: #2d2d2d; border-right: 1px solid #454545;")
        self.sidebar_layout = QVBoxLayout(self.sidebar_container)
        self.sidebar_layout.setContentsMargins(10, 10, 10, 10)
        self.sidebar_layout.setSpacing(10)

        # Barra de Pesquisa
        self.sidebar_search = QLineEdit()
        self.sidebar_search.setPlaceholderText("Buscar...")
        self.sidebar_search.setStyleSheet("""
            QLineEdit {
                background-color: #3c3c3c;
                color: #cccccc;
                border: 1px solid #454545;
                border-radius: 4px;
                padding: 6px;
            }
            QLineEdit:focus { border: 1px solid #007acc; }
        """)
        self.sidebar_search.textChanged.connect(self._filter_sidebar)
        self.sidebar_layout.addWidget(self.sidebar_search)

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setStyleSheet("""
            QListWidget#SettingsSidebar {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget#SettingsSidebar::item {
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 4px;
                color: #858585;
                font-weight: bold;
            }
            QListWidget#SettingsSidebar::item:selected {
                background-color: #37373d;
                color: white;
            }
            QListWidget#SettingsSidebar::item:hover:!selected {
                background-color: #2a2d2e;
            }
        """)
        self.sidebar_layout.addWidget(self.sidebar)
        
        # Aplica o delegate de destaque
        self.highlight_delegate = HighlightDelegate(self.sidebar)
        self.sidebar.setItemDelegate(self.highlight_delegate)

        self.pages = QStackedWidget()
        self.pages.setStyleSheet("background-color: #1e1e1e; border: none;")

        self.content_h_layout.addWidget(self.sidebar_container)
        self.content_h_layout.addWidget(self.pages, 1)
        self.main_layout.addLayout(self.content_h_layout)

        # Categorias
        categories = [
            ("Editor", self._create_editor_page()),
            ("Interface", self._create_interface_page()),
            ("Sistema", self._create_system_page()),
            ("Rede", self._create_network_page())
        ]

        for name, page in categories:
            self.sidebar.addItem(name)
            self.pages.addWidget(page)

        self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        # --- Botões de Ação ---
        self._setup_action_buttons()

    def _create_scroll_page(self, layout):
        widget = QWidget()
        widget.setLayout(layout)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(widget)
        scroll.setStyleSheet("background: transparent; border: none;")
        return scroll

    def _create_editor_page(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(15)
        
        # Família da Fonte
        lbl_font_header = QLabel("TIPOGRAFIA")
        lbl_font_header.setStyleSheet("font-weight: bold; color: #569cd6; font-size: 11px;")
        layout.addWidget(lbl_font_header)

        lbl_font_family = QLabel("Fonte do Editor:")
        
        font_selection_layout = QHBoxLayout()
        self.combo_font_family = QComboBox()
        self.combo_font_family.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px;")
        # Torna o ComboBox pesquisável
        self.combo_font_family.setEditable(True)
        self.combo_font_family.setInsertPolicy(QComboBox.NoInsert)
        self.combo_font_family.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.combo_font_family.completer().setFilterMode(Qt.MatchContains)
        
        btn_install_font = QPushButton("Instalar Fonte (ZIP)")
        btn_install_font.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_install_font.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px; border: 1px solid #454545;")
        btn_install_font.clicked.connect(self._install_font_zip)
        
        font_selection_layout.addWidget(self.combo_font_family)
        font_selection_layout.addWidget(btn_install_font)
        
        # Preview Label
        self.lbl_font_preview = QLabel("The quick brown fox jumps over the lazy dog. 1234567890")
        self.lbl_font_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_font_preview.setFixedHeight(40)
        self.lbl_font_preview.setStyleSheet("background-color: #1e1e1e; color: #cccccc; border: 1px solid #454545; border-radius: 4px; margin-top: 5px; font-size: 14px;")
        
        monospace_fonts = self.font_manager.get_monospace_fonts()
        self.combo_font_family.addItems(monospace_fonts)
        current_font = self.current_config.get('font_family', 'JetBrainsMono Nerd Font')
        if current_font in monospace_fonts:
            self.combo_font_family.setCurrentText(current_font)
            
        self.combo_font_family.currentTextChanged.connect(self._update_font_preview)
        self.combo_font_family.currentTextChanged.connect(lambda v: (self._update_local('font_family', v), self._apply_live()))
        
        # Initial preview
        self._update_font_preview(self.combo_font_family.currentText())

        # Tamanho da Fonte
        lbl_font = QLabel(f"Tamanho da Fonte: {self.current_config.get('font_size')}")
        slider_font = QSlider(Qt.Orientation.Horizontal)
        slider_font.setRange(6, 72)
        slider_font.setValue(self.current_config.get('font_size'))
        slider_font.valueChanged.connect(lambda v: (lbl_font.setText(f"Tamanho da Fonte: {v}"), self._update_local('font_size', v), self._apply_live()))
        
        # Ligaduras
        chk_ligatures = QCheckBox("Habilitar Ligaduras de Fonte")
        chk_ligatures.setChecked(self.current_config.get('font_ligatures', True))
        chk_ligatures.toggled.connect(lambda v: (self._update_local('font_ligatures', v), self._apply_live()))

        # Checkboxes
        chk_lines = QCheckBox("Mostrar Números de Linha")
        chk_lines.setChecked(self.current_config.get('line_numbers'))
        chk_lines.toggled.connect(lambda v: (self._update_local('line_numbers', v), self._apply_live()))
        
        chk_indent = QCheckBox("Auto-indentação")
        chk_indent.setChecked(self.current_config.get('auto_indent'))
        chk_indent.toggled.connect(lambda v: (self._update_local('auto_indent', v), self._apply_live()))
        
        chk_autocomplete = QCheckBox("Habilitar Autocomplete (Beta)")
        chk_autocomplete.setChecked(self.current_config.get('enable_autocomplete', False))
        chk_autocomplete.toggled.connect(lambda v: (self._update_local('enable_autocomplete', v), self._apply_live()))

        # Nova seção: Quebra de Linha
        lbl_wrap_title = QLabel("Opções de Linha Longa:")
        lbl_wrap_title.setStyleSheet("font-weight: bold; margin-top: 10px;")

        radio_horizontal = QRadioButton("Scroll Horizontal")
        radio_wrap = QRadioButton("Quebra de Linha Visual")

        wrap_mode = self.current_config.get("wrap_mode", "horizontal")
        if wrap_mode == "horizontal":
            radio_horizontal.setChecked(True)
        else:
            radio_wrap.setChecked(True)

        # Conecta as mudanças
        radio_horizontal.toggled.connect(lambda checked: (
            self._update_local("wrap_mode", "horizontal"), self._apply_live()
        ) if checked else None)

        radio_wrap.toggled.connect(lambda checked: (
            self._update_local("wrap_mode", "wrap"), self._apply_live()
        ) if checked else None)

        lbl_delay = QLabel(f"Atraso do Autocomplete (ms): {self.current_config.get('autocomplete_delay', 300)}")
        slider_delay = QSlider(Qt.Orientation.Horizontal)
        slider_delay.setRange(0, 2000)
        slider_delay.setValue(self.current_config.get('autocomplete_delay', 300))
        slider_delay.valueChanged.connect(lambda v: (lbl_delay.setText(f"Atraso do Autocomplete (ms): {v}"), self._update_local('autocomplete_delay', v)))

        # Smear Cursor Settings
        lbl_smear_header = QLabel("EFEITOS VISUAIS")
        lbl_smear_header.setStyleSheet("font-weight: bold; color: #569cd6; font-size: 11px; margin-top: 15px;")
        layout.addWidget(lbl_smear_header)

        lbl_smear_title = QLabel("Smear Cursor (Rastro do Cursor):")
        
        # Physics Preset
        lbl_preset = QLabel("Preset de Física:")
        self.combo_preset = QComboBox()
        self.combo_preset.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px;")
        self.combo_preset.addItems(["Default", "Gelatina", "Elástico", "Rígido"])
        self.combo_preset.setCurrentText(self.current_config.get("smear_physics_preset", "Default"))
        self.combo_preset.currentTextChanged.connect(self._on_preset_changed)

        # Glow Color
        lbl_glow = QLabel("Cor do Glow (Partículas):")
        glow_layout = QHBoxLayout()
        self.btn_glow = QPushButton()
        self.btn_glow.setFixedSize(50, 25)
        self.btn_glow.setCursor(Qt.CursorShape.PointingHandCursor)
        current_glow = self.current_config.get("smear_glow_color")
        self._update_glow_btn_style(current_glow)
        self.btn_glow.clicked.connect(self._pick_glow_color)
        
        btn_clear_glow = QPushButton("Auto")
        btn_clear_glow.setToolTip("Usar cor do cursor")
        btn_clear_glow.clicked.connect(lambda: (self._update_local("smear_glow_color", ""), self._update_glow_btn_style(""), self._apply_live()))
        glow_layout.addWidget(self.btn_glow)
        glow_layout.addWidget(btn_clear_glow)
        glow_layout.addStretch()

        lbl_stiffness = QLabel(f"Intensidade do Smear Cursor: {self.current_config.get('smear_stiffness', 0.6):.2f}")
        self.slider_stiffness = QSlider(Qt.Orientation.Horizontal)
        self.slider_stiffness.setRange(1, 100) # 0.01 a 1.0
        self.slider_stiffness.setValue(int(self.current_config.get('smear_stiffness', 0.6) * 100))
        self.slider_stiffness.valueChanged.connect(lambda v: (lbl_stiffness.setText(f"Intensidade do Smear Cursor: {v/100:.2f}"), self._update_local('smear_stiffness', v/100)))
        
        # Opacidade
        lbl_opacity = QLabel(f"Opacidade do Rastro: {int(self.current_config.get('smear_opacity', 1.0) * 100)}%")
        slider_opacity = QSlider(Qt.Orientation.Horizontal)
        slider_opacity.setRange(10, 100)
        slider_opacity.setValue(int(self.current_config.get('smear_opacity', 1.0) * 100))
        slider_opacity.valueChanged.connect(lambda v: (lbl_opacity.setText(f"Opacidade do Rastro: {v}%"), self._update_local('smear_opacity', v/100)))

        # Sparks
        chk_sparks = QCheckBox("Efeito de Faíscas (Power Mode)")
        chk_sparks.setChecked(self.current_config.get('smear_sparks', False))
        chk_sparks.toggled.connect(lambda v: (self._update_local('smear_sparks', v), self._apply_live()))

        lbl_beta = QLabel("O efeito Smear Cursor pode impactar o desempenho em computadores antigos.")
        lbl_beta.setStyleSheet("color: #808080; font-style: italic; font-size: 11px; margin-left: 20px;")

        layout.addWidget(lbl_font_family)
        layout.addLayout(font_selection_layout)
        layout.addWidget(self.lbl_font_preview)
        layout.addWidget(lbl_font)
        layout.addWidget(slider_font)
        layout.addWidget(chk_ligatures)
        layout.addWidget(chk_lines)
        layout.addWidget(chk_indent)
        layout.addWidget(chk_autocomplete)
        layout.addWidget(lbl_wrap_title)
        layout.addWidget(radio_horizontal)
        layout.addWidget(radio_wrap)
        layout.addWidget(lbl_delay)
        layout.addWidget(slider_delay)
        layout.addWidget(lbl_smear_title)
        layout.addWidget(lbl_preset)
        layout.addWidget(self.combo_preset)
        layout.addWidget(lbl_stiffness)
        layout.addWidget(self.slider_stiffness)
        layout.addWidget(lbl_opacity)
        layout.addWidget(slider_opacity)
        layout.addWidget(chk_sparks)
        layout.addWidget(lbl_glow)
        layout.addLayout(glow_layout)
        layout.addWidget(lbl_beta)
        layout.addStretch()
        
        return self._create_scroll_page(layout)

    def _create_interface_page(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        
        lbl_theme = QLabel("Tema:")
        combo_theme = QComboBox()
        combo_theme.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px;")
        themes = self.theme_manager.get_available_themes()
        combo_theme.addItems(themes)
        current_theme = self.current_config.get('theme')
        if current_theme in themes:
            combo_theme.setCurrentText(current_theme)
        combo_theme.currentTextChanged.connect(lambda v: (self._update_local('theme', v), self._apply_live()))

        layout.addWidget(lbl_theme)
        layout.addWidget(combo_theme)
        
        chk_custom_title = QCheckBox("Usar Barra de Título Customizada (Requer Reinício)")
        chk_custom_title.setChecked(self.current_config.get('use_custom_title_bar', False))
        chk_custom_title.toggled.connect(lambda v: self._update_local('use_custom_title_bar', v))
        layout.addWidget(chk_custom_title)
        layout.addStretch()
        
        return self._create_scroll_page(layout)

    def _create_system_page(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        
        chk_restore = QCheckBox("Restaurar sessão anterior ao iniciar")
        chk_restore.setChecked(self.current_config.get('restore_session'))
        chk_restore.toggled.connect(lambda v: self._update_local('restore_session', v))
        
        chk_tasmafile = QCheckBox("Usar Gerenciador de Arquivos TasmaFile (Experimental)")
        chk_tasmafile.setChecked(self.current_config.get('use_tasmafile', True))
        chk_tasmafile.toggled.connect(lambda v: self._update_local('use_tasmafile', v))
        
        layout.addWidget(chk_tasmafile)
        layout.addWidget(chk_restore)
        layout.addStretch()
        
        return self._create_scroll_page(layout)

    def _create_network_page(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 20, 30, 20)
        
        # Live Server Settings
        lbl_ls_title = QLabel("Live Server:")
        lbl_ls_title.setStyleSheet("font-weight: bold; margin-top: 10px;")
        
        chk_ls_browser = QCheckBox("Abrir navegador automaticamente ao iniciar")
        chk_ls_browser.setChecked(self.current_config.get('live_server_open_browser', True))
        chk_ls_browser.toggled.connect(lambda v: self._update_local('live_server_open_browser', v))

        lbl_ls_port = QLabel("Porta (0 = Automático):")
        spin_ls_port = QSpinBox()
        spin_ls_port.setRange(0, 65535)
        spin_ls_port.setValue(self.current_config.get('live_server_port', 0))
        spin_ls_port.valueChanged.connect(lambda v: self._update_local('live_server_port', v))

        lbl_server = QLabel("Endereço do Servidor Local:")
        self.txt_server = QLineEdit()
        self.txt_server.setPlaceholderText("ex: http://127.0.0.1:5000")
        self.txt_server.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px; border: 1px solid #454545;")
        self.txt_server.setText(self.current_config.get('server_address', ''))
        self.txt_server.textChanged.connect(lambda v: self._update_local('server_address', v))
        
        lbl_note = QLabel("Nota: A conexão com o servidor local está em fase experimental e será ativada em versões futuras.")
        lbl_note.setStyleSheet("font-style: italic; color: #808080; font-size: 11px; margin-top: 5px;")
        lbl_note.setWordWrap(True)
        
        layout.addWidget(lbl_ls_title)
        layout.addWidget(chk_ls_browser)
        layout.addWidget(lbl_ls_port)
        layout.addWidget(spin_ls_port)
        layout.addWidget(lbl_server)
        layout.addWidget(self.txt_server)
        layout.addWidget(lbl_note)
        layout.addStretch()
        
        return self._create_scroll_page(layout)

    def _setup_action_buttons(self):
        # --- Botões de Ação ---
        btn_box = QHBoxLayout()
        btn_apply = QPushButton("Aplicar")
        btn_save = QPushButton("Salvar")
        btn_cancel = QPushButton("Cancelar")
        
        for btn in [btn_apply, btn_save, btn_cancel]:
            btn.setStyleSheet("background-color: #3c3c3c; color: white; padding: 8px 16px; border: 1px solid #454545; border-radius: 4px;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_apply.clicked.connect(self._apply_live)
        btn_save.clicked.connect(self._save_and_close)
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        
        self.main_layout.addLayout(btn_box)

    def _update_local(self, key, value):
        self.current_config[key] = value

    def _update_font_preview(self, font_family):
        font = QFont(font_family)
        font.setPointSize(12)
        self.lbl_font_preview.setFont(font)

    def _install_font_zip(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo de Fonte (ZIP)", "", "Zip Files (*.zip)")
        if file_path:
            installed_families = self.font_manager.install_font_from_zip(file_path)
            if installed_families:
                QMessageBox.information(self, "Sucesso", f"Fontes instaladas: {', '.join(installed_families)}")
                
                # Refresh list
                self.combo_font_family.blockSignals(True)
                self.combo_font_family.clear()
                fonts = self.font_manager.get_monospace_fonts()
                self.combo_font_family.addItems(fonts)
                
                # Seleciona e aplica a primeira fonte instalada
                new_font_to_select = installed_families[0]
                if new_font_to_select in fonts:
                    self.combo_font_family.setCurrentText(new_font_to_select)

                self.combo_font_family.blockSignals(False)
                self._update_font_preview(self.combo_font_family.currentText())
                self._update_local('font_family', self.combo_font_family.currentText())
                self._apply_live()
            else:
                QMessageBox.warning(self, "Erro", "Falha ao instalar fontes. Verifique se o arquivo é um ZIP válido contendo fontes (.ttf, .otf).")

    def _on_preset_changed(self, text):
        self._update_local("smear_physics_preset", text)
        # Atualiza a rigidez baseada no preset
        defaults = {"Default": 0.6, "Gelatina": 0.2, "Elástico": 0.4, "Rígido": 0.8}
        if text in defaults:
            new_stiffness = defaults[text]
            self._update_local("smear_stiffness", new_stiffness)
            self.slider_stiffness.setValue(int(new_stiffness * 100))
        self._apply_live()

    def _pick_glow_color(self):
        current = self.current_config.get("smear_glow_color")
        color = QColorDialog.getColor(QColor(current) if current else Qt.white, self, "Cor do Glow")
        if color.isValid():
            hex_color = color.name()
            self._update_local("smear_glow_color", hex_color)
            self._update_glow_btn_style(hex_color)
            self._apply_live()

    def _update_glow_btn_style(self, color_hex):
        self.btn_glow.setStyleSheet(f"background-color: {color_hex if color_hex else '#555'}; border: 1px solid #777;")

    def _apply_live(self):
        self.config_manager.config_changed.emit(self.current_config)

    def _save_and_close(self):
        addr = self.current_config.get('server_address', '')
        print(f"[Config] Endereço do servidor atualizado para: {addr if addr else 'localhost (default)'}")
        self.config_manager.save_config(self.current_config)
        self.accept()

    def _filter_sidebar(self, text):
        """Filtra as categorias da sidebar com base no texto de pesquisa."""
        search_term = text.lower()
        self.highlight_delegate.search_text = text # Atualiza o texto no delegate
        
        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            category_name = item.text().lower()
            
            # 1. Verifica se o termo está no nome da categoria
            match_found = search_term in category_name
            
            # 2. Se não encontrou no nome, busca dentro da página correspondente
            if not match_found and search_term:
                page_widget = self.pages.widget(i)
                match_found = self._search_in_page(page_widget, search_term)
            
            item.setHidden(not match_found)
        
        self.sidebar.update() # Força o repaint para o delegate agir

    def _search_in_page(self, page_widget, text):
        """Busca recursiva de texto dentro de todos os widgets de uma página."""
        # No PySide6, findChildren não aceita uma tupla de tipos como argumento.
        # Iteramos sobre os tipos que possuem o método .text() para realizar a busca.
        for widget_type in (QLabel, QCheckBox, QRadioButton):
            for widget in page_widget.findChildren(widget_type):
                if text in widget.text().lower():
                    return True
        return False

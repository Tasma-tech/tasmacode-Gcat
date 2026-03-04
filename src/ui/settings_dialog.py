from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
                               QLabel, QSlider, QCheckBox, QComboBox, QPushButton, QDialogButtonBox, QLineEdit, QSpinBox, QColorDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class SettingsDialog(QDialog):
    """Janela de preferências do usuário."""

    def __init__(self, config_manager, theme_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        
        # Cópia local das configurações para edição
        self.current_config = config_manager.config.copy()
        
        self.setWindowTitle("Configurações")
        self.resize(500, 400)
        self.setStyleSheet("background-color: #252526; color: #cccccc;")

        layout = QVBoxLayout(self)

        # --- Abas ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #454545; }
            QTabBar::tab { background: #333333; color: #cccccc; padding: 8px; }
            QTabBar::tab:selected { background: #252526; border-top: 2px solid #007acc; }
        """)
        
        self.tab_editor = QWidget()
        self.tab_interface = QWidget()
        self.tab_system = QWidget()
        self.tab_network = QWidget()
        
        self.tabs.addTab(self.tab_editor, "Editor")
        self.tabs.addTab(self.tab_interface, "Interface")
        self.tabs.addTab(self.tab_system, "Sistema")
        self.tabs.addTab(self.tab_network, "Rede")
        
        layout.addWidget(self.tabs)

        # --- Configuração da Aba Editor ---
        editor_layout = QVBoxLayout(self.tab_editor)
        
        # Tamanho da Fonte
        lbl_font = QLabel(f"Tamanho da Fonte: {self.current_config.get('font_size')}")
        slider_font = QSlider(Qt.Orientation.Horizontal)
        slider_font.setRange(6, 72)
        slider_font.setValue(self.current_config.get('font_size'))
        slider_font.valueChanged.connect(lambda v: (lbl_font.setText(f"Tamanho da Fonte: {v}"), self._update_local('font_size', v), self._apply_live()))
        
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

        lbl_delay = QLabel(f"Atraso do Autocomplete (ms): {self.current_config.get('autocomplete_delay', 300)}")
        slider_delay = QSlider(Qt.Orientation.Horizontal)
        slider_delay.setRange(0, 2000)
        slider_delay.setValue(self.current_config.get('autocomplete_delay', 300))
        slider_delay.valueChanged.connect(lambda v: (lbl_delay.setText(f"Atraso do Autocomplete (ms): {v}"), self._update_local('autocomplete_delay', v)))

        # Smear Cursor Settings
        lbl_smear_title = QLabel("Smear Cursor:")
        lbl_smear_title.setStyleSheet("font-weight: bold; margin-top: 10px;")

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

        lbl_beta = QLabel("Nota: Funcionalidade em testes beta. Pode apresentar instabilidade.")
        lbl_beta.setStyleSheet("color: #808080; font-style: italic; font-size: 11px; margin-left: 20px;")

        editor_layout.addWidget(lbl_font)
        editor_layout.addWidget(slider_font)
        editor_layout.addWidget(chk_lines)
        editor_layout.addWidget(chk_indent)
        editor_layout.addWidget(chk_autocomplete)
        editor_layout.addWidget(lbl_delay)
        editor_layout.addWidget(slider_delay)
        editor_layout.addWidget(lbl_smear_title)
        editor_layout.addWidget(lbl_preset)
        editor_layout.addWidget(self.combo_preset)
        editor_layout.addWidget(lbl_stiffness)
        editor_layout.addWidget(self.slider_stiffness)
        editor_layout.addWidget(lbl_opacity)
        editor_layout.addWidget(slider_opacity)
        editor_layout.addWidget(chk_sparks)
        editor_layout.addWidget(lbl_glow)
        editor_layout.addLayout(glow_layout)
        editor_layout.addWidget(lbl_beta)
        editor_layout.addStretch()

        # --- Configuração da Aba Interface ---
        interface_layout = QVBoxLayout(self.tab_interface)
        
        lbl_theme = QLabel("Tema:")
        combo_theme = QComboBox()
        combo_theme.setStyleSheet("background-color: #3c3c3c; color: white; padding: 5px;")
        themes = self.theme_manager.get_available_themes()
        combo_theme.addItems(themes)
        current_theme = self.current_config.get('theme')
        if current_theme in themes:
            combo_theme.setCurrentText(current_theme)
        combo_theme.currentTextChanged.connect(lambda v: (self._update_local('theme', v), self._apply_live()))

        interface_layout.addWidget(lbl_theme)
        interface_layout.addWidget(combo_theme)
        
        chk_custom_title = QCheckBox("Usar Barra de Título Customizada (Requer Reinício)")
        chk_custom_title.setChecked(self.current_config.get('use_custom_title_bar', False))
        chk_custom_title.toggled.connect(lambda v: self._update_local('use_custom_title_bar', v))
        interface_layout.addWidget(chk_custom_title)
        interface_layout.addStretch()

        # --- Configuração da Aba Sistema ---
        system_layout = QVBoxLayout(self.tab_system)
        
        chk_restore = QCheckBox("Restaurar sessão anterior ao iniciar")
        chk_restore.setChecked(self.current_config.get('restore_session'))
        chk_restore.toggled.connect(lambda v: self._update_local('restore_session', v))
        
        system_layout.addWidget(chk_restore)
        system_layout.addStretch()

        # --- Configuração da Aba Rede ---
        network_layout = QVBoxLayout(self.tab_network)
        
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
        
        network_layout.addWidget(lbl_ls_title)
        network_layout.addWidget(chk_ls_browser)
        network_layout.addWidget(lbl_ls_port)
        network_layout.addWidget(spin_ls_port)
        network_layout.addWidget(lbl_server)
        network_layout.addWidget(self.txt_server)
        network_layout.addWidget(lbl_note)
        network_layout.addStretch()

        # --- Botões de Ação ---
        btn_box = QHBoxLayout()
        btn_apply = QPushButton("Aplicar")
        btn_save = QPushButton("Salvar")
        btn_cancel = QPushButton("Cancelar")
        
        for btn in [btn_apply, btn_save, btn_cancel]:
            btn.setStyleSheet("background-color: #3c3c3c; color: white; padding: 6px 12px; border: 1px solid #454545;")
        
        btn_apply.clicked.connect(self._apply_live)
        btn_save.clicked.connect(self._save_and_close)
        btn_cancel.clicked.connect(self.reject)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_apply)
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        
        layout.addLayout(btn_box)

    def _update_local(self, key, value):
        self.current_config[key] = value

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
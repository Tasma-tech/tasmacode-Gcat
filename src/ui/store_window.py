import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
                               QLabel, QMessageBox, QApplication, QListWidget, QFrame, QListWidgetItem, QWidget, QStyle)
from PySide6.QtCore import Qt, QSize, Signal, QPoint
from PySide6.QtGui import QIcon, QCursor, QColor
from src.core.ui_logic.store_manager import StoreManager

class PluginItemWidget(QWidget):
    """Widget customizado para exibir um item de plugin na grade com um botão de remover ao passar o mouse."""
    remove_requested = Signal(str)

    def __init__(self, plugin_name: str, icon: QIcon, theme: dict, parent=None):
        super().__init__(parent)
        self.plugin_name = plugin_name
        
        # Cores baseadas no tema
        bg = theme.get("sidebar_bg", "#3c3c3c")
        fg = theme.get("foreground", "#cccccc")
        
        # Ajuste de contraste para o card (mais claro se tema escuro, mais escuro se tema claro)
        bg_color = QColor(bg).lighter(110) if QColor(bg).lightness() < 128 else QColor(bg).darker(105)
        
        self.setStyleSheet(f"background-color: {bg_color.name()}; border-radius: 8px;")

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 5, 5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Ícone
        self.icon_label = QLabel()
        self.icon_label.setPixmap(icon.pixmap(QSize(64, 64)))
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Nome
        self.name_label = QLabel(plugin_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet(f"color: {fg}; background: transparent;")

        layout.addWidget(self.icon_label)
        layout.addStretch()
        layout.addWidget(self.name_label)

        # Botão de remover (sem layout, posicionado manualmente sobre o widget)
        self.remove_button = QPushButton(self)
        self.remove_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.remove_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_button.setStyleSheet("""
            QPushButton { 
                background-color: rgba(60, 60, 60, 0.8);
                border: none;
                border-radius: 11px;
            }
            QPushButton:hover { background-color: #dc3545; }
        """)
        self.remove_button.setIconSize(QSize(14, 14))
        self.remove_button.setFixedSize(22, 22)
        self.remove_button.hide()
        self.remove_button.clicked.connect(lambda: self.remove_requested.emit(self.plugin_name))

    def enterEvent(self, event):
        """Mostra o botão quando o mouse entra no widget."""
        self.remove_button.move(self.width() - self.remove_button.width() - 5, 5)
        self.remove_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Esconde o botão quando o mouse sai do widget."""
        self.remove_button.hide()
        super().leaveEvent(event)

class StoreWindow(QDialog):
    """
    Janela para a loja de plugins.
    """
    def __init__(self, root_dir: str, theme_manager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.theme = self.theme_manager.current_theme
        
        self.setWindowTitle("Loja de Plugins")
        self.resize(650, 500)
        
        bg = self.theme.get("background", "#252526")
        fg = self.theme.get("foreground", "#cccccc")
        self.setStyleSheet(f"background-color: {bg}; color: {fg};")

        self.root_dir = root_dir
        self.store_manager = StoreManager(self.root_dir)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title_label = QLabel("Instalar via URL do GitHub")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        input_layout = QHBoxLayout()
        
        input_bg = self.theme.get("sidebar_bg", "#3c3c3c")
        border = self.theme.get("border_color", "#454545")
        accent = self.theme.get("accent", "#007acc")
        
        self.link_plugin = QLineEdit()
        self.link_plugin.setObjectName("link_plugin")
        self.link_plugin.setPlaceholderText("Cole a URL do repositório do plugin aqui...")
        self.link_plugin.setStyleSheet(f"""
            QLineEdit {{
                background-color: {input_bg}; border: 1px solid {border};
                padding: 8px; color: {fg}; border-radius: 4px;
            }}
        """)
        
        self.install_button = QPushButton("Instalar")
        self.install_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.install_button.setStyleSheet(f"QPushButton {{ background-color: {accent}; color: white; padding: 8px 16px; border-radius: 4px; border: none; font-weight: bold; }} QPushButton:hover {{ background-color: {QColor(accent).lighter(110).name()}; }}")
        self.install_button.clicked.connect(self._on_install_clicked)

        input_layout.addWidget(self.link_plugin)
        input_layout.addWidget(self.install_button)
        
        layout.addLayout(input_layout)
        
        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # Lista de Plugins Instalados
        lbl_installed = QLabel("Plugins Instalados")
        lbl_installed.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(lbl_installed)

        self.plugins_list = QListWidget()        
        self.plugins_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.plugins_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.plugins_list.setMovement(QListWidget.Movement.Static)
        self.plugins_list.setIconSize(QSize(80, 80))
        self.plugins_list.setGridSize(QSize(120, 120))
        self.plugins_list.setSpacing(15)
        self.plugins_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
            }
        """)
        layout.addWidget(self.plugins_list)

        self._refresh_list()

    def _on_install_clicked(self):
        url = self.link_plugin.text()

        self.install_button.setEnabled(False)
        self.install_button.setText("Instalando...")
        QApplication.processEvents()

        if self.store_manager.install_from_url(url):
            QMessageBox.information(self, "Sucesso", "Plugin instalado com sucesso!\n\nReinicie o JCode para carregar o novo plugin.")
            self._refresh_list()
            self.accept()
        else:
            QMessageBox.critical(self, "Erro de Instalação", "Não foi possível instalar o plugin.\n\nVerifique a URL, sua conexão com a internet e os logs para mais detalhes.")
            self.install_button.setEnabled(True)
            self.install_button.setText("Instalar")

    def _on_remove_requested(self, plugin_name: str):
        reply = QMessageBox.question(
            self, "Remover Plugin",
            f"Tem certeza que deseja remover o plugin '{plugin_name}'?\n\nVocê precisará reiniciar o JCode.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.store_manager.remove_plugin(plugin_name):
                self._refresh_list()
            else:
                QMessageBox.critical(self, "Erro", f"Não foi possível remover o plugin '{plugin_name}'.")

    def _refresh_list(self):
        """Atualiza a lista visual de plugins usando widgets customizados."""
        self.plugins_list.clear()
        
        icon_path = os.path.join(self.root_dir, "icon/icon_plugin.svg")
        plugin_icon = QIcon(icon_path)
        
        plugins = self.store_manager.get_installed_plugins()
        
        if not plugins:
            # Placeholder when no plugins are installed
            self.plugins_list.setViewMode(QListWidget.ViewMode.ListMode)
            item = QListWidgetItem("Nenhum plugin detectado.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.plugins_list.addItem(item)
        else:
            self.plugins_list.setViewMode(QListWidget.ViewMode.IconMode)
            for plugin_name in plugins:
                # Cria o widget customizado para o item
                plugin_widget = PluginItemWidget(plugin_name, plugin_icon, self.theme)
                plugin_widget.remove_requested.connect(self._on_remove_requested)

                # Cria um QListWidgetItem para conter o widget customizado
                item = QListWidgetItem(self.plugins_list)
                item.setSizeHint(plugin_widget.sizeHint())
                
                self.plugins_list.addItem(item)
                self.plugins_list.setItemWidget(item, plugin_widget)
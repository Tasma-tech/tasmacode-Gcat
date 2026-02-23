import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QListWidget, 
                               QListWidgetItem, QLabel, QWidget, QApplication)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent

class ProjectLauncher(QDialog):
    """Janela de troca rápida de projetos (Ctrl+R)."""
    
    project_selected = Signal(str)

    def __init__(self, recent_projects, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Popup)
        self.recent_projects = recent_projects
        self.resize(600, 400)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Estilo Moderno
        self.setStyleSheet("""
            QDialog {
                background-color: #252526;
                border: 1px solid #454545;
                border-radius: 8px;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #007acc;
                border-radius: 4px;
                padding: 8px;
                color: white;
                font-size: 14px;
                selection-background-color: #264f78;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 5px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #37373d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar projeto recente...")
        self.search_input.textChanged.connect(self._filter_list)
        self.search_input.installEventFilter(self) # Para capturar setas

        self.list_widget = QListWidget()
        self.list_widget.itemActivated.connect(self._on_item_activated)

        layout.addWidget(self.search_input)
        layout.addWidget(self.list_widget)

        self._populate_list(self.recent_projects)

    def _populate_list(self, projects):
        self.list_widget.clear()
        for path in projects:
            # Verificação de Existência (Regra de Ouro)
            if not os.path.exists(path):
                continue
                
            item = QListWidgetItem(self.list_widget)
            item.setData(Qt.UserRole, path)
            
            # Widget customizado para renderização rica (Nome em negrito, path em cinza)
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(5, 5, 5, 5)
            vbox.setSpacing(2)
            
            lbl_name = QLabel(os.path.basename(path))
            lbl_name.setStyleSheet("font-weight: bold; color: #cccccc; font-size: 13px;")
            
            lbl_path = QLabel(path)
            lbl_path.setStyleSheet("color: #858585; font-size: 11px;")
            
            vbox.addWidget(lbl_name)
            vbox.addWidget(lbl_path)
            
            item.setSizeHint(container.sizeHint())
            self.list_widget.setItemWidget(item, container)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _filter_list(self, text):
        filtered = [p for p in self.recent_projects if text.lower() in p.lower()]
        self._populate_list(filtered)

    def _on_item_activated(self, item):
        path = item.data(Qt.UserRole)
        self.project_selected.emit(path)
        self.close()

    def eventFilter(self, obj, event):
        """Redireciona navegação do teclado do Input para a Lista."""
        if obj == self.search_input and event.type() == QEvent.KeyPress:
            key = event.key()
            if key in (Qt.Key_Down, Qt.Key_Up):
                self.list_widget.setFocus()
                QApplication.sendEvent(self.list_widget, event)
                self.search_input.setFocus() # Mantém foco no input visualmente
                return True
        return super().eventFilter(obj, event)
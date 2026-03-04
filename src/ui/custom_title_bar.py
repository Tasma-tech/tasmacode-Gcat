from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QApplication, QMenu, QStyle
from PySide6.QtCore import Qt, QPoint, Signal, QSize, QRect
from PySide6.QtGui import QPixmap, QCursor, QIcon, QPainter, QColor

class HideableButton(QPushButton):
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.hide()
        else:
            super().mousePressEvent(event)

class TopLeftGrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(15, 15)
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#666666"))
        
        # Desenha pontos formando um triângulo no canto superior esquerdo
        painter.drawEllipse(2, 2, 3, 3)
        painter.drawEllipse(7, 2, 3, 3)
        painter.drawEllipse(2, 7, 3, 3)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            win = self.window()
            # Tenta usar o redimensionamento nativo do sistema (mais fluido)
            if win.windowHandle() and win.windowHandle().startSystemResize(Qt.Edge.TopEdge | Qt.Edge.LeftEdge):
                return
            
            # Fallback manual se o sistema não suportar
            self.start_pos = event.globalPosition().toPoint()
            self.start_geo = win.geometry()
            self.dragging = True

    def mouseMoveEvent(self, event):
        if hasattr(self, 'dragging') and self.dragging:
            win = self.window()
            pos = event.globalPosition().toPoint()
            delta = pos - self.start_pos
            geo = self.start_geo
            new_rect = QRect(geo.left() + delta.x(), geo.top() + delta.y(), 
                             geo.width() - delta.x(), geo.height() - delta.y())
            
            if new_rect.width() > win.minimumWidth() and new_rect.height() > win.minimumHeight():
                win.setGeometry(new_rect)

    def mouseReleaseEvent(self, event):
        self.dragging = False

class CustomTitleBar(QWidget):
    settings_clicked = Signal()
    profile_clicked = Signal()

    def __init__(self, parent=None, title="JCode"):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMouseTracking(True) # Garante que o modo "Mover" receba eventos
        self.setFixedHeight(35)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 0, 0)
        layout.setSpacing(5)
        
        # Grip de Redimensionamento (Canto Superior Esquerdo)
        self.grip = TopLeftGrip(self)
        layout.addWidget(self.grip, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        # Ícone
        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(30, 30)
        icon_pixmap = QPixmap("/home/johnb/JCODE/icon/JCODE.svg")
        self.icon_label.setPixmap(icon_pixmap.scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.icon_label)
        
        # Ícone e Título
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold; font-family: 'Segoe UI', sans-serif; font-size: 12px; border: none; background: transparent;")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Botões Extras (Perfil e Configurações)
        self.btn_profile = HideableButton()
        self.btn_profile.setIcon(QIcon.fromTheme("user-identity", self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView)))
        self.btn_profile.setIconSize(QSize(16, 16))
        self.btn_profile.setObjectName("btn_profile")
        self.btn_profile.setFixedSize(45, 35)
        self.btn_profile.setToolTip("Perfil (Botão Direito para ocultar)")
        self.btn_profile.clicked.connect(self.profile_clicked.emit)
        layout.addWidget(self.btn_profile)

        self.btn_settings = HideableButton()
        self.btn_settings.setObjectName("btn_settings")
        self.btn_settings.setIcon(QIcon.fromTheme("preferences-system", self.style().standardIcon(QStyle.StandardPixmap.SP_ToolBarHorizontalExtensionButton)))
        self.btn_settings.setFixedSize(45, 35)
        self.btn_settings.setToolTip("Configurações (Botão Direito para ocultar)")
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings)

        # Controles da Janela
        
        self.btn_min = QPushButton("─")
        self.btn_min.setObjectName("btn_min")
        self.btn_min.setFixedSize(45, 35)
        self.btn_min.clicked.connect(self.window().showMinimized)
        
        self.btn_max = QPushButton("☐")
        self.btn_max.setObjectName("btn_max")
        self.btn_max.setFixedSize(45, 35)
        self.btn_max.clicked.connect(self._toggle_max)
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setFixedSize(45, 35)
        self.btn_close.clicked.connect(self.window().close)
        
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_max)
        layout.addWidget(self.btn_close)
        
        self._drag_pos = None
        self._snap_action = None
        self._is_dragging_from_maximized = False
        self.drag_start_local_pos = None
        self._is_in_move_mode = False
        self.theme = {}
        
        # Aplica um tema padrão inicial
        self.apply_theme({})

    def apply_theme(self, theme):
        self.theme = theme
        bg = theme.get("sidebar_bg", "#252526")
        fg = theme.get("foreground", "#cccccc")
        border = theme.get("border_color", "#3e3e42")
        hover = theme.get("selection", "#3e3e42")
        
        self.setStyleSheet(f"""
            CustomTitleBar {{ background-color: {bg}; border-bottom: 1px solid {border}; }}
            QLabel {{ color: {fg}; font-weight: bold; font-family: 'Segoe UI', sans-serif; font-size: 12px; border: none; background: transparent; }}
            QPushButton {{ background-color: transparent; border: none; color: {fg}; }}
            QPushButton:hover {{ background-color: {hover}; }}
            QPushButton#btn_close:hover {{ background-color: #e81123; color: white; }}
        """)

    def set_title(self, title):
        self.title_label.setText(title)

    def _toggle_max(self):
        if self.window().isMaximized():
            self.window().showNormal()
        else:
            self.window().showMaximized()

    def contextMenuEvent(self, event):
        """Mostra menu de contexto para restaurar botões."""
        menu = QMenu(self)
        bg = self.theme.get("sidebar_bg", "#252526")
        fg = self.theme.get("foreground", "#cccccc")
        accent = self.theme.get("accent", "#007acc")
        border = self.theme.get("border_color", "#3e3e42")
        menu.setStyleSheet(f"QMenu {{ background-color: {bg}; color: {fg}; border: 1px solid {border}; }} QMenu::item:selected {{ background-color: {accent}; }}")

        restore_action = menu.addAction("Restaurar botões ocultos")
        restore_action.triggered.connect(self._restore_hidden_buttons)
        menu.exec(event.globalPos())

    def _start_window_move(self):
        """Inicia o modo de movimento da janela, capturando o mouse."""
        self._is_in_move_mode = True
        self.drag_start_local_pos = self.window().mapFromGlobal(QCursor.pos())
        self.grabMouse(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event):
        if self._is_in_move_mode:
            self._is_in_move_mode = False
            self.releaseMouse()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_local_pos = event.position().toPoint()
            if self.window().isMaximized():
                self._is_dragging_from_maximized = True
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._is_in_move_mode:
            self.window().move(event.globalPosition().toPoint() - self.drag_start_local_pos)
            return

        if self._drag_pos:
            # Se arrastando de maximizado, restaura a janela primeiro
            if self._is_dragging_from_maximized:
                self.window().showNormal()
                # Calcula a nova posição da janela para que o cursor fique no mesmo ponto relativo
                new_x = event.globalPosition().toPoint().x() - self.drag_start_local_pos.x()
                new_y = event.globalPosition().toPoint().y() - self.drag_start_local_pos.y()
                self.window().move(new_x, new_y)
                self._is_dragging_from_maximized = False
                # Atualiza a posição de arrasto para continuar o movimento suavemente
                self._drag_pos = event.globalPosition().toPoint()
                return # Pula um evento de movimento para evitar saltos

            # Movimento normal da janela
            if not self.window().isMaximized():
                # Usa delta (diferença) para mover, que é mais robusto que posição absoluta
                delta = event.globalPosition().toPoint() - self._drag_pos
                self.window().move(self.window().pos() + delta)
                self._drag_pos = event.globalPosition().toPoint()

            # Detecção de Snap
            screen = self.window().screen().geometry()
            cursor_pos = event.globalPosition().toPoint()
            
            if cursor_pos.y() <= screen.top():
                self._snap_action = "maximize"
            elif cursor_pos.x() <= screen.left():
                self._snap_action = "snap_left"
            elif cursor_pos.x() >= screen.right() - 1:
                self._snap_action = "snap_right"
            else:
                self._snap_action = None

    def mouseReleaseEvent(self, event):
        if self._snap_action and not self.window().isMaximized():
            screen = self.window().screen().availableGeometry()
            if self._snap_action == "maximize":
                self.window().showMaximized()
            elif self._snap_action == "snap_left":
                self.window().setGeometry(screen.left(), screen.top(), screen.width() // 2, screen.height())
            elif self._snap_action == "snap_right":
                self.window().setGeometry(screen.left() + screen.width() // 2, screen.top(), screen.width() // 2, screen.height())
        
        self._drag_pos = None
        self._snap_action = None
        self._is_dragging_from_maximized = False
        
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.icon_label.geometry().contains(event.position().toPoint()):
                self.window().close()
            else:
                self._toggle_max()

    def _restore_hidden_buttons(self):
        """Mostra os botões de perfil e configurações."""
        self.btn_profile.show()
        self.btn_settings.show()
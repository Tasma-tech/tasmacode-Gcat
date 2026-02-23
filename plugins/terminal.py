import sys
import os
import logging
import re

# Imports específicos de Linux para manipulação de PTY
if sys.platform != "win32":
    import pty
    import termios
    import fcntl
    import struct
    import select
    import tty

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit
from PySide6.QtCore import QThread, Signal, Qt, QEvent
from PySide6.QtGui import QFont, QTextCursor

logger = logging.getLogger("Terminal")

class TerminalWorker(QThread):
    """Thread dedicada para ler a saída do descritor de arquivo mestre (PTY).
    
    Isso evita que a leitura bloqueante do os.read congele a interface gráfica.
    """
    output_received = Signal(str)

    def __init__(self, master_fd):
        super().__init__()
        self.master_fd = master_fd
        self.running = True

    def run(self):
        while self.running:
            try:
                # select aguarda dados disponíveis para leitura com timeout de 0.1s
                r, _, _ = select.select([self.master_fd], [], [], 0.1)
                if self.master_fd in r:
                    # Lê bytes brutos do terminal
                    data = os.read(self.master_fd, 4096)
                    if not data:
                        break
                    # Decodifica para string (tratando erros de unicode)
                    text = data.decode('utf-8', errors='replace')
                    self.output_received.emit(text)
            except (OSError, ValueError):
                # O descritor de arquivo foi fechado ou erro de sistema
                break

    def stop(self):
        self.running = False
        self.wait()

class Terminal(QWidget):
    """Emulador de terminal real baseado em PTY (Linux/Mac)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Widget de exibição (QPlainTextEdit é mais performático que QTextEdit para logs)
        self.display = QPlainTextEdit()
        self.display.setReadOnly(True) # O usuário não edita o texto diretamente, nós capturamos as teclas
        self.display.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.display.setStyleSheet("background-color: #1e1e1e; color: #cccccc; border: none;")
        
        # Configuração de Fonte Monoespaçada
        font = QFont("Monospace")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(10)
        self.display.setFont(font)
        
        self.layout.addWidget(self.display)

        self.master_fd = None
        self.pid = None
        self.worker = None

        # Instala filtro de eventos para capturar teclas antes do widget processá-las
        self.display.installEventFilter(self)

        if sys.platform != "win32":
            self.start_pty()
        else:
            self.display.appendPlainText("Terminal PTY nativo não suportado no Windows.")

    def start_pty(self):
        """Inicia o shell padrão em um novo pseudo-terminal."""
        shell = os.environ.get("SHELL", "/bin/bash")
        
        # pty.fork() cria um processo filho e conecta a um pseudo-terminal
        self.pid, self.master_fd = pty.fork()
        
        if self.pid == 0:
            # --- PROCESSO FILHO (SHELL) ---
            # Configura variáveis de ambiente para cores
            os.environ["TERM"] = "xterm-256color"
            # Substitui o processo atual pelo shell
            os.execv(shell, [shell])
        else:
            # --- PROCESSO PAI (EDITOR) ---
            # Inicia a thread de leitura
            self.worker = TerminalWorker(self.master_fd)
            self.worker.output_received.connect(self._on_output)
            self.worker.start()
            
            # Ajusta o tamanho inicial da janela do terminal
            self._update_size()

    def _on_output(self, text):
        """Recebe dados do shell, processa sequências de controle e exibe."""
        cursor = self.display.textCursor()
        cursor.movePosition(QTextCursor.End)

        # Regex to split text by ANSI control sequences and basic control chars
        pattern = re.compile(r'(\x1b\[[0-9;?]*[a-zA-Z]|\r|\n|\b)')
        parts = pattern.split(text)

        for part in parts:
            if not part:
                continue

            if len(part) > 1 and part.startswith('\x1b['):
                # It's an ANSI sequence
                match = re.match(r'\x1b\[([0-9;?]*)?([a-zA-Z])', part)
                if match:
                    params = match.group(1)
                    command = match.group(2)
                    self._handle_ansi_command(cursor, params, command)
            elif part == '\r':
                cursor.movePosition(QTextCursor.StartOfLine)
            elif part == '\n':
                cursor.insertText('\n')
            elif part == '\b':
                # A simple backspace moves the cursor left.
                # The shell itself handles the character deletion by sending \b \b or similar.
                cursor.movePosition(QTextCursor.PreviousCharacter)
            else:
                # It's plain text
                cursor.insertText(part)

        self.display.setTextCursor(cursor)
        self.display.ensureCursorVisible()

    def _handle_ansi_command(self, cursor, params_str, command):
        """Handles a parsed ANSI command for cursor control and erasing."""
        try:
            params = [int(p) for p in params_str.split(';') if p] if params_str else []
        except ValueError:
            params = []

        if command == 'K':  # Erase in Line
            mode = params[0] if params else 0
            if mode == 0:  # Apaga do cursor até o fim da linha
                cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
            elif mode == 1:  # Apaga do início da linha até o cursor
                cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
            elif mode == 2:  # Erase entire line
                cursor.select(QTextCursor.LineUnderCursor)
                cursor.removeSelectedText()

        elif command == 'J':  # Erase in Display
            mode = params[0] if params else 0
            if mode == 2:  # Erase entire screen
                self.display.clear()

        elif command == 'H' or command == 'f':  # Cursor Position
            # \x1b[H (home)
            if not params_str:
                cursor.movePosition(QTextCursor.Start)
            # TODO: Implement full \x1b[<L>;<C>H support

        elif command == 'm': # SGR (Select Graphic Rendition) - Colors
            # TODO: Implement color handling using QTextCharFormat
            pass

    def eventFilter(self, obj, event):
        """Intercepta teclas no widget e envia para o PTY."""
        if obj == self.display and event.type() == QEvent.KeyPress:
            self._send_key(event)
            return True # Consome o evento (não digita no QPlainTextEdit)
        return super().eventFilter(obj, event)

    def _send_key(self, event):
        """Traduz eventos Qt para bytes e escreve no descritor mestre."""
        if not self.master_fd: return
        
        key = event.key()
        text = event.text()
        modifiers = event.modifiers()
        
        data = b''
        
        # Mapeamento de teclas especiais
        if key == Qt.Key_Enter or key == Qt.Key_Return:
            data = b'\r'
        elif key == Qt.Key_Backspace:
            data = b'\x7f'
        elif key == Qt.Key_Tab:
            data = b'\t'
        elif key == Qt.Key_Up:    data = b'\x1b[A'
        elif key == Qt.Key_Down:  data = b'\x1b[B'
        elif key == Qt.Key_Right: data = b'\x1b[C'
        elif key == Qt.Key_Left:  data = b'\x1b[D'
        elif modifiers & Qt.ControlModifier:
            # Trata Ctrl+C, Ctrl+D, etc.
            if Qt.Key_A <= key <= Qt.Key_Z:
                # Ctrl+A é \x01, Ctrl+C é \x03
                char_code = key - Qt.Key_A + 1
                data = bytes([char_code])
        elif text:
            data = text.encode('utf-8')
            
        if data:
            try:
                os.write(self.master_fd, data)
            except OSError:
                pass

    def resizeEvent(self, event):
        """Notifica o kernel sobre a mudança de tamanho da janela (ioctl)."""
        super().resizeEvent(event)
        self._update_size()

    def _update_size(self):
        """Usa ioctl TIOCSWINSZ para ajustar linhas/colunas do PTY."""
        if not self.master_fd: return
        
        font_metrics = self.display.fontMetrics()
        char_w = font_metrics.horizontalAdvance('M')
        char_h = font_metrics.height()
        
        if char_w <= 0 or char_h <= 0: return
        
        cols = int(self.display.width() / char_w)
        rows = int(self.display.height() / char_h)
        
        try:
            # struct winsize { unsigned short ws_row, ws_col, ws_xpixel, ws_ypixel; };
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
        except Exception as e:
            logger.error(f"Erro ao redimensionar PTY: {e}")

    def change_directory(self, path: str):
        """Envia comando 'cd' para o shell sincronizar com o editor."""
        if self.master_fd and os.path.exists(path):
            # Envia Enter antes para limpar qualquer comando pendente
            cmd = f"\rcd \"{path}\"\r"
            os.write(self.master_fd, cmd.encode())

    def closeEvent(self, event):
        """Limpeza segura de recursos para evitar processos zumbis."""
        if self.worker:
            self.worker.stop()
        
        if self.master_fd:
            os.close(self.master_fd)
            self.master_fd = None
            
        if self.pid:
            try:
                # Envia SIGKILL para garantir que o shell feche
                os.kill(self.pid, 9)
                os.waitpid(self.pid, 0) # Remove da tabela de processos
            except OSError:
                pass
        
        super().closeEvent(event)
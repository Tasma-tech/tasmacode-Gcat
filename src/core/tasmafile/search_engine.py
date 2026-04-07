import os
import logging
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger("FileSearchEngine")

class FileSearchEngine(QThread):
    """Busca conteúdo de texto em arquivos de um diretório de forma assíncrona."""
    
    # Emite (caminho_do_arquivo, numero_linha, linha_com_match)
    match_found = Signal(str, int, str)
    # Emite (mensagem_de_progresso)
    progress_updated = Signal(str)
    # Emite quando a busca termina, com o número de resultados
    search_finished = Signal(int)

    def __init__(self, directory, pattern, parent=None):
        super().__init__(parent)
        self.directory = directory
        self.pattern = pattern.lower()
        self._is_running = True
        self._match_count = 0

    def run(self):
        """Executa a busca em todos os arquivos do diretório."""
        if not self.pattern:
            self.search_finished.emit(0)
            return

        files_to_scan = []
        self.progress_updated.emit("Mapeando arquivos...")
        for root, dirs, files in os.walk(self.directory):
            # Ignora pastas comuns de build/dependências para otimizar
            dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', 'build', 'dist', '.venv']]
            if not self._is_running:
                self.search_finished.emit(self._match_count)
                return
            for file in files:
                files_to_scan.append(os.path.join(root, file))

        total_files = len(files_to_scan)
        for i, filepath in enumerate(files_to_scan):
            if not self._is_running: break
            
            self.progress_updated.emit(f"Buscando... ({i+1}/{total_files})")
            
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if self.pattern in line.lower():
                            self.match_found.emit(filepath, line_num, line.strip())
                            self._match_count += 1
            except Exception:
                continue # Ignora erros de leitura (ex: arquivos binários)

        self.search_finished.emit(self._match_count)

    def stop(self):
        self._is_running = False
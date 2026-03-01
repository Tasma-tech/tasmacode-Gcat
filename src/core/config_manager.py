import json
import os
import logging
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("ConfigManager")

class ConfigManager(QObject):
    """Gerencia as configurações globais do editor."""
    
    # Sinal emitido quando qualquer configuração muda: envia o dicionário completo
    config_changed = Signal(dict)

    def __init__(self):
        super().__init__()
        self.config_dir = os.path.join(os.path.expanduser("~"), ".jcode")
        self.config_file = os.path.join(self.config_dir, "settings.json")
        
        self.defaults = {
            "font_size": 12,
            "line_numbers": True,
            "auto_indent": True,
            "theme": "dark_default",
            "restore_session": True,
            "server_address": "http://localhost:5000",
            "live_server_port": 0,
            "live_server_open_browser": True,
            "enable_autocomplete": False
        }
        self.config = self.load_config()

    def load_config(self) -> dict:
        """Carrega configurações do disco ou retorna padrões."""
        if not os.path.exists(self.config_file):
            return self.defaults.copy()
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                # Merge com defaults para garantir que novas chaves existam
                config = self.defaults.copy()
                config.update(data)
                return config
        except Exception as e:
            logger.error(f"Erro ao carregar settings.json: {e}")
            return self.defaults.copy()

    def save_config(self, new_config: dict):
        """Salva as configurações no disco e notifica a aplicação."""
        self.config = new_config
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.config_changed.emit(self.config)
            logger.info("Configurações salvas com sucesso.")
        except Exception as e:
            logger.error(f"Erro ao salvar settings.json: {e}")

    def get(self, key):
        return self.config.get(key, self.defaults.get(key))
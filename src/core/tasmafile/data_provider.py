import os
import json
from PySide6.QtCore import QObject, QDir, Signal

class TasmaDataProvider(QObject):
    """Fornece dados e caminhos para o gerenciador de arquivos TasmaFile."""
    
    favorites_changed = Signal()

    def __init__(self, session_manager, root_dir):
        super().__init__()
        self.session_manager = session_manager
        self.root_dir = root_dir
        self.categories_file = os.path.join(self.session_manager.session_dir, "tasma_categories.json")

    def get_recent_projects(self):
        """Retorna lista de projetos recentes da sessão."""
        session = self.session_manager.load_session()
        return session.get("recent_projects", [])

    def get_user_plugins(self):
        """Retorna lista de caminhos dos plugins instalados."""
        plugins_dir = os.path.join(self.root_dir, "plugins")
        if os.path.exists(plugins_dir):
            return [os.path.join(plugins_dir, d) for d in os.listdir(plugins_dir) 
                    if os.path.isdir(os.path.join(plugins_dir, d)) and not d.startswith("__")]
        return []

    def get_editor_source(self):
        """Retorna o caminho do código fonte do editor."""
        return os.path.join(self.root_dir, "src")

    def get_home_dir(self):
        return QDir.homePath()
        
    def get_root_dir(self):
        return QDir.rootPath()

    def get_custom_categories(self):
        """Retorna dicionário de categorias personalizadas {nome: caminho}."""
        if os.path.exists(self.categories_file):
            try:
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def add_custom_category(self, name, path):
        """Adiciona uma nova categoria."""
        cats = self.get_custom_categories()
        cats[name] = path
        self._save_categories(cats)
        self.favorites_changed.emit()

    def remove_custom_category(self, name):
        """Remove uma categoria existente."""
        cats = self.get_custom_categories()
        if name in cats:
            del cats[name]
            self._save_categories(cats)
        self.favorites_changed.emit()

    def _save_categories(self, cats):
        try:
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(cats, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar categorias: {e}")
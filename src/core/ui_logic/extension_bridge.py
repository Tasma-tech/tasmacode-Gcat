import os
import sys
import importlib.util
import logging
import traceback
from typing import Dict, List, Callable, Any
from PySide6.QtCore import QObject, Signal

# Configuração básica de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ExtensionBridge")

class EditorAPI:
    """Interface segura para plugins interagirem com o editor.
    
    Encapsula o acesso ao Core e UI, prevenindo que plugins quebrem a aplicação.
    """
    def __init__(self, insert_fn, get_text_fn, add_menu_fn, log_fn, get_editor_fn=None, update_config_fn=None, get_config_fn=None, get_project_root_fn=None, undo_fn=None):
        self._insert_fn = insert_fn
        self._get_text_fn = get_text_fn
        self._add_menu_fn = add_menu_fn
        self._log_fn = log_fn
        self._get_editor_fn = get_editor_fn
        self._update_config_fn = update_config_fn
        self._get_config_fn = get_config_fn
        self._get_project_root_fn = get_project_root_fn
        self._undo_fn = undo_fn

    def insert_text(self, text: str):
        if self._insert_fn: self._insert_fn(text)

    def get_full_text(self) -> str:
        return self._get_text_fn() if self._get_text_fn else ""

    def add_menu_action(self, label: str, callback: Callable[['EditorAPI'], None]):
        """Registra uma ação no menu. O callback recebe esta API como argumento."""
        if self._add_menu_fn:
            # Envolvemos o callback para injetar 'self' (a API)
            self._add_menu_fn(label, lambda: callback(self))

    def log(self, message: str):
        if self._log_fn: self._log_fn(message)

    def get_active_editor(self):
        """Retorna a instância do editor ativo (CodeEditor)."""
        return self._get_editor_fn() if self._get_editor_fn else None

    def update_config(self, key: str, value: Any):
        """Atualiza e salva uma configuração global."""
        if self._update_config_fn:
            self._update_config_fn(key, value)

    def get_config(self, key: str, default: Any = None) -> Any:
        """Recupera uma configuração global."""
        if self._get_config_fn:
            return self._get_config_fn(key, default)
        return default

    def get_project_root(self) -> str | None:
        """Retorna o caminho raiz do projeto atual."""
        if self._get_project_root_fn:
            return self._get_project_root_fn()
        return None

    def undo(self):
        """Dispara a ação de desfazer no editor ativo."""
        if self._undo_fn:
            self._undo_fn()

class ExtensionBridge(QObject):
    """Gerencia o carregamento de plugins e o sistema de Hooks.

    Atua como a ponte entre o Core e funcionalidades estendidas.
    Herda de QObject para permitir comunicação via Sinais se necessário.
    """

    # Sinais para notificar a UI sobre mudanças no estado dos plugins
    plugin_loaded = Signal(str)
    plugin_error = Signal(str, str)
    
    def __init__(self):
        super().__init__()
        self._hooks: Dict[str, List[Callable]] = {
            "on_text_changed": [],
            "on_file_open": [],
            "before_render": [],
            "on_app_start": []
        }
        self._plugins: Dict[str, Any] = {}
        self._loaded_modules: Dict[str, Any] = {} # Módulos carregados mas não ativados

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Registra uma função callback em um hook específico.

        Args:
            hook_name: O nome do evento (ex: 'on_text_changed').
            callback: A função a ser executada.
        """
        if hook_name in self._hooks:
            self._hooks[hook_name].append(callback)
            logger.debug(f"Hook registrado em '{hook_name}': {callback.__name__}")
        else:
            logger.warning(f"Tentativa de registro em hook inexistente: {hook_name}")

    def trigger_hook(self, hook_name: str, *args, **kwargs) -> None:
        """Dispara todos os callbacks registrados para um hook.

        Args:
            hook_name: O nome do evento a disparar.
            *args, **kwargs: Argumentos passados para os callbacks.
        """
        if hook_name in self._hooks:
            for callback in self._hooks[hook_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Erro ao executar hook '{hook_name}': {e}")

    def load_plugins(self, plugins_dir: str) -> None:
        """Carrega dinamicamente todos os scripts Python no diretório de plugins.

        Args:
            plugins_dir: Caminho absoluto ou relativo para a pasta de plugins.
        """
        if not os.path.exists(plugins_dir):
            logger.warning(f"Diretório de plugins não encontrado: {plugins_dir}")
            return

        # Adiciona o diretório ao path para facilitar imports relativos nos plugins
        sys.path.append(plugins_dir)

        for item_name in os.listdir(plugins_dir):
            item_path = os.path.join(plugins_dir, item_name)
            
            # Carrega arquivos .py soltos
            if os.path.isfile(item_path) and item_name.endswith(".py") and not item_name.startswith("__"):
                self._load_single_plugin(plugins_dir, item_name)
            # Carrega pacotes (pastas com __init__.py)
            elif os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
                self._load_package_plugin(plugins_dir, item_name)

    def _load_single_plugin(self, directory: str, filename: str) -> None:
        """Carrega um único arquivo de plugin.

        Espera que o plugin tenha uma função `register(bridge)`.
        """
        plugin_name = filename[:-3] # Remove .py
        path = os.path.join(directory, filename)

        try:
            spec = importlib.util.spec_from_file_location(plugin_name, path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Validação: Verifica se possui o ponto de entrada obrigatório
                if hasattr(module, "plugin_main"):
                    self._loaded_modules[plugin_name] = module
                    logger.info(f"Plugin carregado (pendente ativação): {plugin_name}")
                else:
                    logger.warning(f"Plugin {plugin_name} ignorado: função 'plugin_main' não encontrada.")
        except Exception as e:
            logger.error(f"Falha ao carregar plugin {plugin_name}: {e}")
            self.plugin_error.emit(plugin_name, str(e))

    def _load_package_plugin(self, directory: str, package_name: str) -> None:
        """Carrega um plugin que é um pacote Python."""
        try:
            # Como o diretório pai já está no sys.path, podemos importar diretamente
            module = importlib.import_module(package_name)
            
            if hasattr(module, "plugin_main"):
                self._loaded_modules[package_name] = module
                logger.info(f"Plugin (pacote) carregado: {package_name}")
            else:
                logger.warning(f"Plugin {package_name} ignorado: 'plugin_main' ausente.")
        except Exception as e:
            logger.error(f"Erro ao carregar pacote {package_name}: {e}")
            self.plugin_error.emit(package_name, str(e))

    def activate_plugins(self, api_factory: Callable[[], EditorAPI]) -> None:
        """Fase 2: Ativa todos os plugins carregados, injetando a API."""
        for name, module in self._loaded_modules.items():
            try:
                api = api_factory()
                module.plugin_main(api)
                self._plugins[name] = module
                self.plugin_loaded.emit(name)
                logger.info(f"Plugin ativado com sucesso: {name}")
            except Exception as e:
                logger.error(f"Erro Crítico ao ativar plugin {name}: {e}")
                traceback.print_exc()
                self.plugin_error.emit(name, str(e))
                # Não adicionamos ao registro de plugins ativos

    def get_loaded_plugins(self) -> List[str]:
        """Retorna lista de nomes dos plugins carregados."""
        return list(self._plugins.keys())

    def get_plugin(self, name: str):
        """Retorna um plugin ativo pelo nome."""
        return self._plugins.get(name)
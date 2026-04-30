from typing import Callable, Any

from src.core.ui_logic.extension_bridge import EditorAPI


class EditorApiFactory:
    """Cria instâncias de EditorAPI com as dependências do host."""

    def __init__(
        self,
        insert_fn: Callable[[str], None],
        get_text_fn: Callable[[], str],
        add_menu_fn: Callable[[str, Callable[[], None]], None],
        log_fn: Callable[[str], None],
        get_editor_fn: Callable[[], Any] | None = None,
        update_config_fn: Callable[[str, Any], None] | None = None,
        get_config_fn: Callable[[str, Any], Any] | None = None,
        get_project_root_fn: Callable[[], str | None] | None = None,
        undo_fn: Callable[[], None] | None = None,
    ):
        self._insert_fn = insert_fn
        self._get_text_fn = get_text_fn
        self._add_menu_fn = add_menu_fn
        self._log_fn = log_fn
        self._get_editor_fn = get_editor_fn
        self._update_config_fn = update_config_fn
        self._get_config_fn = get_config_fn
        self._get_project_root_fn = get_project_root_fn
        self._undo_fn = undo_fn

    def create(self) -> EditorAPI:
        return EditorAPI(
            insert_fn=self._insert_fn,
            get_text_fn=self._get_text_fn,
            add_menu_fn=self._add_menu_fn,
            log_fn=self._log_fn,
            get_editor_fn=self._get_editor_fn,
            update_config_fn=self._update_config_fn,
            get_config_fn=self._get_config_fn,
            get_project_root_fn=self._get_project_root_fn,
            undo_fn=self._undo_fn,
        )

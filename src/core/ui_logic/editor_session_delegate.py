import os
from typing import Any, Callable, Iterable


class EditorSessionDelegate:
    """Coordena restauração e persistência de sessão sem acoplar à UI concreta."""

    def __init__(self, project_session_orchestrator):
        self._project_session_orchestrator = project_session_orchestrator

    def load(
        self,
        *,
        set_root_path_fn: Callable[[str], None],
        set_search_root_fn: Callable[[str], None],
        set_window_title_fn: Callable[[str], None],
        open_file_fn: Callable[[str], None],
        restore_active_cursor_fn: Callable[[int, int], None],
        iter_editors_fn: Callable[[], Iterable[tuple[int, Any]]],
        get_editor_path_fn: Callable[[Any], str | None],
        select_tab_by_index_fn: Callable[[int], None],
    ) -> None:
        session_data = self._project_session_orchestrator.load_session_snapshot()

        root_path = session_data.get("last_directory")
        if root_path and os.path.exists(root_path) and os.path.isdir(root_path):
            set_root_path_fn(root_path)
            set_search_root_fn(root_path)
            set_window_title_fn(f"JCode - {os.path.basename(root_path)}")
        else:
            root_path = None

        for file_data in session_data.get("open_files", []):
            path = file_data.get("path")
            if not path:
                continue

            if root_path and not os.path.isabs(path):
                path = os.path.join(root_path, path)

            if not os.path.exists(path):
                continue

            open_file_fn(path)
            cursor_info = file_data.get("cursor") or {}
            restore_active_cursor_fn(cursor_info.get("line", 0), cursor_info.get("col", 0))

        active_file = session_data.get("active_file")
        if root_path and active_file and not os.path.isabs(active_file):
            active_file = os.path.join(root_path, active_file)

        if not active_file:
            return

        for index, editor in iter_editors_fn():
            if get_editor_path_fn(editor) == active_file:
                select_tab_by_index_fn(index)
                break

    def save(
        self,
        *,
        iter_editors_fn: Callable[[], Iterable[Any]],
        get_editor_path_fn: Callable[[Any], str | None],
        get_editor_cursor_fn: Callable[[Any], tuple[int, int]],
        get_root_path_fn: Callable[[], str | None],
        get_active_path_fn: Callable[[], str | None],
    ) -> None:
        open_files = []

        for editor in iter_editors_fn():
            file_path = get_editor_path_fn(editor)
            if not file_path:
                continue
            line, col = get_editor_cursor_fn(editor)
            open_files.append({"path": file_path, "cursor": {"line": line, "col": col}})

        payload = self._project_session_orchestrator.build_session_payload(
            get_root_path_fn(),
            open_files,
            get_active_path_fn(),
        )
        self._project_session_orchestrator.persist_session_payload(payload)

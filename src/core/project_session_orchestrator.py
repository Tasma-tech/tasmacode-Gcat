import os


class ProjectSessionOrchestrator:
    """Orquestra fluxos de projeto/sessão fora da camada de UI."""

    def __init__(self, session_manager):
        self.session_manager = session_manager

    def prepare_project_load(self, path: str):
        project_name = os.path.basename(path)
        self.session_manager.add_to_history(path)
        self.session_manager.save_session(path, [], None)
        return {
            "path": path,
            "project_name": project_name,
            "title": f"JCode - {project_name}",
            "status_message": f"Projeto carregado: {path}",
        }

    def load_session_snapshot(self):
        return self.session_manager.load_session()

    def build_session_payload(self, root_path, open_files, active_path):
        return {
            "root_path": root_path,
            "open_files": open_files,
            "active_path": active_path,
        }

    def persist_session_payload(self, payload):
        self.session_manager.save_session(
            payload.get("root_path"),
            payload.get("open_files", []),
            payload.get("active_path"),
        )

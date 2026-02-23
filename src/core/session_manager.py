import os
import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SessionManager")

class SessionManager:
    """Manages saving and loading of editor sessions."""

    def __init__(self):
        self.session_dir = os.path.join(os.path.expanduser("~"), ".jcode")
        self.session_file = os.path.join(self.session_dir, "session.json")
        os.makedirs(self.session_dir, exist_ok=True)

    def _get_default_session(self) -> Dict[str, Any]:
        return {
            "last_directory": None,
            "open_files": [],
            "active_file": None,
            "recent_projects": []
        }

    def save_session(self, root_path: Optional[str], open_files_data: List[Dict[str, Any]], active_file_path: Optional[str]):
        """
        Saves the current session state to a JSON file.
        open_files_data: [{'path': str, 'cursor': {'line': int, 'col': int}}]
        """
        # Carrega sessão anterior para preservar histórico
        previous_session = self.load_session()
        recent_projects = previous_session.get("recent_projects", [])

        session_data = self._get_default_session()
        session_data["last_directory"] = root_path
        
        # Atualiza lista de projetos recentes
        if root_path:
            if root_path in recent_projects:
                recent_projects.remove(root_path)
            recent_projects.insert(0, root_path)
            # Mantém apenas os 15 mais recentes
            recent_projects = recent_projects[:15]
        
        session_data["recent_projects"] = recent_projects

        if root_path:
            relative_files = []
            for file_data in open_files_data:
                try:
                    rel_path = os.path.relpath(file_data['path'], root_path)
                    relative_files.append({'path': rel_path, 'cursor': file_data['cursor']})
                except ValueError:
                    relative_files.append(file_data)
            session_data["open_files"] = relative_files
            
            if active_file_path:
                try:
                    session_data["active_file"] = os.path.relpath(active_file_path, root_path)
                except ValueError:
                    session_data["active_file"] = active_file_path
        else:
            session_data["open_files"] = open_files_data
            session_data["active_file"] = active_file_path

        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=4)
            logger.info(f"Session saved to {self.session_file}")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    def load_session(self) -> Dict[str, Any]:
        """Loads the last session from the JSON file."""
        if not os.path.exists(self.session_file):
            return self._get_default_session()

        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            return session_data
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to load or parse session file, using default. Error: {e}")
            return self._get_default_session()
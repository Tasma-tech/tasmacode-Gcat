import subprocess
import os
import logging

logger = logging.getLogger("GitLogic")

class GitLogic:
    """Gerencia operações do Git, isolando a lógica de sistema da UI."""

    def clone_repository(self, repo_url: str, destination_folder: str) -> tuple[bool, str]:
        """
        Executa o comando git clone.
        Retorna: (sucesso: bool, mensagem: str)
        """
        if not repo_url or not destination_folder:
            return False, "URL e pasta de destino são obrigatórios."

        try:
            # Executa o git clone no diretório escolhido
            # check=True levanta exceção se o comando falhar
            subprocess.run(["git", "clone", repo_url], cwd=destination_folder, check=True, capture_output=True)
            return True, f"Repositório clonado com sucesso em: {destination_folder}"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode().strip() if e.stderr else "Erro desconhecido"
            return False, f"Erro ao clonar: {error_msg}"
        except Exception as e:
            return False, f"Erro de sistema: {str(e)}"

    def is_repo(self, path: str) -> bool:
        """Verifica se o caminho é um repositório git."""
        try:
            # Usa git rev-parse para verificar se estamos dentro de uma árvore de trabalho git
            # Isso funciona mesmo se abrirmos uma subpasta do repositório
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"], 
                cwd=path, 
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def get_current_branch(self, repo_path: str) -> str:
        try:
            res = subprocess.run(["git", "branch", "--show-current"], cwd=repo_path, capture_output=True, text=True)
            return res.stdout.strip()
        except:
            return "HEAD"

    def get_graph_data(self, repo_path: str) -> list:
        """Retorna lista de commits formatada para o gráfico."""
        # Separador único para evitar conflito com mensagens de commit
        sep = "^@^"
        cmd = ["git", "log", "--all", "--date=short", f"--pretty=format:%h{sep}%p{sep}%s{sep}%cd{sep}%an{sep}%d", "-n", "100"]
        
        try:
            result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, encoding='utf-8', errors='replace')
            if result.returncode != 0:
                return []
                
            commits = []
            for line in result.stdout.splitlines():
                parts = line.split(sep)
                if len(parts) < 6: continue
                
                commits.append({
                    "hash": parts[0],
                    "parents": parts[1].split(),
                    "message": parts[2],
                    "date": parts[3],
                    "author": parts[4],
                    "refs": parts[5].strip()
                })
            return commits
        except Exception as e:
            logger.error(f"Git graph error: {e}")
            return []
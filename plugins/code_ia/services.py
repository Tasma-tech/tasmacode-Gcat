import json
import os


class ChatService:
    def __init__(self, api):
        self.api = api

    def build_attachments_context(self, attached_files):
        if not attached_files:
            return ""
        attachments_content = "\n\n--- Arquivos Anexados ---\n"
        for path in attached_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    attachments_content += f"\nArquivo: {os.path.basename(path)}\n```\n{f.read()}\n```\n"
            except Exception as e:
                attachments_content += f"\nErro ao ler {os.path.basename(path)}: {e}\n"
        return attachments_content

    def load_system_files(self):
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        content = ""
        rules_path = os.path.join(plugin_dir, "regras.txt")
        if os.path.exists(rules_path):
            with open(rules_path, "r", encoding="utf-8") as f:
                content += "Regras:\n" + f.read() + "\n\n"

        persona_path = os.path.join(plugin_dir, "perssonalidade.txt")
        if os.path.exists(persona_path):
            with open(persona_path, "r", encoding="utf-8") as f:
                content += "Personalidade:\n" + f.read()
        return content

    def build_system_message(self):
        system_msg = self.load_system_files()
        system_msg += "\n\n[SYSTEM: Capabilities]\n"
        system_msg += "Você é um especialista em edição de código cirúrgica. Ao editar código existente:\n"
        system_msg += "1. ANALISE o código fornecido no contexto.\n"
        system_msg += "2. IDENTIFIQUE as linhas exatas (classes, funções, variáveis) que precisam mudar.\n"
        system_msg += "3. USE o formato SEARCH/REPLACE para alterar APENAS o necessário. NÃO reescreva o arquivo todo a menos que solicitado.\n\n"
        system_msg += "Formato para Edição Parcial (Search & Replace):\n"
        system_msg += "<<<<<<< SEARCH\n"
        system_msg += "    # Copie aqui EXATAMENTE as linhas do código original que serão alteradas\n"
        system_msg += "    # Inclua indentação correta e contexto suficiente para ser único\n"
        system_msg += "=======\n"
        system_msg += "    # Seu novo código aqui\n"
        system_msg += ">>>>>>> REPLACE\n\n"
        system_msg += "Formato para Criar Arquivos ou Substituição Total:\n"
        system_msg += "# file: path/to/file.ext\n"
        system_msg += "conteudo completo do arquivo...\n"
        return system_msg

    def parse_stream_chunk(self, raw_line):
        decoded_line = raw_line.decode("utf-8")
        if not decoded_line.startswith("data: ") or decoded_line.strip() == "data: [DONE]":
            return None
        try:
            json_data = json.loads(decoded_line[6:])
            delta = json_data["choices"][0].get("delta", {})
            return delta.get("content", "")
        except Exception:
            return None

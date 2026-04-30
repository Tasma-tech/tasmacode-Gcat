import json
import os
import uuid

import requests


class GroqStreamingClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def stream_chat(self, prompt: str, context: str):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": context},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
        }
        return requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60,
            stream=True,
        )


class ChatHistoryRepository:
    def __init__(self):
        self.history_dir = os.path.join(os.path.expanduser("~"), ".jcode", "code_ia")
        os.makedirs(self.history_dir, exist_ok=True)
        self.history_file = os.path.join(self.history_dir, "chats.json")

    def load(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save(self, chats):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(chats, f, indent=2)

    def create_chat(self):
        return {"id": str(uuid.uuid4()), "title": "Novo Chat", "messages": [], "pinned": False}

import re
import os

class AutocompleteManager:
    """Gerencia a lógica de autocomplete."""
    def __init__(self):
        self.trigger_chars = ['.', '(', '[', '{', '<', ':', ' ', '"', "'"]
        
        # Definições por linguagem
        self.languages = {
            'python': {
                'keywords': [
                    "def", "class", "import", "from", "return", "if", "else", "elif",
                    "for", "while", "try", "except", "finally", "with", "as", "pass",
                    "break", "continue", "lambda", "yield", "async", "await", "print",
                    "True", "False", "None", "self", "super"
                ],
                'snippets': {
                    'def': {
                        'label': 'def', 'kind': 'snippet', 'detail': 'Function Definition', 
                        'insert_text': 'def name(args):\n    pass',
                        'documentation': 'Define uma nova função.\n\nSintaxe:\ndef nome_da_funcao(parametros):\n    corpo'
                    },
                    'class': {
                        'label': 'class', 'kind': 'snippet', 'detail': 'Class Definition', 
                        'insert_text': 'class Name:\n    def __init__(self):\n        pass',
                        'documentation': 'Define uma nova classe.\n\nInclui o método construtor __init__.'
                    },
                    'if': {
                        'label': 'if', 'kind': 'snippet', 'detail': 'If Statement', 
                        'insert_text': 'if condition:\n    pass',
                        'documentation': 'Estrutura condicional.\nExecuta o bloco se a condição for verdadeira.'
                    },
                    'for': {
                        'label': 'for', 'kind': 'snippet', 'detail': 'For Loop', 
                        'insert_text': 'for item in iterable:\n    pass',
                        'documentation': 'Loop for para iterar sobre uma sequência.'
                    }
                }
            },
            'html': {
                'keywords': [
                    "div", "span", "a", "href", "class", "id", "body", "html", "head", 
                    "script", "style", "img", "p", "h1", "h2", "ul", "li", "table", "tr", "td",
                    "form", "input", "button", "br", "meta", "link", "title"
                ],
                'snippets': {
                    'html5': {
                        'label': 'html5', 'kind': 'snippet', 'detail': 'HTML5 Template', 
                        'insert_text': '<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <title>Document</title>\n</head>\n<body>\n    \n</body>\n</html>',
                        'documentation': 'Estrutura básica de um documento HTML5.'
                    },
                    'div': {
                        'label': 'div', 'kind': 'snippet', 'detail': 'Div Element', 
                        'insert_text': '<div>\n    \n</div>',
                        'documentation': 'Define uma divisão ou seção em um documento HTML.'
                    },
                    'a': {
                        'label': 'a', 'kind': 'snippet', 'detail': 'Hyperlink', 
                        'insert_text': '<a href=""></a>',
                        'documentation': 'Define um hiperlink.'
                    }
                }
            },
            'css': {
                'keywords': [
                    "color", "background-color", "margin", "padding", "border", "font-size", 
                    "display", "flex", "grid", "width", "height", "position", "absolute", "relative",
                    "top", "left", "right", "bottom", "z-index", "opacity", "cursor"
                ],
                'snippets': {
                    'body': {'label': 'body', 'kind': 'snippet', 'detail': 'Body selector', 'insert_text': 'body {\n    margin: 0;\n    padding: 0;\n}'},
                    'media': {'label': '@media', 'kind': 'snippet', 'detail': 'Media Query', 'insert_text': '@media (max-width: 768px) {\n    \n}'}
                }
            },
            'javascript': {
                'keywords': [
                    "function", "const", "let", "var", "return", "if", "else", "for", "while",
                    "class", "import", "export", "default", "async", "await", "console", "log",
                    "document", "window", "null", "undefined", "true", "false"
                ],
                'snippets': {
                    'log': {'label': 'log', 'kind': 'snippet', 'detail': 'Console Log', 'insert_text': 'console.log();'},
                    'func': {'label': 'function', 'kind': 'snippet', 'detail': 'Function', 'insert_text': 'function name(args) {\n    \n}'}
                }
            }
        }
        
        # Mapeamento de extensões
        self.ext_map = {
            '.py': 'python',
            '.html': 'html', '.htm': 'html',
            '.css': 'css',
            '.js': 'javascript', '.jsx': 'javascript', '.ts': 'javascript'
        }

    def _get_language(self, file_path: str) -> str:
        if not file_path: return 'python' # Default
        _, ext = os.path.splitext(file_path)
        return self.ext_map.get(ext.lower(), 'python')

    def get_suggestions(self, buffer, line, col, file_path: str = "") -> list[dict]:
        """
        Retorna sugestões baseadas no contexto atual.
        Retorna lista de dicts: {'label', 'kind', 'detail', 'insert_text'?}
        """
        if col == 0:
            return []
            
        line_text = buffer.get_lines(line, line + 1)[0]
        
        # Encontra o início da palavra atual
        word_start_col = col
        while word_start_col > 0 and (line_text[word_start_col - 1].isalnum() or line_text[word_start_col - 1] == '_'):
            word_start_col -= 1
            
        current_word = line_text[word_start_col:col]

        if not current_word:
            return []

        lang = self._get_language(file_path)
        lang_data = self.languages.get(lang, self.languages['python'])
        
        suggestions = []

        # 1. Snippets
        for key, data in lang_data.get('snippets', {}).items():
            if key.startswith(current_word):
                suggestions.append(data)

        # 2. Keywords
        for kw in lang_data.get('keywords', []):
            if kw.startswith(current_word) and kw not in lang_data.get('snippets', {}):
                suggestions.append({'label': kw, 'kind': 'keyword', 'detail': 'Keyword'})

        # 3. Palavras no buffer (OTIMIZAÇÃO)
        # Analisa apenas uma janela de 1000 linhas ao redor do cursor para performance
        window_size = 1000
        start_line = max(0, line - window_size // 2)
        end_line = min(buffer.line_count, line + window_size // 2)
        all_text = "\n".join(buffer.get_lines(start_line, end_line))
        
        # Funções
        functions = set(re.findall(r'\bdef\s+([a-zA-Z_]\w*)\b', all_text))
        for func in functions:
            if func.startswith(current_word):
                suggestions.append({'label': func, 'kind': 'function', 'detail': 'Function'})

        # Classes
        classes = set(re.findall(r'\bclass\s+([a-zA-Z_]\w*)\b', all_text))
        for cls in classes:
            if cls.startswith(current_word):
                suggestions.append({'label': cls, 'kind': 'class', 'detail': 'Class'})

        # Outras palavras (variáveis)
        words = set(re.findall(r'\b[a-zA-Z_]\w*\b', all_text))
        existing_labels = {s['label'] for s in suggestions}
        for w in words:
            if w.startswith(current_word) and w not in existing_labels:
                suggestions.append({'label': w, 'kind': 'variable', 'detail': 'Variable'})
        
        # Remove duplicatas e ordena
        final_suggestions = []
        seen_labels = set()
        for s in suggestions:
            if s['label'] not in seen_labels:
                final_suggestions.append(s)
                seen_labels.add(s['label'])
        
        kind_order = {'snippet': 0, 'keyword': 1, 'function': 2, 'class': 3, 'variable': 4}
        final_suggestions.sort(key=lambda x: (kind_order.get(x['kind'], 5), x['label']))
        
        return final_suggestions

    def should_trigger(self, char: str) -> bool:
        """Verifica se o caractere deve acionar autocomplete."""
        return char in self.trigger_chars or (char and (char.isalnum() or char == '_'))
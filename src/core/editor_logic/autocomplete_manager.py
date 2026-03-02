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

    def get_parameter_hint(self, buffer, line, col, file_path: str = "") -> dict | None:
        """
        Verifica se o cursor está dentro de uma chamada de função e retorna a assinatura.
        """
        # 1. Identificar se estamos dentro de parênteses
        # Simplificação: olhar apenas para a linha atual e anteriores próximas
        start_line = max(0, line - 10)
        text_block = "\n".join(buffer.get_lines(start_line, line + 1))
        
        # Calcular offset do cursor dentro do text_block
        lines = buffer.get_lines(start_line, line + 1)
        cursor_offset = 0
        for i in range(len(lines) - 1):
            cursor_offset += len(lines[i]) + 1 # +1 para \n
        cursor_offset += col
        
        # Busca para trás por '(' não fechado
        balance = 0
        func_name = ""
        
        # Limite de busca para trás para performance
        search_limit = max(0, cursor_offset - 1000)
        
        for i in range(cursor_offset - 1, search_limit - 1, -1):
            if i >= len(text_block): continue
            char = text_block[i]
            if char == ')':
                balance += 1
            elif char == '(':
                if balance > 0:
                    balance -= 1
                else:
                    # Encontramos o '(' de abertura
                    # Agora pegamos o nome da função antes dele
                    # Ignora espaços
                    j = i - 1
                    while j >= 0 and text_block[j].isspace():
                        j -= 1
                    
                    # Pega identificador
                    k = j
                    while k >= 0 and (text_block[k].isalnum() or text_block[k] == '_'):
                        k -= 1
                    
                    func_name = text_block[k+1 : j+1]
                    break
        
        if not func_name:
            return None
        
        # Calcular índice do parâmetro ativo
        open_paren_index = i
        args_text = text_block[open_paren_index+1 : cursor_offset]
        
        comma_count = 0
        nest_level = 0
        quote_char = None
        
        for char in args_text:
            if quote_char:
                if char == quote_char and (len(args_text) > 1 and args_text[args_text.index(char)-1] != '\\'): 
                    quote_char = None
            elif char in "\"'":
                quote_char = char
            elif char in "([{":
                nest_level += 1
            elif char in ")]}":
                if nest_level > 0: nest_level -= 1
            elif char == ',' and nest_level == 0:
                comma_count += 1
        
        active_index = comma_count
        
        # 2. Buscar assinatura da função
        lang = self._get_language(file_path)
        
        # Verifica se é um método de classe (ex: variavel.metodo)
        class_type = self._detect_class_type(text_block, open_paren_index, func_name, buffer)
        signature = self._find_signature(func_name, buffer, lang, class_type)
        
        if signature:
            return {
                "name": func_name,
                "params": signature,
                "active_index": active_index
            }
        return None

    def _detect_class_type(self, text_block, open_paren_index, func_name, buffer):
        """Tenta inferir o tipo da variável antes do método."""
        # Procura por '.' antes do nome da função
        # O func_name foi extraído terminando em open_paren_index - 1 (aproximadamente)
        # Precisamos achar onde func_name começa no text_block
        
        # Busca reversa simples a partir do parêntese
        idx = open_paren_index - 1
        while idx >= 0 and text_block[idx].isspace():
            idx -= 1
        
        # Pula o nome da função
        idx -= len(func_name)
        
        if idx >= 0 and text_block[idx] == '.':
            # Temos um ponto! Extrair a variável anterior
            idx -= 1
            while idx >= 0 and text_block[idx].isspace():
                idx -= 1
            
            end_var = idx + 1
            while idx >= 0 and (text_block[idx].isalnum() or text_block[idx] == '_'):
                idx -= 1
            
            var_name = text_block[idx+1 : end_var]
            
            if var_name:
                # Tenta achar a definição da variável no buffer (ex: var = Classe())
                # Simplificação: busca nas últimas 100 linhas
                all_text = buffer.get_text() # Idealmente limitar range
                # Regex simples para atribuição: var = Classe(
                pattern = r'\b' + re.escape(var_name) + r'\s*=\s*([a-zA-Z_]\w*)\s*\('
                matches = list(re.finditer(pattern, all_text))
                if matches:
                    # Pega a última atribuição encontrada antes do cursor seria o ideal, 
                    # mas pegar a última do arquivo é um bom chute
                    return matches[-1].group(1)
                
                # Inferência para tipos built-in comuns baseados em literais (muito básico)
                if var_name.startswith('"') or var_name.startswith("'"): return 'str'
                if var_name.startswith('['): return 'list'
                if var_name.startswith('{'): return 'dict'
                
        return None

    def _find_signature(self, func_name, buffer, lang, class_type=None):
        # 1. Hardcoded signatures (exemplo)
        signatures = {
            'python': {
                'print': 'value, ..., sep=" ", end="\\n"',
                'len': 'obj',
                'range': 'start, stop[, step]',
                'open': 'file, mode="r", buffering=-1, ...',
                'super': 'type, obj_or_type',
                'int': 'x, base=10',
                'str': 'object=""',
                'list': 'iterable=()',
                'dict': 'mapping=(), **kwargs',
                # Métodos de Classes Comuns
                'str.split': 'sep=None, maxsplit=-1',
                'str.replace': 'old, new, count=-1',
                'list.append': 'object',
                'list.pop': 'index=-1',
                'dict.get': 'key, default=None'
            },
            'javascript': {
                'console.log': 'message, ...',
                'alert': 'message',
                'parseInt': 'string, radix',
                'setTimeout': 'function, milliseconds, param1, ...'
            }
        }
        
        # Tenta buscar como Metodo de Classe (ex: str.split)
        if class_type:
            key = f"{class_type}.{func_name}"
            if lang in signatures and key in signatures[lang]:
                return signatures[lang][key]

        if lang in signatures and func_name in signatures[lang]:
            return signatures[lang][func_name]
            
        # 2. Busca no buffer (definições locais)
        all_text = buffer.get_text()
        
        if lang == 'python':
            pattern = r'def\s+' + re.escape(func_name) + r'\s*\((.*?)\)'
        elif lang == 'javascript':
            pattern = r'function\s+' + re.escape(func_name) + r'\s*\((.*?)\)'
        else:
            return None
            
        match = re.search(pattern, all_text, re.DOTALL)
        if match:
            params = match.group(1).replace('\n', '').strip()
            params = re.sub(r'\s+', ' ', params) # Normaliza espaços
            return params
            
        return None
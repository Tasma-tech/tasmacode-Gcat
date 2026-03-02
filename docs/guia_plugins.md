### Guia Oficial de Desenvolvimento de Plugins para Tasmacode-Gcat 

**Objetivo**: Permitir extensões seguras, modulares e fáceis de manter, sem risco ao editor principal. O sistema prioriza simplicidade, isolamento total e estabilidade.

#### 1. Estrutura Obrigatória da Pasta do Plugin
Todo plugin **deve** ter sua própria pasta em `plugins/`:

```
plugins/
└── nome-do-plugin/                  # obrigatório: lowercase, sem espaços, único (ex: smear-cursor, git-tools)
    ├── manifesto.md                 # obrigatório – descrição + metadados humanos (preferência .md, ou .txt)
    ├── main.py                      # obrigatório – ponto de entrada do código
    ├── __init__.py                  # opcional – se existir, o plugin vira pacote Python
    ├── config.py                    # opcional – configurações do plugin
    ├── README.md                    # opcional – documentação extra
    └── icon.png                     # opcional – ícone pra lista ou loja
```
- **Regras estritas**:
  - Não pode ter arquivos soltos diretamente em `plugins/` — só pastas.
  - O loader ignora pastas sem `manifesto.md` (ou .txt) e sem `main.py`.
  - Nome da pasta deve ser único e não pode coincidir com nomes do core.

#### 2. Manifesto (manifesto.md ou manifesto.txt) – Obrigatório
- Formato preferido: **Markdown (.md)** — mais bonito e legível (suporta títulos, listas, código).
- Alternativa simples: **.txt** (texto puro).
- Conteúdo mínimo obrigatório (exemplo em manifesto.md):

```
# Nome do Plugin
Smear Cursor 

## Descrição
Adiciona um cursor elástico com efeito de física de molas durante o movimento. Inspirado no smear-cursor.nvim.

## Versão
0.1.0

## Autor
John-BrenoF

## Licença
MIT

## Requisitos
- PySide6 >= 6.6
- Nenhum pacote extra

## Ponto de Entrada
main.py

## Classe Principal
SmearPlugin

## Categoria
visual

## Ícone
icon.png

## Repositório (opcional)
https://github.com/---/---.git
```

- O loader lê isso como texto simples → parseia linhas chave-valor (ex: "Versão: 0.1.0") ou seções Markdown.
- Pode adicionar qualquer seção extra (ex: "Como usar", "Exemplos", "Notas").

#### 3. Código do Plugin (main.py) – Obrigatório
- Deve herdar de uma classe base do core (pra garantir isolamento):
  ```python
  from core.plugin import PluginBase  # classe base que você cria no editor

  class SmearPlugin(PluginBase):
      def activate(self, editor):
          # Aqui: adiciona ações, menus, timers, etc.
          pass

      def deactivate(self, editor):
          # Aqui: limpa tudo (desconecta sinais, para timers, deleta widgets)
          pass
  ```
- **Regras de isolamento**:
  - Não pode importar módulos do core diretamente (exceto `PluginBase`).
  - Use só APIs permitidas: `editor.add_menu_item(...)`, `editor.register_command(...)`, `editor.get_buffer()`, etc.
  - Em `deactivate`: desconecte sinais, pare QTimer, delete widgets com `deleteLater()`.

#### 4. Regras de Segurança e Estabilidade (obrigatórias)
- **Cleanup obrigatório**: Em `deactivate`, limpe tudo pra evitar vazamentos de memória (desconecte sinais, pare timers, delete widgets).
- **Sem acesso perigoso**:
  - Proibido: `os.system()`, `subprocess` sem whitelist, `exec()`/`eval()`.
  - Se precisar de subprocess (ex: git), use `QProcess` com comandos pré-definidos.
- **Limites**:
  - Máximo 1 thread por plugin.
  - Operações > 500ms devem ser assíncronas (QThread).
  - Nenhum arquivo fora da pasta do plugin (use `editor.get_plugin_dir()` pra pasta data/ segura).
- **Erros**: Capture exceções, logue com `logging.error`, não deixe crashar o editor.

#### 5. Atualização e Distribuição
- Campo opcional no manifesto: `Repositório: https://...`
- Loader pode comparar versão e avisar update (futuro).

#### 6. Recomendações Finais
- Teste sempre em modo "safe" (sandbox).
- Use logging em vez de print.
- Documente bem no README.md interno.
- Plugins que violarem regras serão bloqueados automaticamente.
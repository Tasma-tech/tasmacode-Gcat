from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextBrowser
from PySide6.QtCore import Qt

class BatataWindow(QDialog):
    """
    Janela de novidades (Release Notes) exibindo Markdown.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("TasmaCode v11.0 - Batata Escovada")
        self.resize(800, 600)

        layout = QVBoxLayout(self)
        
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        
        html_text = """
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body { font-family: sans-serif; color: #cccccc; background-color: #252526; }
            h2 { color: #ffffff; font-size: 20px; }
            a { color: #4fc1ff; text-decoration: none; }
            h3 { color: #e0e0e0; font-size: 16px; margin-top: 15px; }
            p { margin-bottom: 10px; line-height: 1.4; }
            li { margin-bottom: 5px; }
            b { color: #ffffff; }
            .code-block { background-color: #1e1e1e; border: 1px solid #3e3e42; padding: 10px; margin: 10px 0; font-family: 'Consolas', 'Monospace'; color: #d4d4d4; }
        </style>
        </head>
        <body>
            <h2>TasmaCode v11.0 – Batata Escovada (Atualização Significativa de Interface e Funcionalidades – 4 de março de 2026)</h2>

            <p>Esta versão, codinome <b>Batata Escovada</b>, introduz diversas melhorias na interface do usuário, usabilidade e funcionalidades principais, consolidando o editor como uma ferramenta mais robusta, personalizável e visualmente consistente.</p>

            <h3>Principais Recursos Adicionados</h3>
            <ul>
                <li><b>Marcadores (Markers)</b>: Implementada a funcionalidade de adicionar marcadores por meio de clique com o botão direito no número da linha. Os marcadores são persistentes, suportam personalização (cores e outros atributos) e permitem navegação direta para a linha correspondente através do menu. Ideal para marcação e referência rápida em arquivos extensos.</li>
                <li><b>Efeito Smear Cursor</b>: Adicionado efeito de rastros animados e fluidos no cursor, reimplementado em Python para ambiente gráfico (baseado em conceitos semelhantes a plugins de editores de terminal). Proporciona maior dinamismo e fluidez visual durante a edição.</li>
                <li><b>Destaque da Linha Atual</b>: A linha sob o cursor é destacada visualmente, facilitando a leitura e o foco durante a navegação e edição de código.</li>
                <li><b>Quebra de Linhas (Word Wrap) e Modo de Rolagem</b>: Implementado envolvimento automático de linhas longas (word wrap) e rolagem suave, com correção completa para que os números de linha acompanhem corretamente o deslocamento do conteúdo, eliminando problemas anteriores de desalinhamento.</li>
                <li><b>Sistema de Undo/Redo Aprimorado</b>: O sistema de undo/redo foi refatorado completamente para corrigir uma implementação anterior incompleta e problemática. Bugs recorrentes incluíam: método redo vazio ou ineficaz, cursores não ajustados corretamente após deleções (especialmente em cenários multi-cursor ou mescla de linhas), perda de estado em operações complexas e desalinhamentos verticais. As principais correções implementadas foram:
                    <ul>
                        <li>Implementação granular do método <code>redo()</code>, espelhando a lógica do <code>undo()</code> para reverter ações de forma precisa.</li>
                        <li>Ajuste automático de cursores vizinhos na mesma linha durante deleções (ex.: shift de colunas quando caractere é removido).</li>
                        <li>Shift vertical negativo para cursores em linhas afetadas por mesclas (ex.: delete_backspace unindo linhas).</li>
                    </ul>
                </li>
            </ul>

            <p><b>Exemplo de trecho implementado no redo (simplificado):</b></p>
            <div class="code-block"><pre>
def redo(self):
    \"\"\"Refaz a última ação desfeita.\"\"\"
    if not self._redo_stack:
        return
    action = self._redo_stack.pop()
    if action.type == 'insert':
        for cursor in action.cursors_before:
            self._insert_at_single_cursor(cursor, action.text)
        self.cursors = [c.copy() for c in action.cursors_after]
    elif action.type in ('delete', 'delete_selection'):
        self.cursors = [c.copy() for c in action.cursors_before]
        if action.type == 'delete_selection':
            self.delete_selection()
        else:
            self.delete_backspace()
    # ... (demais casos como replace_all)
    self._undo_stack.append(action)
    self.dirty = True
</pre></div>

            <p>Exemplo de ajuste de cursores vizinhos em deleção na mesma linha:</p>
            <div class="code-block"><pre>
# Dentro de _delete_char_at()
for other in self.cursors:
    if other is not cursor and other.line == line and other.col >= col:
        other.col -= 1
</pre></div>

            <p>Além dessas correções principais, realizei diversos ajustes adicionais, pois novos bugs menores surgiram durante os testes (desalinhamentos residuais em multi-cursor e edge cases de merge). O sistema agora está consideravelmente mais estável e confiável.</p>

            <ul>
                <li><b>Suporte a Fontes Personalizadas</b>: Adicionado suporte completo para utilização de fontes arbitrárias definidas pelo usuário, sem restrições.</li>
                <li><b>Consistência Total de Temas</b>: Garantida a aplicação uniforme dos temas selecionados em toda a interface, incluindo aparência, atalhos e configurações, eliminando inconsistências visuais.</li>
                <li><b>Novos Temas</b>: Inclusão do tema "void" e refatoração do "voidme", além da adição do "neon". As opções cyberpunk, neon e dark foram aprimoradas em refinamento visual e compatibilidade.</li>
                <li><b>Atualização no Plugin de IA Chat</b>: Implementada barra de janela customizada e melhorias gerais no assistente de IA integrado (com suporte à API Groq), aumentando a usabilidade e a integração com o editor.</li>
            </ul>

            <h3>Correções de Bugs e Otimizações</h3>
            <ul>
                <li>Correções múltiplas no sistema de rolagem e exibição de números de linha, garantindo alinhamento preciso durante o deslocamento.</li>
                <li>Otimizações gerais no código para maior desempenho e estabilidade.</li>
                <li>Inclusão de arquivo <code>.gitignore</code> para melhor organização do repositório.</li>
            </ul>

            <p>Esta versão se encontra em fase <b>beta</b>, com funcionalidades principais estabilizadas, embora ainda haja espaço para refinamentos adicionais. O projeto continua em evolução acelerada. Contribuições, relatórios de bugs e sugestões são bem-vindos por meio das issues.</p>

            <p><b>Créditos especiais</b>: O efeito de smear cursor foi inspirado no projeto <a href="https://github.com/sphamba/smear-cursor.nvim">smear-cursor.nvim</a>, licenciado sob GPL-3.0.</p>

            <p>O código-fonte completo desta versão está disponível para download no repositório. Próximas atualizações em andamento.</p>

            <p><b>Código Fonte:</b> <a href="https://github.com/John-BrenoF/tasmacode-Gcat.git">https://github.com/John-BrenoF/tasmacode-Gcat.git</a></p>
        </body>
        </html>
        """

        self.text_browser.setHtml(html_text)
        layout.addWidget(self.text_browser)

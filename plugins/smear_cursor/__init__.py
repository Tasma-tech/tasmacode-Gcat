"""
Smear Cursor Plugin - Coordenação Principal
Responsabilidade: Orquestrar todos os componentes do plugin
"""
from .widget import SmearCursorWidget
from .config import SmearConfig

def plugin_main(api):
    """Ponto de entrada do plugin."""
    api.log("Smear Cursor Plugin inicializado!")
    
    # Tenta anexar ao editor ativo se houver um
    editor = api.get_active_editor()
    if editor:
        attach_to_editor(editor)

def attach_to_editor(editor):
    """Anexa o widget de efeito ao editor."""
    if not hasattr(editor, 'smear_widget'):
        # Cria o widget passando o editor como pai
        editor.smear_widget = SmearCursorWidget(editor)
        editor.smear_widget.show()
        editor.smear_widget.raise_()
        api_log = getattr(editor, "api_log", print) # Fallback log
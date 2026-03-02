"""
Smear Cursor Plugin - Coordenação Principal
Responsabilidade: Orquestrar todos os componentes do plugin
"""
from .widget import SmearCursorWidget
from .config import SmearConfig

def plugin_main(api):
    """Ponto de entrada do plugin."""
    api.log("Smear Cursor Plugin inicializado!")
    api.add_menu_action("Ativar/Desativar Smear Cursor", toggle_smear)
    api.add_menu_action("Modo: Sólido", lambda api: set_mode(api, 'solid'))
    api.add_menu_action("Modo: Partículas", lambda api: set_mode(api, 'particles'))
    
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

def toggle_smear(api):
    """Alterna o estado do efeito no editor ativo."""
    editor = api.get_active_editor()
    if editor and hasattr(editor, 'smear_widget'):
        widget = editor.smear_widget
        widget.set_enabled(not widget.enabled)
        status = "Ativado" if widget.enabled else "Desativado"
        api.log(f"Smear Cursor {status}")

def set_mode(api, mode):
    """Altera o modo de renderização."""
    api.update_config("smear_mode", mode)
    api.log(f"Smear Cursor: Modo {mode} definido e salvo.")
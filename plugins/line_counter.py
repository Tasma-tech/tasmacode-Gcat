# plugins/line_counter.py
# Este plugin conta o número de linhas no arquivo atual.

def plugin_main(api):
    """Ponto de entrada do plugin, chamado na ativação."""
    api.log("Plugin 'Contador de Linhas' ativado.")
    api.add_menu_action("Contar Linhas do Arquivo", show_line_count)

def show_line_count(api):
    """Pega o texto do buffer, conta as linhas e exibe na barra de status."""
    full_text = api.get_full_text()
    
    # Usar splitlines() é uma forma robusta de contar as linhas
    line_count = len(full_text.splitlines())
        
    api.log(f"Total de linhas: {line_count}")
# Exemplo de Plugin para o JCode
# Este arquivo é carregado automaticamente pelo ExtensionBridge

def plugin_main(api):
    """Ponto de entrada do plugin."""
    api.log("Hello World Plugin inicializado!")
    api.add_menu_action("Hello World (Upper)", to_upper)

def to_upper(api):
    """Callback executado ao clicar no menu."""
    text = api.get_full_text()
    if text:
        # Insere o texto em maiúsculas na posição do cursor
        api.insert_text("\n" + text.upper())
        api.log("Texto transformado em maiúsculas com sucesso!")
    else:
        api.log("O buffer está vazio!")
from .diagram import DiagramWindow


def create_diagram_window(parent=None):
    return DiagramWindow(parent)


def plugin_main(api):
    def open_diagram(_api):
        window = create_diagram_window()
        window.show()
        window.raise_()
        window.activateWindow()
        _api.log("dIAgram aberto.")

    api.add_menu_action("Abrir dIAgram", open_diagram)

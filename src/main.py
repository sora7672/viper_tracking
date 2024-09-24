
from input_tracker import start_input_tracker
from window_tracker import start_window_tracker, init_all_labels_from_db
from gui_handler import start_root_gui, init_root_gui
from system_tray_handler import start_systray_icon
from config_manager import initialize_config_manager


# TODO: in english
#   wenn was hinzugefügt, dann update des tracking threads/microservies/Prozess
#   Auswertungen müssen per label, fenster typ, nach text suche, text/word segments
#   oder irgendeiner kombnation dieser machbar sein
#   Advanced conditions, wie z.B. wenn anwendung A hauptfenster & Anwendung B im Hintergrund, dann setz label

def start_program() -> None:
    """
    The function to start all needed application modules.
    :return: None
    """
# FIXME: also icon not accepted in ttkb windows?

    initialize_config_manager()
    init_all_labels_from_db()

    init_root_gui()

    start_input_tracker()

    start_window_tracker()

    start_systray_icon()

    start_root_gui()
    print("is the program closed?")


    # TODO: termination process handeling, like on errors



if __name__ == "__main__":
    start_program()

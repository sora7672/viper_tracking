
from input_manager import start_input_tracker
from window_manager import start_window_tracker, init_all_labels_from_db
from gui_controller import start_root_gui, init_root_gui
from system_tray_manager import start_systray_icon
from config_manager import initialize_config_manager
from log_handler import get_logger, init_logging
from db_connector import start_db


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
    init_logging()
    get_logger().debug("config_manager init done & log_handler started")

    start_db()
    get_logger().debug("start_db done")

    init_all_labels_from_db()
    get_logger().debug("imported from labels done")

    init_root_gui()
    get_logger().debug("init root gui done")

    start_input_tracker()
    get_logger().debug("input tracker start done")

    start_window_tracker()
    get_logger().debug("window tracker start done")

    start_systray_icon()
    get_logger().debug("started systray icon")
    get_logger().debug("Now starting mainloop")
    start_root_gui()
    get_logger().debug("Mainloop properly finished")



    # TODO: termination process handeling, like on errors



if __name__ == "__main__":
    start_program()

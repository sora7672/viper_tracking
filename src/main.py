
from input_tracker import start_input_tracker
from window_tracker import start_window_tracker, init_all_labels_from_db
from gui_handler import start_root_gui, init_root_gui
from system_tray_handler import start_systray_icon
from config_manager import initialize_config_manager, get_logger


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

    get_logger().info("Logger started")
    initialize_config_manager()
    get_logger().info("config_manager started")
    init_all_labels_from_db()
    get_logger().info("imported Labels from DB")

    init_root_gui()
    get_logger().info("init root gui")

    start_input_tracker()
    get_logger().info("started input tracker")

    start_window_tracker()
    get_logger().info("started window tracker")

    start_systray_icon()
    get_logger().info("started systray icon")
    get_logger().info("start gui main loop")
    start_root_gui()
    get_logger().info("end root gui")
    print("Main loop properly finished")  # FIXME: shows only if destroy is used, if quit is used we wont see this


    # TODO: termination process handeling, like on errors



if __name__ == "__main__":
    start_program()

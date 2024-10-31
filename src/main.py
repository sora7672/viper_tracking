"""
This is the module that needs to be executed to run the program.
It loads and initializes all other modules needed.

Author: sora7672
"""


from input_manager import start_input_tracker
from window_manager import start_window_tracker, init_all_labels_from_db
from gui_controller import start_root_gui, init_root_gui
from system_tray_manager import start_systray_icon
from config_manager import initialize_config_manager
from log_handler import get_logger, init_logging
from db_connector import start_db
from settings_manager import init_user_settings

# TODO: in english
#  We need analyzes that can combine different ways of searching infos from the database.
#  also there needs to be time window pre choices like this week, last week, last 3 days whatsover
#  maybe later advanced conditions for analyzes and labeling. Like background windows or system time (night/day etc)

# FIXME: Not saving manually labels properly or maybe not loading in on restart!
#  What about auto labels?

def start_program() -> None:
    """
    The function to start all needed application modules.
    :return: None
    """

    # TODO: add settings manager init
    initialize_config_manager()
    init_logging()
    get_logger().debug("config_manager init done & log_handler started")

    init_user_settings()
    get_logger().debug("user_settings init done")
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

    # TODO: termination process handling, like on errors


if __name__ == "__main__":
    start_program()

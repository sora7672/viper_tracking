"""
This module handles all operations related to the system tray icon.

Features:
- Provides menu interaction through the systray.
- Integrates with external modules like the GUI and database.
- Includes functionality for starting and stopping the program cleanly.

Author: sora7672
"""
__author__ = 'sora7672'

from pystray import Icon, Menu, MenuItem
from PIL import Image
import threading
from time import sleep

from config_manager import stop_program_threads
from log_handler import get_logger
from input_manager import stop_done as input_stop_done
from window_manager import Label, update_all_labels_to_db, stop_done as win_stop_done
from gui_controller import stop_gui
from db_connector import stop_db
from gui_views import open_main_window, open_systray_label


class MultiFunction:
    """
    A utility class for executing multiple functions from a single event or action.

    This class enables calling a sequence of functions in response to a single GUI
    or system tray event. It also supports passing arguments to these functions.
    """

    def __init__(self, *functions):
        """
        Initializes the `MultiFunction` instance with a list of functions.

        :param functions: list[callable] (One or more functions to be executed sequentially.)
        :return: None
        """

        self.functions = functions

    # Call each function in sequence
    def __call__(self, *args):
        """
        Executes all functions in the `functions` list sequentially.

        :param args: tuple (Arguments to pass to each function.)
        :return: None
        """

        for func in self.functions:
            func()


class SystemTrayManager:
    """
    Handles all operations related to the system tray icon.

    This class runs in a detached mode, creating its own thread, and can be closed
    gracefully using `self.icon.stop()`. It is designed as a singleton to ensure
    only one instance manages the system tray.

    Attributes:
        _instance (SystemTrayManager | None): The singleton instance of the `SystemTrayManager`.
        _initialized (bool): Indicates whether the instance has been initialized. Prevents reinitialization.
        icon (Icon): The system tray icon instance, initialized with the application's icon.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Implements the singleton pattern, ensuring only one instance of the class exists.

        :return: SystemTrayManager (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the SystemTrayManager instance.

        - Sets up the system tray icon with a default menu.
        - Ensures debug logging for initialization.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.icon = Icon("Viper Tracking", Image.open("src/viper_tray.ico"))
            # TODO: Not needed menu?
            self.menu = None
            SystemTrayManager._instance = self
            get_logger().debug("__init__ SystemTrayManager")

    def start_systray(self) -> None:
        """
        Starts the system tray icon and generates its menu.

        This method runs the system tray icon in detached mode, allowing it to
        function in the background without blocking other processes.

        :return: None
        """

        self.update_menu()
        self.icon.run_detached()
        get_logger().debug("started systray icon detached")

    def stop_program(self) -> None:
        """
        Performs all necessary cleanup operations when the program is stopped.

        This method:
        1. Stops all threads gracefully.
        2. Calls the stop function for the GUI and database connections.
        3. Updates all labels to the database.
        4. Stops the systray icon and logs remaining threads.

        :return: None
        """

        stop_program_threads()
        # wait for threads to be done
        if input_stop_done():
            get_logger().debug("input_stop_done()")
        if win_stop_done():
            get_logger().debug("win_stop_done()")

        stop_gui()
        sleep(0.3)
        get_logger().debug("stop_gui is done")

        update_all_labels_to_db()
        sleep(0.3)
        get_logger().debug("update_all_labels_to_db() done")

        stop_db()
        sleep(0.3)
        get_logger().debug("close_db_connection() done")

        self.icon.stop()
        sleep(0.3)
        get_logger().debug("self.icon.stop() done)")

        # Debug to see if after close are still threads open
        for th in threading.enumerate():
            get_logger().debug(f"Thread still open: {th}")

    def update_menu(self) -> None:
        """
        Updates the system tray menu.

        The menu is dynamically generated to reflect the current state of the program,
        including manual labels and their statuses.

        :return: None
        """

        self.icon.menu = Menu(self._label_menu(),
                              MenuItem("Open GUI", open_main_window),
                              MenuItem("Exit Viper Tracking", self.stop_program))
        self.icon.update_menu()

    def _label_menu(self) -> MenuItem:
        """
        Creates menu entries for manually added labels.

        For each manual label, this method adds:
        - Activation and deactivation options based on the label's status.
        - An option to add and start a new label.

        :return: pystray.MenuItem (The menu item containing all manual labels.)
        """

        all_label = Label.get_all_labels()
        menu_labels = []
        for label in all_label:
            if label.manually:
                # TODO: remove the enable/disable and make it to set the value if possible.
                disable_action = MultiFunction(label.disable, self.update_menu)
                enable_action = MultiFunction(label.enable, self.update_menu)

                menu_labels.append(MenuItem(label.name, Menu(
                    MenuItem("Activate", enable_action, visible=not label.active),
                    MenuItem("Deactivate", disable_action, visible=label.active)
                )))

        menu_labels.append(MenuItem("Add & start new Label", open_systray_label))

        tmp_menu = MenuItem("Manual Labels", Menu(*menu_labels))
        return tmp_menu


# # # # External call functions for less import in other files # # # #
def start_systray_icon() -> None:
    """
    Starts the system tray icon using the SystemTrayManager singleton.

    :return: None
    """

    SystemTrayManager().start_systray()


def stop_program():
    """
    Stops the entire program gracefully.

    All external program stops, aside from the system tray, should use this function.

    :return: None
    """

    SystemTrayManager().stop_program()


if __name__ == "__main__":
    # Will get an async error if tested alone, because GUI is not initiated
    print("Please start with the main.py")


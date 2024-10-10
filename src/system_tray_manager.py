"""
This module is handling all related to the systray icon.
Looks and function calls of external modules, like gui.
Author: sora7672
"""

from pystray import Icon, Menu, MenuItem
from PIL import Image


from config_manager import stop_program_threads
from log_handler import get_logger

from input_manager import stop_done as input_stop_done
from window_manager import Label, update_all_labels_to_db, stop_done as win_stop_done
from gui_controller import stop_gui
from db_connector import stop_db
from gui_views import open_main_window, open_systray_label
import threading
from time import sleep

class MultiFunction:
    """
    This class is created to make it possible to call multiple functions
    in one GUI or pystray event which normally would only accept one.
    Also, you can properly hand over the arguments.
    """
    def __init__(self, *functions):
        self.functions = functions

    # Call each function in sequence
    def __call__(self, *args):
        for func in self.functions:
            func()


class SystemTrayManager:
    """
    This class handles all related to the systray icon.
    It's running in detached mode, which creates a thread itself
    and can be threadsafe gracefully closed with self.icon.stop()
    It's a singleton.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.icon = Icon("Viper Tracking", Image.open("src/viper_tray.ico"))
            self.menu = None
            SystemTrayManager._instance = self
            get_logger().debug("__init__ SystemTrayManager")

    def start_systray(self) -> None:
        """
        Just starts the systray icon and generates its menu before.
        :return: None
        """
        self.update_menu()
        self.icon.run_detached()
        get_logger().debug("started systray icon detached")

    def stop_program(self) -> None:
        """
        This methode is the most important after the program start.
        It handles all that needs to be done when the program should be closed.
        There is an import/export function if the program should be stoppable
        from another module also.

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

        for th in threading.enumerate():
            get_logger().debug(f"Thread still open: {th}")

    def update_menu(self) -> None:
        """
        This updates the systray menu.
        """
        self.icon.menu = Menu(self._label_menu(),
                              MenuItem("Open GUI", open_main_window),
                              MenuItem("Exit Viper Tracking", self.stop_program))
        self.icon.update_menu()

    def _label_menu(self) -> MenuItem:
        """
        Helper for menu creation.
        It creates the menu entries for the manually labels that
        can be switched on/off or added a new manually label.
        """
        all_label = Label.get_all_labels()
        menu_labels = []
        for label in all_label:
            if label.manually:

                disable_action = MultiFunction(label.disable, self.update_menu)
                enable_action = MultiFunction(label.enable, self.update_menu)

                menu_labels.append(MenuItem(label.name, Menu(
                    MenuItem("Activate", enable_action, visible=not label.is_active),
                    MenuItem("Deactivate", disable_action, visible=label.is_active)
                )))

        menu_labels.append(MenuItem("Add & start new Label", open_systray_label))

        tmp_menu = MenuItem("Manual Labels", Menu(*menu_labels))
        return tmp_menu


# # # # External call functions for less import in other files # # # #
def start_systray_icon():
    """
    Starts the systray icon.
    """
    SystemTrayManager().start_systray()


def stop_program():
    """
    Stops the whole program with this call.
    All external closes, away from systray should be using this fucntion too!
    """
    SystemTrayManager().stop_program()


if __name__ == "__main__":
    # Will get an async error if tested alone, because GUI is not initiated
    print("Please start with the main.py")


"""
This module handles the main GUI class, `GuiController`, which serves as the foundation for all GUI elements.

Features:
- Thread-safe initialization of GUI components.
- Centralized control of all GUI-related operations.
- Utility functions for managing the GUI lifecycle.

Author: sora7672
"""
__author__ = 'sora7672'

import ttkbootstrap as tb
from tkinter import PhotoImage
from threading import Lock
from log_handler import get_logger
from os import path

from settings_manager import UserSettingsManager
# TODO: Grab the user settings and set the proper style for the windows

class GuiController:
    """
    The primary GUI controller for the application.

    This class manages the main GUI root and ensures proper initialization and teardown
    of GUI elements. It runs exclusively on the main thread to avoid threading conflicts.

    Attributes:
        _instance: Singleton instance of the `GuiController`.
        root: The main GUI window (invisible by default).
        icon_image: The icon image for the window.
        icon_path: Absolute path to the icon image file.
        lock: A threading lock to ensure safe operations.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Implements the singleton pattern by ensuring only one instance of the class exists.

        :return: InputManager (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        Initializes the `GuiController` instance.

        - Configures the main GUI window.
        - Sets up the window title and icon.
        - Initializes a threading lock for safe operations.

        Note:
        - The window is invisible on initialization (`withdraw` is called).
        - Logs initialization details for debugging purposes.

        :raises Exception: If the icon image fails to load.
        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            # TODO: read in config for style from user settings
            self.root = tb.Window(themename="sandstone")
            self.root.withdraw()

            self.root.title('Invisible Window(If you see me report me!)')
            # TODO: get a better image
            self.icon_filename = "viper_tracking_64.png"
            self.icon_folder = path.abspath(path.join(path.dirname(__file__), "..", "images"))
            self.icon_path = path.abspath(path.join(self.icon_folder, self.icon_filename))
            try:
                self.icon_image = PhotoImage(file=self.icon_path)
                self.root.iconphoto(False, self.icon_image)
            except Exception as e:
                get_logger().error(f"Failed to set icon. Error: {e}")

            self.lock = Lock()
            get_logger().debug("__init__ from GuiHandler")

    def run(self) -> None:
        """
        Starts the GUI's main event loop.

        Once this method is called:
        - No further code executes until the loop ends (`self.stop` or `self.stop_helper`).
        - Actions inside the GUI should use `self.root.after(seconds, function)` for proper tracking.

        :return: None
        """

        self.root.mainloop()

    def stop_helper(self) -> None:
        """
        Helper method to stop the main loop safely.

        This method schedules the `stop` method to be called within the GUI's main thread,
        ensuring the loop exits properly.
        If not called like this from another thread the mainloop can't be closed properly.

        :return: None
        """

        self.root.after(100, self.stop)

    def stop(self) -> None:
        """
        Stops the GUI's main event loop and destroys all child windows.

        How it works:
        - Destroys all child windows of the main GUI window.
        - Exits the main loop (`self.root.quit`).
        - Logs the entire shutdown process.

        Important:
        This method must be called using `self.stop_helper()` to ensure proper execution.

        :return: None
        """

        get_logger().debug("methode stop from GuiHandler start")
        childs = self.root.winfo_children()
        for chil in childs:
            chil.destroy()
        get_logger().debug("destroyed all childs from GuiHandler")
        self.root.quit()
        get_logger().debug("after root.quit")
        get_logger().debug("methode stop from GuiHandler end")


# # # # Helper functions for the widgets # # # #


# # # # External call functions for less import in other files # # # #

def stop_gui() -> None:
    """
    Stops the main GUI loop safely.

    This function wraps `GuiController.stop_helper` for external usage, reducing direct imports.

    :return: None
    """

    GuiController().stop_helper()


def init_root_gui() -> None:
    """
    Initializes the root GUI without starting the main event loop.

    This function is useful for setting up the GUI before all other threads are started.

    :return: None
    """

    GuiController()


def start_root_gui() -> None:
    """
    Starts the main GUI event loop.

    Warning:
    - After starting the loop, no additional code will execute until the loop exits.
    - Ensure all necessary threads are started before calling this function.

    :return: None
    """

    GuiController().run()


if __name__ == "__main__":
    print("Please start with the main.py")

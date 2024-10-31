"""
This file will handle the main GUI class, called GUIController.
All windows will be created on toplevel of it for thread safety.

Author: sora7672
"""
import ttkbootstrap as tb
from tkinter import PhotoImage
from threading import Lock
from log_handler import get_logger
from os import path

from settings_manager import UserSettingsManager

class GuiController:
    """ Does not need to be thread safe, because it will allways run in main thread in the background.
    Last thread to start and last to stop then we  have no race conditions."""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            # TODO: read in config for style from user settings
            self.root = tb.Window(themename=UserSettingsManager().gui_theme)
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

    def run(self):
        """
        Starting the root element of the gui.
        After this is called all below/behind will only work after
        the loop got quited from stop().
        If stuff needs to be executed in the content  of GUI Elements,
        it needs to be called with self.root.after(seconds, function)
        else the GUI Root wont track it properly with different threads.
        """
        self.root.mainloop()

    def stop_helper(self):
        """
        Helper to stop properly inside the mainloop.
        """
        # helper to properly call the stop when called form the systray
        # otherwise you cant exit the mainloop properly! (it needs to be called form inside with .after)
        self.root.after(100, self.stop)

    def stop(self):
        """
        Destroys child windows, if still open.
        After quits the mainloop.
        Only works if called with the self.root.after(seconds, function) !
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

def stop_gui():
    """
    Import function to simple stop the GUI Root
    """
    GuiController().stop_helper()


def init_root_gui():
    """
    Import function to simple init the root,
    not starting mainloop!
    That needs to be done after all other threads of the main.py got started!
    """
    GuiController()


def start_root_gui():
    """
    Import function to start the mainloop.
    WARNING!
    After you cant do stuff till the mainloop got properly quited,
    so you need to start ALL threads which run parallel before!
    """
    GuiController().run()


if __name__ == "__main__":
    print("Please start with the main.py")

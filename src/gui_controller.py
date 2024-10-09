"""
This file will handle the main GUI class, called GUIController.
All windows will be created on toplevel of it for thread safety.
Maybe functions for returning canvases or creating optical stuff from the window
wil be outsourced to different files in the future.
Author: sora7672
"""
import ttkbootstrap as tb
from tkinter import Toplevel
from ttkbootstrap import Window
from threading import Lock
from PIL import Image, ImageTk
from log_handler import get_logger


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
            self.root = tb.Window()
            self.root.title('Invisible Window(If you see me report me!)')
            # FIXME: Image not working!!

            tmp = Image.open('src/viper_tray.ico')  # TODO: get a better image
            self.window_icon = ImageTk.PhotoImage(tmp)
            self.root.iconphoto = self.window_icon

            self.root.withdraw()
            self.lock = Lock()
            get_logger().debug("__init__ from GuiHandler")

    def run(self):
        """
        Starting the root element of the gui.
        After this is called all below/behind will only work after
        the loop got quitted from stop().
        If stuff needs to be executed in the contetn of GUI Elements,
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

    def sys_tray_manual_label(self):
        """
        Little Gui element that pops up on the right bottom of the screen(above taskbar)
        No frame for minimize/close/maximize so the user can only enter a
        Label name for manual label and add it.
        """
        get_logger().debug("sys_tray_manual_label start")
        win_width = 300
        win_height = 130
        taskbar_height = 70
        sys_tray_add_lbl_win = Toplevel(self.root)
        sys_tray_add_lbl_win.withdraw()

        sys_tray_add_lbl_win.title('Sys Tray Add Label')
        sys_tray_add_lbl_win.iconphoto = self.window_icon
        s_width = sys_tray_add_lbl_win.winfo_screenwidth()
        s_height = sys_tray_add_lbl_win.winfo_screenheight()
        sys_tray_add_lbl_win.geometry(f"{win_width}x{win_height}+{s_width - win_width}+"
                                      f"{s_height - win_height - taskbar_height}")
        sys_tray_add_lbl_win.resizable(width=False, height=False)
        sys_tray_add_lbl_win.attributes('-toolwindow', True)
        sys_tray_add_lbl_win.attributes('-topmost', True)
        sys_tray_add_lbl_win.overrideredirect(True)

        sys_tray_add_lbl_win.grid_rowconfigure(0, weight=1)
        sys_tray_add_lbl_win.grid_columnconfigure(0, weight=1)
        sys_tray_add_lbl_win.attributes('-alpha', 0.7)
        # TODO: Maybe change to transparent background and give widgets a non transparent image,
        #  so it looks like widgets "fly" on the screen

        title_text = tb.Label(sys_tray_add_lbl_win, text="Choose a label name:", font=("Helvetica", 12))
        label_name = tb.Entry(sys_tray_add_lbl_win, width=40)
        # TODO: Add enter & tab functionality, fast saving new tab without much clicking to close/submit fast
        add_btn = tb.Button(sys_tray_add_lbl_win, text="Add & Start",
                            command=lambda wind=sys_tray_add_lbl_win, lbl_name=label_name: sys_add(wind, lbl_name))
        cancel_btn = tb.Button(sys_tray_add_lbl_win, text="Cancel",
                               command=lambda wind=sys_tray_add_lbl_win: win_close(wind))

        title_text.grid_configure(row=0, column=0, columnspan=2, sticky='ews', padx=10)
        label_name.grid_configure(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        add_btn.grid_configure(row=2, column=0, sticky='sw', padx=10, pady=10)
        cancel_btn.grid_configure(row=2, column=1, sticky='nw', padx=10, pady=10)

        sys_tray_add_lbl_win.deiconify()  # shows the window again
        get_logger().debug("sys_tray_manual_label end")

    # TODO: create a real main window
    #  Should have access to all other needs.
    def main_window(self, name: str = "Empty", geo="300x200"):
        get_logger().debug("main_window start")
        n_win = Toplevel(self.root)
        n_win.iconphoto = self.window_icon
        n_win.title(name)
        n_win.geometry(geo)
        get_logger().debug("main_window end")


# # # # Helper functions for the widgets # # # #
def win_close(win: Window):
    """
    Helper function to destroy/close a window element properly.
    e.g. The Manual Label from Systray.
    """
    win.destroy()


def sys_add(win: Window, label_text):
    """
    Helper function to add label to database and update the systray.
    """
    # TODO: Probably need to make this smoother, because circular import if import on top
    get_logger().debug("adding manual label by systray start")
    from system_tray_manager import SystemTrayManager
    from window_manager import Label
    Label(label_text.get(), manually=True)
    win_close(win)
    SystemTrayManager().update_menu()
    get_logger().debug("adding manual label by systray end")


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
    so you need to start ALL threads which run paralell before!
    """
    GuiController().run()


def sys_tray_manual_label():
    """
    Import function that opens the system tray manual label GUI.
    """
    GuiController().sys_tray_manual_label()


def open_main_gui():
    """
    Import function that opens the main GUI.
    """
    GuiController().main_window()


if __name__ == "__main__":
    print("Please start with the main.py")

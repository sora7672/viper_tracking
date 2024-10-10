"""
This will control the calls of the different views.
Everything related to the gui looks will be created here.
Diagrams & calculation will happen in analysis_and_diagrams.py

Author: sora7672
"""


import ttkbootstrap as tb
from tkinter import Toplevel, PhotoImage, Widget
from ttkbootstrap import Window
from threading import Lock
from ttkbootstrap import Frame

from log_handler import get_logger
from os import path

from gui_controller import GuiController

# GuiController().root
# will be used to create
# new_window = Toplevel(GuiController().root)


# TODO: windows should allways work with a main window.
#  if its not existing, because of close, it should create a new toplevel win
#  otherwise only all widgets on the window should be destroyed and rebuild what needed
# TODO: style change menu, which will change this theme. Also save it in user settings.

class ViewController:
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

    def main_window(self):
        get_logger().debug("main_window start")

        # Create the Toplevel window
        n_win = Toplevel(GuiController().root)
        n_win.iconphoto(True, GuiController().icon_image)
        n_win.title("Viper Tracking - Main View")

        # Set the minimum size of the window
        n_win.minsize(400, 400)  # Minimum size of the window (can be changed)

        # Get the correct geometry to position the window in the center of the screen
        center_window(n_win, 400, 400)

        # Configure dynamic row/column resizing for the main window
        n_win.grid_rowconfigure(0, weight=1)  # Upper half
        n_win.grid_rowconfigure(1, weight=1)  # Lower half
        n_win.grid_columnconfigure(0, weight=1)

        # Create upper and lower half frames
        upper_frame = Frame(n_win, borderwidth=2, relief="solid")
        lower_frame = Frame(n_win, borderwidth=2, relief="solid")

        # Place the frames using grid for dynamic sizing
        upper_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        lower_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        # Configure dynamic resizing for the lower frame
        lower_frame.grid_columnconfigure(0, weight=1)  # Left half
        lower_frame.grid_columnconfigure(1, weight=1)  # Right half
        lower_frame.grid_rowconfigure(0, weight=1)

        # Create left and right frames in the lower half
        left_frame = Frame(lower_frame, borderwidth=2, relief="solid")
        right_frame = Frame(lower_frame, borderwidth=2, relief="solid")

        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Configure dynamic resizing for the 2x2 grid inside the left frame
        for r in range(2):
            for c in range(2):
                inner_frame = Frame(left_frame, borderwidth=2, relief="solid")
                inner_frame.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")

        left_frame.grid_rowconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_columnconfigure(1, weight=1)

        # set_standard_focus_on_window(n_win)


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
        sys_tray_win = Toplevel(GuiController().root, height=0, width=0)
        sys_tray_win.overrideredirect(True)
        sys_tray_win.withdraw()

        sys_tray_win.title('Sys Tray Add Label')
        sys_tray_win.iconphoto(True, GuiController().icon_image)
        s_width = sys_tray_win.winfo_screenwidth()
        s_height = sys_tray_win.winfo_screenheight()
        sys_tray_win.geometry(f"{win_width}x{win_height}+{s_width - win_width}+"
                              f"{s_height - win_height - taskbar_height}")
        sys_tray_win.resizable(width=False, height=False)
        sys_tray_win.attributes('-toolwindow', True)
        sys_tray_win.attributes('-topmost', True)
        sys_tray_win.overrideredirect(True)

        sys_tray_win.grid_rowconfigure(0, weight=1)
        sys_tray_win.grid_columnconfigure(0, weight=1)
        sys_tray_win.attributes('-alpha', 0.7)
        # TODO: Maybe change to transparent background and give widgets a non transparent image,
        #  so it looks like widgets "fly" on the screen

        title_text = tb.Label(sys_tray_win, text="Choose a label name:", font=("Helvetica", 12))
        label_name = tb.Entry(sys_tray_win, width=40)
        label_name.bind("<Return>", lambda event: add_btn.invoke())

        add_btn = tb.Button(sys_tray_win, text="Add & Start",
                            command=lambda wind=sys_tray_win, lbl_name=label_name: sys_add(wind, lbl_name))
        cancel_btn = tb.Button(sys_tray_win, text="Cancel",
                               command=lambda wind=sys_tray_win: win_close(wind))

        title_text.grid_configure(row=0, column=0, columnspan=2, sticky='ews', padx=10)
        label_name.grid_configure(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        add_btn.grid_configure(row=2, column=0, sticky='sw', padx=10, pady=10)
        cancel_btn.grid_configure(row=2, column=1, sticky='nw', padx=10, pady=10)

        sys_tray_win.deiconify()  # shows the window again
        label_name.focus()
        get_logger().debug("sys_tray_manual_label end")


# # # # Helper functions for the widgets # # # #
def win_close(win: Window):
    """
    Helper function to destroy/close a window element properly.
    e.g. The Manual Label from Systray.
    """
    win.destroy()


def set_focus_visual(transform_widget: Widget):
    if transform_widget.winfo_class() in ['TButton', 'TEntry', 'TCheckbutton', 'TRadiobutton', 'TCombobox']:
        transform_widget.bind("<FocusOut>",
                              lambda event: event.widget.configure(style=f"primary.{event.widget.winfo_class()}"))
        transform_widget.bind("<FocusIn>",
                              lambda event: event.widget.configure(style=f"info.{event.widget.winfo_class()}"))


def set_standard_focus_on_window(wind: Window | Toplevel):
    for widget in wind.winfo_children():
        set_focus_visual(widget)


def center_window(window, width, height):
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x = int((screen_width / 2) - (width / 2))
    y = int((screen_height / 2) - (height / 2))
    window.geometry(f'{width}x{height}+{x}+{y}')


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
def open_main_window():
    ViewController().main_window()

def open_systray_label():
    ViewController().sys_tray_manual_label()

if __name__ == "__main__":
    print("Please start with the main.py")

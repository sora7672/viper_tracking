"""
This will control the calls of the different views.
Everything related to the gui looks will be created here.
Diagrams & calculation will happen in analysis_and_diagrams.py

Author: sora7672
"""


import ttkbootstrap as tb
from tkinter import Toplevel, PhotoImage, Widget, ttk
from ttkbootstrap import Window
from window_manager import Label
from ttkbootstrap import Frame
from ttkbootstrap.dialogs import Messagebox

from log_handler import get_logger
from os import path

from gui_controller import GuiController

# GuiController().root
# will be used to create
# new_window = Toplevel(GuiController().root)

dict_resolution: dict[str, tuple[int, int]] = {
            "VGA(4:3)": (640, 480),
            "SVGA(4:3)": (800, 600),
            "XGA(4:3)": (1024, 768),
            "HD(16:9)": (1280, 720),
            "WXGA(16:10)": (1280, 800),
            "HD Ready(16:9)": (1366, 768),
            "WXGA+(16:10)": (1440, 900),
            "HD+(16:9)": (1600, 900),
            "WSXGA+(16:10)": (1680, 1050),
            "FULL HD (16:9)": (1920, 1080),
            "WUXGA(16:10)": (1920, 1200),
            "QHD/2K(16:9)": (2560, 1440),
            "WQXGA(16:10)": (2560, 1600),
            "4K UHD(16:9)": (3840, 2160),
            "5K(16:9)": (5120, 2880),
            "8K(16:9)": (7680, 4320)}


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
            self._main_window = None

    def main_window(self):
        get_logger().debug("main_window start")

        # Create the Toplevel window
        self._main_window = Toplevel(GuiController().root)
        self._main_window.iconphoto(True, GuiController().icon_image)
        self._main_window.title("Viper Tracking")
        win_width = 800
        win_height = 600
        self._main_window.minsize(win_width, win_height)
        center_window(self._main_window, win_width, win_height)

        notebook = ttk.Notebook(self._main_window)
        notebook.bind("<<NotebookTabChanged>>", self.update_tab)
        main_tab = ttk.Frame(notebook)
        analysis_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook)

        notebook.add(main_tab, text="Overview")
        notebook.add(analysis_tab, text="Analysis")
        notebook.add(settings_tab, text="Settings")
        notebook.pack(expand=True, fill="both", padx=0, pady=0)
        self.update_main_tab(main_tab)

    def update_tab(self, event):
        nb = event.widget
        tab_index = event.widget.index("current")  # Get the index of the selected tab
        match tab_index:

            case 0:  # MainTab
                self.update_main_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 1:  # AnalysisTab
                self.update_analysis_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 2:  # SettingsTab
                self.update_settings_tab(event.widget.nametowidget(nb.tabs()[tab_index]))


    def update_main_tab(self, tab):
        tab.grid_rowconfigure(0, weight=1)  # Upper half
        tab.grid_rowconfigure(1, weight=1)  # Lower half
        tab.grid_columnconfigure(0, weight=1)

        # Create upper and lower half frames
        upper_frame = Frame(tab, borderwidth=2, relief="solid")
        lower_frame = Frame(tab, borderwidth=2, relief="solid")

        upper_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        lower_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        lower_frame.grid_columnconfigure(0, weight=1)  # Left half
        lower_frame.grid_columnconfigure(1, weight=1)  # Right half
        lower_frame.grid_rowconfigure(0, weight=1)

        # Create left and right frames in the lower half
        low_left_frame = Frame(lower_frame, borderwidth=2, relief="solid")
        low_right_frame = Frame(lower_frame, borderwidth=2, relief="solid")
        low_left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        low_right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        left_frames_list = []
        for r in range(2):
            for c in range(2):
                inner_frame = Frame(low_left_frame, borderwidth=2, relief="solid")
                inner_frame.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
                left_frames_list.append(inner_frame)

        low_left_frame.grid_rowconfigure(0, weight=1)
        low_left_frame.grid_rowconfigure(1, weight=1)
        low_left_frame.grid_columnconfigure(0, weight=1)
        low_left_frame.grid_columnconfigure(1, weight=1)

        # set_standard_focus_on_window(n_win)
    def update_settings_tab(self, tab):
        upper_frame = Frame(tab, borderwidth=2, relief="solid")
        lower_frame = Frame(tab, borderwidth=2, relief="solid")

        upper_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        lower_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=5)

        # Dropdown for resolution placed at the top-left (absolute positioning)
        d_res_values = [f"{key}: {value[0]}x{value[1]}" for key, value in dict_resolution.items()]
        dropdown_resolution = tb.Combobox(upper_frame, values=d_res_values, state="readonly")
        dropdown_resolution.current(0)
        dropdown_resolution.place(x=10, y=10)  # Absolute position at the top-left corner

        # Save button placed at the bottom-left (absolute positioning)
        save_button = tb.Button(upper_frame, text="SAVE CHANGES",
                                command=lambda: self.save_changes(dropdown_resolution, dropdown_themes))
        save_button.place(x=10, rely=0.98, anchor="sw")  # Position at bottom-left corner

        # Right frame holding the example frame, dropdown, and apply button
        right_frame = Frame(upper_frame)
        right_frame.pack(side="right", anchor="ne", padx=10, pady=5)

        # Example frame inside right frame
        example_frame = Frame(right_frame, borderwidth=2, relief="solid")
        example_frame.pack(side="top", fill="both", expand=False, padx=5, pady=5)

        # Populate the example frame with various widgets (showcasing styles)
        tb.Label(example_frame, text="Dummy Label (info)", bootstyle="info").pack(padx=10, pady=10)
        tb.Checkbutton(example_frame, text="Check me (success)", bootstyle="success").pack(padx=10, pady=10)
        tb.Radiobutton(example_frame, text="Option 1 (warning)", bootstyle="warning").pack(padx=10, pady=10)
        tb.Radiobutton(example_frame, text="Option 2 (danger)", bootstyle="danger").pack(padx=10, pady=10)
        dropdown_demo = tb.Combobox(example_frame, values=["Option 1", "Option 2"], bootstyle="primary")
        dropdown_demo.pack(padx=10, pady=10)
        tb.Button(example_frame, text="Action Button (primary)", bootstyle="primary").pack(padx=10, pady=10)

        # Dropdown for themes inside right_frame, below example_frame
        list_themes = GuiController().root.style.theme_names()
        dropdown_themes = tb.Combobox(right_frame, values=list_themes, state="readonly")
        dropdown_themes.set(GuiController().root.style.theme_use())
        dropdown_themes.pack(side="left", padx=10, pady=5)

        # Apply button next to the dropdown (on the right)
        apply_button = tb.Button(right_frame, text="APPLY",
                                 command=lambda: self.apply_changes(dropdown_resolution, dropdown_themes))
        apply_button.pack(side="left", padx=10, pady=5)



    def apply_changes(self, dropdown_resolution, dropdown_themes):
        GuiController().root.style.theme_use(dropdown_themes.get())
        ind = dropdown_resolution.current()

        selected_key = list(dict_resolution.keys())[ind]
        width, height = dict_resolution[selected_key]

        center_window(self._main_window, width, height)

    def save_changes(self, dropdown_resolution, dropdown_themes):
        new_theme = dropdown_themes.get()
        ind = dropdown_resolution.current()

        selected_key = list(dict_resolution.keys())[ind]
        reso = dict_resolution[selected_key]

        # TODO: save to settings
        self.apply_changes(dict_resolution, dropdown_resolution, dropdown_themes)

    def update_analysis_tab(self, tab):
        print(tab)
        print("analysis")
        pass

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
        sys_tray_win.focus_force()
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

    if screen_width <= width or screen_height <= height:
        window.state('zoomed')
        Messagebox.show_info("Your resolution is bigger than your screen.\nWe set the window to maximized instead.",
                             "Warning", parent=window)
    else:
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

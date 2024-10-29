"""
This will control the calls of the different views.
Everything related to the gui looks will be created here.
Diagrams & calculation will happen in analysis_and_diagrams.py

Author: sora7672
"""

from os import path
from datetime import datetime
from time import time
import ttkbootstrap as tb
from ttkbootstrap import Frame, Window
from ttkbootstrap.dialogs import Messagebox
from tkinter import Toplevel, PhotoImage, Widget, ttk, IntVar, BooleanVar, StringVar, Canvas, TclError

from log_handler import get_logger
from window_manager import Label, Condition
from gui_controller import GuiController


dict_resolution: dict[str, tuple[int, int]] = {
           # "VGA(4:3)": (640, 480),
           # "SVGA(4:3)": (800, 600),
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


class FormValidationError(Exception):
    def __init__(self, message: str = None, error_code=None, faulty_fields=None):
        self.message = message or (f"The validation was not ok. These fields are not filled properly:\n"
                                   f"{faulty_fields}")
        super().__init__(message)
        self.error_code = error_code



class ScrollableFrame(tb.Frame):
    # TODO: weirdly build up frame, needs some refining, because it seems like there is some DUPES
    def __init__(self, parent):
        super().__init__(parent)

        # Create a canvas for scrolling
        self.canvas = Canvas(self)
        self.canvas.pack(side="left", fill="both", expand=True)

        # Add a vertical scrollbar linked to the canvas
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Create a frame within the canvas to hold scrollable content
        self.scrollable_frame = tb.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        # Update the scroll region whenever the scrollable frame changes size
        self.scrollable_frame.bind("<Configure>", self.update_scroll_region)

        # Bind the mouse scroll event to the canvas
        self.bind_mouse_scroll()

    def update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


    def bind_mouse_scroll(self):
        self.canvas.bind_all("<MouseWheel>", self.on_mouse_scroll)

    def on_mouse_scroll(self, event):
        if event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")  # Scroll down
        elif event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")  # Scroll up

class ConditionFrame(Frame):
    def __init__(self, parent, with_remove=False, condition:Condition = None):
        super().__init__(parent)
        self.with_remove = with_remove
        self.condition = condition
        self.name = "condition"
        self.number_checks = ["gte", "lte", "gt", "lt"]
        self.text_checks = ["eq", "neq", "in", "nin"]
        self.condition_types = ["window_type", "window_title", "window_text_words", "timestamp"]
        self.pack(fill="x", padx=5, pady=5)
        self.create_widgets()




    def create_widgets(self):
        # Dropdown "Condition Type"

        max_chars = max([len(c) for c in self.condition_types]) + 1
        # FIXME: Add anyhow to show every 2nd and below are are "AND" clauses not or.
        tb.Label(self, text="Condition Type").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.condition_type = tb.Combobox(self, values=self.condition_types, state="readonly", width=max_chars)
        self.condition_type.set(self.condition_types[0])
        self.condition_type.grid(row=0, column=1, padx=3, pady=5)


        # Dropdown "Condition Check"
        max_chars = max([len(c) for c in (self.number_checks+self.text_checks)]) + 1
        tb.Label(self, text="Condition Check").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.condition_check = tb.Combobox(self, values=self.text_checks, state="readonly", width=max_chars)
        self.condition_check.set(self.text_checks[0])  # Fallback to first item
        self.condition_check.grid(row=0, column=3, padx=3, pady=5)

        # Entry "Condition Value" with a default text value
        tb.Label(self, text="Condition Value").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.condition_value_var = tb.StringVar(value="")
        self.condition_value = tb.Entry(self, textvariable=self.condition_value_var)
        self.condition_value.grid(row=0, column=5, padx=3, pady=5)

        self.condition_type.bind("<<ComboboxSelected>>", self._updated_type)


        # SET Conditon values:
        if self.condition:
            if self.condition.condition_type in self.condition_types:
                self.condition_type.set(self.condition.condition_type)
                self._updated_type()
            else:
                print("error in condition type")
            if self.condition.condition_check in (self.number_checks+self.text_checks):
                self.condition_check.set(self.condition.condition_check)
            else:
                print("error in Condition.condition_check")
            self.condition_value_var.set(self.condition.condition_value)


        # "+" Button to add new condition frame at the same level
        self.add_button = tb.Button(self, text="+", width=2, command=self.add_condition)
        self.add_button.grid(row=0, column=6, padx=3, pady=5)

        # "-" Button to remove the condition frame, if needed
        if self.with_remove:
            self.remove_button = tb.Button(self, text="-", width=2, command=self.delete_self)
            self.remove_button.grid(row=0, column=7, padx=3, pady=5)

    def _updated_type(self, event=None):
        if self.condition_type.get() == "timestamp":
            self.condition_check.configure(values=self.number_checks)
            self.condition_check.set(self.number_checks[0])
        else:
            self.condition_check.configure(values=self.text_checks)
            self.condition_check.set(self.text_checks[0])

    def get_values(self):
        if self.condition_value_var.get() == "":
            raise FormValidationError(faulty_fields="condition value")
        return self.condition_type.get(), self.condition_check.get(), self.condition_value_var.get()

    def add_condition(self):
        parent = self.master
        if isinstance(parent, ttk.LabelFrame):
            ConditionFrame(parent, with_remove=True)
        else:
            print("Error on adding condition frame with add function")

    def delete_self(self):
        self.destroy()

class LabelFrame(tb.Frame):
    def __init__(self, parent, label = None):
        super().__init__(parent, borderwidth=2, relief="solid")
        if label is None:
            self.label = None
            self.label_name = StringVar(value="")
            self.manually_var = BooleanVar(value=False)
            self.active_var = BooleanVar(value=False)
            self.creation_timestamp = time()
        else:
            self.label = label
            self.label_name = StringVar(value=label.name)
            self.manually_var = BooleanVar(value=label.manually)
            self.active_var = BooleanVar(value=label.is_active)
            self.creation_timestamp = label.get_creation_timestamp()

        self.create_widgets()


    def create_widgets(self):
        # Upper Frame for Label Name, Manually, Active Checkboxes, and Datetime Label
        upper_frame = Frame(self)
        upper_frame.name = "upper"
        upper_frame.pack(fill="x", padx=5, pady=5)

        # Entry field for "Label name"
        tb.Label(upper_frame, text="Label name:").grid(row=0, column=0, padx=(5, 0), pady=5, sticky="w")
        self.label_entry = tb.Entry(upper_frame, textvariable=self.label_name)
        self.label_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Checkbox for "Manually"
        manually_checkbox = tb.Checkbutton(upper_frame, text="Manually", variable=self.manually_var, command=self.toggle_conditions)
        manually_checkbox.grid(row=0, column=2, padx=5, pady=5)

        # Checkbox for "Active"
        active_checkbox = tb.Checkbutton(upper_frame, text="Active", variable=self.active_var)
        active_checkbox.grid(row=0, column=3, padx=5, pady=5)

        # Timestamp
        formatted_date = datetime.fromtimestamp(self.creation_timestamp).strftime("%d.%m.%y - %H:%M")
        datetime_label = tb.Label(upper_frame, text=f"Created {formatted_date}")
        datetime_label.grid(row=0, column=4, padx=(5, 0), pady=5)

        # Delete Button
        delete_btn = tb.Button(upper_frame, text="Delete", width=8, bootstyle="danger")
        delete_btn.grid(row=0, column=5, padx=(170, 0), pady=5, sticky="e")  # Todo: better align this then with fixed
        delete_btn.bind("<Button-1>", self.delete_label)





        # Container for all condition frames
        # TODO: check for this methods here, feels wrong
        self.all_condition_frame = ttk.LabelFrame(self, text="Automatically Conditions")
        self.all_condition_frame.name = "all_conditions"
        self.all_condition_frame.pack(fill="x", padx=5, pady=5)
        c_list = []
        if self.label is not None:
            c_list = self.label.get_condition_list()
        if len(c_list) > 0:
            first = True
            for condition in c_list:
                if first:
                    first = False
                    ConditionFrame(self.all_condition_frame, with_remove=False, condition=condition)
                else:
                    ConditionFrame(self.all_condition_frame,  with_remove=True, condition=condition)
        else:
            ConditionFrame(self.all_condition_frame)
        self.toggle_conditions()


    def toggle_conditions(self):
        state = "disabled" if self.manually_var.get() else "normal"
        for frame in self.all_condition_frame.winfo_children():
            for child in frame.winfo_children():
                try:
                    if isinstance(child, tb.Combobox) and state == "normal":
                        child.config(state="readonly")
                    else:
                        child.config(state=state)
                except (AttributeError, TclError):
                    # TODO: try/except take more resources, so switch to real tests
                    pass #  Ignore error
    def save_label_to_db(self):
        lab_name = self.label_name.get()
        if lab_name == "":
            raise FormValidationError(faulty_fields="label name")
        lab_manually = self.manually_var.get()
        lab_active = self.active_var.get()
        lab_condition_list = []
        if not lab_manually:
            for cond_frame in self.all_condition_frame.winfo_children():
                if isinstance(cond_frame, ConditionFrame):
                    lab_condition_list.append(Condition(*cond_frame.get_values()))
                else:
                    print("Error on saving label frame conditions")

        if self.label is None:
            # do stuff for new label
            Label(lab_name, manually=lab_manually, active=lab_active, condition_list=lab_condition_list)
        else:
            self.label.name = lab_name
            self.label.manually = lab_manually
            self.label.active = lab_active
            self.label.condition_list = lab_condition_list
            self.label.update_in_db()

    def delete_label(self, event):
        if not event.state & 0x0001:  # Shift key flag
            result = Messagebox.okcancel(f"Do you want to delete label '{self.label_name.get()}'({
                                            self.label.name if self.label else ""}) ?",
                                         "WARNING! Delete Label", parent=self.master.master)
            if result != "OK":
                return
        from system_tray_manager import SystemTrayManager

        if self.label is not None:
            self.label.delete_in_db()
        SystemTrayManager().update_menu()
        self.destroy()

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
        win_width, win_height = 1024, 768
        self._main_window.minsize(win_width, win_height)
        center_window(self._main_window, win_width, win_height)

        notebook = ttk.Notebook(self._main_window)
        notebook.bind("<<NotebookTabChanged>>", self.update_tab)
        main_tab = ttk.Frame(notebook)
        analysis_tab = ttk.Frame(notebook)
        label_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook)

        notebook.add(main_tab, text="Overview")
        notebook.add(analysis_tab, text="Analysis")
        notebook.add(label_tab, text="Label")
        notebook.add(settings_tab, text="Settings")
        notebook.pack(expand=True, fill="both", padx=0, pady=0)
        self.update_main_tab(main_tab)

    def update_tab(self, event):
        nb = event.widget
        tab_index = event.widget.index("current")  # Get the index of the selected tab
        child_tabs = event.widget.winfo_children()
        for tabs in child_tabs:
            frame_childs = tabs.winfo_children()
            for child in frame_childs:
                child.destroy()
        match tab_index:
            case 0:  # MainTab
                self.update_main_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 1:  # AnalysisTab
                self.update_analysis_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 2:  # LabelTab
                self.update_label_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 3:  # SettingsTab
                self.update_settings_tab(event.widget.nametowidget(nb.tabs()[tab_index]))


    def update_main_tab(self, tab):
        # TODO: Content of the tab
        #  Base analysis graph, with update button(F5 shortcut)
        #  Some basic stats, which are configurable as user settings
        #  Possible stats: activity time, pc online time, average key pushes (per time window),
        #  Average activity time (weekday based), ...
        #  Some more advanced features later, like creating own querrys per field that should be shown.
        #

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



    def update_analysis_tab(self, tab):
        # TODO: This should make user choosable what kind of stuff they want to analys
        #  They should be able to create and access querrys from here,
        #  to analyze their favorite activitys /behaviour.
        #  It will allways include standard analysis, like per label and/or multiple labels,
        #  Weekdays, weeks, daytime, time window
        label_list = Label.get_all_labels()
        if label_list:
            dropdown_values = list({lab.name for lab in label_list})
        else:
            dropdown_values = ["No labels existing"]
        label_dropdown = tb.Combobox(tab, values=dropdown_values, state="readonly")
        label_dropdown.current(0)
        label_dropdown.pack(padx=10, pady=10)


    def update_label_tab(self, tab):
        scrollable_frame = ScrollableFrame(tab)
        scrollable_frame.pack(fill="both", expand=True)


        label_list = Label.get_all_labels()
        for lab in label_list:
            lab_frame = LabelFrame(parent=scrollable_frame.scrollable_frame, label=lab)
            lab_frame.pack(fill="x", padx=5, pady=5)

        btn_frame = Frame(scrollable_frame.scrollable_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        new_label_button = tb.Button(btn_frame, text="Add new Label")
        new_label_button.pack(padx=5, pady=5, side="left", expand=True)  # Center with expand=True


        save_labels_button = tb.Button(btn_frame, text="Save")
        save_labels_button.pack(padx=5, pady=5, side="right")  # Move to the right side and block space for lbl btn

        new_label_button.bind("<Button-1>", self.add_new_label)
        save_labels_button.bind("<Button-1>", self.save_labels)

    def save_labels(self, event=None):
        if event is None:
            print("error no button provied")
        else:
            from system_tray_manager import SystemTrayManager

            parent = event.widget.master.master

            for label_frame in parent.winfo_children():
                if isinstance(label_frame, LabelFrame):
                    try:
                        label_frame.save_label_to_db()
                    except FormValidationError as err:
                        Messagebox.show_info(f"{err.message}\nNot saved to DB properly!", "Notice",
                                             parent=parent.master)
                        return

            SystemTrayManager().update_menu()



    def add_new_label(self, event=None):
        if event is None:
            print("error no button provied")
        else:

            tab_frame = event.widget.master.master
            btn_frame= event.widget.master
            btn_frame.pack_forget()
            n_lab = LabelFrame(parent=tab_frame)
            n_lab.pack(fill="x", padx=10, pady=5)
            btn_frame.pack(fill="x", padx=5, pady=5)



    def update_settings_tab(self, tab):


        # TODO: Maybe adding here some feature request area for users, which will send
        #  an email to us/me for adding some features & a support button for our discord or website or so.
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

        # Some show off examples
        check_var = BooleanVar()
        check_var.set(True)
        radio_var = IntVar()
        radio_var.set(0)
        tb.Label(example_frame, text="Dummy Label (info)", bootstyle="info").pack(padx=10, pady=10)
        tb.Checkbutton(example_frame, text="Check me (success)", bootstyle="success", variable=check_var).pack(padx=10,
                                                                                                               pady=10)
        tb.Checkbutton(example_frame, text="Check me (primary)", variable=check_var).pack(padx=10, pady=10)
        tb.Radiobutton(example_frame, text="Option 1 (primary)", variable=radio_var, value=0).pack(padx=10, pady=10)
        tb.Radiobutton(example_frame, text="Option 2 (success)", variable=radio_var, value=0, bootstyle="success").pack(
            padx=10, pady=10)
        tb.Radiobutton(example_frame, text="Option 3 (warning)", variable=radio_var, value=0, bootstyle="warning").pack(
            padx=10, pady=10)
        tb.Radiobutton(example_frame, text="Option 4 (danger)", variable=radio_var, value=0, bootstyle="danger").pack(
            padx=10, pady=10)

        dropdown_demo = tb.Combobox(example_frame, values=["Option 1", "Option 2"], bootstyle="primary")
        dropdown_demo.current(0)
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
        self.apply_changes(dropdown_resolution, dropdown_themes)

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

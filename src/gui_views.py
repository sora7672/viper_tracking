"""
This module manages GUI views and their components.

Features:
- Controls the creation and management of various GUI views.
- Provides classes for custom widgets, such as scrollable frames and condition lists.
- Includes functionality to handle user interactions and database updates.

Author: sora7672
"""
__author__ = 'sora7672'

from stylemanager import StyleManager

from datetime import datetime, date
from ttkbootstrap import Frame, Window, Style, DateEntry, Querybox, Scrollbar, Combobox
from ttkbootstrap.dialogs import Messagebox, DatePickerDialog
from ttkbootstrap.constants import *
from tkinter import Toplevel, PhotoImage, Widget, ttk, IntVar, BooleanVar, StringVar, Canvas, TclError
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from pandas import DataFrame
from PIL import ImageTk, Image

import ttkbootstrap as tb
import tkinter as tk
import calendar
import locale

from helper_classes import DynamicTimeframe
from pandas_data_manager import ViperDF, DayAnalyzer
from filter_manager import DatabaseFilter
from log_handler import get_logger
from window_manager import Label
from conditions import ObjectCondition, ConditionList
from gui_controller import GuiController
from settings_manager import UserSettingsManager
from db_connector import DBHandler



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
                                               "8K(16:9)": (7680, 4320)
                                                }


def debug_widget_infos(widget, flag="") -> None:
    """
    Print detailed debugging information about a widget and its layout.

    :param widget: Widget (The widget to inspect.)
    :param flag: str (Optional prefix for print statements to identify context.)
    :return: None
    """

    print(f"\n======= DEBUG {flag if flag else ''} =======")
    current = widget

    while current:

        full_name = str(current)
        widget_name = full_name.split("!")[-1]
        print(f"\n----- {widget_name} -----")

        current.update_idletasks()
        width = current.winfo_width()
        height = current.winfo_height()
        print(f"{width}x{height}")
        print(f"Pixels in area : {width * height}")
        print(f"Y From {current.winfo_rooty()} to {current.winfo_rooty() + height}")
        print(f"X From {current.winfo_rootx()} to {current.winfo_rootx() + width}")

        layout_found = False

        # Check for grid
        try:
            grid_info = current.grid_info()
            if grid_info:
                print("[Grid]")
                for k, v in grid_info.items():
                    print(f"  {k}: {v}")
                propagate = current.grid_propagate() if hasattr(current, "grid_propagate") else False
                print(f"  grid_propagate: {propagate if propagate is not None else "False"}")
                layout_found = True
        except:
            pass

        # Check for pack
        if not layout_found:
            try:
                pack_info = current.pack_info()
                if pack_info:
                    print("[Pack]")
                    for k, v in pack_info.items():
                        print(f"  {k}: {v}")
                    propagate = current.pack_propagate() if hasattr(current, "pack_propagate") else False
                    print(f"  pack_propagate: {propagate if propagate is not None else "False"}")
                    layout_found = True
            except:
                pass

        # Check for place
        if not layout_found:
            try:
                place_info = current.place_info()
                if place_info:
                    print("[Place]")
                    for k, v in place_info.items():
                        print(f"  {k}: {v}")
                    propagate = current.place_propagate() if hasattr(current, "place_propagate") else False
                    print(f"  place_propagate: {propagate if propagate is not None else "False"}")
                    layout_found = True
            except:
                pass

        if not layout_found:
            print("[No layout manager info available]")

        # Sub infos
        bg = current.cget("background") if "background" in current.keys() else "Not set"
        relief = current.cget("relief") if "relief" in current.keys() else "Not set"
        bd = current.cget("bd") if "bd" in current.keys() else "Not set"
        print(f"Style: relief={relief}, border={bd}, bg={bg}")

        current = current.master


class FormValidationError(Exception):
    """
    Exception raised when form validation fails.

    Attributes:
        fields (list[str]): A list of strings representing the invalid fields.
        error_code (str | int | None): Optional error code for the validation issue.
        message (str): Formatted error message combining field information and error code.
    """

    def __init__(self, fields: str | list[str], error_code: str | int = None):
        """
        Initializes the FormValidationError exception with an error message and optional details.

        :param fields: list[str] (A list of stings that indicate faulty fields)
        :param error_code: str | int (Optional error code as integer or string)
        :raises: FormValidationError (This is a custom exception.)
        """

        if isinstance(fields, str):
            fields = [fields]
        elif isinstance(fields, list):
            if not all(isinstance(f, str) for f in fields):
                raise ValueError("All elements in 'fields' must be strings.")
        else:
            raise TypeError("Expected a string or list of strings for 'fields'.")

        self.fields = fields
        self.error_code = error_code
        self.message = "Form Validation Failed!\nFaulty fields:\n- " + "\n- ".join(self.fields)

        if error_code is not None:
            self.message += f"\n\nError Code: {error_code}"

        super().__init__(self.message)

    def __str__(self) -> str:
        """
        Returns the error message when the exception is converted to a string.

        Returns:
            str: The formatted error message.
        """
        return self.message


class ScrollFrame(Frame):
    """
    A scrollable frame with configurable scrollbar orientation and placement.

    Use `inner_frame` to place widgets instead of this outer container directly.
    Supports mousewheel scrolling with automatic binding when hovered.

    Allowed scrollbar positions: ["e", "s", "w", "n", "top", "left", "right", "bottom"]

    Attributes:
        scrollbar_list (list): List of scrollbar widgets (max 2).
        scrollbar_configs (list[dict]): Scrollbar config dictionaries with position and orientation.
        _canvas_side (str | None): Side where the canvas is attached relative to scrollbars.
        _canvas (Canvas): Internal canvas used to contain the scrollable content.
        inner_frame (Frame): The frame inside the canvas where widgets should be placed.
        _allowed_scrollbar_positions (list[str]): Valid string values for scrollbar positions.
    """

    _allowed_scrollbar_positions = ["e", "s", "w", "n", "top", "left", "right", "bottom"]

    def __init__(self, parent, scrollbar_position: str | tuple[str, str] | list[str, str] = "e",
                 canvas_height: int = None, canvas_width: int = None, *args, **kwargs):
        """
        Initializes the ScrollFrame widget for adding scrollable content inside a canvas.

        :param parent: Widget (The parent widget this frame is attached to.)
        :param scrollbar_position: str | tuple[str, str] | list[str, str] (Scrollbar position(s),
        max 2. Allowed values: "left", "right", "top", "bottom" or their aliases.)
        :param canvas_height: int | None (Optional height for the canvas.)
        :param canvas_width: int | None (Optional width for the canvas.)
        :raises ValueError: If scrollbar position is invalid or conflicts with orientation rules.
        :raises TypeError: If input types are incorrect.
        :return: None
        """

        super().__init__(parent, *args, **kwargs)

        if canvas_height is not None:
            if not isinstance(canvas_height, int):
                raise TypeError("canvas_height must be an integer or None.")

        if canvas_width is not None and not isinstance(canvas_width, int):
            raise TypeError("canvas_width must be an integer or None.")

        self.scrollbar_list = []  #  Max 2!
        self.scrollbar_configs = []  # List of dicts that should hold each config option per scrollbar
        # example configs: "scrollbar_position" = "left", "orientation" = "vertical", "canvas_side" = "right"

        config_keys = ["scrollbar_position", "orientation", "canvas_side"]
        self._canvas_side = None   # needed for saving where the canvas is even on 2 bars

        if isinstance(scrollbar_position, tuple) or isinstance(scrollbar_position, list):
            if len(scrollbar_position) != 2:
                raise ValueError("Scrollbar position must be a tuple/list of exactly 2 entries.")
            else:

                self.scrollbar_configs.append(dict(zip(config_keys,
                                                       self._check_scrollbar_position(scrollbar_position[0]))))
                self.scrollbar_configs.append(dict(zip(config_keys,
                                                       self._check_scrollbar_position(scrollbar_position[1]))))

                x_num_lr = 0
                for sbar in self.scrollbar_configs:
                    if sbar["scrollbar_position"] in ["left", "right"]:
                        self._canvas_side = "left" if sbar["position"] == "right" else "right"
                        x_num_lr += 1
                if x_num_lr != 1:
                    raise ValueError("Scrollbar position can only have one for each: \n"
                                     "['left','right'] & ['top','bottom']")
                self._orientation = "vertical"
                # allways vertical on 2 scrollbars

        elif isinstance(scrollbar_position, str):
            self.scrollbar_configs.append(dict(zip(config_keys,
                                                   self._check_scrollbar_position(scrollbar_position))))
        else:
            raise TypeError("scrollbar_position must be a string or tuple/list of 2 strings.")

        for sbar in self.scrollbar_configs:
            sbar["is_positioned"] = False

        self._canvas = Canvas(self)
        if canvas_height:
            self._canvas.configure(height=canvas_height)
        if canvas_width:
            self._canvas.configure(width=canvas_width)

        self.inner_frame = Frame(self._canvas)

        if len(self.scrollbar_configs) == 1:
            if self.scrollbar_configs[0]["orientation"] == "vertical":
                self.scrollbar_list.append(Scrollbar(self, orient="vertical", command=self._canvas.yview))
                self._canvas.configure(yscrollcommand=self.scrollbar_list[0].set)

            else:
                self.scrollbar_list.append(Scrollbar(self, orient="horizontal", command=self._canvas.xview))
                self._canvas.configure(xscrollcommand=self.scrollbar_list[0].set)

        elif len(self.scrollbar_configs) == 2:
            y_command = None
            x_command = None

            for sbar in self.scrollbar_configs:
                if sbar["orientation"] == "vertical":
                    self.scrollbar_list.append(Scrollbar(self, orient="vertical", command=self._canvas.yview))
                    y_command = self.scrollbar_list[-1].set

                else:
                    self.scrollbar_list.append(Scrollbar(self, orient="horizontal", command=self._canvas.xview))
                    x_command = self.scrollbar_list[-1].set

            self._canvas.configure(yscrollcommand=y_command)
            self._canvas.configure(xscrollcommand=x_command)
        else:
            raise ValueError("Scrollbar position must be a tuple/list of exactly 2 entries.")

        self._canvas.pack(side=self._canvas_side, fill="both", expand=True)
        self._canvas.pack_propagate(False)
        self._canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")


        self._canvas.bind("<Enter>", self._bind_mousewheel)
        self._canvas.bind("<Leave>", self._unbind_mousewheel)

        self.inner_frame.bind("<Configure>", self._frame_size_changed)
        self.master.bind("<Configure>", self._frame_size_changed)

        self.after(100, self._frame_size_changed)


    def _frame_size_changed(self, event=None) -> None:
        """
        Updates the canvas scroll region whenever the size of the inner frame changes.

        :param event: Event (Optional tkinter event.)
        :return: None
        """

        self.inner_frame.update_idletasks()

        frame_width = self.inner_frame.winfo_width()
        frame_height = self.inner_frame.winfo_height()
        canvas_width = self._canvas.winfo_width()
        canvas_height= self._canvas.winfo_height()
        v_scroll_needed = frame_height > canvas_height
        h_scroll_needed = frame_width > canvas_width

        for bar, config in zip(self.scrollbar_list, self.scrollbar_configs):

            if config["orientation"] == "vertical" and v_scroll_needed:
                bar.pack(side=config["scrollbar_position"], fill="y")

                if config["is_positioned"] is False:
                    self._canvas.pack_forget()
                    self._canvas.pack(side=self._canvas_side, fill="both", expand=True)
                    config["is_positioned"] = True

            elif config["orientation"] == "horizontal" and h_scroll_needed:
                bar.pack(side=config["scrollbar_position"], fill="x")

                if config["is_positioned"] is False:
                    self._canvas.pack_forget()
                    self._canvas.pack(side=self._canvas_side, fill="both", expand=True)
                    config["is_positioned"] = True

            else:
                bar.pack_forget()
                config["is_positioned"] = False

        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _bind_mousewheel(self, event=None) -> None:
        """
        Binds mousewheel scroll events to this widget when hovered.

        :param event: Event (Optional tkinter event.)
        :return: None
        """

        self._canvas.bind_all("<MouseWheel>", self._on_mouse_scroll)
        self._canvas.bind_all("<Button-4>", self._on_mouse_scroll)
        self._canvas.bind_all("<Button-5>", self._on_mouse_scroll)

    def _unbind_mousewheel(self, event=None) -> None:
        """
        Unbinds mousewheel scroll events when mouse leaves this widget.

        :param event: Event (Optional tkinter event.)
        :return: None
        """

        self._canvas.unbind("<MouseWheel>")
        self._canvas.unbind("<Button-4>")
        self._canvas.unbind("<Button-5>")

    def _on_mouse_scroll(self, event=None) -> None:
        """
        Handles vertical scroll movement when a scroll event occurs.

        Only scrolls if the event originated from within this ScrollFrame's widget path.

        :param event: Event (Mouse scroll event.)
        :return: None
        :raises ValueError: If no event is provided.
        """

        if event is None:
            raise ValueError("No event provided")
        if not str(event.widget).startswith(str(self)):
            return

        canvas_width = self._canvas.winfo_width()
        canvas_height = self._canvas.winfo_height()
        inner_width = self.inner_frame.winfo_reqwidth()
        inner_height = self.inner_frame.winfo_reqheight()

        if len(self.scrollbar_list) == 1:
            orientation = self.scrollbar_configs[0]["orientation"]
        else:
            orientation = "vertical"

        if orientation == "vertical" and inner_height > canvas_height:
            direction = 1 if event.num == 5 or event.delta == -120 else -1
            self._canvas.yview_scroll(direction, "units")
        elif orientation == "horizontal" and inner_width > canvas_width:
            direction = 1 if event.num == 5 or event.delta == -120 else -1
            self._canvas.xview_scroll(direction, "units")

    def _check_scrollbar_position(self, position_string) -> tuple[str,str,str]:
        """
        Determines the scrollbar orientation and canvas attachment side from a position code.

        Converts a shorthand position string (e.g., "e", "w", "n", "s") or full position name
        ("left", "right", "top", "bottom") into a tuple of (`scrollbar_position`, `orientation`, `canvas_side`).
        This helper is used to configure the scrollbar placement and ensure the canvas is on the opposite side.

        :param position_string: str (The position code for the scrollbar.)
        :return: tuple[str, str, str] (A tuple containing the normalized scrollbar position, the scrollbar orientation
         ("vertical" or "horizontal"), and the side where the canvas should be placed.)
        :raises ValueError: If the provided position code is not recognized.
        """

        match position_string.lower():
            case "e" | "left":
                scrollbar_position = "left"
                orientation = "vertical"
                canvas_side = "right"
            case "w" | "right":
                scrollbar_position = "right"
                orientation = "vertical"
                canvas_side = "left"
            case "s" | "bottom":
                scrollbar_position = "bottom"
                orientation = "horizontal"
                canvas_side = "top"
            case "n" | "top":
                scrollbar_position = "top"
                orientation = "horizontal"
                canvas_side = "bottom"
            case _:
                raise ValueError(f"Invalid scrollbar position {position_string}.\n"
                                 f"Allowed: {self._allowed_scrollbar_positions}")

        return scrollbar_position, orientation, canvas_side

class SmartDateEntry(DateEntry):
    """
    An enhanced date entry widget that uses a specific date format and handles keyboard interactions.

    This widget wraps a `ttkbootstrap.DateEntry` to enforce a DD.MM.YYYY format and adds convenient
    keyboard bindings (Enter and Escape) to open the date picker or clear the entry.

    Attributes:
        _dateformat (str): The enforced date display format.
    """

    def __init__(self, master, *args, **kwargs):
        """
        Initializes a SmartDateEntry with a fixed date format and key bindings.
        With fixed dateformat "%d.%m.%Y".

        :param master: Widget (The parent widget.)
        :param args: tuple (Additional positional arguments passed to DateEntry.)
        :param kwargs: dict (Additional keyword arguments passed to DateEntry.)
        :return: None
        """

        super().__init__(master, dateformat="%d.%m.%Y", firstweekday=0, *args, **kwargs)
        self._dateformat = "%d.%m.%Y"
        self.entry.delete(0, "end")
        self.button.pack_forget()
        self.entry.bind("<Button-1>", self._open_calender)
        self.entry.bind("<Escape>", self._on_escape)
        self.entry.bind("<Return>", self._on_return)

    def set(self, value) -> None:
        """
        Sets the current value of the date entry.

        :param value: date | str (The date value or ISO date string to display in the entry.)
        :return: None
        """

        if isinstance(value, date):
            value = value.strftime(self._dateformat)
        elif isinstance(value, str):
            value = datetime.fromisoformat(value).date().strftime(self._dateformat) if value != "" else ""
        self.entry.delete(first=0, last=tk.END)
        self.entry.insert(tk.END, value)

    def get(self) -> str:
        """
        Retrieves the current text value of the date entry.

        :return: str (The currently displayed date string in DD.MM.YYYY format.)
        """

        return self.entry.get()

    def _on_return(self, event) -> None:
        """
        Opens the date picker dialog when the Return (Enter) key is pressed.

        :param event: Event (The key press event triggering this action.)
        :return: None
        """

        self._open_calender(event)

    def _on_escape(self, event) -> None:
        """
        Clears the date entry field when the Escape key is pressed.

        :param event: Event (The key press event triggering this action.)
        :return: None
        """

        self.entry.delete(first=0, last=tk.END)

    def _open_calender(self, event) -> None:
        """
        Opens the calendar popup (date picker) programmatically.

        :param event: Event (The mouse click or key event triggering the calendar.)
        :return: None
        """

        self.button.invoke()

    def _on_date_ask(self) -> None:
        """
        Opens a SmartDatePickerDialog and sets the selected date in the entry.

        :return: None
        """

        _val = self.entry.get() or datetime.today().strftime(self._dateformat)
        try:
            self._startdate = datetime.strptime(_val, self._dateformat)

        except Exception as e:
            # Original ttkbootstrap behaviour, that's why we don't change much here.
            print("Date entry text does not match", self._dateformat)
            self._startdate = datetime.today()
            self.entry.delete(first=0, last=tk.END)
            self.entry.insert(tk.END, self._startdate.strftime(self._dateformat))

        old_date = datetime.strptime(_val, self._dateformat)

        # get the new date and insert into the entry
        new_date = SmartQuerybox.get_date(parent=self.entry, startdate=old_date, firstweekday=self._firstweekday,
                                          bootstyle=self._bootstyle,)
        tmp_entry_value = self.entry.get()

        self.entry.delete(first=0, last=tk.END)
        if not new_date == "":
            self.entry.insert(tk.END, new_date.strftime(self._dateformat))
        else:
            self.entry.insert(tk.END, tmp_entry_value)
        self.entry.focus_force()


class SmartQuerybox(Querybox):
    """
    A specialized Querybox that provides a static method for date selection.

    This class wraps a `ttkbootstrap.Querybox` to provide an easy-to-use date picker dialog
    via the `get_date` static method.
    """

    @staticmethod
    def get_date(parent=None, title=" ", firstweekday=6, startdate=None, bootstyle="primary",) -> datetime:
        """
        Shows a calendar popup and returns the selected date.

        :param parent: Widget | None (The parent widget. The popup appears bottom-right of the parent; if None,
        it's centered on screen.)
        :param title: str (The text that appears on the popup titlebar.)
        :param firstweekday: int (First day of the week; 0 is Monday, 6 is Sunday.)
        :param startdate: datetime | None (The date that should be in focus when the widget opens.)
        :param bootstyle: str (Color style of the popup. Options: primary, secondary, info, warning, success, danger,
        light, dark.)
        :return: datetime (The selected date, or current date if none is selected.)
        """

        chooser = SmartDatePickerDialog(parent=parent, title=title, firstweekday=firstweekday, startdate=startdate,
            bootstyle=bootstyle,)

        return chooser.date_selected


class SmartDatePickerDialog(DatePickerDialog):
    """
    A custom date picker dialog that ensures locale settings are applied.

    Extends `ttkbootstrap.DatePickerDialog` to fix locale issues so the calendar displays in the correct locale.

    Attributes:
        parent (Widget | None): The parent widget for the dialog.
        root (Toplevel): The dialog window.
        firstweekday (int): First day of the week (0 = Monday, 6 = Sunday).
        startdate (date): The initial date in focus.
        bootstyle (str): The visual theme for styling.
        date_selected (date | str): The final date selected or empty string if cancelled.
        date (date): The currently focused calendar date.
        calendar (calendar.Calendar): Calendar object for rendering.
        titlevar (StringVar): Title variable for the dialog.
        datevar (IntVar): IntVar tracking the currently selected day.
    """

    locale.setlocale(locale.LC_ALL, locale.setlocale(locale.LC_TIME, ""))

    def __init__(self, parent=None, title=" ", firstweekday=6, startdate=None, bootstyle=PRIMARY,):
        """
        Initializes the SmartDatePickerDialog with given parameters and fixes locale settings.

        :param parent: Widget | None (The parent widget for this dialog; if None, the dialog is centered on screen.)
        :param title: str (The text to display as the dialog's title.)
        :param firstweekday: int (The first day of the week for the calendar, 0=Monday through 6=Sunday.)
        :param startdate: datetime | None (The initially selected date when the dialog opens.)
        :param bootstyle: str (Appearance style for the dialog, e.g., "primary", "secondary", etc.)
        :return: None
        """

        self.parent = parent
        self.root = tb.Toplevel(title=title, transient=self.parent, resizable=(False, False), topmost=True,
                                minsize=(226, 1), iconify=True,)
        # New binds for more dynamic usage
        self.root.bind("<Escape>", self._on_escape)
        self.root.bind("<Return>", self._on_return)
        self.root.bind("<FocusOut>", self._on_focus_out)
        self.root.bind("<Button-1>", self._on_click)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.root.bind("<KeyPress>", self._navigate_keys)

        self.firstweekday = firstweekday
        self.startdate = startdate or datetime.today().date()
        self.bootstyle = bootstyle or PRIMARY

        self.date_selected = self.startdate
        self.date = startdate or self.date_selected
        self.calendar = calendar.Calendar(firstweekday=firstweekday)

        self.titlevar = tb.StringVar()
        self.datevar = tb.IntVar()

        self._setup_calendar()
        self.root.grab_set()
        self.root.wait_window()

    def _navigate_keys(self, event) -> None:
        """
        Handles keyboard navigation within the calendar.

        Allows left/right/up/down and key controls to navigate between days and months.

        :param event: Event (The keyboard event.)
        :return: None
        """

        keys = event.keysym
        match keys:
            case "Left" | "a":
                add_value = -1
            case "Right" | "d":
                add_value = 1
            case "Up" | "w":
                add_value = -7
            case "Down" | "s":
                add_value = 7
            case _:
                return
        self._calc_new_entry(add_value)

    def _get_last_day_current_month(self) -> int:
        """
        Calculates the last day of the currently displayed month.

        :return: int (The last day of the current month, considering leap years.)
        """

        return calendar.monthrange(self.date.year, self.date.month)[1]

    def _calc_new_entry(self, add_val: int) -> None:
        """
        Calculates and updates the calendar selection by applying an offset to the current day index.

        :param add_val: int (The number of days to add or subtract from the current selection.)
        :return: None
        """

        if self._current_button_index is not None:
            current_ind = self._current_button_index
            current_btn = self._day_buttons[current_ind]["btn"]
            new_ind = current_ind + add_val
            if new_ind < 0:

                self.prev_period.invoke()
                self.month_last_day = self._get_last_day_current_month()

                new_ind = self.month_last_day + new_ind  # Ind is negative here so + subtracts
                new_day = self._day_buttons[new_ind]["day"]
                self.datevar.set(new_day)
                self._current_button_index = new_ind
                self.date_selected = self.date_selected.replace(day=new_day, month=self.date.month)


            elif new_ind >= len(self._day_buttons):
                new_ind = new_ind - len(self._day_buttons)
                self.next_period.invoke()
                self.month_last_day = self._get_last_day_current_month()
                new_day = self._day_buttons[new_ind]["day"]
                self.datevar.set(new_day)
                self._current_button_index = new_ind
                self.date_selected = self.date_selected.replace(day=new_day, month=self.date.month)


            else:
                new_day = self._day_buttons[new_ind]["day"]
                self.datevar.set(new_day)
                current_btn.configure(bootstyle=f"{self.bootstyle}-calendar")
                self._current_button_index = new_ind
                self.date_selected = self.date_selected.replace(day=new_day)

    def _on_focus_out(self, event) -> None:
        """
        Closes the calendar if focus is lost and the mouse is outside the calendar window.

        :param event: Event (The focus-out event.)
        :return: None
        """

        self._on_escape(event)

    def _on_return(self, event) -> None:
        """
        Confirms the currently selected date and closes the dialog.

        :param event: Event (The key press event, typically Enter.)
        :return: None
        """

        self.root.destroy()

    def _on_click(self, event) -> None:
        """
        Sets the selected date based on the clicked calendar item.

        :param event: Event (The mouse click event on a calendar date.)
        :return: None
        """

        clicked_widget = self.root.winfo_containing(event.x_root, event.y_root)
        if clicked_widget is None or clicked_widget.winfo_toplevel() is not self.root:
            self._on_escape(event)

    def _on_close(self) -> None:
        """
        Closes the date picker dialog and clears internal state.

        :return: None
        """

        self._on_escape(None)

    def _on_escape(self, event) -> None:
        """
        Cancels the date selection and closes the dialog.

        :param event: Event (The Escape key event.)
        :return: None
        """

        self.date_selected = ""
        self.root.destroy()

    def _draw_calendar(self) -> None:
        """
        Creates and displays the calendar interface for the current month and year.

        Draws the calendar grid and populates it with the correct day numbers.

        :return: None
        """

        self._update_widget_bootstyle()
        self._set_title()
        self._current_month_days()
        self.frm_dates = tb.Frame(self.frm_calendar)
        self.frm_dates.pack(fill=BOTH, expand=YES)
        self._day_buttons = []
        self._current_button_index = None

        for row, weekday_list in enumerate(self.monthdays):
            for col, day in enumerate(weekday_list):
                self.frm_dates.columnconfigure(col, weight=1)
                if day == 0:
                    tb.Label(
                        master=self.frm_dates,
                        text=self.monthdates[row][col].day,
                        anchor=CENTER,
                        padding=5,
                        bootstyle=SECONDARY,
                    ).grid(row=row, column=col, sticky=NSEW)
                else:

                    if all(
                            [
                                day == self.date_selected.day,
                                self.date.month == self.date_selected.month,
                                self.date.year == self.date_selected.year,
                            ]
                    ):
                        day_style = "secondary-toolbutton"
                    else:
                        day_style = f"{self.bootstyle}-calendar"

                    def selected(x=row, y=col) -> datetime:
                        """
                        Returns the selected date from the calendar dialog.

                        :return: datetime | None (The selected date, or None if no date was chosen.)
                        """

                        self._on_date_selected(x, y)

                    btn = tb.Radiobutton(
                        master=self.frm_dates,
                        variable=self.datevar,
                        value=day,
                        text=day,
                        bootstyle=day_style,
                        padding=5,
                        command=selected,
                    )
                    btn.grid(row=row, column=col, sticky=NSEW)
                    if day_style == "secondary-toolbutton":
                        self._current_button_index = len(self._day_buttons)
                    self._day_buttons.append({"row": row, "col": col, "day": day, "btn": btn})

        self.month_last_day = self._get_last_day_current_month()

class FlexFrame(Frame):
    """
    A flexible frame container that provides an inner frame for widget placement.

    As standard, the FlexFrame is expanded.

    Use `<FlexFrame>.inner_frame` to add child widgets instead of adding directly to the FlexFrame.
    This separation allows the outer frame to manage layout flexibility (like expansion/collapse).

    Attributes:
        inner_frame (Frame): The user-facing inner frame for placing widgets.
        expanded (bool): Whether the FlexFrame is currently expanded.
        expand_char (str): Character shown when frame is collapsed (e.g. "▼").
        shrink_char (str): Character shown when frame is expanded (e.g. "▶").
        title_side (str): Side of the title and toggle button ("left" or "right").
        _title_var (tk.StringVar): Variable holding the title label text.
        _flex_text_var (tk.StringVar): Variable holding the current expand/collapse symbol.
        _title_frame (Frame): Container for the title label and button.
        _title_label (Label): Label showing the title text.
        _flex_btn (Button): Toggle button for expanding/collapsing.
        _placeholder (Frame | None): Frame used to maintain layout when collapsed.
    """

    _forbidden_methods_inner = {"pack", "grid", "place", "pack_forget", "grid_forget", "place_forget",
                                "winfo_width", "winfo_height"}

    def __init__(self, master=None, title_text: str = None, title_var: tk.StringVar = None,
                 title_side: str = "left", expand_char: str = "▼", shrink_char: str = "▶", *args, **kwargs):
        """
        Initializes a collapsible FlexFrame widget with a title and toggleable content.

        :param master: Widget | None (The parent container.)
        :param title_text: str | None (Optional static title text.)
        :param title_var: tk.StringVar | None (Optional dynamic title variable.
        Use either this or `title_text`, not both.)
        :param title_side: str (Side where the title and button appear. Must be "left" or "right".)
        :param expand_char: str (Character displayed when collapsed. Must be a single character.)
        :param shrink_char: str (Character displayed when expanded. Must be a single character.)
        :param args: Additional positional arguments passed to the Frame.
        :param kwargs: Additional keyword arguments passed to the Frame.
        :raises ValueError: If both `title_text` and `title_var` are provided, or if `expand_char`/`shrink_char`
        are not single characters.
        :return: None
        """

        super().__init__(master, *args, **kwargs)

        if title_text is not None and title_var is not None:
            raise ValueError("You can't specify both title_text and title_var.\n"
                             "Rather set the value of your title_var beforehand.")
        if len(expand_char) != 1:
            raise ValueError("expand char has to be one char.")
        if len(shrink_char) != 1:
            raise ValueError("shrink char has to be one char.")

        if title_text is None and title_var is None:
            title_text = "Expand here"
        self._title_var = title_var or tk.StringVar()

        if title_text is not None:
            self._title_var.set(title_text)

        self.title_side = title_side

        self._flex_text_var = tk.StringVar()
        self.expanded = True
        self.expand_char = expand_char
        self.shrink_char = shrink_char
        self._flex_text_var.set(self.shrink_char)

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)

        self._title_frame = tb.Frame(self)
        self._title_frame.grid(row=0, column=0, sticky="ew")

        self._flex_btn = tb.Button(self._title_frame, textvariable=self._flex_text_var,
                                   command=self.toggle_expanded, width=2)
        self._title_label = tb.Label(self._title_frame, textvariable=self._title_var, font=("Arial", 16))

        self._flex_btn.pack(side=self.title_side, padx=5, pady=5)
        self._title_label.pack(side=self.title_side, padx=5, pady=5)

        self.inner_frame = tb.Frame(self, name="inner_frame")
        self.inner_frame.grid(row=1)

        # Configure inner_frame restricted/forbidden methods
        self.inner_frame._original_grid_forget = self.inner_frame.grid_forget
        self.inner_frame._original_winfo_width = self.inner_frame.winfo_width
        self.inner_frame._original_grid = self.inner_frame.grid
        for fm in self._forbidden_methods_inner:
            if hasattr(self.inner_frame, fm):
                setattr(self.inner_frame, fm, self._forbidden_method)
        self.inner_frame._original_configure = self.inner_frame.configure
        self.inner_frame.configure = self._restricted_configure

        self._placeholder: tb.Frame = None


    def _forbidden_method(self, *args, **kwargs) -> None:
        """
        Raises an error when a forbidden method is called on the inner frame.

        This is used to block layout and geometry-related operations directly on `inner_frame`.

        :param args: Ignored positional arguments.
        :param kwargs: Ignored keyword arguments.
        :raises RuntimeError: Always raised to indicate the method is not allowed.
        :return: None
        """

        raise RuntimeError(f"You used a forbidden method on inner Frame of FlexFrame: "
                           f"{', '.join(FlexFrame._forbidden_methods_inner)}."
                           f"Try for this options <Object>.this")

    def _restricted_configure(self, **kwargs):
        """
        Wrapper for `configure()` to block layout-related changes on the inner frame.

        Blocks specific keys that could interfere with the layout integrity of the FlexFrame.

        :param kwargs: dict (Configuration options passed to `configure`.)
        :raises RuntimeError: If any restricted keys are used in the configuration.
        :return: Any (The result of the original `configure()` call.)
        """

        restricted_keys = {"width", "height", "padx", "pady", "borderwidth", "relief"}
        blocked_keys = [key for key in kwargs if key in restricted_keys]

        if blocked_keys:
            raise RuntimeError(
                f"Cannot set configure options {', '.join(blocked_keys)} on inner Frame.\n"
                f"Try for this <Object>.this.configure")

        return self.inner_frame._original_configure(**kwargs)

    def toggle_expanded(self) -> None:
        """
        Toggles the expanded/collapsed state of the FlexFrame.

        Expands if currently collapsed, and collapses if currently expanded.

        :return: None
        """

        if self.expanded:
            self.expanded = False
            self._flex_text_var.set(self.expand_char)
            self._shrink()
        else:
            self.expanded = True
            self._flex_text_var.set(self.shrink_char)
            self._expand()

    def _expand(self) -> None:
        """
        Expands the FlexFrame to show its full height/content.

        :return: None
        """

        if self._placeholder is not None:
            self._placeholder.grid_forget()
            self._placeholder.destroy()
            self._placeholder = None
        self.inner_frame._original_grid(row=1)

    def _shrink(self) -> None:
        """
        Collapses the FlexFrame to hide its internal content.

        :return: None
        """

        self.update_idletasks()
        self.inner_frame._original_grid_forget()
        width = max(self.inner_frame._original_winfo_width(), 1)

        self._placeholder = Frame(self, width=width, height=0)
        self._placeholder.grid(row=1, column=0, sticky="ew")

class ItemSelectFrame(tb.Frame):
    # TODO: Docstrings
    def __init__(self, parent, text_value: str, internal_value=None, on_selected_color: str = None,
                 on_not_selected_color: str = None, *args, **kwargs):
        super().__init__(parent, relief="solid", borderwidth=1.5, *args, **kwargs)


        self._text_value = text_value
        self._internal_value = internal_value or text_value
        self._on_selected_color = on_selected_color or "#00BCD4"
        self._on_not_selected_color = on_not_selected_color or "#B07C84"
        self._is_selected = False
        self.text_is_internal_value = self._internal_value == self._text_value

        # Custom styles to make it look like it should
        StyleManager().register_style(
            style_name="ItemSelection.TButton",
            config={
                "background": "$color.bg", "foreground": "$color.fg", "borderwidth": 0,
                "padding": 5, "font": ("TkDefaultFont", 10), "relief": "flat"
            },
            mapconfig={
                "bordercolor": [
                    ("selected hover", self._on_selected_color),
                    ("!selected hover", self._on_not_selected_color)
                ],
                "borderwidth": [
                    ("selected hover", 1),
                    ("!selected hover", 1),
                    ("selected", 1),
                    ("!selected", 1)
                ],
                "relief": [("hover", "solid"), ("!hover", "flat")],
                "foreground": [("!disabled", "$color.fg")],
                "background": [("!disabled", "$color.bg")],
                "focuscolor": [("focus", "$color.bg")]
            }
        )

        StyleManager().register_style(
            style_name="ItemSelection.TFrame",
            config={
                "borderwidth": 0, "relief": "solid", "padding": 0
            },
            mapconfig={
                "bordercolor": [
                    ("selected", self._on_selected_color),
                    ("!selected", self._on_not_selected_color)
                ],
                "background": [("!disabled", "$color.bg")]
            }
        )

        self._fake_button = tb.Button(self, text=self._text_value, command=self.widget_clicked)
        self._fake_button.pack(expand=True, fill=BOTH)
        self._fake_button.configure(style="ItemSelection.TButton")
        self.configure(style="ItemSelection.TFrame")
        self.state(["!selected"])
        self._fake_button.state(["!selected"])


    def get_value(self):
        if self._is_selected:
            return self._internal_value
        else:
            return None
    @property
    def internal_value(self):
        return self._internal_value

    @property
    def text_value(self):
        return self._text_value

    def widget_clicked(self):
        self.event_generate("<<ItemClicked>>", when="tail")
        self.toggle_state()

    def toggle_state(self):
        if self._is_selected:
            self._is_selected = False
            self.state(["!selected"])
            self._fake_button.state(["!selected"])
            self.event_generate("<<ItemDisabled>>", when="tail")
        else:
            self._is_selected = True
            self.state(["selected"])
            self._fake_button.state(["selected"])
            self.event_generate("<<ItemEnabled>>", when="tail")

    def set_selected(self, selected: bool = True):
        if not isinstance(selected, bool):
            raise TypeError(f"Expected bool but got {type(selected)}")

        if selected:
            self._is_selected = True
            self.state(["selected"])
            self._fake_button.state(["selected"])
        else:
            self._is_selected = False
            self.state(["!selected"])
            self._fake_button.state(["!selected"])

class InfoBoxFrame(Frame):
    """
    A small frame showing an information icon that displays a tooltip on hover.

    This frame contains a "?" icon. When the user hovers over it, a separate tooltip window appears,
    showing additional information text.

    Attributes:
        _info_text (str): The text displayed in the tooltip.
        info_window (Toplevel | None): The floating window for showing the tooltip on hover.
    """

    def __init__(self, master, info_text: str | list[str] = None, *args, **kwargs):
        """
        Initializes the InfoBoxFrame with a given information text and parent container.

        :param master: Widget (The parent frame where this info box is placed.)
        :param info_text: str | list[str] (The information text that appears on hover.)
        :param args: Additional positional arguments for the Frame.
        :param kwargs: Additional keyword arguments for the Frame. Supports 'borderwidth' and 'relief'.
        :return: None
        """

        borderwidth = kwargs.pop("borderwidth", 5)
        relief = kwargs.pop("relief", "sunken")
        super().__init__(master, borderwidth=borderwidth, relief=relief, width=32, height=35, *args, **kwargs)

        if info_text:
            self._info_text = info_text if isinstance(info_text, str) else "".join([f"{inf}\n" for inf in info_text])
        else:
            self._info_text = ""
        self.info_window = None
        tb.Label(self, text="?", font=("Arial", 12, "bold")).pack(expand=True)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_hover_out)

    @property
    def info_text(self) -> str:
        """
        Gets the informational text displayed in the hover tooltip.

        :return: str (The current info text that will appear when hovering over the icon.)
        """

        return self._info_text

    @info_text.setter
    def info_text(self, info_text: str | list[str]):
        """
        Sets the content of the information text shown in the info window.

        :param info_text: str | list[str] (The new info text to be displayed.)
        :return: None
        """

        self._info_text = info_text if isinstance(info_text, str) else "".join([f"{inf}\n" for inf in info_text])

    def _on_hover(self, event) -> None:
        """
        Displays the tooltip window when the mouse enters the icon area.

        :param event: Event (The mouse enter event.)
        :return: None
        """

        if self.info_window:
            return  # Prevent duplicate windows

        self.info_window = tk.Toplevel(self)
        self.info_window.overrideredirect(True)  # Remove window borders
        self.info_window.geometry(f"+{self.winfo_rootx() + 40}+{self.winfo_rooty() - 10}")  # Position above

        # Tooltip label inside the floating window
        tb.Label(self.info_window, text=self._info_text, font=("Arial", 10), background="lightyellow", relief="solid",
                 borderwidth=1).pack()

    def _on_hover_out(self, event) -> None:
        """
        Hides the tooltip window when the mouse leaves the icon area.

        :param event: Event (The mouse leave event.)
        :return: None
        """

        if self.info_window:
            self.info_window.destroy()
            self.info_window = None


class TimeRangeFrame(tb.Frame):
    """
    A composite frame with controls for selecting a time range.

    This frame includes input fields for a start date/time and end date/time,
    as well as a dropdown for choosing a dynamic timeframe (like "last_7_days").

    Attributes:
        _start_date (StringVar): Text variable holding the selected start date.
        _start_time (StringVar): Text variable holding the selected start time.
        _end_date (StringVar): Text variable holding the selected end date.
        _end_time (StringVar): Text variable holding the selected end time.
        _dynamic_time_frame (StringVar): Selected dynamic timeframe.
        _dynamic_time_frame_list (list[str]): Available dynamic timeframe options.
        _left_frame (Frame): Frame containing static date/time fields.
        _right_frame (Frame): Frame containing the dynamic timeframe selector.
        start_date_entry (SmartDateEntry): Widget for selecting the start date.
        end_date_entry (SmartDateEntry): Widget for selecting the end date.
        dynamic_combobox (Combobox): Dropdown for dynamic timeframe selection.
    """

    def __init__(self, master, *args, **kwargs):
        """
        Initializes a TimeRangeFrame with fields for selecting dynamic and static time ranges.

        :param master: Widget (Parent widget.)
        :param args: Additional positional arguments for the Frame.
        :param kwargs: Additional keyword arguments for the Frame.
        :return: None
        """

        super().__init__(master, *args, **kwargs)

        self._start_date = tk.StringVar()
        self._start_time = tk.StringVar()
        self._end_date = tk.StringVar()
        self._end_time = tk.StringVar()
        self._dynamic_time_frame = tk.StringVar()
        self._dynamic_time_frame_list = ["", *DynamicTimeframe.get_entries()]
        self.columnconfigure(0, weight=0, minsize=300)
        self.columnconfigure(1, weight=0, minsize=150)

        self._left_frame = tb.Frame(self)
        self._right_frame = tb.Frame(self)

        self._left_frame.grid(column=0, row=0, sticky="NEW")
        self._right_frame.grid(column=1, row=0, sticky="NEW", padx=(20, 0))

        self._left_frame.rowconfigure(0, weight=0)
        self._left_frame.rowconfigure(1, weight=0)
        self._left_frame.columnconfigure(0, weight=0)
        self._left_frame.columnconfigure(1, weight=0)
        self._left_frame.columnconfigure(2, weight=0)
        self._left_frame.columnconfigure(3, weight=0)
        tb.Label(self._left_frame, text="Start Date:").grid(column=0, row=0, sticky="W")
        self.start_date_entry = SmartDateEntry(self._left_frame, width=12, name="start_date")
        self.start_date_entry.grid(row=0, column=1, pady=2, sticky="W")
        self.start_date_entry.bind("<FocusOut>", self._check_change)

        tb.Label(self._left_frame, text="Time:").grid(row=0, column=2, pady=2, sticky="W")
        tb.Entry(self._left_frame, textvariable=self._start_time, width=8).grid(row=0, column=3, pady=2, sticky="W")

        tb.Label(self._left_frame, text="End Date:").grid(row=1, column=0, pady=2, sticky="W")
        self.end_date_entry = SmartDateEntry(self._left_frame, width=12, name="end_date")
        self.end_date_entry.grid(row=1, column=1, pady=2, sticky="W")
        self.end_date_entry.bind("<FocusOut>", self._check_change)

        tb.Label(self._left_frame, text="Time:").grid(row=1, column=2, pady=2, sticky="W")
        tb.Entry(self._left_frame, textvariable=self._end_time, width=8).grid(row=1, column=3, pady=2, sticky="W")

        self._right_frame.rowconfigure(0, weight=0)
        self._right_frame.rowconfigure(1, weight=0)
        tb.Label(self._right_frame, text="Dynamic Timeframe:").grid(column=0, row=0, sticky="W")
        self.dynamic_combobox = tb.Combobox(self._right_frame, textvariable=self._dynamic_time_frame,
                                            values=self._dynamic_time_frame_list, width=15, state="readonly")

        self.dynamic_combobox.current(0)
        self.dynamic_combobox.bind("<Escape>", lambda event: self.dynamic_combobox.current(0))
        self.dynamic_combobox.grid(row=1, column=0, pady=2, sticky="W")

    def _check_change(self, event) -> None:
        """
        Ensures time fields are populated when a valid date is entered.

        If a date field is set and its corresponding time field is empty,
        default values ("00:00" for start, "23:59" for end) are applied.

        :param event: Event (The focus-out event from a date field.)
        :return: None
        """

        txt = event.widget.entry.get()
        if not txt == "":
            if event.widget.winfo_name() == "start_date":
                if self._start_time.get() == "":
                    self._start_time.set("00:00")
            else:
                if self._end_time.get() == "":
                    self._end_time.set("23:59")

    def get_fields(self) -> tuple[str, str, str]:
        """
        Retrieves and validates the selected time range values.

        Validates formatting of entered dates and times, and ensures that either
        a dynamic timeframe or a valid date range is selected (but not both).

        :raises FormValidationError: If any input fields contain invalid or inconsistent data.
        :return: tuple[str, str, str] (A tuple of (dynamic_range, start_datetime_str, end_datetime_str).)
        """

        faulty_fields = []
        dynamic_time_frame = self._dynamic_time_frame.get()
        start_date = self.start_date_entry.entry.get()
        start_time = self._start_time.get()
        end_date = self.end_date_entry.entry.get()
        end_time = self._end_time.get()

        dynamic_has_value = dynamic_time_frame == "" or dynamic_time_frame in self._dynamic_time_frame_list
        if not dynamic_has_value:
            faulty_fields.append("Dynamic Timeframe has no proper value")
        if not dynamic_time_frame and not (start_date or end_date):
            faulty_fields.append("No Absolute or Dynamic Timeframe was chosen.")

        if start_date or end_date:
            if not (start_date and end_date):
                faulty_fields.append("Start Date missing" if end_date else "End Date missing")
            if not dynamic_time_frame == "":
                faulty_fields.append("Dynamic Timeframe can't be used with fixed dates")

            # fallback for no entry set
            if not start_time:
                self._start_time.set("00:00")
            if not end_time:
                self._end_time.set("23:59")

        if not dynamic_time_frame:
            try:
                start_date = datetime.strptime(start_date, "%d.%m.%Y")
            except ValueError:
                faulty_fields.append("Start Date not a valid Date (dd.mm.yyyy)")

            try:
                start_time = datetime.strptime(start_time, "%H:%M")
            except ValueError:
                faulty_fields.append("Start Time not a valid Time (HH:MM)")

            try:
                end_date = datetime.strptime(end_date, "%d.%m.%Y")
            except ValueError:
                faulty_fields.append("End  Date is not a valid date format (dd.mm.yyyy)")

            try:
                end_time = datetime.strptime(end_time, "%H:%M")
            except ValueError:
                faulty_fields.append("End Time not a valid Time (HH:MM)")

        if faulty_fields:
            raise FormValidationError(faulty_fields)

        if dynamic_time_frame:
            start_datetime = ""
            end_datetime = ""
        else:
            start_datetime = datetime.combine(start_date.date(), start_time.time())
            end_datetime = datetime.combine(end_date.date(), end_time.time())

        return dynamic_time_frame, start_datetime, end_datetime


class FilterFrame(tb.Frame):
    """
    Frame for editing and managing a single filter's settings.

    This frame contains UI elements for specifying filter attributes such as name, time range,
    window type, labels, etc. It also provides controls to save or delete the filter,
    and dynamically updates its content based on user input.

    Attributes:
        flex (FlexFrame): The outer container frame for layout and collapsibility.
        _filter (DatabaseFilter | None): The current filter instance being edited or created.
        _filter_id (int | None): The ID of the filter if it exists in the database.
        _name (StringVar): The name of the filter.
        _window_type (StringVar): The window type filter string.
        _window_title (StringVar): The window title filter string.
        _word_list (StringVar): Comma-separated keywords for filtering.
        _text_label_list (StringVar): Text representation of selected labels.
        _choice_box_label_list (StringVar): Current selection in the label combobox.
        _chosen_label_dict (dict): Dictionary of selected label IDs and their names.
        _all_labels_dict (dict): All available labels mapped by ID to name.
        _time_frame (TimeRangeFrame): Subframe for selecting start/end times or dynamic range.
        _label_choice_box (Combobox): Dropdown for selecting additional labels.
    """

    def __init__(self, parent, database_filter=None, *args, **kwargs):
        """
        Initializes the FilterFrame with a given filter object.

        Sets up internal variables and populates the frame with default values.
        If a `database_filter` is provided, its fields (like name and labels) are loaded into the UI components.
        Ensures that a new filter is assigned an ID if it’s added to the database.

        :param parent: Widget (The parent container in which this frame is placed.)
        :param database_filter: DatabaseFilter | None (An existing filter object to edit.
        If None, a new filter is being created.)
        :param args: Additional positional arguments for the Frame initializer.
        :param kwargs: Additional keyword arguments for the Frame initializer.
        """

        super().__init__(parent, *args, **kwargs)

        self._filter = database_filter

        self._filter_id = self._filter.id if self._filter else None

        self._name_var = tk.StringVar()
        self._window_type = tk.StringVar()
        self._window_title = tk.StringVar()
        self._word_list = tk.StringVar()
        self._text_label_list = tk.StringVar()
        self._choice_box_label_list = tk.StringVar()
        self._chosen_label_dict = {}
        self._all_labels_dict: dict = {lab.id: lab.name for lab in Label.get_all_labels()}

        self.flex = FlexFrame(self, title_var=self._name_var)
        self.flex.pack(fill=tk.BOTH, expand=True)
        [self.flex.inner_frame.rowconfigure(i, weight=0) for i in range(7)]
        self.flex.inner_frame.columnconfigure(0, weight=0)
        self.flex.inner_frame.columnconfigure(1, weight=1)

        tb.Label(self.flex.inner_frame, text="Filter Name:").grid(column=0, row=0, padx=(0, 5), pady=3, sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self._name_var).grid(column=1, row=0, pady=1, sticky="W")

        self._time_frame = TimeRangeFrame(self.flex.inner_frame)
        self._time_frame.grid(column=0, columnspan=2, row=1, padx=(0, 5), pady=3, sticky="W")

        tb.Label(self.flex.inner_frame, text="Window Type:").grid(column=0, row=2, padx=(0, 5), pady=3, sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self._window_type).grid(column=1, row=2, pady=1, sticky="W")

        tb.Label(self.flex.inner_frame, text="Window Title:").grid(column=0, row=3, padx=(0, 5), pady=3, sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self._window_title).grid(column=1, row=3, pady=1, sticky="W")

        tb.Label(self.flex.inner_frame, text="Word List:").grid(column=0, row=4, padx=(0, 5), pady=3, sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self._word_list).grid(column=1, row=4, pady=1, sticky="W")

        # Stuff for labels
        tb.Label(self.flex.inner_frame, text="Chosen Labels").grid(row=5, column=0, sticky="W")
        info_text = ("Choose from the dropdown the Labels you want to include in your filter.\n"
                     "If you set labels, it only results in entries which have at least 1 of them.\n"
                     "Use the reset button to remove all saved entries so far.")
        InfoBoxFrame(self.flex.inner_frame, info_text=info_text).grid(column=1, row=5, padx=(0, 5), pady=5,  sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self._text_label_list, state="disabled")\
            .grid(row=6, column=0, columnspan=2, sticky="EW")

        label_names = [name for name in self._all_labels_dict.values()]
        self._label_choice_box = tb.Combobox(self.flex.inner_frame, textvariable=self._choice_box_label_list, values=label_names,
                                             width=15, state="readonly")
        self._label_choice_box.grid(row=7, column=0, sticky="W")

        label_buttons_frame = tb.Frame(self.flex.inner_frame)
        label_buttons_frame.grid(row=7, column=1, sticky="W")

        label_buttons_frame.rowconfigure(0, weight=0)
        label_buttons_frame.rowconfigure(1, weight=0)
        tb.Button(label_buttons_frame, text="Add", command=self._change_label)\
            .grid(column=2, row=0, sticky="W", padx=5, pady=5)
        tb.Button(label_buttons_frame, text="Reset", command=self._reset_labels) \
            .grid(column=2, row=1, sticky="W", padx=5, pady=5)

        delete_btn = tb.Button(self.flex.inner_frame, text="Del", bootstyle="danger")
        delete_btn.place(relx=1.0, rely=0, x=-55)

        delete_btn.bind("<Button-1>", self.delete_filter)

        if self._filter is not None:
            self._fill_with_filter()

    def _fill_with_filter(self) -> None:
        """
        Populates all input fields in the UI with values from the current filter object.

        Loads name, time range, window type/title, word list, and associated labels into their
        respective input fields and widgets. Skips any fields that are None or empty.

        :return: None
        """

        filter_dict = self._filter.as_dict()

        self._name_var.set(filter_dict["name"] or "")

        self._time_frame.start_date_entry.set(filter_dict["start_date"] or "")
        self._time_frame._start_time.set(filter_dict["start_time"] or "")
        self._time_frame.end_date_entry.set(filter_dict["end_date"] or "")
        self._time_frame._end_time.set(filter_dict["end_time"] or "")

        if filter_dict["dynamic_time_frame"] and filter_dict["dynamic_time_frame"].value \
                in self._time_frame._dynamic_time_frame_list:
            value_index = self._time_frame._dynamic_time_frame_list.index(filter_dict["dynamic_time_frame"].value)
            self._time_frame.dynamic_combobox.current(value_index)
        else:
            self._time_frame.dynamic_combobox.current(0)

        self._window_type.set(filter_dict["window_type"] or "")
        self._window_title.set(filter_dict["window_title"] or "")
        self._word_list.set(", ".join(filter_dict["word_list"]) if filter_dict.get("word_list") else "")

        if filter_dict["label_list"]:
            self._text_label_list.set(", ".join(self._all_labels_dict[lab_id] for lab_id in filter_dict["label_list"]
                                                if lab_id in self._all_labels_dict))
            self._chosen_label_dict = {}
            for lab_id in filter_dict["label_list"]:
                self._chosen_label_dict[lab_id] = self._all_labels_dict[lab_id]

    def delete_filter(self, event) -> None:
        """
        Deletes the filter after optional user confirmation.

        If the Shift key is held, deletion occurs immediately. Otherwise, a confirmation
        dialog is shown. Deletes the filter from the database if it exists, then removes
        this frame from the UI.

        :param event: Event (The button click event, used to check Shift key state.)
        :return: None
        """

        if not event.state & 0x0001:  # Shift key flag
            result = Messagebox.okcancel(f"Do you want to delete filter '{self._name.get()}'"
                f"({self._filter._name if self._filter else ''}) ?",
            "WARNING! Delete Filter", parent=self.master.master)
            if result != "OK":
                return

        if self._filter is not None:
            self._filter.delete_in_db()
        self.destroy()

    def save_to_db(self) -> None:
        """
        Saves or updates the current filter in the database.

        Collects all field values, validates them, and either updates the existing filter or
        creates a new one. If validation fails, an error message is shown.

        :return: None
        """

        db_dict = {}
        try:
            db_dict["dynamic_time_frame"], db_dict["start_datetime"], db_dict["end_datetime"] \
                = self._time_frame.get_fields()

            (db_dict["name"], db_dict["window_type"], db_dict["window_title"], db_dict["word_list"],
             db_dict["label_list"]) = self.validate_fields()

        except FormValidationError as e:
            Messagebox.show_warning(e.message, "Form Validation Failed")
        else:
            if self._filter_id is not None:
                # update mechanic
                self._filter.update(**db_dict)
            else:
                # create new filter
                self._filter = DatabaseFilter(**db_dict)
                self._filter_id = self._filter.id

    def validate_fields(self) -> tuple[str, str, str, list, list]:
        """
        Validates all editable input fields in the filter UI.

        Checks that required fields are filled and contain only valid characters.
        Processes the word list and selected labels for database storage.

        :raises FormValidationError: If invalid or missing data is found.
        :return: tuple (name, window_type, window_title, word_list, label_list)
        """

        faulty_fields = []
        name = self._name.get().strip() or ""
        window_type = self._window_type.get().strip() or ""
        window_title = self._window_title.get().strip() or ""
        word_list = self._word_list.get().strip() or ""

        if not name:
            faulty_fields.append("Name is required")

        allowed_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
        if window_type:
            if any(char not in allowed_chars for char in window_type):
                faulty_fields.append("Window Type field includes invalid characters")

        allowed_chars = allowed_chars + ",+!? "
        if window_title:
            if any(char not in allowed_chars for char in window_title):
                faulty_fields.append("Window Title field includes invalid characters")
        if word_list:
            if any(char not in allowed_chars for char in word_list):
                faulty_fields.append("Word List field includes invalid characters")

        if faulty_fields:
            raise FormValidationError(faulty_fields)
        word_list = FilterFrame.split_comma_separated_entries(word_list) if word_list else ""
        label_list = [label_id for label_id in self._chosen_label_dict.keys()]
        return name, window_type, window_title, word_list, label_list

    def _change_label(self) -> None:
        """
        Adds the currently selected label to the list of chosen labels.

        Updates the internal label dictionary and refreshes the visible text list of labels.
        If no valid selection is made, the method exits without action.

        :return: None
        """

        label_index = self._label_choice_box.current()
        if label_index == -1:
            return
        self._text_label_list.set("")

        label_key = list(self._all_labels_dict)[label_index]
        self._chosen_label_dict[label_key] = self._all_labels_dict[label_key]
        n_text = [f"{self._chosen_label_dict[lab]}, " for lab in self._chosen_label_dict]

        self._text_label_list.set("".join(n_text))

    def _reset_labels(self) -> None:
        """
        Clears all selected labels from the filter.

        Resets the internal label tracking dictionary and the label display text.

        :return: None
        """

        self._text_label_list.set("")
        self._chosen_label_dict = {}

    @staticmethod
    def split_comma_separated_entries(entry_string: str) -> list[str]:
        """
        Utility method to split a comma-separated string into a list of entries.

        Strips whitespace from each entry and filters out any empty strings. Duplicate entries are removed.

        :param entry_string: str (A string containing items separated by commas.)
        :return: list[str] (A list of unique, trimmed entries extracted from the string.)
        """

        return list(set([entry.strip() for entry in entry_string.split(',') if entry.strip()]))


class ConditionListFrame(Frame):
    """
    Frame for managing and displaying condition lists with logic.

    This widget provides UI support for creating, editing, and nesting
    conditions using logical operators ("AND"/"OR"). It can contain both
    simple conditions and nested condition lists.

    Attributes:
        top_list (bool): True if this is the outermost condition list frame.
        first_element (bool): True if this is the first condition block.
        condition_list (ConditionList): The condition list object to render.
        bool_operator_dropdown (Combobox): Dropdown for AND/OR selection.
        transform_button (Button): Button to convert list to a single condition.
        remove_btn (Button): Button to remove this condition list (if allowed).
        operator_frame (Frame): Wrapper frame for operator controls.
    """

    def __init__(self, parent, condition_list: ConditionList = None, top_list: bool = False,
                 first_element: bool = False, *args, **kwargs):
        """
        Initializes the `ConditionListFrame`.

        :param parent: Widget (The parent widget.)
        :param condition_list: ConditionList (Optional condition list to display.)
        :param top_list: bool (Indicates if this frame is the top-level condition list.)
        :param first_element: bool (Indicates if this is the first element in the list.)
        """

        super().__init__(parent, relief="solid", borderwidth=2, *args, **kwargs)
        self.configure(style="AndConditionList.TFrame")
        self.top_list = top_list
        self.first_element = first_element
        self.condition_list = condition_list

        self.pack(fill="x", padx=(5, 3), pady=(5, 3))
        self._create_widgets()

    def _create_widgets(self) -> None:
        """
        Creates and packs widgets for the `ConditionListFrame`.

        :return: None
        """

        if self.top_list:
            and_info = tb.Label(self, text="AND")
            and_info.pack(padx=(5, 0), pady=0, side="top", anchor="w")

        else:
            self.operator_frame = tb.Frame(self)
            self.operator_frame.pack(anchor="w", padx=0, pady=0)
            self.operator_frame.columnconfigure(2, weight=1)
            self.operator_frame.rowconfigure(0, weight=1)

            self.bool_operator_dropdown = Combobox(self.operator_frame, values=["AND", "OR"], width=4, state="readonly")
            self.bool_operator_dropdown.current(0)
            self.bool_operator_dropdown.bind("<MouseWheel>", disable_scroll)
            self.bool_operator_dropdown.bind("<<ComboboxSelected>>", self._updated_operator)
            self.bool_operator_dropdown.grid(row=0, column=0, padx=(5, 0))

            self.transform_button = tb.Button(self.operator_frame, text="🔄", width=3, command=self.transform)
            self.transform_button.grid(row=0, column=1, padx=(5, 0))
            if not self.first_element:
                self.remove_btn = tb.Button(self.operator_frame, text="-", width=2, bootstyle="danger",
                                            command=self.remove_self)
                self.remove_btn.grid(row=0, column=2, padx=(5, 0))

        if self.condition_list:
            first_condition = True if self.top_list else False
            for cond in self.condition_list.conditions:
                if isinstance(cond, ObjectCondition):
                    if first_condition:
                        ConditionFrame(self, condition=cond, first_element=True)
                        first_condition = False
                    else:
                        ConditionFrame(self, condition=cond)
                elif isinstance(cond, ConditionList):
                    if first_condition:
                        ConditionListFrame(self, condition_list=cond, first_element=True)
                    else:
                        ConditionListFrame(self, condition_list=cond)
                else:
                    raise ValueError(f"Invalid condition type: {type(cond)}")
        else:
            ConditionFrame(self, first_element=True)

    def toggle_state(self) -> None:
        """
        Toggles the enabled/disabled state of all widgets within the `ConditionListFrame`.

        This method disables or enables the condition list frame, including any child widgets
        such as dropdowns, buttons, and nested frames. Useful for restricting user interaction
        when certain conditions are met or unmet.

        :return: None
        """

        if not self.top_list:
            if str(self.bool_operator_dropdown.cget("state")) == "disabled":
                self.bool_operator_dropdown["state"] = "readonly"
                self.transform_button["state"] = "normal"
                self.remove_btn["state"] = "normal"
            else:
                self.bool_operator_dropdown["state"] = "disabled"
                self.transform_button["state"] = "disabled"
                self.remove_btn["state"] = "disabled"

        for cframe in self.winfo_children():
            if isinstance(cframe, (ConditionFrame, ConditionListFrame)):
                cframe.toggle_state()

    def transform(self) -> None:
        """
        Converts the `ConditionListFrame` into a single condition frame.

        This is used to simplify complex nested condition lists into a single condition.
        All child widgets in the frame are destroyed and replaced with a `ConditionFrame`.

        :return: None
        """

        parent = self.master
        self.pack_forget()
        self.destroy()
        ConditionFrame(parent, first_element=self.first_element)

    def get_as_object(self) -> ConditionList:
        """
        Converts the current `ConditionListFrame` into a `ConditionList` object.

        Iterates through all child frames (both `ConditionFrame` and nested `ConditionListFrame`)
        and collects them into a single `ConditionList` object.

        :return: ConditionList (The condition list represented by this frame.)
        """

        cond_list = []
        for child in self.winfo_children():
            if isinstance(child, (ConditionListFrame, ConditionFrame)):
                cond_list.append(child.get_as_object())
        if self.top_list:
            op = "AND"

        else:
            op = self.bool_operator_dropdown.get()
        return ConditionList(*cond_list, operator=op)

    def _updated_operator(self, event=None) -> None:
        """
        Updates the visual style based on the selected logical operator.

        Changes the frame's appearance according to the "AND"/"OR" setting
        to improve visual clarity.

        :param event: Event (Optional combobox selection event.)
        :return: None
        """

        op = self.bool_operator_dropdown.get()
        if op.lower() == "and":
            self.configure(style="AndConditionList.TFrame")
        elif op.lower() == "or":
            self.configure(style="OrConditionList.TFrame")

    def remove_self(self) -> None:
        """
        Removes this ConditionListFrame from its parent container.

        Used by UI controls to delete the current group of conditions.

        :return: None
        """

        self.destroy()


class ConditionFrame(Frame):
    """
    Frame for managing and displaying a single condition.

    This widget allows users to define a condition by selecting an attribute,
    choosing a comparison operator, and providing a value for comparison.

    Attributes:
        condition_type (Combobox): Dropdown for selecting the condition attribute.
        condition_check (Combobox): Dropdown for selecting the comparison operator.
        condition_value (Entry): Input field for the comparison value.
        condition_value_var (StringVar): Linked variable for the value field.
        add_button (Button): Button to add a new sibling condition.
        transform_button (Button): Button to convert the frame into a condition list.
        remove_button (Button): Button to remove the condition (if not the first element).
        first_element (bool): Whether this is the first condition in its group.
        condition (ObjectCondition): Existing condition used to pre-fill the frame.
        _number_checks (list[str]): Operators valid for numeric conditions.
        _text_checks (list[str]): Operators valid for text-based conditions.
        _all_checks (list[str]): Combined list of all valid operators.
        _condition_types (list[str]): Supported condition attribute types.
    """

    _number_checks = ObjectCondition.get_operators_for_number()
    _text_checks = ObjectCondition.get_operators_for_string()
    _all_checks = _number_checks + _text_checks
    _condition_types = ["window_type", "window_title", "window_text_words", "timestamp"]
    # TODO: Timestanmp really needed??? Maybe later smth like dynamic things predefined: morning/evening,
    #  monday, tuesday etc.

    def __init__(self, parent, condition:ObjectCondition = None,  first_element=False, *args, **kwargs):
        """
        Initializes the `ConditionFrame`.

        Sets up the frame to display the attribute selector, operator dropdown, and
        value input field. Optionally, a pre-existing condition can be loaded into the
        frame.

        :param parent: Widget (The parent widget where this frame will be placed.)
        :param condition: ObjectCondition (Optional pre-existing condition to populate the frame.)
        :param first_element: bool (Indicates if this is the first condition in a list. Default is False.)
        :return: None
        """

        super().__init__(parent, *args, **kwargs)

        self.first_element = first_element
        self.condition = condition

        self.pack(fill="x", padx=(5, 3), pady=3)

        # Dropdown "Condition Type"
        max_chars = max([len(c) for c in ConditionFrame._condition_types]) + 1
        tb.Label(self, text="Condition Type").grid(row=0, column=0, padx=(5, 0), pady=(5, 0), sticky="w")
        self.condition_type = tb.Combobox(self, values=ConditionFrame._condition_types, state="readonly",
                                          width=max_chars)
        self.condition_type.set(ConditionFrame._condition_types[0])
        self.condition_type.bind("<MouseWheel>", disable_scroll)
        self.condition_type.grid(row=0, column=1, padx=(3, 0), pady=(5, 0))

        # Dropdown "Condition Check"
        max_chars = max([len(c) for c in ConditionFrame._all_checks]) + 1
        tb.Label(self, text="Condition Check").grid(row=0, column=2, padx=(5, 0), pady=(5, 0), sticky="w")
        self.condition_check = tb.Combobox(self, values=ConditionFrame._text_checks, state="readonly", width=max_chars)
        self.condition_check.set(ConditionFrame._text_checks[0])  # Fallback to first item
        self.condition_check.bind("<MouseWheel>", disable_scroll)
        self.condition_check.grid(row=0, column=3, padx=(3, 0), pady=(5, 0))

        # Entry "Condition Value" with a default text value
        tb.Label(self, text="Condition Value").grid(row=0, column=4, padx=(5, 0), pady=(5, 0), sticky="w")
        self.condition_value_var = tb.StringVar(value="")
        self.condition_value = tb.Entry(self, textvariable=self.condition_value_var)
        self.condition_value.grid(row=0, column=5, padx=(3, 0), pady=(5, 0))

        self.condition_type.bind("<<ComboboxSelected>>", self._updated_type)

        # SET Conditon values:
        if self.condition:
            # TODO: Check, maybe some problem with attribute_name and the WinInfo attributes.
            if self.condition.attribute_name in ConditionFrame._condition_types:
                self.condition_type.set(self.condition.attribute_name)
                self._updated_type()
            else:
                print("error in condition type")
            if self.condition.comp_operator in ConditionFrame._all_checks:
                self.condition_check.set(self.condition.comp_operator)
            else:
                print("error in Condition.condition_check")
            self.condition_value_var.set(self.condition.attribute_value)

        # "+" Button to add new condition frame at the same level
        self.add_button = tb.Button(self, text="+", width=2, command=self.add_condition)
        self.add_button.grid(row=0, column=6, padx=(3, 0), pady=(5, 0))

        self.transform_button = tb.Button(self, text="🔄", width=3, command=self.transform)
        self.transform_button.grid(row=0, column=7, padx=(3, 0), pady=(5, 0))

        if not self.first_element:
            self.remove_button = tb.Button(self, text="-", width=2, command=self.remove_self, bootstyle="danger")
            self.remove_button.grid(row=0, column=8, padx=(3, 0), pady=(5, 0))

    def _updated_type(self, event=None) -> None:
        """
        Updates the available operators based on the selected attribute type.

        For example:
        - Numeric attributes allow operators like `<`, `>`, `<=`, and `>=`.
        - String attributes allow operators like `==`, `!=`, `in`, and `not in`.

        This method dynamically adjusts the options available in the operator dropdown.

        :param event: Event (The event triggering the update, such as a dropdown selection.)
        :return: None
        """

        if self.condition_type.get() == "timestamp":
            self.condition_check.configure(values=ConditionFrame._number_checks)
        else:
            self.condition_check.configure(values=ConditionFrame._text_checks)

        self.condition_check.set(self.condition_check["values"][0])

    def toggle_state(self) -> None:
        """
        Toggles the enabled/disabled state of all widgets within the `ConditionFrame`.

        This method is useful when user interaction with the frame needs to be restricted,
        such as during validation or when a parent frame is disabled.

        :return: None
        """

        if str(self.add_button.cget("state")) == "disabled":
            self.condition_type.configure(state="readonly")
            self.condition_check.configure(state="readonly")
            self.condition_value.configure(state="normal")
            self.add_button.configure(state="normal")
            self.transform_button.configure(state="normal")
            if hasattr(self, "remove_button"):
                self.remove_button.configure(state="normal")

        else:
            self.condition_type.configure(state="disabled")
            self.condition_check.configure(state="disabled")
            self.condition_value.configure(state="disabled")
            self.add_button.configure(state="disabled")
            self.transform_button.configure(state="disabled")
            if hasattr(self, "remove_button"):
                self.remove_button.configure(state="disabled")

    def transform(self) -> None:
        """
        Transforms the current `ConditionFrame` into a `ConditionListFrame`.

        This is used when a single condition needs to be expanded into a list of conditions.
        The current widgets are replaced with a new `ConditionListFrame`.

        :return: None
        """

        parent = self.master
        self.pack_forget()
        self.destroy()
        ConditionListFrame(parent, first_element=self.first_element)

    def add_condition(self) -> None:
        """
        Adds a new `ConditionFrame` at the same level as the current frame.

        This allows users to dynamically add multiple conditions in a list.

        :return: None
        """

        parent = self.master
        if isinstance(parent, Frame):
            ConditionFrame(parent)
        else:
            print("Error on adding condition frame with add function")

    def get_values(self) -> tuple:
        """
        Retrieves the current condition's attribute, operator, and value.

        This method validates that all fields are properly filled before returning the data.
        Validation errors are raised to ensure the integrity of the condition.

        :return: tuple (A tuple containing the attribute name, operator, and value of the condition.)
        :raises FormValidationError: If required fields are empty or invalid.
        """

        if self.condition_value_var.get() == "":
            raise FormValidationError(faulty_fields="condition value")
        return self.condition_type.get(), self.condition_check.get(), self.condition_value_var.get()

    def get_as_object(self) -> ObjectCondition:
        """
        Converts the `ConditionFrame` into an `ObjectCondition` object.

        This method takes the selected attribute, operator, and value,
        and returns an instance of `ObjectCondition` representing this condition.

        :return: ObjectCondition (The condition represented by this frame.)
        """

        # TODO: add another field when choosing timestamp/datetime from WinInfo, there should be the
        #  choice for date/time/datetime
        #  So you can choose different value types!
        value_type = "str"
        attr_name, compare_operator, attr_value = self.get_values()
        return ObjectCondition(attr_name, compare_operator, attr_value, value_type)

    def remove_self(self) -> None:
        """
        Removes and destroys the `ConditionFrame` from its parent widget.

        This is a helper methode for the commands.

        :return: None
        """

        self.destroy()


class FilterChoiceFrame(Frame):
    """
    Frame containing UI elements to choose a filter from a list.

    The `FilterChoiceFrame` provides a selection interface for available filters,
    allowing the user to pick which filter to apply or edit. It also enables combining
    a main filter with multiple sub-filters for data analysis.

    Attributes:
        analyzing_return_function (Callable | None): Optional function that will be called with the result
        of the analysis.
        all_filter_dict (dict[int, str]): Dictionary mapping filter IDs to filter names.
        all_filter_name_list (list[str]): List of all available filter names.
        main_frame (Frame): Container for primary controls.
        wrapper_scroll_frame (Frame): Container holding the scrollable sub-filter section.
        scroll_frame (ScrollFrame): Scrollable frame for displaying sub-filters.
        sub_filter_frame (Frame): Internal frame within the scroll view where sub-filters are placed.
        main_filter_combobox (Combobox): Dropdown to select the main filter.
        main_filter_combobox_textlabel (Label): Label for the main filter dropdown.
        btn_add_sub (Button): Button to add a new sub-filter to the list.
        btn_analyze (Button): Button to trigger filter combination and analysis.
        _is_analyzing (bool): Prevents re-entry during analysis processing.
        _sub_filter_index (int): Tracks the position of the next sub-filter for grid layout.
        _free_grid_sub_filter_list (list[tuple[int, int]]): Tracks reusable positions in the grid layout
        for removed sub-filters.
    """

    def __init__(self, parent, *args, **kwargs):
        """
        Initializes the `FilterChoiceFrame`.

        Sets up UI elements including main filter selection, sub-filter list with scroll support,
        and buttons for adding sub-filters or performing analysis.

        :param parent: Widget (The parent widget in which this frame is placed.)
        :return: None
        """

        super().__init__(parent, *args, **kwargs)

        self._is_analyzing = False
        self.analyzing_return_function = None
        filter_list = DatabaseFilter.get_all_filter()
        self.all_filter_dict = {fil.id: fil.name for fil in filter_list}
        self.all_filter_name_list = list(self.all_filter_dict.values())

        self.main_frame = Frame(self)
        self.wrapper_scroll_frame = Frame(self)
        self.scroll_frame = ScrollFrame(self.wrapper_scroll_frame, scrollbar_position="bottom", canvas_height=237)
        self.sub_filter_frame = self.scroll_frame.inner_frame
        self._sub_filter_index = 0
        self._free_grid_sub_filter_list = []

        self.main_filter_combobox = Combobox(self.main_frame, values=self.all_filter_name_list, state="readonly")
        self.main_filter_combobox_textlabel = tb.Label(self.main_frame, text="Main filter:")
        self.btn_add_sub = tb.Button(self.main_frame, text="Add sub filter", command=self._new_subfilter)
        self.btn_analyze = tb.Button(self.main_frame, text="Combine & Analyze", command=self._analyze)

        self.columnconfigure(0, weight=0, minsize=100)
        self.columnconfigure(1, weight=1)
        self.main_frame.grid(column=0, row=0, sticky="nsew")
        self.wrapper_scroll_frame.grid(column=1, row=0, sticky="ew")
        self.wrapper_scroll_frame.grid_propagate(False)
        self.scroll_frame.pack(fill="both", expand=False)

        self.main_filter_combobox_textlabel.pack(anchor="w", pady=(5,0), padx=3)
        self.main_filter_combobox.pack(anchor="w", pady=(0,5), padx=3)
        self.btn_add_sub.pack(anchor="w", pady=5, padx=3)
        self.btn_analyze.pack(anchor="w", pady=5, padx=3)

    def set_analyzing_return_function(self, function) -> None:
        """
        Sets the function to be called when analysis is completed.

        This function will receive the resulting combined DataFrame from the analysis.

        :param function: Callable (Function that accepts the final DataFrame as a parameter.)
        :return: None
        """

        self.analyzing_return_function = function

    def _new_subfilter(self) -> None:
        """
        Creates and places a new `SubFilterFrame` into the scroll area.

        Calculates the next available row/column based on existing sub-filters or reuses
        a previously freed grid position.

        :return: None
        """

        sf = SubFilterFrame(self.sub_filter_frame)
        sf.bind("<Destroy>", self._sub_destroyed)

        if len(self._free_grid_sub_filter_list) > 0:
            row, column = self._free_grid_sub_filter_list.pop(0)
        else:
            row = self._sub_filter_index % 2
            column = (self._sub_filter_index) // 2
            self._sub_filter_index += 1
        sf._row = row
        sf._column = column
        sf.grid(row=row, column=column)

    def _sub_destroyed(self, event) -> None:
        """
        Callback triggered when a `SubFilterFrame` is destroyed.

        Frees its grid position for reuse by a future sub-filter.

        :param event: Event (Destruction event from the widget.)
        :return: None
        """

        self._free_grid_sub_filter_list.append((event.widget._row, event.widget._column))

    def _get_main_filter(self) -> DatabaseFilter:
        """
        Retrieves the currently selected main filter from the combobox.

        Validates that a selection was made, and fetches the corresponding filter from the database.

        :return: DatabaseFilter (The selected main filter object.)
        :raises FormValidationError: If no filter is selected in the combobox.
        """

        filter_index = self.main_filter_combobox.current()
        if filter_index == -1:
            raise FormValidationError("No main filter chosen")

        filter_id = list(self.all_filter_dict)[filter_index]
        return DatabaseFilter.get_filter_by_id(filter_id)

    def _analyze(self) -> None:
        """
        Combines the main filter with selected sub-filters and triggers the analysis.

        This method prevents re-entrancy during execution using `_is_analyzing`, gathers all sub-filter
        selections, and combines them with the selected main filter. The result is passed to the
        configured callback function if available.

        :return: None
        """

        if self._is_analyzing:
            return
        else:
            self._is_analyzing= True
            sub_filter_list = []  # Fills with list[list[filter, bool]]
            for sub in self.sub_filter_frame.winfo_children():
                if isinstance(sub, SubFilterFrame):
                    fil_id, add_it = sub.get_sub_filter()
                    fil = DatabaseFilter.get_filter_by_id(fil_id)
                    sub_filter_list.append([fil, add_it])

            main_filter = self._get_main_filter()
            main_df = DatabaseFilter.combine_filters(main_filter, sub_filter_list)

            self.after(1000, lambda : setattr(self, '_is_analyzing', False))

            if self.analyzing_return_function is not None:
                self.analyzing_return_function(main_df)


class SubFilterFrame(Frame):
    """
    Frame for editing sub-filters or nested filter criteria.

    A `SubFilterFrame` represents a portion of a filter (for example, a sub-condition).
    It provides UI elements to edit sub-filter parameters and integrates with the main filter frame.

    Attributes:
        use_add (bool): Indicates if the sub-filter is in 'combine' (True) or 'reduce' (False) mode.
        change_type_btn (Button): Button to toggle between combine and reduce logic.
        sub_label (Label): Label indicating this is a sub-filter field.
        sub_combobox (Combobox): Dropdown to select the sub-filter.
        delete_btn (Button): Button to remove this sub-filter frame.
        _subfilter_name_var (StringVar): Placeholder for potential name binding (unused directly here).
        _sub_change_var (StringVar): Tracks the current mode for the sub-filter logic.
        _all_filter_dict (dict[int, str]): Maps filter IDs to names for selection.
        _all_filter_name_list (list[str]): List of all filter names for the dropdown.
    """

    def __init__(self, parent, *args, **kwargs):
        """
        Initializes the `SubFilterFrame`.

        Sets up UI components for selecting a filter, toggling logic between combine/reduce,
        and deleting the frame. Prepares filter list for dropdown selection.

        :param parent: Widget (The parent widget where this frame will be placed.)
        :return: None
        """

        super().__init__(parent, borderwidth=1, relief="raised", *args, **kwargs)
        self._subfilter_name_var = StringVar()
        self._sub_change_var = StringVar()
        self.use_add = True
        self._sub_change_var.set("COMBINE")
        filter_list = DatabaseFilter.get_all_filter()
        self._all_filter_dict = {fil.id : fil.name for fil in filter_list}
        self._all_filter_name_list = list(self._all_filter_dict.values())

        self.change_type_btn = tb.Button(self, textvariable=self._sub_change_var,
                                         command=self.change_sub_connector, bootstyle="success")
        self.sub_label = tb.Label(self, text="Subfilter:")
        self.sub_combobox = Combobox(self, values=self._all_filter_name_list, state="readonly")
        self.sub_combobox.bind("<MouseWheel>", lambda e: "break")
        self.delete_btn = tb.Button(self, text="X", bootstyle="danger")
        self.delete_btn.bind("<Button-1>", self.delete_sub_filter)

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=0)

        self.sub_label.grid(row=0, column=0, padx=2, pady=(4,8))
        self.sub_combobox.grid(row=1, column=0, padx=5, sticky="w")
        self.change_type_btn.grid(row=2, column=0, padx=5, pady=5)
        self.delete_btn.place(relx=1, rely=0, anchor="ne")

    def change_sub_connector(self) -> None:
        """
        Toggles the logical connector type between "COMBINE" and "REDUCE".

        Updates the UI to reflect the current state, and modifies `use_add` accordingly.

        :return: None
        """

        if self._sub_change_var.get() == "COMBINE":
            self._sub_change_var.set("REDUCE")
            self.change_type_btn.configure(bootstyle="danger")
            self.use_add = False
        else:
            self._sub_change_var.set("COMBINE")
            self.change_type_btn.configure(bootstyle="success")
            self.use_add = True

    def delete_sub_filter(self, event) -> None:
        """
        Destroys the current sub-filter frame.

        This is typically triggered by a user clicking the delete button.

        :param event: Event (The button click event that triggered this action.)
        :return: None
        """

        self.destroy()

    def get_sub_filter(self) -> tuple[int, bool] | None:
        """
        Retrieves the selected filter ID and logical connector state.

        Used to gather sub-filter data for combining with a main filter.
        If no selection is made, returns None.

        :return: tuple[int, bool] | None (The filter ID and whether it should be added
        (True = combine, False = reduce).)
        """

        filter_index = self.sub_combobox.current()
        if filter_index == -1:
            return

        filter_id = list(self._all_filter_dict)[filter_index]

        return filter_id, self.use_add


class AnalysisFrame(Frame):
    """
    Frame that encapsulates the analysis view for filter results.

    The `AnalysisFrame` contains charts, tables, or other visualization components
    that display the outcome of applying a filter. It manages layout and updating
    of these analytical components.

    Attributes:
        vdf (ViperDF | None): The analyzed dataset used for visualizations.
        main_plot_frame (MainPlotFrame): Frame showing the main visualization.
        app_plot_frame (AppPlotFrame): Frame for application-specific visual output.
        label_plot_frame (LabelPlotFrame): Frame for label-based output or insights.
    """

    def __init__(self, parent, *args, **kwargs):
        """
        Initializes the `AnalysisFrame`.

        Configures the grid layout and embeds all subframes used for visualization.
        Each subframe is placed in a distinct region of the layout.

        :param parent: Widget (The parent widget in which this frame is placed.)
        :return: None
        """

        super().__init__(parent, *args, **kwargs)

        self.vdf = None
        self.rowconfigure(0, weight=2)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.main_plot_frame = MainPlotFrame(self)
        self.main_plot_frame.grid(row=0, column=0, columnspan=2, sticky="nesw")
        self.main_plot_frame.grid_propagate(False)

        self.app_plot_frame = AppPlotFrame(self)
        self.app_plot_frame.grid(row=1, column=0, sticky="nesw")
        self.app_plot_frame.grid_propagate(False)
        self.label_plot_frame = LabelPlotFrame(self)
        self.label_plot_frame.grid_propagate(False)
        self.label_plot_frame.grid(row=1, column=1, sticky="nesw")

    def add_vdf_to_show(self, vdf: DataFrame | ViperDF) -> None:
        """
        Adds a `ViperDF` or `DataFrame` for analysis and visualization.

        If a `DataFrame` is provided, it is converted to a `ViperDF` instance and analyzed.
        The resulting `ViperDF` is stored and passed to the visualization subframes.

        :param vdf: DataFrame | ViperDF (The data to be analyzed and visualized.)
        :return: None
        :raises TypeError: If the input is not a `DataFrame` or `ViperDF`.
        """

        if isinstance(vdf, ViperDF):
            new_vdf = vdf
        elif isinstance(vdf, DataFrame):
            new_vdf = ViperDF(name="analysis", main_df=vdf)
            new_vdf.analyze().plot()
        else:
            raise TypeError("Unsupported type. Not [ViperDF, DataFrame]")
        self.vdf = new_vdf
        self.update_frames()

    def update_frames(self) -> None:
        """
        Updates all plot subframes with the current `ViperDF`.

        Each subframe receives the current analyzed dataset to refresh its visual content.

        :return: None
        """

        if self.vdf is not None:
            self.main_plot_frame.add_vdf(self.vdf)
            self.app_plot_frame.add_vdf(self.vdf)
            self.label_plot_frame.add_vdf(self.vdf)


class ImageFrame(Frame):
    """
    Frame that displays an image (typically a plot snapshot) within the GUI.

    The `ImageFrame` holds a `tk.PhotoImage` (or similar image object) and is used to show
    static images of charts or graphs. It provides functionality to set a click callback
    on the image.

    Attributes:
        showing_image (PhotoImage): The image currently being displayed.
        _original_tk_photoimage (PhotoImage): The unscaled original image.
        old_parent_width (int | None): Stores the last known width for resize comparison.
        old_parent_height (int | None): Stores the last known height for resize comparison.
        image_label (Label): Label widget used to display the image.
        _on_click_function (Callable | None): Optional callback to execute when the image is clicked.
    """

    def __init__(self, parent, tk_photoimage: PhotoImage, on_click = None, *args, **kwargs):
        """
        Initializes the `ImageFrame`.

        Sets up the image display and binds resize and click events.
        Stores the original image and prepares it for dynamic resizing.

        :param parent: Widget (The parent widget where this frame is placed.)
        :param tk_photoimage: PhotoImage (The image to display.)
        :param on_click: Callable | None (Optional function to be called on image click.)
        :return: None
        """

        super().__init__(parent, *args, **kwargs)

        self.showing_image = tk_photoimage
        self._original_tk_photoimage = tk_photoimage
        self.old_parent_width = None
        self.old_parent_height = None

        self.image_label = tb.Label(self)
        self.image_label.place(relx=0.5, rely=0.5, anchor="center")

        self._on_click_function = on_click

        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self.on_click)
        self.image_label.bind("<Button-1>", self.on_click)

    def set_on_click(self, on_click) -> None:
        """
        Registers a callback to be executed when the image is clicked.

        Attaches the provided function to the image such that when the user clicks on it,
        the function is invoked. Useful for toggling overlays or expanding the image.

        :param on_click: Callable (The function to call when the image is clicked.)
        :return: None
        """

        self._on_click_function = on_click

    def on_click(self, event):
        """
        Internal handler for image click events.

        If a callback function is registered, this method invokes it with the click event.

        :param event: Event (Click event from tkinter.)
        :return: None
        """

        if self._on_click_function is None:
            return
        else:
            self._on_click_function(event)

    def _on_resize(self, event=None) -> None:
        """
        Triggered on frame resize events to schedule image rescaling.

        Debounces multiple resize triggers by scheduling the resize with a short delay.

        :param event: Event | None (The tkinter resize event, optional.)
        :return: None
        """

        if hasattr(self, "_resize_job") and self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, self._perform_resize)

    def _perform_resize(self) -> None:
        """
        Performs the actual resizing of the image to fit the parent frame.

        Scales the image proportionally to the frame's height (if smaller than original).
        Updates the image label with the resized image or restores the original image
        if scaling is not needed.

        :return: None
        """

        self.update_idletasks()

        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        if parent_height == self.old_parent_height:
            return

        photo_width = self._original_tk_photoimage.width()
        photo_height = self._original_tk_photoimage.height()

        scale = min(parent_height / photo_height, 1)

        if scale < 1:
            pil = ImageTk.getimage(self._original_tk_photoimage)
            resized_image = pil.resize((int(photo_width * scale), int(photo_height * scale)),
                                       Image.Resampling.LANCZOS)
            self.showing_image = ImageTk.PhotoImage(resized_image)

            self.image_label.config(image=self.showing_image)
            self.old_parent_height = parent_height

        else:
            self.image_label.config(image=self._original_tk_photoimage)
            self.old_parent_height = parent_height


class OverlayFrame(Frame):
    """
    A frame that overlays content on top of other GUI elements (pop-up style).

    `OverlayFrame` acts as a floating container that can be shown or hidden (expanded or shrunk) on demand.
    Widgets should be added to `OverlayFrame.inner_frame` for them to be visible. The frame manages its own
    close button and events to hide itself when focus is lost.

    Attributes:
        _inner_name (str | None): Optional name used for styling or debugging the inner frame.
        _original_master (Widget): The parent widget over which this overlay appears.
        _top_level_master (Widget): The top-level window that contains the overlay.
        inner_frame (Frame): The actual frame displayed as the overlay.
        close_btn (Button): Close button attached to the top-right of the overlay.
        overlay_active (bool): Indicates whether the overlay is currently shown.
    """

    def __init__(self, parent, name: str = None, *args, **kwargs):
        """
        Initializes the overlay frame and its inner content frame.

        :param parent: Widget (The parent widget over which this overlay will appear.)
        :param name: str | None (An optional name for the inner frame, useful for styling or debugging.)
        :param args: Additional positional arguments for the Frame initializer.
        :param kwargs: Additional keyword arguments for the Frame initializer.
        :return: None
        """

        self._inner_name = name
        super().__init__(parent, *args, **kwargs)

        self._original_master = parent
        self._top_level_master = parent.winfo_toplevel()
        if self._inner_name is not None:
            self.inner_frame = Frame(self._top_level_master, name=self._inner_name, bootstyle="dark")
        else:
            self.inner_frame = Frame(self._top_level_master, bootstyle="dark")
        self.close_btn = tb.Button(self.inner_frame, text="X", bootstyle="danger", command=self.shrink)
        self.close_btn.place(relx=1.0, rely=0, anchor="ne")
        self.overlay_active = False

    def _on_click_outside(self, event) -> None:
        """
        Callback that closes the overlay if a click occurs outside of it.

        When the overlay is expanded, this method is bound to global mouse clicks.
        If the click event's coordinates are outside the bounds of the overlay's inner frame,
        the overlay will shrink (hide) itself.

        :param event: Event (Mouse click event.)
        :return: None
        """

        x_pos, y_pos = event.x_root, event.y_root

        left_x = self.inner_frame.winfo_rootx()
        right_x = left_x + self.inner_frame.winfo_width()

        bottom_y = self.inner_frame.winfo_rooty()
        top_y = bottom_y + self.inner_frame.winfo_height()

        if not (left_x <= x_pos <= right_x and  bottom_y <= y_pos <= top_y):
            self.shrink()

    def _on_focus_out(self, event) -> None:
        """
        Callback that closes the overlay when it loses focus.

        If the top-level window containing the overlay loses focus (e.g., user switches to another
        application or dialog), this method ensures the overlay is hidden by calling `shrink()`.

        :param event: Event (Focus-out event.)
        :return: None
        """

        if not self._top_level_master.focus_displayof():
            self.shrink()

    def expand(self, event=None) -> None:
        """
        Displays (expands) the overlay frame.

        Places the inner frame onto the parent window with a predefined relative size and brings it to the front.
        Binds the necessary global events (Escape key, outside clicks, focus out) to allow the overlay to be closed.
        Does nothing if the overlay is already active.

        :param event: Event | None (Optional event that triggered the expansion.)
        :return: None
        """

        if not self.overlay_active:
            self.inner_frame.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.9, anchor="nw")
            self.inner_frame.lift()
            # Maybe in some special cases needed, noted for later:
            # aboveThis=self.top_level_master.winfo_children()[0]

            self.overlay_active = True
            self._top_level_master.bind_all("<Escape>", self.shrink)
            self._top_level_master.bind_all("<Button-1>", self._on_click_outside)
            self._top_level_master.bind("<FocusOut>", self._on_focus_out)

    def shrink(self, event=None) -> None:
        """
        Hides (shrinks) the overlay frame.

        Removes the inner frame from view and unbinds the global events that were set in `expand()`.
        This effectively closes the overlay. Does nothing if the overlay is already inactive.

        :param event: Event | None (Optional event that triggered the shrink.)
        :return: None
        """

        if self.overlay_active:
            self.inner_frame.place_forget()
            self.overlay_active = False
            self._top_level_master.unbind_all("<Escape>")
            self._top_level_master.unbind_all("<Button-1>")
            self._top_level_master.unbind("<FocusOut>")

    def pack(self, *args, **kwargs) -> None:
        """
        Prevents usage of `pack()` on `OverlayFrame`.

        Raises an error to enforce use of `expand()` instead.

        :raises RuntimeError: Always raised when called.
        """

        raise RuntimeError("Use .expand() to make visible.")

    def grid(self, *args, **kwargs) -> None:
        """
        Prevents usage of `grid()` on `OverlayFrame`.

        Raises an error to enforce use of `expand()` instead.

        :raises RuntimeError: Always raised when called.
        """

        raise RuntimeError("Use .expand() to make visible.")

    def place(self, *args, **kwargs) -> None:
        """
        Prevents usage of `place()` on `OverlayFrame`.

        Raises an error to enforce use of `expand()` instead.

        :raises RuntimeError: Always raised when called.
        """

        raise RuntimeError("Use .expand() to make visible.")

    def pack_forget(self, *args, **kwargs) -> None:
        raise RuntimeError("Use .shrink() to make invisible.")

    def grid_forget(self, *args, **kwargs) -> None:
        """
        Prevents usage of `pack_forget()` on `OverlayFrame`.

        Raises an error to enforce use of `shrink()` instead.

        :raises RuntimeError: Always raised when called.
        """

        raise RuntimeError("Use .shrink() to make invisible.")

    def place_forget(self, *args, **kwargs) -> None:
        """
        Prevents usage of `grid_forget()` on `OverlayFrame`.

        Raises an error to enforce use of `shrink()` instead.

        :raises RuntimeError: Always raised when called.
        """

        raise RuntimeError("Use .shrink() to make invisible.")

# class SelectableItem(Frame):
#     """
#     This item can be selected and changes how it looks on selected.
#     it has property that return states and infos.
#     You can grab show_text, internal_value and if selected
#
#     Later will have a way to change its values also ater init.
#     """
#     def __init__(self, parent, text: str = None, internal_value = None
#                  *args, **kwargs):
#
#         super().__init__(parent, *args, **kwargs)
#
#         self.__display_text = text
#         self.__internal_value = internal_value
#         self.__state = False
#         self.__is_clicked = False
#
#         # Override current style so button is not showing
#         style = tb.Style()
#         default_background = style.lookup("TButton", "background")
#         style.map("TButton", background=[
#                 ("active", default_background),
#                 ("pressed", default_background),
#                 ("selected", default_background),
#                 ("focus", default_background),
#             ])
#
#         self.__clickable = tb.Button(self,style=default_background, command=self.__clicked)
#         self.__clickable.pack(fill="both", expand=True)
#
#     def __clicked(self):
#         if self.__is_clicked:
#             return
#         self.__is_clicked = True
#         self.after(300, self.__reset_click_state)
#         self.__toggle_state()
#
#     def __reset_click_state(self):
#         self.__is_clicked = False
#
#
#     def __toggle_state(self):
#         self.event_generate("<<ItemChanged>>", when="tail")
#         if self.__state:
#             self.__state_switch_off()
#         else:
#             self.__state_switch_on()
#
#     def __state_switch_on(self):
#         self.event_generate("<<ItemToggledOn>>", when="tail")
#         self.__state = True
#         # change visuals
#         ...
#
#     def __state_switch_off(self):
#         self.event_generate("<<ItemToggledOff>>", when="tail")
#         self.__state = True
#         # change visuals
#         ...
#
#     @property
#     def display_text(self):
#         return self.__display_text
#
#     @display_text.setter
#     def display_text(self, value: str):
#         if not isinstance(value, str):
#             raise TypeError("Value must be a string.")
#         self.__display_text = value
#
#     @property
#     def value(self):
#         if self.__state:
#             return self.__internal_value if self.__internal_value is not None else self.__display_text
#         else:
#             return None
#
#     @property
#     def state(self):
#         return self.__state
#
#
# class KeySelectorFrame(Frame):
#     """
#     This frame will be initialized with a dict to show the values of each key as label
#     or later other visual widget and the enduser can choose multiple of the values.
#     The button can be bound to a function the programmer gives it.
#     The called function will allways be called with a parameter chosen_keys(tuple).
#
#     """
#     def __init__(self, parent, dict_with_keys:dict, max_choices: int = None, linked_function=None,
#                  button_text: str = None, max_width: int=None, max_height: int = None,
#                  *args, **kwargs):
#
#         super().__init__(parent, *args, **kwargs)
#
#         self.__fields_are_existing = False
#         self.__choice_list = []
#
#         # Call properties for error handeling & logics
#         self.dict_with_keys = dict_with_keys
#         self.max_choices = max_choices
#         # End of property setting
#
#
#
#
#         self._linked_function = linked_function
#         self._button_text = button_text or "Execute"
#         self.execute_button = tb.Button(self, text=self._button_text, command=self.__call_linked_function)
#
#         self.__create_choice_frames()
#
#     def __create_choice_frames(self):
#         self.__fields_are_existing = True
#         # Every choiceframe/button needs to get a showtext value and a internal value (int/str/float)
#         # and should emit a change event & a on/off event
#         ...
#
#     def __update_choice_frames(self) -> list:
#
#         # get  old values
#         old_values = self.choices
#
#         # remove fields
#         for chil in self.winfo_children():
#             if isinstance(chil, Frame):
#                 chil.destroy()
#
#         # set new values
#         self.__key_list = list(self.dict_with_keys.keys())
#         self.__text_list = [str(val) for val in self.dict_with_keys.values()]
#
#         #create new fields
#         self.__create_choice_frames()
#
#         return old_values or None # Case of old_values = []
#
#     def reset_choices(self):
#         self.__choice_list = []
#
#         for chil in self.winfo_children():
#             if isinstance(chil, Frame):
#                 # todo: for every element taht can be choosen reset it to not choosen
#                 ...
#
#     def select_choices_per_key(self, key_list: list|tuple):
#         if not isinstance(key_list, (list, tuple))
#             raise TypeError("'key_list' must be a list or tuple.")
#         if len(key_list) == 0:
#             return
#         if not all(isinstance(val, (str, int, float)) for val in key_list):
#             raise TypeError("All values in 'key_list' have to be str, int or float")
#
#         for choice_key in key_list:
#             # todo: check for keys in the labels/frames and set them to choosen
#             ...
#
#     def __call_linked_function(self):
#         if self._linked_function is not None:
#             # TODO: remove temp to test
#             self.__choice_list = (1, 2, 3)  # ("zoom", "boom", "truth)
#
#             all_keys = self.choices
#             self._linked_function(all_keys)
#
#     @property
#     def choices(self):
#         return self.__choice_list
#
#     @property.setter
#     def linked_function(self, linked_function):
#         if not callable(linked_function):
#             raise TypeError("linked_function must be callable.")
#         self._linked_function = linked_function
#
#     @property
#     def key_list(self) -> list:
#         return self.__key_list
#
#     @property
#     def text_list(self) -> list:
#         return self.__text_list
#
#     @property
#     def dict_with_keys(self) -> list:
#         return self._dict_with_keys
#
#     @property.setter
#     def dict_with_keys(self, dict_with_keys:dict):
#         if not isinstance(dict_with_keys, dict):
#             raise TypeError("dict_with_keys must be an instance of dict")
#
#         for val in dict_with_keys.values():
#             if not isinstance(val, (int, float, str)):
#                 raise TypeError("All values of 'dict_with_keys' must be int, float or str")
#
#         self._dict_with_keys = dict_with_keys
#
#         if self.__fields_are_existing:
#             self.__update_choice_frames()
#         else:
#             # first init of text & keys
#             self.__key_list = list(self.dict_with_keys.keys())
#             self.__text_list = [str(val) for val in self.dict_with_keys.values()]
#
#     @property
#     def button_text(self) -> str:
#         return self._button_text
#
#     @property.setter
#     def button_text(self, text:str):
#         if not isinstance(text, str):
#             raise TypeError("Button text must be a string.")
#         self._button_text = text
#
#         if hasattr(self, "execute_button"):
#             self.execute_button.config(text=text)
#
#     @property
#     def max_choices(self) -> int:
#         return self.__max_choices
#
#     @property.setter
#     def max_choices(self, max_choices: int):
#         if not isinstance(max_choices, int):
#             raise TypeError("'max_choices' has to be a int")
#         self.__max_choices = max_choices
#
#         if len(self.choices) > max_choices:
#             self.reset_choices()


class MainPlotFrame(Frame):
    """
    Frame that holds the main combined plot of the application.

    `MainPlotFrame` manages a composite view that includes multiple subplots or chart areas
    (e.g., an activity timeline and summary charts). It organizes the main plot area and side
    info panel, and handles dynamic updates when data changes.

    Attributes:
        vdf (ViperDF | None): The data object used for generating plots.
        main_figure (Figure | None): The current matplotlib figure for the main plot.
        info_frame (Frame): Frame on the left displaying info labels.
        main_plot_image_frame (ImageFrame | Frame): Frame displaying the main plot as an image.
        overlay_frame (OverlayFrame): Overlay panel containing additional interactive elements.
        overlay_pack_frame (Frame): Internal frame used to pack overlay widgets.
        plot_label_frame (Frame): Container for label-related controls inside overlay.
        label_frame_title (Label): Title label for the label selector section.
        refresh_label_btn (Button): Button to trigger refresh of available labels.
        plot_canvas (FigureCanvasTkAgg | None): Canvas for displaying the live matplotlib figure.
        plot_widget (Widget | None): The tkinter widget associated with the matplotlib figure.
    """

    def __init__(self, parent, viper_df: ViperDF = None, *args, **kwargs):
        """
        Initializes the `MainPlotFrame`.

        Sets up layout and all interactive or visual components required to display
        the main analytical plot and label-based overlays.

        :param parent: Widget (The parent widget this frame belongs to.)
        :param viper_df: ViperDF | None (Optional preloaded data object to initialize the plot.)
        :return: None
        """

        super().__init__(parent, *args, **kwargs)
        self.vdf = viper_df

        self.main_figure = None

        self.columnconfigure(index=0, weight=1)
        self.columnconfigure(index=1, weight=3)

        self.info_frame = Frame(self)
        self.info_frame.grid(column=0, row=0, sticky="nsew")
        self.main_plot_image_frame = Frame(self, name="placeholder")
        self.main_plot_image_frame.grid_propagate(False)
        self.main_plot_image_frame.grid(column=1, row=0, sticky="nsew")

        self.overlay_frame = OverlayFrame(self)
        self.overlay_pack_frame = self.overlay_frame.inner_frame

        # TODO: pack on the left lower side in frame
        self.plot_label_frame = Frame(self.overlay_pack_frame)
        self.label_frame_title = tb.Label(self.plot_label_frame, text="Choose Labels (max 5)")
        # todo: foreach label create a checkbox, max 3 rows,
        #  on the right top fixed a refresh button (like overlay)
        # TODO: function for btn
        self.refresh_label_btn = tb.Button(self.plot_label_frame, text="Refresh")

        self.plot_canvas = None
        self.plot_widget = None

    def add_vdf(self, vdf: ViperDF) -> None:
        """
        Assigns a ViperDF data object to this frame and refreshes the plot.

        Validates that the provided object is of type `ViperDF`, stores it,
        and calls `update_main_plot()` to render the new content.

        :param vdf: ViperDF (The data object containing analysis results for plotting.)
        :return: None
        :raises TypeError: If the provided `vdf` is not an instance of ViperDF.
        """

        if not isinstance(vdf, ViperDF):
            raise TypeError("Unsupported type. Not a ViperDF")

        self.vdf = vdf
        self.update_main_plot()

    def update_main_plot(self) -> None:
        """
        Generates or refreshes the main combined plot.

        Destroys any existing plot widget and replaces it with a new one reflecting
        the current data (`self.vdf`). The updated plot is embedded in the overlay area.
        Also initializes a new static image fallback with click support.

        :return: None
        """

        if self.plot_widget:
            self.plot_widget.destroy()
            self.plot_widget = None
        if self.plot_canvas:
            self.plot_canvas = None

        self.main_figure = self.vdf.get_main_plot()
        self.plot_canvas = FigureCanvasTkAgg(self.main_figure, master=self.overlay_pack_frame)
        self.plot_widget = self.plot_canvas.get_tk_widget()
        self.plot_widget.place(relx=0.5, rely=0.5, anchor="center")

        if self.main_plot_image_frame:
            self.main_plot_image_frame.destroy()
            self.main_plot_image_frame = None
        self.main_plot_image_frame = ImageFrame(self, tk_photoimage=self.vdf.image_main_plot)
        self.main_plot_image_frame.grid_propagate(False)
        self.main_plot_image_frame.grid(column=1, row=0, sticky="nsew")
        self.main_plot_image_frame.set_on_click(self.overlay_frame.expand)

        self.update_info_area()

    def update_info_area(self) -> None:
        """
        Refreshes the info section on the left of the plot.

        Clears any existing content in `info_frame` and populates it with key-value
        pairs returned by `vdf.main_infos()`. Automatically handles wrapping of long labels.

        :return: None
        """

        for child in self.info_frame.winfo_children():
            child.destroy()

        for i, item in enumerate(self.vdf.main_infos()):
            self.info_frame.rowconfigure(i, weight=0)
            row_frame = Frame(self.info_frame)
            row_frame.grid(row=i, column=0, sticky="nsew")
            tb.Label(row_frame, text=item[0], font=("TkDefaultFont", 10))\
                .grid(row=0, column=0, pady=1, sticky="w")

            left_text = tb.Label(row_frame, text=item[1], font=("TkDefaultFont", 10, "bold"))
            if len(item[1]) <= 20:
                left_text.grid(row=0, column=1, pady=1, sticky="w")
            else:

                left_text.grid(row=1, column=0, pady=1, sticky="w")

class AppPlotFrame(Frame):
    """
    Frame that holds the application-specific usage plot.

    `AppPlotFrame` displays a chart focusing on application usage data
    (either a pie chart or bar chart of app usage). It manages toggling between
    chart types and contains an `ImageFrame` to show a snapshot of the plot.

    Attributes:
        vdf (ViperDF | None): The data object used for generating app plots.
        app_figure (Figure | None): The currently active app usage plot figure.
        image_frame (ImageFrame | Frame): Frame used to display the static snapshot of the plot.
        overlay_frame (OverlayFrame): Overlay container for displaying live interactive plots.
        overlay_pack_frame (Frame): The internal widget container for the overlay plot area.
        overlay_switch_plot_type_btn (Button | None): Button in the overlay for toggling plot type.
        plot_widget (Widget | None): Widget used to render the matplotlib plot.
        plot_canvas (FigureCanvasTkAgg | None): Canvas for embedding the matplotlib figure.
        plot_type (str): Currently selected plot type ("Pie" or "Vbar").
        switch_plot_type_btn (Button | None): Toggle button in main UI for switching plot types.
    """

    def __init__(self, parent, viper_df: ViperDF = None, *args, **kwargs):
        """
        Initializes the `AppPlotFrame`.

        Sets up the layout, image frame, overlay system, and default plot configuration.
        If a `ViperDF` is provided, an initial plot is rendered automatically.

        :param parent: Widget (The parent container for this frame.)
        :param viper_df: ViperDF | None (Optional data object for initialization.)
        :return: None
        """

        super().__init__(parent, *args, **kwargs)

        self.vdf = viper_df
        self.app_figure = None
        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=1)
        self.image_frame = Frame(self, name="placeholder")
        self.image_frame.grid_propagate(False)
        self.image_frame.grid(column=0, row=0, sticky="nesw")

        self.overlay_frame = OverlayFrame(self, name="app_plot")
        self.overlay_pack_frame = self.overlay_frame.inner_frame
        self.overlay_switch_plot_type_btn = None

        self.plot_widget = None
        self.plot_canvas = None

        self.plot_type = "Pie"
        self.switch_plot_type_btn = None
        self.switch_plot_type_overlay_btn = None

        if isinstance(self.vdf, ViperDF):
            self.update_app_plot()

    def add_vdf(self, vdf: ViperDF) -> None:
        """
        Sets the `ViperDF` data for this frame and triggers the initial app plot render.

        :param vdf: ViperDF (The data object with application usage analysis.)
        :return: None
        :raises TypeError: If `vdf` is not a `ViperDF` instance.
        """

        if not isinstance(vdf, ViperDF):
            raise TypeError("Unsupported type. Not a ViperDF")

        self.vdf = vdf
        self.update_app_plot()

    def update_app_plot(self) -> None:
        """
        Updates the application usage plot displayed in this frame.

        Clears existing plot widgets and creates a new plot based on `plot_type`.
        Uses the `ViperDF` to retrieve either a pie chart or bar chart figure and displays it.
        Updates both the interactive overlay and static image view, and refreshes toggle buttons.

        :return: None
        """

        if self.plot_widget:
            self.plot_widget.destroy()
            self.plot_widget = None
        if self.plot_canvas:
            self.plot_canvas = None

        self.app_figure = self.vdf.get_pie_apps() if self.plot_type == "Pie" else self.vdf.get_vbar_apps()
        self.plot_canvas = FigureCanvasTkAgg(self.app_figure, master=self.overlay_pack_frame)
        self.plot_widget = self.plot_canvas.get_tk_widget()
        self.plot_widget.place(relx=0.5, rely=0.5, anchor="center")
        if self.overlay_switch_plot_type_btn:
            self.overlay_switch_plot_type_btn.destroy()
            self.overlay_switch_plot_type_btn = None
        self.overlay_switch_plot_type_btn = tb.Button(self.overlay_pack_frame, text=self.plot_type, command=self.switch_plot_type)
        self.overlay_switch_plot_type_btn.place(relx=0, rely=0, anchor="nw")

        if self.image_frame:
            self.image_frame.destroy()
            self.image_frame = None
        self.app_image = self.vdf.image_app_pie_plot if self.plot_type == "Pie" else self.vdf.image_app_vbar_plot
        self.image_frame = ImageFrame(self, tk_photoimage=self.app_image)
        self.image_frame.grid_propagate(False)
        self.image_frame.grid(column=0, row=0, sticky="nsew")
        self.image_frame.set_on_click(self.overlay_frame.expand)

        if self.switch_plot_type_btn:
            self.switch_plot_type_btn.destroy()
            self.switch_plot_type_btn = None
        self.switch_plot_type_btn = tb.Button(self, text=self.plot_type, command=self.switch_plot_type)
        self.switch_plot_type_btn.place(relx=0, rely=0, anchor="nw")

    def switch_plot_type(self) -> None:
        """
        Toggles the plot type between pie chart and vertical bar chart.

        Switches `plot_type` and then calls `update_app_plot()` to reflect the change in the UI.

        :return: None
        """

        if self.plot_type == "Pie":
            self.plot_type = "Vbar"
        else:
            self.plot_type = "Pie"
        self.update_app_plot()

    
class LabelPlotFrame(Frame):
    """
    Frame that holds the label-specific usage plot.

    `LabelPlotFrame` displays a chart focusing on label usage data (pie or bar chart).
    It includes an overlay for interactive visualizations and manages toggling between
    chart types to provide flexible data representation.

    Attributes:
        vdf (ViperDF | None): The data object used for generating label plots.
        label_figure (Figure | None): The active label usage plot figure.
        image_frame (ImageFrame | Frame): Frame displaying a static image of the plot.
        overlay_frame (OverlayFrame): Interactive overlay container for displaying the full plot.
        overlay_pack_frame (Frame): Internal frame within the overlay used for layout.
        overlay_switch_plot_type_btn (Button | None): Button for toggling plot type inside overlay.
        plot_widget (Widget | None): Tkinter widget rendering the Matplotlib plot.
        plot_canvas (FigureCanvasTkAgg | None): Canvas for embedding the plot figure.
        plot_type (str): The current plot type ("Pie" or "Vbar").
        switch_plot_type_btn (Button | None): Toggle button shown with the image for switching chart type.
    """

    def __init__(self, parent, viper_df: ViperDF = None, *args, **kwargs):
        """
        Initializes the `LabelPlotFrame`.

        Sets up the layout, image container, and overlay structure. If a valid
        `ViperDF` is provided, the label plot is generated immediately.

        :param parent: Widget (The parent widget in which this frame is placed.)
        :param viper_df: ViperDF | None (Optional data object to initialize the chart.)
        :return: None
        """

        super().__init__(parent, *args, **kwargs)

        self.vdf = viper_df
        self.label_figure = None
        self.columnconfigure(index=0, weight=1)
        self.rowconfigure(index=0, weight=1)
        self.image_frame = Frame(self, name="placeholder")
        self.image_frame.grid_propagate(False)
        self.image_frame.grid(column=0, row=0, sticky="nesw")

        self.overlay_frame = OverlayFrame(self, name="label_plot")
        self.overlay_pack_frame = self.overlay_frame.inner_frame
        self.overlay_switch_plot_type_btn = None

        self.plot_widget = None
        self.plot_canvas = None

        self.plot_type = "Pie"
        self.switch_plot_type_btn = None
        self.switch_plot_type_overlay_btn = None

        if isinstance(self.vdf, ViperDF):
            self.update_label_plot()

    def add_vdf(self, vdf: ViperDF) -> None:
        """
        Associates a `ViperDF` data object with this frame and, if valid, generates the initial label usage plot.

        :param vdf: ViperDF (The data object with label usage analysis results.)
        :return: None
        :raises TypeError: If `vdf` is not an instance of ViperDF.
        """

        if not isinstance(vdf, ViperDF):
            raise TypeError("Unsupported type. Not a ViperDF")

        self.vdf = vdf
        self.update_label_plot()

    def update_label_plot(self) -> None:
        """
        Updates the label usage plot displayed in this frame.

        Destroys any existing chart widgets and generates a new one based on `plot_type`.
        Pulls the correct plot figure from the `ViperDF` and displays both a live chart in the overlay
        and a static image fallback in the main frame. Refreshes plot type buttons accordingly.

        :return: None
        """

        if self.plot_widget:
            self.plot_widget.destroy()
            self.plot_widget = None
        if self.plot_canvas:
            self.plot_canvas = None

        self.label_figure = self.vdf.get_pie_labels() if self.plot_type == "Pie" else self.vdf.get_vbar_labels()
        self.plot_canvas = FigureCanvasTkAgg(self.label_figure, master=self.overlay_pack_frame)
        self.plot_widget = self.plot_canvas.get_tk_widget()
        self.plot_widget.place(relx=0.5, rely=0.5, anchor="center")
        if self.overlay_switch_plot_type_btn:
            self.overlay_switch_plot_type_btn.destroy()
            self.overlay_switch_plot_type_btn = None

        self.update_idletasks()
        self.overlay_switch_plot_type_btn = tb.Button(self.overlay_pack_frame, text=self.plot_type, command=self.switch_plot_type)
        self.overlay_switch_plot_type_btn.place(relx=0, rely=0, anchor="nw")

        if self.image_frame:
            self.image_frame.destroy()
            self.image_frame = None
        self.label_image = self.vdf.image_label_pie_plot if self.plot_type == "Pie" else self.vdf.image_label_vbar_plot
        self.image_frame = ImageFrame(self, tk_photoimage=self.label_image)
        self.image_frame.grid_propagate(False)
        self.image_frame.grid(column=0, row=0, sticky="nsew")
        self.image_frame.set_on_click(self.overlay_frame.expand)

        if self.switch_plot_type_btn:
            self.switch_plot_type_btn.destroy()
            self.switch_plot_type_btn = None
        self.switch_plot_type_btn = tb.Button(self, text=self.plot_type, command=self.switch_plot_type)
        self.switch_plot_type_btn.place(relx=0, rely=0, anchor="nw")

    def switch_plot_type(self) -> None:
        """
        Switches the label plot between pie chart and vertical bar chart representations.

        Changes the `plot_type` attribute from "Pie" to "Vbar" or vice versa,
        then calls `update_label_plot()` to redraw the chart using the new format.

        :return: None
        """

        if self.plot_type == "Pie":
            self.plot_type = "Vbar"
        else:
            self.plot_type = "Pie"
        self.update_label_plot()


class LabelFrame(Frame):
    """
    Frame for creating, editing, and managing labels.

    This frame provides functionality to:
    - Define labels with associated conditions.
    - Save labels to a database.
    - Delete labels from the application.

    Each label can be configured with conditions that determine when it applies.

    Attributes:
        label_name (StringVar): Text variable for the label name entry field.
        manually_var (BooleanVar): Checkbox state indicating if the label is set manually.
        active_var (BooleanVar): Checkbox state indicating if the label is currently active.
        creation_datetime (datetime): Timestamp of label creation.
        flex (FlexFrame): Main container for all label UI components.
        label_entry (Entry): Text entry field for the label name.
        all_conditions_list_frame (ConditionListFrame): Container managing the list of conditions tied to the label.
        _label (Label | None): The associated label object (if any).
    """

    def __init__(self, parent, label: Label | None = None, *args, **kwargs):
        """
        Initializes the `LabelFrame`.

        Sets up the label editing interface, including input fields, checkboxes, creation timestamp,
        and an optional list of conditions. If a label is provided, its data is preloaded.

        :param parent: Widget (The parent widget where this frame will be placed.)
        :param label: Label | None (Optional label object to populate the frame.)
        :return: None
        """
        # TODO: init stlyes via style manager
        # TODO: Styles and such infos need to be initialized properly with a function or on the gui_controller
        # FIXME: styl needs to be created inside the mainloop anyhow
        # Style().configure("AndConditionList.TFrame", borderwidth=2, relief="solid", background="purple")
        # Style().configure("OrConditionList.TFrame", borderwidth=2, relief="solid", background="cyan")

        super().__init__(parent, *args, **kwargs)
        if label is None:
            self._label = None
            self.label_name = StringVar(value="")
            self.manually_var = BooleanVar(value=False)
            self.active_var = BooleanVar(value=False)
            self.creation_datetime = datetime.now()
        else:
            self._label = label
            self.label_name = StringVar(value=label.name)
            self.manually_var = BooleanVar(value=label.manually)
            self.active_var = BooleanVar(value=label.active)
            self.creation_datetime = label.creation_datetime

        self.flex = FlexFrame(self, title_var=self.label_name)
        self.flex.pack(fill=BOTH, expand=True)

        # Upper Frame for Label Name, Manually, Active Checkboxes, and Datetime Label
        upper_frame = Frame(self.flex.inner_frame, name="upper")
        upper_frame.pack(fill="x", padx=(5, 0), pady=(5, 0))

        # Entry field for "Label name"
        tb.Label(upper_frame, text="Label name:").grid(row=0, column=0, padx=(5, 0), pady=(5, 0), sticky="w")
        self.label_entry = tb.Entry(upper_frame, textvariable=self.label_name)
        self.label_entry.grid(row=0, column=1, padx=(5, 0), pady=(5, 0), sticky="ew")

        # Checkbox for "Manually"
        manually_checkbox = tb.Checkbutton(upper_frame, text="Manually", variable=self.manually_var, command=self.toggle_conditions)
        manually_checkbox.grid(row=0, column=2, padx=(5, 0), pady=(5, 0))

        # Checkbox for "Active"
        active_checkbox = tb.Checkbutton(upper_frame, text="Active", variable=self.active_var)
        active_checkbox.grid(row=0, column=3, padx=(5, 0), pady=(5, 0))

        # Datetime creation
        formatted_date = self.creation_datetime.strftime("%d.%m.%y - %H:%M")
        datetime_label = tb.Label(upper_frame, text=f"Created {formatted_date}")
        datetime_label.grid(row=0, column=4, padx=(5, 0), pady=(5, 0))

        # Delete Button
        delete_btn = tb.Button(self.flex.inner_frame, text="Del", bootstyle="danger")
        delete_btn.place(relx=1.0, rely=0, x=-55)

        delete_btn.bind("<Button-1>", self.delete_label)

        conds_list = None
        if hasattr(self._label, "condition_list"):
            conds_list = self._label.condition_list
        self.all_conditions_list_frame = ConditionListFrame(self.flex.inner_frame, condition_list=conds_list, top_list=True)

        if self.manually_var.get():
            self.toggle_conditions()

    def toggle_conditions(self) -> None:
        """
        Toggles the enabled/disabled state of the condition list associated with the label.

        When disabled, the user cannot modify the conditions tied to the label.

        :return: None
        """

        self.all_conditions_list_frame.toggle_state()

    def save_label_to_db(self) -> None:
        """
        Saves the label and its associated conditions to the database.

        If the label is new, a new record is created. If it's an existing label, the record
        is updated with new data. Validation is performed before saving.

        :return: None
        :raises FormValidationError: If required fields are empty or invalid.
        """

        # FIXME: TO fast interaction with save fucntion = in multiple entry creation
        lab_name = self.label_name.get()
        if lab_name == "":
            raise FormValidationError(faulty_fields="label name")
        lab_manually = self.manually_var.get()
        lab_active = self.active_var.get()
        lab_condition_list = None
        if not lab_manually:
            lab_condition_list = self.all_conditions_list_frame.get_as_object()

        if self._label is None:
            Label(lab_name, manually=lab_manually, active=lab_active, condition_list=lab_condition_list)
        else:
            self._label.name = lab_name
            self._label.manually = lab_manually
            self._label.active = lab_active
            self._label.condition_list = lab_condition_list
            self._label.update_in_db()

    def delete_label(self, event) -> None:
        """
        Deletes the label from the database and removes its frame from the GUI.

        If the Shift key is not held, a confirmation prompt is shown. If confirmed (or Shift is held),
        the label is deleted and the system tray is updated.

        :param event: Event (The event triggering the deletion.)
        :return: None
        """

        if not event.state & 0x0001:  # Shift key flag
            result = Messagebox.okcancel(f"Do you want to delete label '{self.label_name.get()}'({
                                            self._label.name if self._label else ""}) ?",
                                         "WARNING! Delete Label", parent=self.master.master)
            if result != "OK":
                return
        from system_tray_manager import SystemTrayManager

        if self._label is not None:
            self._label.delete_in_db()
        SystemTrayManager().update_menu()
        self.destroy()


class MainViewFrame(Frame):
    """
    Main application frame for displaying analyzed data plots and related information.

    `MainViewFrame` initializes a `ViperDF`, performs analysis and plotting, and
    organizes three main UI sections: the main plot, subplots (app/label plots),
    and an info panel. It serves as a self-contained visualization container for
    testing or embedding in a larger interface.

    Attributes:
        vdf (ViperDF): The analyzed data object used for all plots and stats.
        mainplot_frame (Frame): Frame displaying the main plot.
        subplot_frame (Frame): Frame holding subplots (AppPlotFrame and LabelPlotFrame).
        info_frame (Frame): Frame on the right side showing summarized information.
        main_figure (Figure): The matplotlib figure object for the main plot.
        plot_canvas (FigureCanvasTkAgg): Canvas used to embed the main plot into tkinter.
        plot_widget (Widget): The tkinter widget that holds the main plot canvas.
        app_plot (AppPlotFrame): Subframe displaying application usage data.
        label_plot (LabelPlotFrame): Subframe displaying label statistics.
    """

    def __init__(self, parent,  *args, **kwargs):
        """
        Initializes the `MainViewFrame`.

        Loads and analyzes test data, builds the plot structure, and sets up layout
        grids for main, sub, and info sections. Populates the info frame with VDF insights.

        :param parent: Widget (The parent widget this frame belongs to.)
        :return: None
        """

        super().__init__(parent, *args, **kwargs)

        test_df = DBHandler().search_window_log(start_time=datetime(2025, 1, 16, 0, 0),
                                                end_time=datetime(2025, 1, 17, 0, 0))
        vdf = ViperDF("testing", test_df)
        vdf.analyze()
        self.vdf = vdf
        # DayAnalyzer().get_data()
        self.vdf.plot()

        # till here VDF needs to be analyzed & plotted!!!!

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0, minsize=130)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0, minsize=210)

        self.mainplot_frame = Frame(self, name="mainplot_frame")
        self.subplot_frame = Frame(self, name="subplot_frame")
        self.info_frame = Frame(self, name="info_frame")

        self.mainplot_frame.grid(row=0, column=0, sticky="nesw")
        self.mainplot_frame.grid_propagate(True)
        self.mainplot_frame.grid_rowconfigure(0, weight=1)
        self.mainplot_frame.grid_columnconfigure(0, weight=1)

        self.subplot_frame.grid(row=1, column=0, sticky="nesw")
        self.subplot_frame.grid_propagate(False)
        self.subplot_frame.grid_rowconfigure(0, weight=1)
        self.subplot_frame.grid_columnconfigure(0, weight=1)
        self.subplot_frame.grid_columnconfigure(1, weight=1)

        self.info_frame.grid(row=0, column=1, rowspan=2, sticky="nesw")
        self.info_frame.grid_propagate(False)

        self.main_figure = self.vdf.get_main_plot()
        self.plot_canvas = FigureCanvasTkAgg(self.main_figure, master=self.mainplot_frame)
        self.plot_widget = self.plot_canvas.get_tk_widget()
        self.plot_widget.grid(row=0, column=0, sticky="nw")
        self.plot_widget.grid_propagate(False)

        self.app_plot = AppPlotFrame(self.subplot_frame, self.vdf)
        self.app_plot.grid(row=0, column=0, sticky="nesw")

        self.label_plot = LabelPlotFrame(self.subplot_frame, self.vdf)
        self.label_plot.grid(row=0, column=1, sticky="nesw")

        last_entry_id = len(self.vdf.main_infos()) - 1
        for i, item in enumerate(self.vdf.main_infos()):
            row_base = i * 3
            self.info_frame.rowconfigure(row_base, weight=0)
            self.info_frame.rowconfigure(row_base + 1, weight=0)

            row_frame = Frame(self.info_frame)
            row_frame.grid(row=row_base, column=0, rowspan=2, sticky="nsew")

            tb.Label(row_frame, text=item[0], font=("TkDefaultFont", 10)) \
                .grid(row=0, column=0, pady=1, sticky="w")

            left_text = tb.Label(row_frame, text=item[1], font=("TkDefaultFont", 10, "bold"))
            left_text.grid(row=1, column=0, pady=1, sticky="w")

            if i < last_entry_id:
                tb.Separator(self.info_frame, orient="horizontal") \
                    .grid(row=row_base + 2, column=0, sticky="ew", pady=(2, 4))

class ViewController:
    """
    Controller for managing the main GUI views of the application.

    This class handles:
    - Creating and managing the main window.
    - Managing and updating tabs for different application sections (e.g., Overview, Labels, Settings).
    - Applying and saving GUI-related settings.

    Attributes:
        _main_window (Toplevel | None): The root window of the application.
        _initialized (bool): Ensures `__init__` runs only once (singleton).
        _instance (ViewController | None): Holds the singleton instance.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Implements the singleton pattern for the `ViewController`.

        This ensures that only one instance of the `ViewController` exists during the application's lifecycle.

        :return: ViewController (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the `ViewController`.

        Sets up the main application state and prepares for GUI window creation. Ensures
        initialization only runs once per lifecycle.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._main_window = None

    def main_window(self) -> None:
        """
        Creates and displays the main application window.

        Initializes the main tab structure, sets up the title, size, and layout,
        and prepares tab-switching logic.

        :return: None
        """

        get_logger().debug("main_window start")

        # Create the Toplevel window
        self._main_window = Toplevel(GuiController().root)
        # TODO: window icon & taskbar icon need to be set properly (probably seen after windows installation)
        #self._main_window.iconphoto(True, GuiController().icon_image)
        self._main_window.title("Viper Tracking")
        win_width, win_height = UserSettingsManager().gui_resolution
        self._main_window.minsize(win_width, win_height)
        center_window(self._main_window, win_width, win_height)

        notebook = ttk.Notebook(self._main_window)
        notebook.bind("<<NotebookTabChanged>>", self.update_tab)
        main_tab = ttk.Frame(notebook)
        analysis_tab = ttk.Frame(notebook)
        label_tab = ttk.Frame(notebook)
        filter_tab = ttk.Frame(notebook)
        settings_tab = ttk.Frame(notebook)

        notebook.add(main_tab, text="Overview")
        notebook.add(analysis_tab, text="Analysis")
        notebook.add(label_tab, text="Label")
        notebook.add(filter_tab, text="Filter")
        notebook.add(settings_tab, text="Settings")
        notebook.pack(expand=True, fill="both", padx=0, pady=0)



    def update_tab(self, event) -> None:
        """
        Updates the content of the currently selected tab.

        Destroys all children of the tab frame and reloads the appropriate section
        based on the selected index.

        :param event: Event (Triggered by tab switch.)
        :return: None
        """
        nb = event.widget
        tab_index = event.widget.index("current")  # Get the index of the selected tab
        child_tabs = event.widget.winfo_children()
        for tabs in child_tabs:
            frame_childs = tabs.winfo_children()
            for child in frame_childs:
                if isinstance(child, Frame):
                    child.destroy()
        match tab_index:
            case 0:  # MainTab
                self.update_main_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 1:  # AnalysisTab
                self.update_analysis_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 2:  # LabelTab
                self.update_label_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 3:  # FilterTab
                self.update_filter_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 4:  # SettingsTab
                self.update_settings_tab(event.widget.nametowidget(nb.tabs()[tab_index]))

    def update_main_tab(self, tab) -> None:
        """
        Updates the content of the "Overview" tab in the main application window.

        Displays a high-level analysis view of the data using `MainViewFrame`.

        :param tab: Frame (The "Overview" tab to update.)
        :return: None
        """

        MainViewFrame(tab).pack(fill="both", expand=True)

    def update_analysis_tab(self, tab) -> None:
        """
        Updates the content of the "Analysis" tab in the main application window.

        Initializes filter selection and result display. Connects filter logic to
        update the analysis frame dynamically.

        :param tab: Frame (The "Analysis" tab to update.)
        :return: None
        """

        all_frame = Frame(tab, name="all_frame")
        all_frame.pack(fill="both", expand=True)
        all_frame.pack_propagate(False)

        fcf = FilterChoiceFrame(all_frame, height=300)
        fcf.pack(fill="x")
        fcf.pack_propagate(False)

        af = AnalysisFrame(all_frame)
        af.pack_propagate(False)
        af.pack(fill="both", expand=True)

        fcf.set_analyzing_return_function(af.add_vdf_to_show)

    def update_label_tab(self, tab) -> None:
        """
        Updates the content of the "Labels" tab.

        Loads all labels from the database, populates the UI with `LabelFrame` instances,
        and adds buttons to create new labels or save changes.

        :param tab: Frame (The "Labels" tab to update.)
        :return: None
        """

        scroll_frame = ScrollFrame(tab, scrollbar_position="right")
        scroll_frame.pack(fill="both", expand=True)
        label_frame_list = []
        for lab in Label.get_all_labels():
            lab_frame = LabelFrame(parent=scroll_frame.inner_frame, label=lab)
            lab_frame.pack(fill="x", padx=5, pady=5)
            label_frame_list.append(lab_frame)

        btn_frame = Frame(scroll_frame.inner_frame)
        btn_frame.pack(side="left", fill="x", padx=5, pady=5)

        new_label_button = tb.Button(btn_frame, text="Add new Label")
        new_label_button.pack(padx=5, pady=5, side="left", expand=True)  # Center with expand=True

        save_labels_button = tb.Button(btn_frame, text="Save")
        save_labels_button.pack(padx=5, pady=5, side="left")  # Move to the right side and block space for lbl btn

        new_label_button.bind("<Button-1>", self.add_new_label)
        save_labels_button.bind("<Button-1>", self.save_labels)

        tab.after_idle(lambda: self._shrink_flex_child(label_frame_list) )

    def _shrink_flex_child(self, frame_list):
        """
        Collapses the flex sections of a given list of frames.

        Used to shrink expandable content in `LabelFrame` or `FilterFrame` widgets.

        :param frame_list: list[Frame] (The list of frames to collapse.)
        :return: None
        """

        for parent_frame in frame_list:
            parent_frame.flex.toggle_expanded()

    def save_labels(self, event=None) -> None:
        """
        Saves all labels in the "Labels" tab to the database.

        Validates all `LabelFrame` inputs and attempts to commit the data. Displays a
        notice if any validation errors occur.

        :param event: Event (Triggered by the "Save" button.)
        :return: None
        """
        # FIXME: to fast clicking results in multiple label creation
        if event is None:
            print("error no button provided")
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

    def add_new_label(self, event=None) -> None:
        """
        Adds a new label to the "Labels" tab in the main application window.

        Inserts a new `LabelFrame` before the control button row for the user to edit.

        :param event: Event (Triggered by the "Add new Label" button.)
        :return: None
        """

        if event is None:
            print("error no button provided")
        else:
            # Order of master's
            # <class 'tkinter.ttk.Frame'>
            # <class 'tkinter.ttk.Frame'>
            # <class 'tkinter.Canvas'>
            # <class 'gui_views.ScrollableFrame'>

            canvas_frame = event.widget.master.master
            btn_frame = event.widget.master
            btn_frame.pack_forget()
            n_lab = LabelFrame(parent=canvas_frame)
            n_lab.pack(fill="x", padx=5, pady=5)
            btn_frame.pack(side="left", fill="x", padx=5, pady=5)

    def update_filter_tab(self, tab) -> None:
        """
        Updates the content of the "Filter" tab.

        Loads all filters from the database and builds a list of editable `FilterFrame` instances.
        Includes options to add new filters and save changes.

        :param tab: Frame (The "Filter" tab to update.)
        :return: None
        """

        scroll_frame = ScrollFrame(tab, scrollbar_position="right")
        scroll_frame.pack(fill="both", expand=True)
        filter_frame_list = []
        for fil in DatabaseFilter.get_all_filter():
            filter_frame = FilterFrame(parent=scroll_frame.inner_frame, database_filter=fil)
            filter_frame.pack(fill="x", padx=5, pady=5)
            filter_frame_list.append(filter_frame)

        btn_frame = Frame(scroll_frame.inner_frame)
        btn_frame.pack(side="left", fill="x", padx=5, pady=5)

        new_filter_button = tb.Button(btn_frame, text="Add new Filter")
        new_filter_button.pack(padx=5, pady=5, side="left", expand=True)  # Center with expand=True

        save_filter_button = tb.Button(btn_frame, text="Save")
        save_filter_button.pack(padx=5, pady=5, side="left")  # Move to the right side and block space for lbl btn

        new_filter_button.bind("<Button-1>", self.add_new_filter)
        save_filter_button.bind("<Button-1>", self.save_all_filter)

        tab.after_idle(lambda: self._shrink_flex_child(filter_frame_list))

    def save_all_filter(self, event=None) -> None:
        """
        Saves all filters in the "Filter" tab to the database.

        Iterates through each `FilterFrame`, collects and commits their state.

        :param event: Event (Triggered by the "Save" button.)
        :return: None
        """
        # FIXME: MAYBE ERROR: to fast clicking results in multiple filter creation
        if event is None:
            print("error no button provided")
        else:
            parent = event.widget.master.master
            for filter_frame in parent.winfo_children():
                if isinstance(filter_frame, FilterFrame):

                    filter_frame.save_to_db()

    def add_new_filter(self, event=None) -> None:
        """
        Adds a new filter to the "Filter" tab.

        Inserts a new `FilterFrame` instance before the control button row.

        :param event: Event (Triggered by the "Add new Filter" button.)
        :return: None
        """

        if event is None:
            print("error no button provided")
        else:
            # Order of master's
            # <class 'tkinter.ttk.Frame'>
            # <class 'tkinter.ttk.Frame'>
            # <class 'tkinter.Canvas'>
            # <class 'gui_views.ScrollableFrame'>

            canvas_frame = event.widget.master.master
            btn_frame = event.widget.master
            btn_frame.pack_forget()
            n_filter = FilterFrame(parent=canvas_frame)
            n_filter.pack(fill="x", padx=5, pady=5)
            btn_frame.pack(side="left", fill="x", padx=5, pady=5)


    def update_settings_tab(self, tab) -> None:
        """
        Updates the content of the "Settings" tab in the main application window.

        Loads resolution and theme options, displays example widgets, and sets up
        saving and applying of GUI preferences.

        :param tab: Frame (The "Settings" tab to update.)
        :return: None
        """

        upper_frame = Frame(tab, borderwidth=2, relief="solid")
        lower_frame = Frame(tab, borderwidth=2, relief="solid")

        upper_frame.pack(side="top", fill="both", expand=True, padx=10, pady=5)
        lower_frame.pack(side="bottom", fill="both", expand=True, padx=10, pady=5)

        # Dropdown for resolution placed at the top-left (absolute positioning)
        d_res_values = [f"{key}: {value[0]}x{value[1]}" for key, value in dict_resolution.items()]
        dropdown_resolution = tb.Combobox(upper_frame, values=d_res_values, state="readonly")
        dropdown_resolution.current(0)
        dropdown_resolution.bind("<MouseWheel>", disable_scroll)
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
        dropdown_demo.bind("<MouseWheel>", disable_scroll)
        dropdown_demo.pack(padx=10, pady=10)
        tb.Button(example_frame, text="Action Button (primary)", bootstyle="primary").pack(padx=10, pady=10)

        # Dropdown for themes inside right_frame, below example_frame
        list_themes = GuiController().root.style.theme_names()
        dropdown_themes = tb.Combobox(right_frame, values=list_themes, state="readonly")
        dropdown_themes.set(GuiController().root.style.theme_use())
        dropdown_themes.bind("<MouseWheel>", disable_scroll)
        dropdown_themes.pack(side="left", padx=10, pady=5)

        # Apply button next to the dropdown (on the right)
        apply_button = tb.Button(right_frame, text="APPLY",
                                 command=lambda: self.apply_changes(dropdown_resolution, dropdown_themes))
        apply_button.pack(side="left", padx=10, pady=5)

    def apply_changes(self, dropdown_resolution, dropdown_themes) -> None:
        """
        Applies GUI settings, such as theme and resolution, to the application.

        Applies user-selected configuration options to the active window and theme.

        :param dropdown_resolution: Combobox (Dropdown for selecting resolution.)
        :param dropdown_themes: Combobox (Dropdown for selecting theme.)
        :return: None
        """

        GuiController().root.style.theme_use(dropdown_themes.get())
        ind = dropdown_resolution.current()

        selected_key = list(dict_resolution.keys())[ind]
        width, height = dict_resolution[selected_key]

        center_window(self._main_window, width, height)

    def save_changes(self, dropdown_resolution, dropdown_themes) -> None:
        """
        Saves the current GUI settings, such as theme and resolution, to the user's configuration.

        Updates the `UserSettingsManager` and saves persistent preferences.

        :param dropdown_resolution: Combobox (Dropdown for selecting resolution.)
        :param dropdown_themes: Combobox (Dropdown for selecting theme.)
        :return: None
        """

        new_theme = dropdown_themes.get()
        selected_reso = list(dict_resolution.keys())[dropdown_resolution.current()]
        reso = dict_resolution[selected_reso]

        UserSettingsManager().gui_theme = new_theme
        UserSettingsManager().gui_resolution = list(reso)
        UserSettingsManager().save_settings()
        self.apply_changes(dropdown_resolution, dropdown_themes)

    def sys_tray_manual_label(self) -> None:
        """
        Displays a small GUI popup to quickly create a manual label from the system tray.

        The overlay appears above the taskbar with no window chrome, offering only a
        textbox and buttons for label creation.

        :return: None
        """
        get_logger().debug("sys_tray_manual_label start")
        win_width = 300
        win_height = 130
        taskbar_height = 70
        sys_tray_win = Toplevel(GuiController().root, height=0, width=0)
        sys_tray_win.overrideredirect(True)
        sys_tray_win.withdraw()

        sys_tray_win.title('Sys Tray Add Label')
        # sys_tray_win.iconphoto(True, GuiController().icon_image)
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
def disable_scroll(event):
    """
    Disables mouse wheel scrolling on a widget.

    Used to prevent accidental value changes in scrollable widgets like dropdowns.

    :param event: Event (The scroll event to block.)
    :return: str (Always returns "break" to stop default behavior.)
    """

    return "break"


def win_close(win: Window) -> None:
    """
    Closes a specified window.

    This utility function ensures proper cleanup and destruction of the window.

    :param win: Toplevel (The window to be closed.)
    :return: None
    """

    win.destroy()


def set_focus_visual(transform_widget: Widget) -> None:
    """
    Adds visual indicators to a widget when it gains or loses focus.

    This function updates the widget's style dynamically based on its focus state.

    :param transform_widget: Widget (The widget to apply focus visuals to.)
    :return: None
    """

    if transform_widget.winfo_class() in ['TButton', 'TEntry', 'TCheckbutton', 'TRadiobutton', 'TCombobox']:
        transform_widget.bind("<FocusOut>",
                              lambda event: event.widget.configure(style=f"primary.{event.widget.winfo_class()}"))
        transform_widget.bind("<FocusIn>",
                              lambda event: event.widget.configure(style=f"info.{event.widget.winfo_class()}"))


def set_standard_focus_on_window(wind: Window) -> None:
    """
    Applies standard focus visuals to all widgets in a given window.

    Iterates over all child widgets of the specified window and applies focus styles
    consistently.

    :param wind: Toplevel (The parent window containing the widgets.)
    :return: None
    """

    for widget in wind.winfo_children():
        set_focus_visual(widget)


def center_window(window, width, height) -> None:
    """
    Centers a window on the user's screen.

    If the window's size exceeds the screen dimensions, it is maximized instead.

    :param window: Toplevel (The window to be centered.)
    :param width: int (The desired width of the window.)
    :param height: int (The desired height of the window.)
    :return: None
    """

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


def sys_add(win: Window, label_text) -> None:
    """
    Adds a manual label through the system tray and updates the menu.

    The label is saved to the database, and the system tray interface is refreshed
    to include the new label.

    :param win: Toplevel (The system tray window.)
    :param label_text: Entry (The input field containing the new label's name.)
    :return: None
    """

    # TODO: Probably need to make this smoother, because circular import if import on top
    get_logger().debug("adding manual label by systray start")
    from system_tray_manager import SystemTrayManager

    Label(label_text.get(), manually=True)
    win_close(win)
    SystemTrayManager().update_menu()
    get_logger().debug("adding manual label by systray end")


# # # # External call functions for less import in other files # # # #
def open_main_window() -> None:
    """
    Opens the main application window.

    This function initializes and displays the primary GUI for managing the application's functionality.

    :return: None
    """

    # Todo: If window is allready open (mainwindow) dont reopen it, just make it foreground again
    ViewController().main_window()


def open_systray_label() -> None:
    """
    Opens the system tray manual label input window.

    This allows users to add a manual label via the system tray interface.

    :return: None
    """
    # TODO: also only 1 instance of this should be allowed
    ViewController().sys_tray_manual_label()


if __name__ == "__main__":
    print("Please start with the main.py")

"""
This module manages GUI views and their components.

Features:
- Controls the creation and management of various GUI views.
- Provides classes for custom widgets, such as scrollable frames and condition lists.
- Includes functionality to handle user interactions and database updates.

Author: sora7672
"""
__author__ = 'sora7672'

from datetime import datetime, date
from ttkbootstrap import Frame, Window, Style, DateEntry, Querybox, Scrollbar
from ttkbootstrap.dialogs import Messagebox, DatePickerDialog
from ttkbootstrap.constants import *
from tkinter import Toplevel, PhotoImage, Widget, ttk, IntVar, BooleanVar, StringVar, Canvas, TclError
from tkinter.ttk import Combobox  # Fixme: This should use tb not tk
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


# TODO: Styles and such infos need to be initialized properly with a function or on the gui_controller
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
# FIXME: styl needs to be created inside the mainloop anyhow
# Style().configure("AndConditionList.TFrame", borderwidth=2, relief="solid", background="purple")
# Style().configure("OrConditionList.TFrame", borderwidth=2, relief="solid", background="cyan")

# TODO: remove temp debug function
def debug_widget_infos(widget, flag=""):
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
        fields (list[str]): A list of strings representing the faulty fields.
        error_code (Any, optional): An optional error code related to the validation error.
        message (str): A formatted error message listing the faulty fields.

    Raises:
        ValueError: If any element in the provided list is not a string.
        TypeError: If 'fields' is not a string or a list of strings.
    """

    def __init__(self, fields: str | list[str], error_code: str | int = None):
        """
        Initializes the `FormValidationError` with faulty fields and an optional error code.

        Parameters:
            fields (str or list[str]): A single faulty field (string) or a list of faulty fields (list of strings).
            error_code (Any, optional): An optional error code for the validation error.

        Raises:
            ValueError: If any element in 'fields' is not a string.
            TypeError: If 'fields' is not a string or a list of strings.
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

    def __str__(self):
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
    """

    _allowed_scrollbar_positions = ["e", "s", "w", "n", "top", "left", "right", "bottom"]

    def __init__(self, parent, scrollbar_position: str | tuple[str, str] | list[str, str]= "e", canvas_height: int = None, canvas_width: int = None, *args, **kwargs):
        """
        Initializes a scrollable frame with optional scrollbar position.

        :param parent: Widget (The parent widget to attach the scroll frame to.)
        :param _scrollbar_position: str (Scrollbar position: 'top', 'bottom', 'left', or 'right')
        :param canvas_height: int (if a fixed size is needed)
        :param canvas_width: int (if a fixed size is needed)
        :param args: Any additional positional arguments for Frame.
        :param kwargs: Any additional keyword arguments for Frame.
        :raises TypeError: If scrollbar_position is not a string.
        :raises ValueError: If scrollbar_position is not one of the allowed values.
        """
        super().__init__(parent, *args, **kwargs)

        if canvas_height is not None:
            if not isinstance(canvas_height, int):
                raise TypeError("canvas_height must be an integer or None.")

        if canvas_width is not None and not isinstance(canvas_width, int):
            raise TypeError("canvas_width must be an integer or None.")

        self.scrollbar_list = []  #  Max 2!
        self.scrollbar_configs = []  # List of dicts that should hold each config option per scrollbar
        # scrollbar_position = "left"
        # orientation = "vertical"
        # canvas_side = "right"
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
                    raise ValueError("Scrollbar position can only have one for each: ['left','right'] & ['top','bottom']")
                self._orientation = "vertical"
                # allways vertical on 2 scrollbars

        elif isinstance(scrollbar_position, str):
            self.scrollbar_configs.append(dict(zip(config_keys,
                                                 self._check_scrollbar_position(scrollbar_position))))
        else:
            raise TypeError("scrollbar_position must be a string or tuple/list of 2 strings.")

        for sbar in self.scrollbar_configs:
            sbar["is_positioned"] = True

        self.canvas = Canvas(self)
        if canvas_height:
            self.canvas.configure(height=canvas_height)
        if canvas_width:
            self.canvas.configure(width=canvas_width)

        self.inner_frame = Frame(self.canvas)

        if len(self.scrollbar_configs) == 1:
            if self.scrollbar_configs[0]["orientation"] == "vertical":
                self.scrollbar_list.append(Scrollbar(self, orient="vertical", command=self.canvas.yview))
                self.canvas.configure(yscrollcommand=self.scrollbar_list[0].set)
                #self.scrollbar_list[0].pack(side=self.scrollbar_configs[0]["scrollbar_position"], fill="y")
            else:
                self.scrollbar_list.append(Scrollbar(self, orient="horizontal", command=self.canvas.xview))
                self.canvas.configure(xscrollcommand=self.scrollbar_list[0].set)
                #self.scrollbar_list[0].pack(side=self.scrollbar_configs[0]["scrollbar_position"], fill="x")

        elif len(self.scrollbar_configs) == 2:
            y_command = None
            x_command = None

            for sbar in self.scrollbar_configs:
                if sbar["orientation"] == "vertical":
                    self.scrollbar_list.append(Scrollbar(self, orient="vertical", command=self.canvas.yview))
                    y_command = self.scrollbar_list[-1].set
                    #self.scrollbar_list[-1].pack(side=sbar["scrollbar_position"], fill="y")

                else:
                    self.scrollbar_list.append(Scrollbar(self, orient="horizontal", command=self.canvas.xview))
                    x_command = self.scrollbar_list[-1].set
                    #self.scrollbar_list[-1].pack(side=sbar["scrollbar_position"], fill="x")

            self.canvas.configure(yscrollcommand=y_command)
            self.canvas.configure(xscrollcommand=x_command)
        else:
            raise ValueError("Scrollbar position must be a tuple/list of exactly 2 entries.")


        self.canvas.pack(side=self._canvas_side, fill="both", expand=True)
        self.canvas.pack_propagate(False)
        self.canvas.create_window((0, 0), window=self.inner_frame, anchor="nw")

        self.inner_frame.bind("<Configure>", self._frame_size_changed)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)




    def _check_scrollbar_position(self, position_string):
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

    def _frame_size_changed(self, event=None) -> None:
        """
        Updates the canvas scroll region whenever the size of the inner frame changes.

        :param event: Event (Optional tkinter event.)
        :return: None
        """

        self.update_idletasks()
        frame_width = self.inner_frame.winfo_width()
        frame_height = self.inner_frame.winfo_height()
        canvas_width = self.canvas.winfo_width()
        canvas_height= self.canvas.winfo_height()
        v_scroll_needed = frame_height > canvas_height
        h_scroll_needed = frame_width > canvas_width

        for bar, config in zip(self.scrollbar_list, self.scrollbar_configs):
            if config["orientation"] == "vertical" and v_scroll_needed:
                bar.pack(side=config["scrollbar_position"], fill="y")

                if config["is_positioned"] == False:
                    self.canvas.pack_forget()
                    self.canvas.pack(side=self._canvas_side, fill="both", expand=True)
                    config["is_positioned"] = True


            elif config["orientation"] == "horizontal" and h_scroll_needed:
                bar.pack(side=config["scrollbar_position"], fill="x")

                if config["is_positioned"] == False:
                    self.canvas.pack_forget()
                    self.canvas.pack(side=self._canvas_side, fill="both", expand=True)
                    config["is_positioned"] = True

            else:
                bar.pack_forget()
                if config["is_positioned"] == True:
                    config["is_positioned"] = False

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))



    def _bind_mousewheel(self, event=None) -> None:
        """
        Binds mousewheel scroll events to this widget when hovered.

        :param event: Event (Optional tkinter event.)
        :return: None
        """
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_scroll)
        self.canvas.bind_all("<Button-4>", self._on_mouse_scroll)
        self.canvas.bind_all("<Button-5>", self._on_mouse_scroll)

    def _unbind_mousewheel(self, event=None) -> None:
        """
        Unbinds mousewheel scroll events when mouse leaves this widget.

        :param event: Event (Optional tkinter event.)
        :return: None
        """
        self.canvas.unbind("<MouseWheel>")
        self.canvas.unbind("<Button-4>")
        self.canvas.unbind("<Button-5>")

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

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        inner_width = self.inner_frame.winfo_reqwidth()
        inner_height = self.inner_frame.winfo_reqheight()

        if len(self.scrollbar_list) == 1:
            orientation = self.scrollbar_configs[0]["orientation"]
        else:
            orientation = "vertical"

        if orientation == "vertical" and inner_height > canvas_height:
            direction = 1 if event.num == 5 or event.delta == -120 else -1
            self.canvas.yview_scroll(direction, "units")
        elif orientation == "horizontal" and inner_width > canvas_width:
            direction = 1 if event.num == 5 or event.delta == -120 else -1
            self.canvas.xview_scroll(direction, "units")

class SmartDateEntry(DateEntry):

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, dateformat="%d.%m.%Y", firstweekday=0, *args, **kwargs)
        self._dateformat = "%d.%m.%Y"
        self.entry.delete(0, "end")
        self.button.pack_forget()
        self.entry.bind("<Button-1>", self._open_calender)
        self.entry.bind("<Escape>", self._on_escape)
        self.entry.bind("<Return>", self._on_return)

    def set(self, value):

        if isinstance(value, date):
            value = value.strftime(self._dateformat)
        elif isinstance(value, str):
            value = datetime.fromisoformat(value).date().strftime(self._dateformat) if value != "" else ""
        self.entry.delete(first=0, last=tk.END)
        self.entry.insert(tk.END, value)

    def get(self):
        return self.entry.get()

    def _on_return(self, event):
        self._open_calender(event)

    def _on_escape(self, event):
        self.entry.delete(first=0, last=tk.END)

    def _open_calender(self, event):
        self.button.invoke()


    def _on_date_ask(self):
        """Callback for pushing the date button"""
        _val = self.entry.get() or datetime.today().strftime(self._dateformat)
        try:
            self._startdate = datetime.strptime(_val, self._dateformat)
        except Exception as e:
            print("Date entry text does not match", self._dateformat)
            self._startdate = datetime.today()
            self.entry.delete(first=0, last=tk.END)
            self.entry.insert(
                tk.END, self._startdate.strftime(self._dateformat)
            )

        old_date = datetime.strptime(_val, self._dateformat)

        # get the new date and insert into the entry
        new_date = SmartQuerybox.get_date(
            parent=self.entry,
            startdate=old_date,
            firstweekday=self._firstweekday,
            bootstyle=self._bootstyle,
        )
        tmp_entry_value = self.entry.get()

        self.entry.delete(first=0, last=tk.END)
        if not new_date == "":
            self.entry.insert(tk.END, new_date.strftime(self._dateformat))
        else:
            self.entry.insert(tk.END, tmp_entry_value)
        self.entry.focus_force()

class SmartQuerybox(Querybox):

    @staticmethod
    def get_date(
        parent=None,
        title=" ",
        firstweekday=6,
        startdate=None,
        bootstyle="primary",
    ):
        """Shows a calendar popup and returns the selection.

        ![](../../assets/dialogs/querybox-get-date.png)

        Parameters:

            parent (Widget):
                The parent widget; the popup will appear to the
                bottom-right of the parent widget. If no parent is
                provided, the widget is centered on the screen.

            title (str):
                The text that appears on the popup titlebar.

            firstweekday (int):
                Specifies the first day of the week. `0` is Monday, `6` is
                Sunday (the default).

            startdate (datetime):
                The date to be in focus when the widget is displayed;

            bootstyle (str):
                The following colors can be used to change the color of the
                title and hover / pressed color -> primary, secondary, info,
                warning, success, danger, light, dark.

        Returns:

            datetime:
                The date selected; the current date if no date is selected.
        """
        chooser = SmartDatePickerDialog(
            parent=parent,
            title=title,
            firstweekday=firstweekday,
            startdate=startdate,
            bootstyle=bootstyle,
        )


        return chooser.date_selected


class SmartDatePickerDialog(DatePickerDialog):

    locale.setlocale(locale.LC_ALL, locale.setlocale(locale.LC_TIME, ""))

    def __init__(
        self,
        parent=None,
        title=" ",
        firstweekday=6,
        startdate=None,
        bootstyle=PRIMARY,
    ):
        """
        Parameters:

            parent (Widget):
                The parent widget; the popup will appear to the
                bottom-right of the parent widget. If no parent is
                provided, the widget is centered on the screen.

            title (str):
                The text that appears on the titlebar.

            firstweekday (int):
                Specifies the first day of the week. 0=Monday,
                1=Tuesday, etc...

            startdate (datetime):
                The date to be in focus when the widget is
                displayed.

            bootstyle (str):
                The following colors can be used to change the color of
                the title and hover / pressed color -> primary,
                secondary, info, warning, success, danger, light, dark.
        """
        self.parent = parent
        self.root = tb.Toplevel(
            title=title,
            transient=self.parent,
            resizable=(False, False),
            topmost=True,
            minsize=(226, 1),
            iconify=True,
        )
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

    def _navigate_keys(self, event):
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


    def _get_last_day_current_month(self):
        return calendar.monthrange(self.date.year, self.date.month)[1]

    def _calc_new_entry(self, add_val: int):
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


    def _on_focus_out(self, event):
        self._on_escape(event)

    def _on_return(self, event):
        # should take the current selection as return value
        self.root.destroy()

    def _on_click(self, event):
        clicked_widget = self.root.winfo_containing(event.x_root, event.y_root)
        if clicked_widget is None or clicked_widget.winfo_toplevel() is not self.root:
            self._on_escape(event)

    def _on_close(self):
        self._on_escape(None)

    def _on_escape(self, event):
        self.date_selected = ""
        self.root.destroy()


    def _draw_calendar(self):
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

                    def selected(x=row, y=col):
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
    Make sure to add your widgets to <object>.inner_frame
    not directly on <object>
    """
    _forbidden_methods_inner = {"pack", "grid", "place", "pack_forget", "grid_forget", "place_forget",
                                "winfo_width", "winfo_height"}

    def __init__(self, master=None, title_text: str = None, title_var: tk.StringVar = None,
                 title_side: str = "left", expand_char: str = "▼", shrink_char: str = "▶", *args, **kwargs):
        """
        Make sure to add your widgets to <object>.inner_frame
        not directly on <object>
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
        self.title_var = title_var or tk.StringVar()

        if title_text is not None:
            self.title_var.set(title_text)

        self.title_side = title_side

        self.flex_text_var = tk.StringVar()
        self.expanded = True
        self.expand_char = expand_char
        self.shrink_char = shrink_char
        self.flex_text_var.set(self.shrink_char)

        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)

        self.title_frame = tb.Frame(self)
        self.title_frame.grid(row=0, column=0, sticky="ew")

        self.flex_btn = tb.Button(self.title_frame, textvariable=self.flex_text_var, command=self.toggle_expanded, width=2)
        self.title_label = tb.Label(self.title_frame, textvariable=self.title_var, font=("Arial", 16))

        self.flex_btn.pack(side=self.title_side, padx=5, pady=5)
        self.title_label.pack(side=self.title_side, padx=5, pady=5)

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

        self.placeholder: tb.Frame = None


    def _forbidden_method(self, *args, **kwargs):

        raise RuntimeError(f"You used a forbidden method on inner Frame of FlexFrame: "
                           f"{', '.join(FlexFrame._forbidden_methods_inner)}."
                           f"Try for this options <Object>.this")

    def _restricted_configure(self, **kwargs):
        restricted_keys = {"width", "height", "padx", "pady", "borderwidth", "relief"}
        blocked_keys = [key for key in kwargs if key in restricted_keys]

        if blocked_keys:
            raise RuntimeError(
                f"Cannot set configure options {', '.join(blocked_keys)} on inner Frame.\n"
                f"Try for this <Object>.this.configure")

        return self.inner_frame._original_configure(**kwargs)

    def toggle_expanded(self):
        if self.expanded:
            self.expanded = False
            self.flex_text_var.set(self.expand_char)
            self._shrink()
        else:
            self.expanded = True
            self.flex_text_var.set(self.shrink_char)
            self._expand()

    def _expand(self):
        if self.placeholder is not None:
            self.placeholder.grid_forget()
            self.placeholder.destroy()
            self.placeholder = None
        self.inner_frame._original_grid(row=1)


    def _shrink(self):
        self.update_idletasks()
        self.inner_frame._original_grid_forget()
        width = max(self.inner_frame._original_winfo_width(), 1)

        self.placeholder = tb.Frame(self, width=width, height=0)
        self.placeholder.grid(row=1, column=0, sticky="ew")


class InfoBoxFrame(tb.Frame):

    def __init__(self, master, info_text: str | list[str] = None, *args, **kwargs):
        borderwidth = kwargs.pop("borderwidth", 5)
        relief = kwargs.pop("relief", "sunken")
        super().__init__(master, borderwidth=borderwidth, relief=relief, width=32, height=35, *args, **kwargs)
        self.pack_propagate(False)
        if info_text:
            self._info_text = info_text if isinstance(info_text, str) else "".join([f"{inf}\n" for inf in info_text])
        else:
            self._info_text = ""
        self.info_window = None
        tb.Label(self, text="?", font=("Arial", 12, "bold")).pack(expand=True)
        self.bind("<Enter>", self._on_hover)
        self.bind("<Leave>", self._on_hover_out)

    @property
    def info_text(self):
        return self._info_text

    @info_text.setter
    def info_text(self, info_text: str | list[str]):
        self._info_text = info_text if isinstance(info_text, str) else "".join([f"{inf}\n" for inf in info_text])

    def _on_hover(self, event):
        """Create a tooltip-like window above and slightly right of the frame."""
        if self.info_window:
            return  # Prevent duplicate windows

        self.info_window = tk.Toplevel(self)
        self.info_window.overrideredirect(True)  # Remove window borders
        self.info_window.geometry(f"+{self.winfo_rootx() + 40}+{self.winfo_rooty() - 10}")  # Position above

        # Tooltip label inside the floating window
        tb.Label(self.info_window, text=self._info_text, font=("Arial", 10), background="lightyellow", relief="solid",
                 borderwidth=1).pack()

    def _on_hover_out(self, event):
        """Destroy tooltip when mouse leaves the frame."""
        if self.info_window:
            self.info_window.destroy()
            self.info_window = None

class TimeRangeFrame(tb.Frame):
    # TODO: Add date picker & time picker
    #  If pushed esc while inside a entry, remove content
    def __init__(self, master, *args, **kwargs):
        super().__init__(master, *args, **kwargs)

        self.start_date = tk.StringVar()
        self.start_time = tk.StringVar()
        self.end_date = tk.StringVar()
        self.end_time = tk.StringVar()
        self.dynamic_time_frame = tk.StringVar()
        self.dynamic_time_frame_list = ["", *DynamicTimeframe.get_entries()]
        self.columnconfigure(0, weight=0, minsize=300)
        self.columnconfigure(1, weight=0, minsize=150)

        self.left_frame = tb.Frame(self)
        self.right_frame = tb.Frame(self)

        self.left_frame.grid(column=0, row=0, sticky="NEW")
        self.right_frame.grid(column=1, row=0, sticky="NEW", padx=(20,0))

        self.left_frame.rowconfigure(0, weight=0)
        self.left_frame.rowconfigure(1, weight=0)
        self.left_frame.columnconfigure(0, weight=0)
        self.left_frame.columnconfigure(1, weight=0)
        self.left_frame.columnconfigure(2, weight=0)
        self.left_frame.columnconfigure(3, weight=0)
        tb.Label(self.left_frame, text="Start Date:").grid(column=0, row=0, sticky="W")
        self.start_date_entry = SmartDateEntry(self.left_frame, width=12, name="start_date")
        self.start_date_entry.grid(row=0, column=1, pady=2, sticky="W")
        self.start_date_entry.bind("<FocusOut>", self._check_change)


        tb.Label(self.left_frame, text="Time:").grid(row=0, column=2, pady=2, sticky="W")
        tb.Entry(self.left_frame, textvariable=self.start_time, width=8).grid(row=0, column=3,  pady=2, sticky="W")

        tb.Label(self.left_frame, text="End Date:").grid(row=1, column=0, pady=2, sticky="W")
        self.end_date_entry = SmartDateEntry(self.left_frame, width=12, name="end_date")
        self.end_date_entry.grid(row=1, column=1, pady=2, sticky="W")
        self.end_date_entry.bind("<FocusOut>", self._check_change)

        tb.Label(self.left_frame, text="Time:").grid(row=1, column=2, pady=2, sticky="W")
        tb.Entry(self.left_frame, textvariable=self.end_time, width=8).grid(row=1, column=3, pady=2, sticky="W")

        self.right_frame.rowconfigure(0, weight=0)
        self.right_frame.rowconfigure(1, weight=0)
        tb.Label(self.right_frame, text="Dynamic Timeframe:").grid(column=0, row=0, sticky="W")
        self.dynamic_combobox = tb.Combobox(self.right_frame, textvariable=self.dynamic_time_frame, values=self.dynamic_time_frame_list,
                                            width=15, state="readonly")

        self.dynamic_combobox.current(0)
        self.dynamic_combobox.bind("<Escape>", lambda event: self.dynamic_combobox.current(0))
        self.dynamic_combobox.grid(row=1, column=0, pady=2, sticky="W")

    def _check_change(self, event):
        txt = event.widget.entry.get()
        if not txt == "":
            if event.widget.winfo_name() == "start_date":
                if self.start_time.get() == "":
                    self.start_time.set("00:00")
            else:
                if self.end_time.get() == "":
                    self.end_time.set("23:59")


    def get_fields(self):
        """
        Needs to except FormValidationError, if wrong entries.
        Else returns values of all fields.
        """
        faulty_fields = []
        dynamic_time_frame = self.dynamic_time_frame.get()
        start_date = self.start_date_entry.entry.get()
        start_time = self.start_time.get()
        end_date = self.end_date_entry.entry.get()
        end_time = self.end_time.get()

        dynamic_has_value = dynamic_time_frame == "" or dynamic_time_frame in self.dynamic_time_frame_list
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
                self.start_time.set("00:00")
            if not end_time:
                self.end_time.set("23:59")

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
    def __init__(self, parent, database_filter=None, *args, **kwargs):

        super().__init__(parent, *args, **kwargs)

        self.filter = database_filter

        self.filter_id = self.filter.id if self.filter else None

        self.name = tk.StringVar()
        self.window_type = tk.StringVar()
        self.window_title = tk.StringVar()
        self.word_list = tk.StringVar()
        self.text_label_list = tk.StringVar()
        self.choice_box_label_list = tk.StringVar()
        self.chosen_label_dict = {}
        self.all_labels_dict: dict = {lab.id: lab.name for lab in Label.get_all_labels()}


        # Widgets
        self.flex = FlexFrame(self, title_var=self.name)
        self.flex.pack(fill=tk.BOTH, expand=True)
        [self.flex.inner_frame.rowconfigure(i, weight=0) for i in range(7)]
        self.flex.inner_frame.columnconfigure(0, weight=0)
        self.flex.inner_frame.columnconfigure(1, weight=1)

        tb.Label(self.flex.inner_frame, text="Filter Name:").grid(column=0, row=0, padx=(0, 5), pady=3, sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self.name).grid(column=1, row=0, pady=1, sticky="W")

        self.time_frame = TimeRangeFrame(self.flex.inner_frame)
        self.time_frame.grid(column=0, columnspan=2, row=1, padx=(0, 5), pady=3, sticky="W")

        tb.Label(self.flex.inner_frame, text="Window Type:").grid(column=0, row=2, padx=(0, 5), pady=3, sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self.window_type).grid(column=1, row=2, pady=1, sticky="W")

        tb.Label(self.flex.inner_frame, text="Window Title:").grid(column=0, row=3, padx=(0, 5), pady=3, sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self.window_title).grid(column=1, row=3, pady=1, sticky="W")

        tb.Label(self.flex.inner_frame, text="Word List:").grid(column=0, row=4, padx=(0, 5), pady=3, sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self.word_list).grid(column=1, row=4, pady=1, sticky="W")

        # Stuff for labels
        tb.Label(self.flex.inner_frame, text="Chosen Labels").grid(row=5, column=0, sticky="W")
        info_text = ("Choose from the dropdown the Labels you want to include in your filter.\n"
                     "If you set labels, it only results in entries which have at least 1 of them.\n"
                     "Use the reset button to remove all saved entries so far.")
        InfoBoxFrame(self.flex.inner_frame, info_text=info_text).grid(column=1, row=5, padx=(0, 5), pady=5,  sticky="W")
        tb.Entry(self.flex.inner_frame, textvariable=self.text_label_list, state="disabled").grid(row=6, column=0, columnspan=2, sticky="EW")

        label_names = [name for name in self.all_labels_dict.values()]
        self.label_choice_box = tb.Combobox(self.flex.inner_frame, textvariable=self.choice_box_label_list, values=label_names,
                    width=15, state="readonly")
        self.label_choice_box.grid(row=7, column=0, sticky="W")

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

        if self.filter is not None:
            self._fill_with_filter()

    def _fill_with_filter(self):
        # FIll all vars / entries with filter values

        filter_dict = self.filter.as_dict()

        self.name.set(filter_dict["name"] or "")

        self.time_frame.start_date_entry.set(filter_dict["start_date"] or "")
        self.time_frame.start_time.set(filter_dict["start_time"] or "")
        self.time_frame.end_date_entry.set(filter_dict["end_date"] or "")
        self.time_frame.end_time.set(filter_dict["end_time"] or "")

        if filter_dict["dynamic_time_frame"] and filter_dict["dynamic_time_frame"].value \
                in self.time_frame.dynamic_time_frame_list:
            value_index = self.time_frame.dynamic_time_frame_list.index(filter_dict["dynamic_time_frame"].value)
            self.time_frame.dynamic_combobox.current(value_index)
        else:
            self.time_frame.dynamic_combobox.current(0)

        self.window_type.set(filter_dict["window_type"] or "")
        self.window_title.set(filter_dict["window_title"] or "")
        self.word_list.set(", ".join(filter_dict["word_list"]) if filter_dict.get("word_list") else "")

        if filter_dict["label_list"]:
            self.text_label_list.set(", ".join(self.all_labels_dict[lab_id] for lab_id in filter_dict["label_list"]
                                          if lab_id in self.all_labels_dict))
            self.chosen_label_dict = {}
            for lab_id in filter_dict["label_list"]:
                self.chosen_label_dict[lab_id] = self.all_labels_dict[lab_id]



    def delete_filter(self, event):
        if not event.state & 0x0001:  # Shift key flag
            result = Messagebox.okcancel(f"Do you want to delete filter '{self.name.get()}'({
            self.filter._name if self.filter else ""}) ?",
                                         "WARNING! Delete Filter", parent=self.master.master)
            if result != "OK":
                return

        if self.filter is not None:
            self.filter.delete_in_db()
        self.destroy()


    def save_to_db(self):

        db_dict = {}
        try:
            db_dict["dynamic_time_frame"], db_dict["start_datetime"], db_dict["end_datetime"] \
                = self.time_frame.get_fields()

            (db_dict["name"], db_dict["window_type"], db_dict["window_title"], db_dict["word_list"],
             db_dict["label_list"]) = self.validate_fields()

        except FormValidationError as e:
            Messagebox.show_warning(e.message, "Form Validation Failed")
        else:
            if self.filter_id is not None:
                # update mechanic
                self.filter.update(**db_dict)
            else:
                # create new filter
                self.filter = DatabaseFilter(**db_dict)
                self.filter_id = self.filter.id

    def validate_fields(self):

        faulty_fields = []
        name = self.name.get().strip() or ""
        window_type = self.window_type.get().strip() or ""
        window_title = self.window_title.get().strip() or ""
        word_list = self.word_list.get().strip() or ""

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
        label_list = [label_id for label_id in self.chosen_label_dict.keys()]
        return name, window_type, window_title, word_list, label_list

    def _change_label(self):

        label_index = self.label_choice_box.current()
        if label_index == -1:
            return
        self.text_label_list.set("")

        label_key = list(self.all_labels_dict)[label_index]
        self.chosen_label_dict[label_key] = self.all_labels_dict[label_key]
        n_text = [f"{self.chosen_label_dict[lab]}, " for lab in self.chosen_label_dict]

        self.text_label_list.set("".join(n_text))

    def _reset_labels(self):
        self.text_label_list.set("")
        self.chosen_label_dict = {}

    @staticmethod
    def split_comma_separated_entries(entry_string: str):
        return list(set([entry.strip() for entry in entry_string.split(',') if entry.strip()]))


class ConditionListFrame(Frame):
    """
    Frame for managing and displaying condition lists.

    This widget supports creating, editing, and displaying nested conditions
    with logical operators (AND/OR).
    """

    def __init__(self, parent, condition_list:ConditionList = None, top_list=False, first_element=False):
        """
        Initializes the `ConditionListFrame`.

        :param parent: Widget (The parent widget.)
        :param condition_list: ConditionList (Optional condition list to display.)
        :param top_list: bool (Indicates if this frame is the top-level condition list.)
        :param first_element: bool (Indicates if this is the first element in the list.)
        """

        super().__init__(parent, relief="solid", borderwidth=2)
        self.configure(style="AndConditionList.TFrame")
        self.top_list = top_list
        self.first_element = first_element
        self.condition_list = condition_list
        self.name = "conditionlist"

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
        Updates the visual style of the `ConditionListFrame` based on the selected logical operator.

        For example, selecting "AND" may visually emphasize stricter evaluation, while "OR"
        indicates more flexibility. This method ensures the UI reflects the logical operator's meaning.

        :param event: Event (The event triggering the operator update, such as a dropdown selection.)
        :return: None
        """

        op = self.bool_operator_dropdown.get()
        if op.lower() == "and":
            self.configure(style="AndConditionList.TFrame")
        elif op.lower() == "or":
            self.configure(style="OrConditionList.TFrame")

    def remove_self(self) -> None:
        """
        Removes and destroys the `ConditionListFrame` from its parent widget.

        This is a helper methode for the commands.

        :return: None
        """

        self.destroy()


class ConditionFrame(Frame):
    """
    Frame for managing and displaying a single condition.

    This widget provides functionality for users to define a condition, including:
    - Selecting an attribute to evaluate.
    - Choosing a comparison operator (e.g., `==`, `<`, `in`).
    - Providing a value for comparison.

    Conditions created using this frame can be part of a larger condition list or used independently.
    """

    _number_checks = ObjectCondition.get_operators_for_number()
    _text_checks = ObjectCondition.get_operators_for_string()
    _all_checks = _number_checks + _text_checks
    _condition_types = ["window_type", "window_title", "window_text_words", "timestamp"]
    # TODO: Timestanmp really needed??? Maybe later smth like dynamic things predefined: morning/evening,
    #  monday, tuesday etc.

    def __init__(self, parent, condition:ObjectCondition = None,  first_element=False):
        """
        Initializes the `ConditionFrame`.

        Sets up the frame to display the attribute selector, operator dropdown, and value input field.
        Optionally, a pre-existing condition can be loaded into the frame.

        :param parent: Widget (The parent widget where this frame will be placed.)
        :param condition: ObjectCondition (Optional pre-existing condition to populate the frame.)
        :param first_element: bool (Indicates if this is the first condition in a list. Default is False.)
        :return: None
        """

        super().__init__(parent)

        self.first_element = first_element
        self.condition = condition
        self.name = "condition"

        self.pack(fill="x", padx=(5, 3), pady=3)
        self._create_widgets()

    def _create_widgets(self) -> None:
        """
        Creates and packs all widgets for the `ConditionFrame`.

        Widgets include:
        - Dropdown for selecting the attribute.
        - Dropdown for selecting the operator.
        - Input field for the value.
        - Buttons for adding or removing conditions.

        :return: None
        """

        # Dropdown "Condition Type"
        max_chars = max([len(c) for c in ConditionFrame._condition_types]) + 1
        tb.Label(self, text="Condition Type").grid(row=0, column=0, padx=(5, 0), pady=(5, 0), sticky="w")
        self.condition_type = tb.Combobox(self, values=ConditionFrame._condition_types, state="readonly", width=max_chars)
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

    def get_as_object(self):
        """
        Converts the `ConditionFrame` into an `ObjectCondition` object.

        This method takes the selected attribute, operator, and value,
        and returns an instance of `ObjectCondition` representing this condition.

        :return: ObjectCondition (The condition represented by this frame.)
        """

        # TODO: add another field when choosing timestamp/datetime from WinInfo, there should be the choice for date/time/datetime
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

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self._is_analyzing = False
        self.analyzing_return_function = None
        filter_list = DatabaseFilter.get_all_filter()
        self.all_filter_dict = {fil.id : fil.name for fil in filter_list}
        self.all_filter_name_list = list(self.all_filter_dict.values())

        self.main_frame = Frame(self)
        self.wrapper_scroll_frame = Frame(self)
        self.scroll_frame = ScrollFrame(self.wrapper_scroll_frame, scrollbar_position="bottom", canvas_height=237)
        self.sub_filter_frame = self.scroll_frame.inner_frame
        self.sub_filter_index = 0
        self.free_grid_sub_filter_list = []


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


        # TODO: this 2 things should be hidden for now and are not in use
        self.main_filter_combobox_textlabel.pack(anchor="w", pady=(5,0), padx=3)
        self.main_filter_combobox.pack(anchor="w", pady=(0,5), padx=3)
        self.btn_add_sub.pack(anchor="w", pady=5, padx=3)
        self.btn_analyze.pack(anchor="w", pady=5, padx=3)


    def set_analyzing_return_function(self, function) -> None:
        self.analyzing_return_function = function

    def _new_subfilter(self):

        sf = SubFilterFrame(self.sub_filter_frame)
        sf.bind("<Destroy>", self._sub_destroyed)

        if len(self.free_grid_sub_filter_list) > 0:
            row, column = self.free_grid_sub_filter_list.pop(0)
        else:
            row = self.sub_filter_index % 2
            column = (self.sub_filter_index) // 2
            self.sub_filter_index += 1
        sf._row= row
        sf._column = column
        sf.grid(row=row, column=column)


    def _sub_destroyed(self, event) -> None:
        self.free_grid_sub_filter_list.append((event.widget._row, event.widget._column))

    def _get_main_filter(self):
        filter_index = self.main_filter_combobox.current()
        if filter_index == -1:
            raise FormValidationError("No main filter chosen")

        filter_id = list(self.all_filter_dict)[filter_index]
        return DatabaseFilter.get_filter_by_id(filter_id)


    def _analyze(self):
        if self._is_analyzing:
            return
        else:
            self._is_analyzing= True
            sub_filter_list = []  # in the end list[list[filter, bool]]
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

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, borderwidth=1, relief="raised", *args, **kwargs)
        self.subfilter_name_var = StringVar()
        self.sub_change_var = StringVar()
        self.use_add = True
        self.sub_change_var.set("COMBINE")
        filter_list = DatabaseFilter.get_all_filter()
        self.all_filter_dict = {fil.id : fil.name for fil in filter_list}
        self.all_filter_name_list = list(self.all_filter_dict.values())

        self.change_type_btn = tb.Button(self, textvariable=self.sub_change_var,
                                         command=self.change_sub_connector, bootstyle="success")
        self.sub_label = tb.Label(self, text="Subfilter:")
        self.sub_combobox = Combobox(self, values=self.all_filter_name_list, state="readonly")
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

    def change_sub_connector(self):
        if self.sub_change_var.get() == "COMBINE":
            self.sub_change_var.set("REDUCE")
            self.change_type_btn.configure(bootstyle="danger")
            self.use_add = False
        else:
            self.sub_change_var.set("COMBINE")
            self.change_type_btn.configure(bootstyle="success")
            self.use_add = True

    def delete_sub_filter(self, event):
        self.destroy()

    def get_sub_filter(self):
        """
        use this to get each subfilter and then make a list and iterate thorugh it with fo each
        returns filter ID & boolean if it should be added(true=add)
        """

        filter_index = self.sub_combobox.current()
        if filter_index == -1:
            return

        filter_id = list(self.all_filter_dict)[filter_index]

        return filter_id, self.use_add



class AnalysisFrame(Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        # TODO: This all need to be placeholder
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


    def add_vdf_to_show(self, vdf: DataFrame | ViperDF):
        # Either add a vdf of df, if df mke it to a vdf(it will analyze itself)
        if isinstance(vdf, ViperDF):
            new_vdf = vdf
        elif isinstance(vdf, DataFrame):
            new_vdf = ViperDF(name="analysis", main_df=vdf)
            new_vdf.analyze().plot()
        else:
            raise TypeError("Unsupported type. Not [ViperDF, DataFrame]")
        self.vdf = new_vdf
        self.update_frames()

    def update_frames(self):
        if self.vdf is not None:
            self.main_plot_frame.add_vdf(self.vdf)
            self.app_plot_frame.add_vdf(self.vdf)
            self.label_plot_frame.add_vdf(self.vdf)


class ImageFrame(Frame):
    """

    """
    def __init__(self, parent, tk_photoimage: PhotoImage, on_click = None, *args, **kwargs):
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

    def set_on_click(self, on_click):
        self._on_click_function = on_click

    def on_click(self, event):
        if self._on_click_function is None:
            return
        else:
            self._on_click_function(event)


    def _on_resize(self, event=None):
        if hasattr(self, "_resize_job") and self._resize_job:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(100, self._perform_resize)

    def _perform_resize(self):
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
            resized_image = pil.resize((int(photo_width * scale), int(photo_height * scale)), Image.Resampling.LANCZOS)
            self.showing_image = ImageTk.PhotoImage(resized_image)

            self.image_label.config(image=self.showing_image)
            self.old_parent_height = parent_height

        else:
            self.image_label.config(image=self._original_tk_photoimage)
            self.old_parent_height = parent_height

class OverlayFrame(Frame):
    """
    Every widget need to be placed/packed/grided on:
    OverlayFrame.inner_frame
    or it wont be shown/existing.
    Binds also need to be set onto this.
    use the OverlayFrame.expand methode to show the frame
    """
    def __init__(self, parent, name: str = None, *args, **kwargs):

        self._inner_name = name
        super().__init__(parent, *args, **kwargs)

        self.original_master = parent
        self.top_level_master = parent.winfo_toplevel()
        if self._inner_name is not None:
            self.inner_frame = Frame(self.top_level_master, name=self._inner_name, bootstyle="dark")
        else:
            self.inner_frame = Frame(self.top_level_master, bootstyle="dark")
        self.close_btn = tb.Button(self.inner_frame, text="X", bootstyle="danger", command=self.shrink)
        self.close_btn.place(relx=1.0, rely=0, anchor="ne")
        self.overlay_active = False


    def _on_click_outside(self, event):
        x_pos, y_pos = event.x_root, event.y_root

        left_x = self.inner_frame.winfo_rootx()
        right_x = left_x + self.inner_frame.winfo_width()

        bottom_y = self.inner_frame.winfo_rooty()
        top_y = bottom_y + self.inner_frame.winfo_height()

        if not (left_x <= x_pos <= right_x and  bottom_y <= y_pos <= top_y):
            self.shrink()

    def _on_focus_out(self, event):
        if not self.top_level_master.focus_displayof():
            self.shrink()

    def expand(self, event=None):
        if not self.overlay_active:
            self.inner_frame.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.9, anchor="nw")
            self.inner_frame.lift()
            # Maybe in some special cases needed, noted for later:
            # aboveThis=self.top_level_master.winfo_children()[0]

            self.overlay_active = True
            self.top_level_master.bind_all("<Escape>", self.shrink)
            self.top_level_master.bind_all("<Button-1>", self._on_click_outside)
            self.top_level_master.bind("<FocusOut>", self._on_focus_out)


    def shrink(self, event=None):
        if self.overlay_active:
            self.inner_frame.place_forget()
            self.overlay_active = False
            self.top_level_master.unbind_all("<Escape>")
            self.top_level_master.unbind_all("<Button-1>")
            self.top_level_master.unbind("<FocusOut>")

    def pack(self, *args, **kwargs):
        raise RuntimeError("Use .expand() to make visible.")

    def grid(self, *args, **kwargs):
        raise RuntimeError("Use .expand() to make visible.")

    def place(self, *args, **kwargs):
        raise RuntimeError("Use .expand() to make visible.")

    def pack_forget(self, *args, **kwargs):
        raise RuntimeError("Use .shrink() to make invisible.")

    def grid_forget(self, *args, **kwargs):
        raise RuntimeError("Use .shrink() to make invisible.")

    def place_forget(self, *args, **kwargs):
        raise RuntimeError("Use .shrink() to make invisible.")


class MainPlotFrame(Frame):
    def __init__(self, parent, viper_df: ViperDF = None, *args, **kwargs):
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

    def add_vdf(self, vdf: ViperDF):
        if not isinstance(vdf, ViperDF):
            raise TypeError("Unsupported type. Not a ViperDF")

        self.vdf = vdf
        self.update_main_plot()


    def update_main_plot(self):
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

    def update_info_area(self):
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
    def __init__(self, parent, viper_df: ViperDF = None, *args, **kwargs):
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


    def add_vdf(self, vdf: ViperDF):
        if not isinstance(vdf, ViperDF):
            raise TypeError("Unsupported type. Not a ViperDF")

        self.vdf = vdf
        self.update_app_plot()

    def update_app_plot(self):
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


    def switch_plot_type(self):
        if self.plot_type == "Pie":
            self.plot_type = "Vbar"
        else:
            self.plot_type = "Pie"
        self.update_app_plot()

    
class LabelPlotFrame(Frame):
    def __init__(self, parent, viper_df: ViperDF=None, *args, **kwargs):
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

    def add_vdf(self, vdf: ViperDF):
        if not isinstance(vdf, ViperDF):
            raise TypeError("Unsupported type. Not a ViperDF")

        self.vdf = vdf
        self.update_label_plot()

    def update_label_plot(self):
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


    def switch_plot_type(self):
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
    """

    def __init__(self, parent, label: Label | None = None):
        """
        Initializes the `LabelFrame`.

        Sets up the label editing interface, including input fields, buttons, and an optional
        condition list frame. If a pre-existing label is provided, its data populates the frame.

        :param parent: Widget (The parent widget where this frame will be placed.)
        :param label: Label (Optional label object to populate the frame.)
        :return: None
        """

        super().__init__(parent)
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

        self._create_widgets()

    def _create_widgets(self) -> None:
        """
        Creates and packs the widgets for the `LabelFrame`.

        Widgets include:
        - Input fields for the label name.
        - Toggle buttons for enabling/disabling conditions.
        - Buttons for saving or deleting the label.

        :return: None
        """

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

        Validates the label's information before saving. Any validation errors
        are raised to ensure data integrity.

        :raises FormValidationError: If required fields are empty or invalid.
        :return: None
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

        This action permanently removes the label and its associated data. Should be used
        with user confirmation to prevent accidental deletions.

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

    def __init__(self, parent,  *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        test_df = DBHandler().search_window_log(start_time=datetime(2025, 1, 16, 0, 0),
                                                end_time=datetime(2025, 3, 17, 0, 0))
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

        Sets up the main application window and tabs for managing the application's functionality.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._main_window = None

    def main_window(self) -> None:
        """
        Creates and displays the main application window.

        This includes:
        - Setting up the tabs for different sections (e.g., Overview, Labels, Settings).
        - Adding navigation and action buttons for user interaction.

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

        This method reloads the content dynamically based on the selected tab index.

        :param event: Event (The event triggered when the selected tab changes.)
        :return: None
        """
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
            case 3:  # FilterTab
                self.update_filter_tab(event.widget.nametowidget(nb.tabs()[tab_index]))
            case 4:  # SettingsTab
                self.update_settings_tab(event.widget.nametowidget(nb.tabs()[tab_index]))

    def update_main_tab(self, tab) -> None:
        """
        Updates the content of the "Overview" tab in the main application window.

        This method reloads or refreshes data displayed in the "Overview" tab, ensuring it reflects
        the most recent state of the application.

        :param tab: Frame (The "Overview" tab to update.)
        :return: None
        """

        # TODO: Content of the tab
        #  Base analysis graph, with update button(F5 shortcut)
        #  Some basic stats, which are configurable as user settings
        #  Possible stats: activity time, pc online time, average key pushes (per time window),
        #  Average activity time (weekday based), ...
        #  Some more advanced features later, like creating own query per field that should be shown.

        MainViewFrame(tab).pack(fill="both", expand=True)


    def update_analysis_tab(self, tab) -> None:
        """
        Updates the content of the "Analysis" tab in the main application window.

        This method prepares the "Analysis" tab by retrieving and displaying relevant
        data and visualizations. It ensures the tab reflects the most recent state
        of analyzed information, such as statistics, graphs, or logs.

        :param tab: Frame (The "Analysis" tab to update.)
        :return: None
        """

        # TODO: This should make user choosable what kind of stuff they want to analys
        #  They should be able to create and access querrys from here,
        #  to analyze their favorite activitys /behaviour.
        #  It will allways include standard analysis, like per label and/or multiple labels,
        #  Weekdays, weeks, daytime, time window
        #  We need analyzes that can combine different ways of searching infos from the database.
        #  also there needs to be time window pre choices like this week, last week, last 3 days whatsover
        #  maybe later advanced conditions for analyzes and labeling.
        #  Like background windows or system time (night/day etc)

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

        This method reloads the list of labels and their associated conditions, ensuring
        the displayed information reflects the current state.

        :param tab: Frame (The tab to update.)
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
        for parent_frame in frame_list:
            parent_frame.flex.toggle_expanded()

    def save_labels(self, event=None) -> None:
        """
        Saves all labels in the "Labels" tab to the database.

        Iterates through all active `LabelFrame` instances, validates their data, and saves
        the labels and their associated conditions to persistent storage. Alerts the user
        to any validation errors.

        :param event: Event (The event triggering the save operation, typically a button press.)
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

        This method dynamically creates a new `LabelFrame` for the user to input and configure
        a new label. It ensures the new label is added to the GUI and prepared for database integration.

        :param event: Event (The event triggering the addition of a new label, typically a button press.)
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
        updates the filter tab
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
        Saves all labels in the "Labels" tab to the database.

        Iterates through all active `LabelFrame` instances, validates their data, and saves
        the labels and their associated conditions to persistent storage. Alerts the user
        to any validation errors.

        :param event: Event (The event triggering the save operation, typically a button press.)
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

        This method ensures that the "Settings" tab reflects the latest configuration options
        and allows users to modify application settings dynamically.

        :param tab: Frame (The "Settings" tab to update.)
        :return: None
        """

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

        Settings are saved for persistence across sessions.

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


def disable_scroll(event):
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


def set_standard_focus_on_window(wind: Window | Toplevel) -> None:
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

    ViewController().sys_tray_manual_label()


if __name__ == "__main__":
    print("Please start with the main.py")

"""
This module manages GUI views and their components.

Features:
- Controls the creation and management of various GUI views.
- Provides classes for custom widgets, such as scrollable frames and condition lists.
- Includes functionality to handle user interactions and database updates.

Author: sora7672
"""
__author__ = 'sora7672'

from datetime import datetime
from tkinter.ttk import Combobox
import ttkbootstrap as tb
from ttkbootstrap import Frame, Window, Style
from ttkbootstrap.dialogs import Messagebox
from tkinter import Toplevel, PhotoImage, Widget, ttk, IntVar, BooleanVar, StringVar, Canvas, TclError

from log_handler import get_logger
from window_manager import Label
from conditions import ObjectCondition, ConditionList
from gui_controller import GuiController
from settings_manager import UserSettingsManager


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


class FormValidationError(Exception):
    """
    Exception raised when form validation fails.

    Attributes:
        message: str (Error message detailing the validation issue.)
        error_code: Any (Optional error code associated with the validation.)
        faulty_fields: Any (Fields that failed validation.)
    """

    def __init__(self, message: str = None, error_code=None, faulty_fields=None):
        """
        Initializes the `FormValidationError` exception with a message, error code, and faulty fields.

        :param message: str (Custom error message. Defaults to a generic validation error message.)
        :param error_code: Any (Optional error code for the validation error.)
        :param faulty_fields: Any (Optional details about the fields that caused the validation error.)
        :return: None
        """

        self.message = message or (f"The validation was not ok. These fields are not filled properly:\n"
                                   f"{faulty_fields}")
        super().__init__(message)
        self.error_code = error_code


class ScrollableFrame(Frame):
    """
    A scrollable frame widget.

    This widget allows content to exceed the visible area, adding scrollbars for navigation.
    """

    # TODO: weirdly build up frame, needs some refining, because it seems like there is some DUPES
    def __init__(self, parent):
        """
        Initializes the `ScrollableFrame` with a parent widget.

        :param parent: Widget (The parent widget for this scrollable frame.)
        """

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

    def update_scroll_region(self, event=None) -> None:
        """
        Updates the scrollable region of the canvas based on its content.

        :param event: Event (Optional event triggering the update. Defaults to None.)
        :return: None
        """

        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def bind_mouse_scroll(self) -> None:
        """
        Binds mouse scroll events to the canvas for vertical scrolling.

        :return: None
        """

        self.canvas.bind_all("<MouseWheel>", self.on_mouse_scroll)

    def on_mouse_scroll(self, event) -> None:
        """
        Handles mouse scroll events for the canvas.

        :param event: Event (Mouse scroll event.)
        :return: None
        """

        notebook = self.master.master
        selected_tab_id = notebook.select()
        selected_tab_widget = notebook.nametowidget(selected_tab_id)

        if self.master == selected_tab_widget:
            if event.num == 5 or event.delta == -120:
                self.canvas.yview_scroll(1, "units")  # Scroll down
            elif event.num == 4 or event.delta == 120:
                self.canvas.yview_scroll(-1, "units")  # Scroll up


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

        super().__init__(parent, borderwidth=2, relief="solid")
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

        # Upper Frame for Label Name, Manually, Active Checkboxes, and Datetime Label
        upper_frame = Frame(self)
        upper_frame.name = "upper"
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
        delete_btn = tb.Button(upper_frame, text="Delete", width=8, bootstyle="danger")
        delete_btn.grid(row=0, column=5, padx=(170, 5), pady=(5, 0), sticky="e")  # Todo: better align this then with fixed
        delete_btn.bind("<Button-1>", self.delete_label)

        conds_list = None
        if hasattr(self._label, "condition_list"):
            conds_list = self._label.condition_list
        self.all_conditions_list_frame = ConditionListFrame(self, condition_list=conds_list, top_list=True)

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
        settings_tab = ttk.Frame(notebook)

        notebook.add(main_tab, text="Overview")
        notebook.add(analysis_tab, text="Analysis")
        notebook.add(label_tab, text="Label")
        notebook.add(settings_tab, text="Settings")
        notebook.pack(expand=True, fill="both", padx=0, pady=0)
        self.update_main_tab(main_tab)

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
            case 3:  # SettingsTab
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

        label_list = Label.get_all_labels()
        if label_list:
            dropdown_values = list({lab.name for lab in label_list})
        else:
            dropdown_values = ["No labels existing"]
        label_dropdown = tb.Combobox(tab, values=dropdown_values, state="readonly")
        label_dropdown.current(0)
        label_dropdown.bind("<MouseWheel>", disable_scroll)
        label_dropdown.pack(padx=10, pady=10)

    def update_label_tab(self, tab) -> None:
        """
        Updates the content of the "Labels" tab.

        This method reloads the list of labels and their associated conditions, ensuring
        the displayed information reflects the current state.

        :param tab: Frame (The tab to update.)
        :return: None
        """

        # FIXME: seems like there can happen to be multiple of the same label,
        #  if saved over under specific(unknown) conditions
        scrollable_frame = ScrollableFrame(tab)
        scrollable_frame.pack(fill="both", expand=True)

        for lab in Label.get_all_labels():
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

            tab_frame = event.widget.master.master
            btn_frame = event.widget.master
            btn_frame.pack_forget()
            n_lab = LabelFrame(parent=tab_frame)
            n_lab.pack(fill="x", padx=10, pady=5)
            btn_frame.pack(fill="x", padx=5, pady=5)

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

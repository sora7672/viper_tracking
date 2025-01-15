"""
Main module for handling all aspects of logging windows and managing labels.

This module includes:
- Window tracking functionality.
- Label assignment to windows based on conditions.
- Integration with the database for storing window logs.

Author: sora7672
"""
__author__ = 'sora7672'

from win32gui import GetForegroundWindow, GetWindowText
from win32process import GetWindowThreadProcessId
from psutil import Process, NoSuchProcess
from db_connector import DBHandler
from threading import Thread, Lock
from time import sleep
from config_manager import interval_windows, threads_are_stopped
from log_handler import get_logger
from conditions import ObjectCondition, ConditionList
from datetime import datetime

window_thread: Thread = None
# TODO: Add this to the config
untracked_types = []
repl_chars = "–—-"
removable_chars = "._-,!?;: "


class WinInfo:
    """
    Represents information about a foreground window.

    This class provides a consistent structure for storing window data,
    including metadata such as process ID, title, and associated labels.

    Attributes:
        creation_datetime (datetime): Timestamp of when the instance was created.
        process_id (int): ID of the associated process.
        window_type (str): Type of the window (e.g., application name).
        window_title (str): Title of the window.
        window_text_words (list[str]): Words extracted from the window text.
        _label_list (list[str]): Labels associated with the window.
    """

    def __init__(self) -> None:
        self.creation_datetime: datetime = datetime.now()
        self.process_id: int = 0
        self.window_type: str = ""
        self.window_title: str = ""
        self.window_text_words: list[str] = []
        self._label_list: list[int] = []

    def __str__(self):
        return str(self.__dict__)

    def fill_self(self) -> None:
        """
        Gathers all relevant information about the active foreground window.

        If the process ID cannot be determined, an error is logged, and the operation is aborted.
        Handles special cases for untracked window types.

        :return: None
        """

        a_win = GetForegroundWindow()
        self.window_title = GetWindowText(a_win)
        _, self.process_id = GetWindowThreadProcessId(a_win)
        # TODO: Test this. Should fix the problem with broken pids
        try:
            self.window_type = Process(self.process_id).name()
        except NoSuchProcess | ValueError as e:
            get_logger().error(f"WinInfo object could not be filled properly: {e}")
            del self
            return
        # # # # # Old error, maybe fixed # # # #
        #
        #     Exception in thread Thread-6 (window_tracker):
        #     Traceback (most recent call last):
        #       File "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\_pswindows.py", line 727, in wrapper
        #         return fun(self, *args, **kwargs)
        #                ^^^^^^^^^^^^^^^^^^^^^^^^^^
        #       File "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\_pswindows.py", line 989, in create_time
        #         _user, _system, created = cext.proc_times(self.pid)
        #                                   ^^^^^^^^^^^^^^^^^^^^^^^^^
        #     ProcessLookupError: [Errno 3] assume no such process (originated from OpenProcess -> ERROR_INVALID_PARAMETER)
        #
        #     During handling of the above exception, another exception occurred:
        #
        #     Traceback (most recent call last):
        #       File "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\__init__.py", line 355, in _init
        #         self.create_time()
        #       File "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\__init__.py", line 757, in create_time
        #         self._create_time = self._proc.create_time()
        #                             ^^^^^^^^^^^^^^^^^^^^^^^^
        #       File "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\_pswindows.py", line 729, in wrapper
        #         raise convert_oserror(err, pid=self.pid, name=self._name)
        #     psutil.NoSuchProcess: process no longer exists (pid=1963797664)
        #
        #     During handling of the above exception, another exception occurred:
        #
        #     Traceback (most recent call last):
        #       File "C:\Users\s0rab\AppData\Local\Programs\Python\Python312\Lib\threading.py", line 1073, in _bootstrap_inner
        #         self.run()
        #       File "C:\Users\s0rab\AppData\Local\Programs\Python\Python312\Lib\threading.py", line 1010, in run
        #         self._target(*self._args, **self._kwargs)
        #       File "C:\git\python\viper_tracking\src\window_manager.py", line 417, in window_tracker
        #         WinInfo().fill_self()
        #       File "C:\git\python\viper_tracking\src\window_manager.py", line 50, in fill_self
        #         self.window_type = Process(self.process_id).name()
        #                            ^^^^^^^^^^^^^^^^^^^^^^^^
        #       File "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\__init__.py", line 319, in __init__
        #         self._init(pid)
        #       File "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\__init__.py", line 368, in _init
        #         raise NoSuchProcess(pid, msg=msg)
        #     psutil.NoSuchProcess: process PID not found (pid=1963797664)
        # # # # # #  error no 2. # # # # # # #
        # Exception in thread
        # Thread - 6(window_tracker):
        # Traceback(most
        # recent
        # call
        # last):
        # File
        # "C:\Users\s0rab\AppData\Local\Programs\Python\Python312\Lib\threading.py", line
        # 1073, in _bootstrap_inner
        # self.run()
        #
        # File
        # "C:\Users\s0rab\AppData\Local\Programs\Python\Python312\Lib\threading.py", line
        # 1010, in run
        # self._target(*self._args, **self._kwargs)

        #
        # File
        # "C:\git\python\viper_tracking\src\window_manager.py", line
        # 530, in window_tracker
        # WinInfo().fill_self()
        # File
        # "C:\git\python\viper_tracking\src\window_manager.py", line
        # 50, in fill_self
        # self.window_type = Process(self.process_id).name()
        # ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^
        # File
        # "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\__init__.py", line
        # 319, in __init__
        # self._init(pid)
        # File
        # "C:\git\python\viper_tracking\.venv\Lib\site-packages\psutil\__init__.py", line
        # 330, in _init
        # raise ValueError(msg)
        # ValueError: pid
        # must
        # be
        # a
        # positive
        # integer(got - 1827508448)

        if self.window_type not in untracked_types:
            for r_char in repl_chars:
                self.window_title = self.window_title.replace(r_char, "-")
            tmp_segments = self.window_title.split(" - ")
            for i in range(len(tmp_segments)):
                tmp_segments[i] = tmp_segments[i].strip(removable_chars)

            win_words = tmp_segments.copy()
            for rem in removable_chars:
                tmp_segments = win_words.copy()
                win_words = []
                for t_segm in tmp_segments:
                    win_words.extend(t_segm.split(rem))

            self.window_text_words = list(dict.fromkeys(win_words))
            self.set_labels()
            self.write_to_db()

    def set_labels(self) -> None:
        """
        Assigns labels to the window by evaluating all defined conditions.

        Labels are applied if their conditions are met or if they are marked as manual.

        :return: None
        """

        for lab in Label.get_all_labels():
            lab.check_and_add_to_window(self)

    def write_to_db(self):
        """
        Saves the current window's information to the database.

        :return: None
        """

        DBHandler().add_window_log(self.as_dict())

    def add_label(self, value):
        """
        Adds a label name to the window object if it does not already exist.

        :param value: str (The label name to be added.)
        :return: self (For chaining method calls.)
        """

        if value not in self.label_list:
            self._label_list.append(value)
        return self

    def as_dict(self) -> dict:
        """
        Converts the window's attributes into a dictionary.

        :return: dict (A dictionary of the window's attributes.)
        """

        return dict({"creation_datetime": self.creation_datetime,
                     "window_type": self.window_type, "window_title": self.window_title,
                     "window_text_words": self.window_text_words,
                     "label_list": self._label_list})

    @property
    def label_list(self) -> list[int]:
        """
        Returns the list of labels associated with the window.

        :return: list[str]
        """

        return self._label_list


class Label:
    """
    Represents a label that can be applied to windows based on conditions.

    This class supports:
    - Assigning labels to windows.
    - Managing conditions for label assignment.
    - Interacting with the database for saving, updating, and retrieving labels.

    Thread-safe implementation ensures consistency when multiple threads modify labels.
    """

    _label_list = []
    _lock = Lock()

    def __init__(self, name: str, manually: bool = False, condition_list: ConditionList | None = None,
                 active: bool = True, creation_datetime=None, db_id=None):
        self.lock = Lock()
        self._name: str = name
        self._manually = manually
        self._active = active
        # todo: simplyfy with just conditionlist param?
        self._condition_list: ConditionList | None = condition_list or None
        self._creation_datetime = datetime.now() if creation_datetime is None else creation_datetime
        self._id = db_id

        if self._id is None and (self._condition_list is not None or self._manually):
            self.add_to_db()
        get_logger().debug("(CLASS) LABEL lock use")
        with Label._lock:
            Label._label_list.append(self)
        get_logger().debug("(CLASS) LABEL lock release")

    @property
    def condition_list(self) -> ConditionList:
        with self.lock:
            return self._condition_list

    @condition_list.setter
    def condition_list(self, condition: ConditionList | ObjectCondition | None) -> None:
        with self.lock:
            if isinstance(self._condition_list, ObjectCondition):
                self._condition_list = ConditionList(condition)
            else:
                self._condition_list = condition

    @property
    def id(self):
        with self.lock:
            return self._id

    @property
    def name(self):
        with self.lock:
            return self._name

    @name.setter
    def name(self, name: str):
        with self.lock:
            self._name = name

    @property
    def manually(self):
        with self.lock:
            return self._manually

    @manually.setter
    def manually(self, manually: bool):
        with self.lock:
            self._manually = manually

    @property
    def active(self):
        with self.lock:
            return self._active

    @active.setter
    def active(self, active: bool):
        with self.lock:
            self._active = active

    @property
    def creation_datetime(self):
        with self.lock:
            return self._creation_datetime

    def enable(self):
        """
        Activates the label.

        Sets the label's `active` property to True, marking it as active for application.

        :return: Label (Returns the instance for method chaining.)
        """

        self.active = True
        return self

    def disable(self):
        """
        Deactivates the label.

        Sets the label's `active` property to False, marking it as inactive for application.

        :return: Label (Returns the instance for method chaining.)
        """

        self.active = False
        return self

    # FIXME: check all propertys to be used properly, changed a lot of them
    def get_as_dict(self):
        """
        Converts the label's attributes into a dictionary.

        :return: dict (A dictionary of the label's attributes.)
        """

        get_logger().debug(f"LABEL {self._name} lock use")
        with self.lock:
            tmp_dict = {"id": self._id, "name": self._name, "manually": self._manually, "active": self._active,
                        "conditions": self._condition_list.to_dict() if self._condition_list else None,
                        "creation_datetime": self._creation_datetime}

        get_logger().debug(f"LABEL {self._name} lock release")
        return tmp_dict

    def add_to_db(self):
        """
        Adds the Label into the database.
        Enables chain method casting.
        :return: self
        """
        get_logger().debug(f"LABEL {self._name} lock use")
        with self.lock:
            if self._id is not None:
                get_logger().warning("Label was already added to the database.")
            if not self._condition_list and not self._manually:
                get_logger().error("No conditions were provided.")
            else:
                dict_no_id = {"name": self._name, "manually": self._manually, "active": self._active,
                              "conditions": self._condition_list.to_dict() if self._condition_list else None,
                              "creation_datetime": self._creation_datetime}
                self._id = DBHandler().add_label(dict_no_id)

        get_logger().debug(f"LABEL {self._name} lock release")
        return self

    def update_in_db(self):
        """
        Updates the label's information in the database.

        :return: None
        """

        get_logger().debug(f"LABEL {self._name} lock use")
        with self.lock:
            if self._id is not None and self._id != "":
                dict_with_id = {"id": self._id, "name": self._name, "manually": self._manually, "active": self._active,
                                "conditions": self._condition_list.to_dict() if self._condition_list else None,
                                "creation_datetime": self._creation_datetime}
                DBHandler().update_label(dict_with_id)

            else:
                get_logger().error("update_in_db only works if the Label._id is properly set!")
        get_logger().debug(f"LABEL {self._name} lock release")
        return self

    def delete_in_db(self) -> None:
        """
        Deletes the label from the database and removes it from the label list.

        :return: None
        """

        DBHandler().delete_label_by_id(self._id)
        with Label._lock:
            Label._label_list.remove(self)
        with self.lock:
            del self

    def add_conditions(self, *conditions: ObjectCondition | ConditionList):
        """
        Adds a condition to the Label object.
        Enables chain method casting.
        Can add multiple conditions with multiple methode calls.
        :return: self
        """

        get_logger().debug(f"LABEL {self._name} lock use")
        with self.lock:
            if self._condition_list:
                self._condition_list.add(*conditions)
            else:
                self._condition_list = ConditionList(conditions)
        get_logger().debug(f"LABEL {self._name} lock release")
        return self

    def check_and_add_to_window(self, win_info: WinInfo) -> None:
        """
        Evaluates the label's conditions and adds it to the provided window if applicable.

        :param win_info: WinInfo (The window object to evaluate.)
        :return: None
        """

        get_logger().debug(f"LABEL {self._name} lock use")
        with self.lock:
            if self._active and (self._manually or self._condition_list.is_true(win_info)):
                win_info.add_label(self._id)

        get_logger().debug(f"LABEL {self._id} lock release")

    @classmethod
    def get_all_labels(cls) -> list:
        """
        Retrieves all existing labels as a list.

        :return: list[Label] (A list of all label objects.)
        """

        get_logger().debug("(CLASS) LABEL lock use")
        with Label._lock:
            tmp_list = cls._label_list
        get_logger().debug("(CLASS) LABEL lock release")
        return tmp_list

    @classmethod
    def init_all_labels_from_db(cls):
        """
        Initializes all label objects from the database.

        :return: None
        """

        label_dicts = DBHandler().get_all_labels()
        for label_dict in label_dicts:
            if label_dict["condition_json"] == "{}":
                tmp_conditionlist = None
            else:
                tmp_conditionlist = ConditionList.from_json(label_dict["condition_json"])

            Label(name=label_dict["name"], manually=label_dict["manually"], db_id=label_dict["id"],
                  active=label_dict["active"], creation_datetime=label_dict["creation_datetime"],
                  condition_list=tmp_conditionlist)


def window_tracker() -> None:
    """
    Tracks the active foreground window and logs its details periodically.

    This function runs in a thread and checks for new windows at intervals specified in the configuration.

    :return: None
    """

    do_stop = False
    while not threads_are_stopped():
        inter = interval_windows()
        if inter % 5 != 0:
            raise ValueError(f'Unexpected input interval! Needs to be multiple of 5: {inter}')
        fifth_timer = inter // 5

        for i in range(fifth_timer):
            sleep(5)
            if threads_are_stopped():
                do_stop = True
                break
        if do_stop:
            break
        WinInfo().fill_self()
    get_logger().debug("window_tracker() end")


def start_window_tracker() -> None:
    """
    Starts the window tracking functionality in a separate thread.

    :return: None
    """

    global window_thread
    window_thread = Thread(target=window_tracker)
    window_thread.start()
    get_logger().debug("window_thread.start()")


# # # # External call functions for less import in other files # # # #
def stop_done() -> bool:
    """
    Stops the window tracking thread and waits for it to finish.

    :return: bool (True when the thread has stopped.)
    """

    global window_thread
    window_thread.join()
    return True


def init_all_labels_from_db() -> None:
    """
    Initializes all labels from the database.

    :return: None
    """

    Label.init_all_labels_from_db()


def update_all_labels_to_db() -> None:
    """
    Updates all labels in the database. Useful for saving label states before exiting.

    :return: None
    """

    for lab in Label.get_all_labels():
        lab.update_in_db()


if __name__ == "__main__":
    print("Please start with the main.py")



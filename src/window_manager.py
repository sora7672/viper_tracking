"""

Author: sora7672
"""

# TODO: Minimize the imports!
from win32gui import GetForegroundWindow, GetWindowText
from win32process import GetWindowThreadProcessId
from psutil import Process
from db_connector import DBHandler
from threading import Thread, Lock
from time import time, sleep
from config_manager import interval_windows, threads_are_stopped
from log_handler import get_logger


window_thread: Thread = None

# TODO: Add this to the config
untracked_types = []
repl_chars = "–—-"
removable_chars = "._-,!?;: "


class WinInfo:
    """
    Saves all infos from a read in foreground window
    This is a class for collecting data in one object, to access it easier
    and have the same structure all time.
    """
    def __init__(self):
        self.timestamp: float = 0
        self.process_id: int = 0
        self.window_type: str = ""
        self.window_title: str = ""
        self.window_text_words: list[str] = []
        self._label_list: list[str] = []

    def __str__(self):
        return str(self.__dict__)

    def fill_self(self):
        """
        Grabs all infos needed from the active window.
        Maybe later some extension with background windows too.
        """
        a_win = GetForegroundWindow()
        self.window_title = GetWindowText(a_win)
        _, self.process_id = GetWindowThreadProcessId(a_win)
        self.window_type = Process(self.process_id).name()

        # FIXME: If the application gets closed in the time between grabbing the process ID and checking it, results in this error:
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
        #

        if self.window_type not in untracked_types:

            self.timestamp = time()

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

    def set_labels(self):
        """
        Loops through all labels,
        which loop through all their conditions to check
        if the window is ok to have this label.
        """
        for lab in Label.get_all_labels():
            lab.check_and_add_to_window(self)

    def write_to_db(self):
        """
        Simple call to add it to the database
        """
        DBHandler().add_window_log(self.get_as_dict())

    def add_label(self, value):
        """
        Adds a new label to this object.
        No duplicated labels are added.
        (Could happen if multiple conditions
        for the same name are met)
        Enables chain method casting.
        :param value: str
        :return: self
        """
        if value.lower() not in [item.lower() for item in self.label_list]:
            self._label_list.append(value)
        return self

    def get_as_dict(self) -> dict:
        """
        Just returns important attributes as a dict for further usage.
        :return: dict
        """
        return dict({"timestamp": self.timestamp,
                     "window_type": self.window_type, "window_title": self.window_title,
                     "window_text_words": self.window_text_words,
                     "label_list": self._label_list})

    @property
    def label_list(self) -> list[str]:
        """
        Returns a list of all labels in this object
        :return: list[str]
        """
        return self._label_list


class Condition:
    """
    This conditions can be added to the Label objects.
    Its purpose is to make sure the checks allways run the same.
    allowed condition_type = "window_type", "window_title", "window_text_words","timestamp"\n
    allowed condition_check = "gt", "lt", "lte", "gte", "eq", "neq", "in", "nin"
    """

    _possible_condition_types = ["window_type", "window_title","window_text_words",
                                 "timestamp"]
    _possible_condition_checks = ["gt", "lt", "lte", "gte", "eq", "neq", "in", "nin"]

    def __init__(self, condition_type: str, condition_check: str, condition_value: any):
        self.condition_type = condition_type if condition_type in self._possible_condition_types else None
        self.condition_check = condition_check if condition_check in self._possible_condition_checks else None
        self.condition_value = condition_value

        if self.condition_type is None or self.condition_check is None:
            raise ValueError("Condition type and/or condition check were provided with wrong values.")
        if self.condition_type == "timestamp" and self.condition_check not in self._possible_condition_checks[0:3]:
            raise ValueError("Timestamp condition_type was provided with wrong condition_check.")
        elif self.condition_type != "timestamp" and self.condition_check in self._possible_condition_checks[0:3]:
            raise ValueError("Text checks cant be done with gt,lt,lte,gte!")

    def check(self, window: WinInfo) -> bool:
        """
        Check on a WinInfo object, if the set condition are correct and
        return True or False based on that.
        :param window: WinInfo object
        :return: bool
        """
        match self.condition_check:
            case "gt":
                if getattr(window, self.condition_type) < self.condition_value:
                    return True

            case "lt":
                if getattr(window, self.condition_type) > self.condition_value:
                    return True

            case "lte":
                if getattr(window, self.condition_type) <= self.condition_value:
                    return True

            case "gte":
                if getattr(window, self.condition_type) >= self.condition_value:
                    return True

            case "eq":
                if getattr(window, self.condition_type) == self.condition_value:
                    return True

            case "neq":
                if getattr(window, self.condition_type) != self.condition_value:
                    return True

            case "in":
                if str(self.condition_value).lower() in getattr(window, self.condition_type).lower():
                    return True

            case "nin":
                if str(self.condition_value).lower() not in getattr(window, self.condition_type).lower():
                    return True

            case _:
                raise ValueError("Condition check was provided with wrong values.")
        return False

    def get_as_dict(self):
        """
         Just returns important attributes as a dict for further usage.
         :return: dict
         """
        return {"condition_type": self.condition_type, "condition_check": self.condition_check,
                "condition_value": self.condition_value}

    @staticmethod
    def get_condition_types() -> list[str]:
        return Condition._possible_condition_types

    @staticmethod
    def get_condition_checks() -> list[str]:
        return Condition._possible_condition_checks

class Label:
    """
    This class objects hold information about when to apply a Label to a WinInfo object
    and have methods to append & check these. Can have multiple conditions that need to be True to append.
    """
    _label_list = []
    _lock = Lock()

    # FIXME: all attributes need to be protected and have a method to return, for thread safety
    def __init__(self, name: str, manually: bool = False, db_id=None, condition_list: list[Condition] = None,
                 active: bool = True, creation_timestamp=None):
        self.lock = Lock()
        self.name: str = name
        self.manually = manually
        self._active = active
        self._condition_list: list[Condition] = condition_list or []
        self._creation_timestamp = time() if creation_timestamp is None else creation_timestamp
        self._id = db_id

        if self._id is None and (len(self._condition_list) >= 1 or self.manually):
            self.add_to_db()
        get_logger().debug("(CLASS) LABEL lock use")
        with Label._lock:
            Label._label_list.append(self)
        get_logger().debug("(CLASS) LABEL lock release")

    def get_as_dict(self):
        """
        Just returns important attributes as a dict for further usage.
        :return: dict
        """
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            tmp_dict = {"id": self._id, "name": self.name, "manually": self.manually, "active": self._active,
                        "conditions": [cond.get_as_dict() for cond in self._condition_list],
                        "creation_timestamp": self._creation_timestamp}

        get_logger().debug(f"LABEL {self.name} lock release")
        return tmp_dict

    def add_to_db(self):
        """
        Adds the Label into the database.
        Enables chain method casting.
        :return: self
        """
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            if self._id is not None:
                get_logger().warning("Label was already added to the database.")
            if (self._condition_list is None or len(self._condition_list) == 0) and not self.manually:
                get_logger().error("No conditions were provided.")
            else:
                dict_no_id = {"name": self.name, "manually": self.manually, "active": self._active,
                              "conditions": [cond.get_as_dict() for cond in self._condition_list],
                              "creation_timestamp": self._creation_timestamp}
                self._id = DBHandler().add_label(dict_no_id)

        get_logger().debug(f"LABEL {self.name} lock release")
        return self

    def update_in_db(self):
        """
        Updates the label object in the database.
        When its set inactive for example.
        """
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            if self._id is not None and self._id != "":
                dict_with_id = {"id": self._id, "name": self.name, "manually": self.manually, "active": self._active,
                                "conditions": [cond.get_as_dict() for cond in self._condition_list],
                                "creation_timestamp": self._creation_timestamp}
                DBHandler().update_label(dict_with_id)

            else:
                get_logger().error("update_in_db only works if the Label._id is properly set!")
        get_logger().debug(f"LABEL {self.name} lock release")
        return self

    def enable(self):
        """
        Sets the label active for checking.
        Purpose of this is, to create multiple labels,
        that can be turned on and off for adding to the WinInfo object.
        Enables chain method casting.
        :return: self
        """
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            self._active = True
        get_logger().debug(f"LABEL {self.name} lock release")
        return self

    def disable(self):
        """
        Sets the label inactive for checking.
        Purpose of this is, to create multiple labels,
        that can be turned on and off for adding to the WinInfo object.
        Enables chain method casting.
        :return: self
        """
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            self._active = False
        get_logger().debug(f"LABEL {self.name} lock release")
        return self

    def add_conditions(self, *conditions: Condition):
        """
        Adds a condition to the Label object.
        Enables chain method casting.
        Can add multiple conditions with multiple methode calls.
        :return: self
        """
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            for cond in conditions:
                self._condition_list.append(cond)
        get_logger().debug(f"LABEL {self.name} lock release")
        return self

    def check_and_add_to_window(self, window: WinInfo) -> None:
        """
        Runs all Condition checks from the Label Object on the WinInfo object.
        :param window: WinInfo
        :return: None
        """
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            if self._active:
                if self.manually:
                    window.add_label(self.name)
                else:
                    set_label = True
                    for condition in self._condition_list:
                        if condition.check(window):
                            continue
                        else:
                            set_label = False
                    if set_label:
                        window.add_label(self.name)
        get_logger().debug(f"LABEL {self.name} lock release")

    def get_creation_timestamp(self):
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            tmp_date = self._creation_timestamp
        get_logger().debug(f"LABEL {self.name} lock release")
        return tmp_date

    def get_condition_list(self):
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            tmp_list = self._condition_list
        get_logger().debug(f"LABEL {self.name} lock release")
        return tmp_list

    @property
    def is_active(self):
        get_logger().debug(f"LABEL {self.name} lock use")
        with self.lock:
            tmp_bool = self._active
        get_logger().debug(f"LABEL {self.name} lock release")
        return tmp_bool

    @classmethod
    def get_all_labels(cls) -> list:
        """
        Returns all existing labels as list.
        :return: list[Label]
        """
        get_logger().debug("(CLASS) LABEL lock use")
        with Label._lock:
            tmp_list = cls._label_list
        get_logger().debug("(CLASS) LABEL lock release")
        return tmp_list

    @classmethod
    def init_all_labels_from_db(cls):
        """
           This function is for initializing the Label objects from the database.
           :return: None
           """
        label_dicts = DBHandler().get_all_labels()
        for label_dict in label_dicts:
            # self, name: str, manually: bool = False, db_id = None, condition_list: list[Condition] = None):
            tmp_label = Label(name=label_dict["name"], manually=label_dict["manually"], db_id=label_dict["id"],
                              active=label_dict["active"], creation_timestamp=label_dict["creation_timestamp"])

            tmp_label.add_conditions(*[Condition(cond["condition_type"], cond["condition_check"], cond["condition_value"])
                                       for cond in label_dict["conditions"]])


def window_tracker() -> None:
    """
    This function is for adding to teh thread to run it properly.
    :return: None
    """

    while not threads_are_stopped():
        inter = interval_windows()
        if inter % 5 != 0:
            raise Exception(f'Unexpected input interval! Needs to be multiple of 5: {inter}')
        fifth_timer = inter // 5
        do_stop = False
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
    This function gets called from outside to start the window_tracker module thread.
    :return: None
    """

    global window_thread
    window_thread = Thread(target=window_tracker)
    window_thread.start()
    get_logger().debug("window_thread.start()")


# # # # External call functions for less import in other files # # # #
def stop_done() -> bool:
    """
    This function gets called from outside to stop the window_tracker module thread.
    :return: bool
    """
    global window_thread
    window_thread.join()
    return True


def init_all_labels_from_db() -> None:
    """
    This function is for initializing the Label objects from the database.
    :return: None
    """
    Label.init_all_labels_from_db()


def update_all_labels_to_db() -> None:
    """
    This imported function loops through all labels and updates them in the database.
    Was created in case we want to save all labels in DB on exit of the app.
    :return: None
    """
    for lab in Label.get_all_labels():
        lab.update_in_db()


if __name__ == "__main__":
    print("Please start with the main.py")



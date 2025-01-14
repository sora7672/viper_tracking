"""

Author: sora7672
"""

# TODO: Minimize the imports!
from win32gui import GetForegroundWindow, GetWindowText
from win32process import GetWindowThreadProcessId
from psutil import Process, NoSuchProcess
from db_connector import DBHandler
from threading import Thread, Lock
from time import time, sleep
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
    Saves all infos from a read in foreground window
    This is a class for collecting data in one object, to access it easier
    and have the same structure all time.
    """
    def __init__(self):
        self.creation_datetime: datetime = datetime.now()
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
        DBHandler().add_window_log(self.as_dict())

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

    def as_dict(self) -> dict:
        """
        Just returns important attributes as a dict for further usage.
        :return: dict
        """
        return dict({"creation_datetime": self.creation_datetime,
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


class Label:
    """
    This class objects hold information about when to apply a Label to a WinInfo object
    and have methods to append & check these. Can have multiple conditions that need to be True to append.
    """
    _label_list = []
    _lock = Lock()

    def __init__(self, name: str, manually: bool = False, condition_list: ConditionList | None = None,
                 active: bool = True, creation_datetime=None, db_id=None):
        self.lock = Lock()
        self._name: str = name
        self._manually = manually
        self._active = active
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
        :return: self
        """

        self.active = True
        return self

    def disable(self):
        """
        :return: self
        """

        self.active = False
        return self

    # FIXME: check all propertys to be used properly, changed a lot of them
    def get_as_dict(self):
        """
        Just returns important attributes as a dict for further usage.
        :return: dict
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
        Updates the label object in the database.
        When its set inactive for example.
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

    def delete_in_db(self):
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
        Runs all Condition checks from the Label Object on the WinInfo object.
        :param win_info: WinInfo
        :return: None
        """
        get_logger().debug(f"LABEL {self._name} lock use")
        with self.lock:
            if self._active and (self._manually or self._condition_list.is_true(win_info)):
                win_info.add_label(self._name)

        get_logger().debug(f"LABEL {self._name} lock release")

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
            if label_dict["condition_json"] == "{}":
                tmp_conditionlist = None
            else:
                tmp_conditionlist = ConditionList.from_json(label_dict["condition_json"])

            Label(name=label_dict["name"], manually=label_dict["manually"], db_id=label_dict["id"],
                  active=label_dict["active"], creation_datetime=label_dict["creation_datetime"],
                  condition_list=tmp_conditionlist)


def window_tracker() -> None:
    """
    This function is for adding to teh thread to run it properly.
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
    # Label(name="python learning", manually = False, db_id=None, condition_list=[
    #     Condition("window_text_words", "in", "W3Schools"),
    # Condition("window_text_words", "in", "python")])

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



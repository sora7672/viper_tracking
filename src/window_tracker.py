import threading

# TODO: Minimize the imports!
import win32gui
import win32process
import psutil
import db_connector
from threading import Thread, Event, Lock
from time import time, sleep
from config_manager import interval_windows, threads_are_stopped




window_thread: Thread = None

# temp vars, later replaced with a configuration read in file
# TODO: Add this to the config
viper_settings = {"debug": False}
removeable_title_segments = ["Mozilla Firefox"]  # TODO: Need this? Maybe cut the type and check for its words and remove?
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
        self.window_text_segments: list[str] = []
        self.window_text_words: list[str] = []
        self._label_list: list[str] = []
        self._activity: bool = False

    def __str__(self):
        return str(self.__dict__)

    def fill_self(self):
        a_win = win32gui.GetForegroundWindow()
        self.window_title = win32gui.GetWindowText(a_win)
        _, self.process_id = win32process.GetWindowThreadProcessId(a_win)
        self.window_type = psutil.Process(self.process_id).name()

        if self.window_type not in untracked_types:

            self.timestamp = time()

            for r_char in repl_chars:
                self.window_title = self.window_title.replace(r_char, "-")
            tmp_segments = self.window_title.split(" - ")
            for i in range(len(tmp_segments)):
                tmp_segments[i] = tmp_segments[i].strip(removable_chars)

            out_segments = [t_segm for t_segm in tmp_segments if not
                            any(r_title in t_segm for r_title in removeable_title_segments)]

            win_words = out_segments.copy()
            for rem in removable_chars:
                tmp_segments = win_words.copy()
                win_words = []
                for t_segm in tmp_segments:
                    win_words.extend(t_segm.split(rem))

            self.window_text_segments = list(dict.fromkeys(out_segments))
            self.window_text_words = list(dict.fromkeys(win_words))
            self.set_labels()
            self.write_to_db()


    def set_labels(self):
        for lab in Label.get_all_labels():
            lab.check_and_add_to_window(self)

    def write_to_db(self):
        db_connector.add_window_dict(self.get_as_dict())

    def add_label(self, value):
        """
        Adds a new label to this object.
        No duplicated labels are added.
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
        return dict({"timestamp": self.timestamp, "activity": self._activity, "process_id": self.process_id,
                     "window_type": self.window_type, "window_title": self.window_title,
                     "window_text_segments": self.window_text_segments, "window_text_words": self.window_text_words,
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
    allowed condition_type = "window_type", "window_title", "window_text_segments", "window_text_words","timestamp"\n
    allowed condition_check = "gt", "lt", "lte", "gte", "eq", "neq", "in", "nin"
    """

    _possible_condition_types = ["window_type", "window_title", "window_text_segments", "window_text_words",
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


class Label:
    """
    This class objects hold information about when to apply a Label to a WinInfo object
    and have methods to append & check these. Can have multiple conditions that need to be True to append.
    """
    _label_list = []
    _lock = Lock()

    def __init__(self, name: str, manually: bool = False, db_id=None, condition_list: list[Condition] = None,
                 active: bool = True):
        self.lock = Lock()
        self.name: str = name
        self.manually = manually
        self._active = active
        self._condition_list: list[Condition] = condition_list or []

        self._id = db_id

        if self._id is None and (len(self._condition_list) >= 1 or self.manually):
            self.add_to_db()
        with Label._lock:
            Label._label_list.append(self)

    def get_as_dict(self):
        """
        Just returns important attributes as a dict for further usage.
        :return: dict
        """
        with self.lock:
            return {"_id": self._id, "name": self.name, "manually": self.manually, "active": self._active,
                    "conditions": [cond.get_as_dict() for cond in self._condition_list]}

    def add_to_db(self):
        """
        Adds the Label into the database.
        Enables chain method casting.
        :return: self
        """
        with self.lock:
            if self._id is not None:
                raise Exception("Label was already added to the database.")
            if (self._condition_list is None or len(self._condition_list) == 0) and not self.manually:
                raise ValueError("No conditions were provided.")
            else:
                dict_no_id = {"name": self.name, "manually": self.manually, "active": self._active,
                              "conditions": [cond.get_as_dict() for cond in self._condition_list]}
                self._id = db_connector.add_label(dict_no_id)
                return self

    def update_in_db(self):
        with self.lock:
            if self._id is not None and self._id != "":
                dict_with_id = {"_id": self._id, "name": self.name, "manually": self.manually, "active": self._active,
                                "conditions": [cond.get_as_dict() for cond in self._condition_list]}
                db_connector.update_label(dict_with_id)

            else:
                raise ValueError("update_in_db only works if the Label._id is properly set!")

    def enable(self):
        """
        Sets the label active for checking.
        Purpose of this is, to create multiple labels,
        that can be turned on and off for adding to the WinInfo object.
        Enables chain method casting.
        :return: self
        """
        with self.lock:
            self._active = True
            return self

    def disable(self):
        """
        Sets the label inactive for checking.
        Purpose of this is, to create multiple labels,
        that can be turned on and off for adding to the WinInfo object.
        Enables chain method casting.
        :return: self
        """
        with self.lock:
            self._active = False
            return self

    def add_conditions(self, *conditions: Condition):
        """
        Adds a condition to the Label object.
        Enables chain method casting.
        Can add multiple conditions with multiple methode calls.
        :return: self
        """
        with self.lock:
            for cond in conditions:
                self._condition_list.append(cond)
            return self

    def check_and_add_to_window(self, window: WinInfo) -> None:
        """
        Runs all Condition checks from the Label Object on the WinInfo object.
        :param window: WinInfo
        :return: None
        """
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

    @property
    def is_active(self):
        with self.lock:
            return self._active

    @classmethod
    def get_all_labels(cls) -> list:
        """
        Returns all existing labels as list.
        :return: list[Label]
        """
        with Label._lock:
            return cls._label_list

    @classmethod
    def init_all_labels_from_db(cls):
        """
           This function is for initializing the Label objects from the database.
           :return: None
           """
        label_dicts = db_connector.get_label_list()
        for label_dict in label_dicts:
            # self, name: str, manually: bool = False, db_id = None, condition_list: list[Condition] = None):
            tmp_label = Label(name=label_dict["name"], manually=label_dict["manually"], db_id=label_dict["_id"],
                              active=label_dict["active"])

            tmp_label.add_conditions(*[Condition(cond["condition_type"], cond["condition_check"], cond["condition_value"])
                                       for cond in label_dict["conditions"]])


def tracker() -> None:
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


def start_window_tracker() -> None:
    """
    This function gets called from outside to start the window_tracker module thread.
    :return: None
    """

    global window_thread
    window_thread = Thread(target=tracker)
    window_thread.start()


# # # # External call functions for less import in other files # # # #
def stop_done() -> bool:
    """
    This function gets called from outside to stop the window_tracker module thread.
    :return: None
    """
    global window_thread
    window_thread.join()
    return True


def init_all_labels_from_db():
    Label.init_all_labels_from_db()


def update_all_labels_to_db():
    for lab in Label.get_all_labels():
        lab.update_in_db()


if __name__ == "__main__":
    print("Please start with the main.py")
    # one time only test setup:
    # Label("Mongo DB", condition_list=[Condition("window_title", "in", "mongo")])
    # Label("Java", condition_list=[Condition("window_title", "in", "java")])
    # Label("Python", condition_list=[Condition("window_title", "in", ".py")])
    # Label("Python", condition_list=[Condition("window_title", "in", "python")])
    # Label("Research", condition_list=[Condition("window_title", "in", "chatgpt")])


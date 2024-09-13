
import win32gui
import win32process
import psutil
import db_writer
from threading import Thread, Event, Lock
from time import time, sleep




# TODO:
#   funktion zum hinzufügen von label bedingungen
#   wenn was hinzugefügt, dann update des tracking threads/microservies/Prozess
#   Manuellle label funktion, wenn aktiv dann schreib bei jedme log das label dazu
#   Wenn inkativ mache das nicht mehr
#   Auswertungen müssen per label, fenster typ, nach text suche, text/word segments
#   oder irgendeiner kombnation dieser machbar sein
#   user activity tracking, bsp. count zeitraum alle 30 sekunden,
#   dort jeweils nach ablauf der zeit eintragen und zählen von maus clicks links, rechts und rad, sowie key push number
#   Advanced conditions, wie z.B. wenn anwendung A hauptfenster & Anwendung B im Hintergrund, dann setz label

# boolean for stopping window readings loop, if set True window tracking stops
stopper = False

window_thread: Thread = None

viper_settings = {"interval": 5, "runtime": 30, "debug": True}
removeable_title_segments = ["Mozilla Firefox"]
untracked_types = []
repl_chars = "–—-"
removable_chars = "._-,!?;: "



class WinInfo:
    def __init__(self):
        self.timestamp: float = 0
        self.process_id: int = 0
        self.window_type: str = ""
        self.window_title: str = ""
        self.window_text_segments: list = []
        self.window_text_words: list = []
        self._label_list: list = []

    def __str__(self):
        return str(self.__dict__)

    @property
    def label_list(self):
        return self._label_list

    def add_label(self, value):
        if value.lower() not in [item.lower() for item in self.label_list]:
            self._label_list.append(value)

    def write_to_db(self):
        pass


class Condition:
    """
    condition_type = "window_type", "window_title", "window_text_segments", "window_text_words","timestamp"\n
    condition_check = "gt", "lt", "lte", "gte", "eq", "neq", "in", "nin"
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


class Label:
    _label_list = []

    def __init__(self, name: str):
        self.name: str = name
        self._condition_list: list[Condition] = []
        Label._label_list.append(self)

    def add_condition(self, condition: Condition):
        self._condition_list.append(condition)
        return self

    def check_label_condition(self, window: WinInfo):
        set_label = True
        for condition in self._condition_list:
            if condition.check(window):
                continue
            else:
                set_label = False
        if set_label:
            window.add_label(self.name)

    @classmethod
    def get_all_labels(cls) -> list:
        return cls._label_list


def win_track():

    tmp_win = WinInfo()
    a_win = win32gui.GetForegroundWindow()
    tmp_win.window_title = win32gui.GetWindowText(a_win)
    _, tmp_win.process_id = win32process.GetWindowThreadProcessId(a_win)
    tmp_win.window_type = psutil.Process(tmp_win.process_id).name()

    if tmp_win.window_type not in untracked_types:

        tmp_win.timestamp = time()

        for r_char in repl_chars:
            tmp_win.window_title = tmp_win.window_title.replace(r_char, "-")
        t_segments = tmp_win.window_title.split(" - ")
        for i in range(len(t_segments)):
            t_segments[i] = t_segments[i].strip(removable_chars)

        out_segments = [t_segm for t_segm in t_segments if not any(r_title in t_segm for r_title in removeable_title_segments)]

        win_words = out_segments.copy()
        for rem in removable_chars:
            tmp_segments = win_words.copy()
            win_words = []
            for t_segm in tmp_segments:
                win_words.extend(t_segm.split(rem))

        tmp_win.window_text_segments = list(dict.fromkeys(out_segments))
        tmp_win.window_text_words = list(dict.fromkeys(win_words))

        for lab in Label.get_all_labels():
            lab.check_label_condition(tmp_win)

        print(tmp_win) if viper_settings["debug"] else None

        #db_writer.add_window_dict(out_entry)


def stop():
    global window_thread
    global stopper

    stopper = True
    window_thread.join()


def tracker():
    global stopper
    while not stopper:
        sleep(viper_settings["interval"])
        if stopper:
            break
        win_track()


def start():
    # add temp labels/conditions
    # Condition(self, condition_type: str, condition_check: str, condition_value: any)

    Label("Mongo DB").add_condition(Condition("window_title", "in", "mongo"))

    global window_thread
    window_thread = Thread(target=tracker)
    window_thread.start()


if __name__ == "__main__":
    print("Please start with the main.py")


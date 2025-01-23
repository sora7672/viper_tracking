"""
Here we handle the storage of data frames from pandas,
the sorting and what else.

Author: sora7672
"""
__author__ = 'sora7672'

from datetime import datetime, timedelta, time
from threading import Lock, Thread
from time import sleep, gmtime, strftime
from pandas import DataFrame, Series
from abc import ABC, abstractmethod

import pandas as pd

from config_manager import threads_are_stopped, stop_program_threads
from db_connector import DBHandler, stop_db, start_db
from helper_classes import Classproperty


class Seconds(int):

    def __new__(cls, value):
        if not isinstance(value, int):
            raise ValueError("Seconds must be initialized with an integer value.")
        return super().__new__(cls, value)

    @property
    def mins(self):
        mins, secs = divmod(self, 60)
        return f"{mins}:{secs}"

    @property
    def hours(self):
        mins, secs = divmod(self, 60)
        hours, mins = divmod(mins, 60)
        return f"{hours}:{mins}:{secs}"

    @property
    def days(self):
        mins, secs = divmod(self, 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        return f"{days}:{hours}:{mins}:{secs}"

    @property
    def weeks(self):
        mins, secs = divmod(self, 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        weeks, days = divmod(days, 7)
        return f"{weeks}:{days}:{hours}:{mins}:{secs}"


class ViperDF:

    def __init__(self, name: str, main_df: DataFrame):
        # Naming should be "name" or "label:blahh" or "app:blahh" if name includes ":" check for app/label
        # and set some flags for further implementation
        self.name = name
        self._lock = Lock()
        self._main_df: DataFrame = main_df
        self.empty = main_df.empty
        if not self._validate_mainframe():
            print("not valid mainframe, created empty DataFrame")
            self.empty = True
        self.analysis_results: dict = {}
        self._is_analyzed = False
        self.is_app_based = name.startswith("app:")
        self.is_label_based = name.startswith("label:")

    def __repr__(self):
        return f"VDF '{self.name}'"

    def __str__(self):
        return f"VDF '{self.name}'"


    def _validate_mainframe(self):
        # Check for all fields in the DF that are needed from the analyses
        needed_columns = ["window_id", "window_type", "window_title", "word_list", "creation_datetime", "activity",
                          "count_key_pressed", "count_mouse_pressed",  "count_direction_key_pressed",
                          "count_char_key_pressed", "count_special_key_pressed", "count_mouse_scrolls",
                          "count_left_mouse_pressed", "count_right_mouse_pressed", "count_middle_mouse_pressed"]
        if all(ncol in self._main_df.columns for ncol in needed_columns):
            return True
        else:
            return False

    def split_data_on_label(self):
        if not self.empty:
            if not self._is_analyzed:
                raise ValueError("Main frame is not analyzed.")

            n_vdf = []
            exploded_df = self._main_df.explode('label_list')
            for lab in self.analysis_results["labels"]["entries"].keys():
                tmp_df = exploded_df[exploded_df['label_list'] == lab]
                window_ids = tuple(tmp_df['window_id'].tolist())
                out_df = self._main_df[self._main_df['window_id'].isin(window_ids)]
                if len(out_df) == self.analysis_results["entry_count"]:
                    # Dont append if the sub DF is the same as the main DF
                    continue
                n_vdf.append(ViperDF(lab, out_df))
                n_vdf[-1].analyze()

            return n_vdf



    def split_data_on_app(self):
        if not self.empty:
            if not self._is_analyzed:
                raise ValueError("Main frame is not analyzed.")

            n_vdf = []

            for w_type in self.analysis_results["apps"]["entries"].keys():
                out_df = self._main_df[self._main_df['window_type'] == w_type]
                if len(out_df) == self.analysis_results["entry_count"]:
                    # Dont append if the sub DF is the same as the main DF
                    continue
                n_vdf.append(ViperDF(w_type, out_df))
                n_vdf[-1].analyze()

            return n_vdf

    def analyze(self):
        """
        calls all protected analyzes functions
        ORDER MATTERS!
        """
        if not self.empty:
            self._time_analysis()
            self._input_analysis()
            self._app_analysis()
            self._label_analysis()

            self._is_analyzed = True

    def _time_analysis(self):
        self._main_df.sort_values(by=["creation_datetime"], ascending=True)
        self.analysis_results["first_datetime"] = self._main_df["creation_datetime"].iloc[0]
        self.analysis_results["last_datetime"] = self._main_df["creation_datetime"].iloc[-1]
        self.analysis_results["time_frame_seconds"] = Seconds(int((self.analysis_results["last_datetime"]
                                                                   - self.analysis_results["first_datetime"])
                                                                  .total_seconds()))

        self.analysis_results["entry_count"] = len(self._main_df)
        self.analysis_results["tracked_seconds"] = Seconds(5 * self.analysis_results["entry_count"])
        self.analysis_results["untracked_seconds"] = Seconds(self.analysis_results["time_frame_seconds"]
                                                             - self.analysis_results["tracked_seconds"])

        self.analysis_results["active_secs"] = Seconds(5 * len(self._main_df[self._main_df["activity"]]))
        self.analysis_results["inactive_secs"] = (self.analysis_results["tracked_seconds"] -
                                                  self.analysis_results["active_secs"])

        self.analysis_results["percent_active"] = round((self.analysis_results["active_secs"]/(
                                                    self.analysis_results["tracked_seconds"]/100)), 2)

    def _input_analysis(self):

        input_columns = [
            "count_key_pressed",
            "count_mouse_pressed",
            "count_direction_key_pressed",
            "count_char_key_pressed",
            "count_special_key_pressed",
            "count_mouse_scrolls",
            "count_left_mouse_pressed",
            "count_right_mouse_pressed",
            "count_middle_mouse_pressed",
            "all_activity_count"
        ]

        only_actives = self._main_df[self._main_df['activity']]
        num_activities = len(only_actives)
        if num_activities == 0:
            all_max = 0
            all_summed = 0
            all_average = 0
            all_active_value = 0
        else:
            all_max = {col: int(only_actives[col].max()) for col in input_columns}
            all_summed = {col: int(only_actives[col].sum()) for col in input_columns}
            all_average = {col: int(all_summed[col] / num_activities) for col in input_columns}
            all_active_value = {col: int((all_max[col] + all_average[col]) / 2) for col in input_columns}

        self.analysis_results["input_max"] = all_max
        self.analysis_results["input_summed"] = all_summed
        self.analysis_results["input_average"] = all_average
        self.analysis_results["input_active_value"] = all_active_value

    def _app_analysis(self):
        app_win_count = self._main_df["window_type"].value_counts().to_dict()
        self.analysis_results["apps"] = {"count_unique": len(app_win_count), "entries": app_win_count}

    def _label_analysis(self):

        all_labels = self._main_df["label_list"].dropna().explode()
        label_counts = all_labels.value_counts().to_dict()
        self.analysis_results["entry_count_labeled"] = len(self._main_df["label_list"].dropna())
        self.analysis_results["entry_count_unlabeled"] = (self.analysis_results["entry_count"]
                                                          - self.analysis_results["entry_count_labeled"])
        self.analysis_results["labels"] = {
            "count_unique": len(label_counts),
            "entries": label_counts
        }


class Analyzer(ABC):
    _all_analyzer = []
    _class_lock = Lock()

    def __init__(self, name: str, main_df: DataFrame):
        self.lock = Lock()

        self._name: str = name.upper()
        self._main_df = main_df
        with Analyzer._class_lock:
            Analyzer._all_analyzer.append(self)

    def __del__(self):
        with Analyzer._class_lock:
            Analyzer._all_analyzer.remove(self)
        del self

    @abstractmethod
    def _analyze(self):
        """ This methode will analyze the data frame according to the analyzer type."""
        pass

    @abstractmethod
    def _refresh_data(self):
        """ This methode will refresh the data frame according to the analyzer type."""
        pass

    def refresh(self):
        """ This method will call the refresh_data and after analyze method to refresh the data frame."""
        self._refresh_data()
        self._analyze()

    @property
    def name(self):
        with self.lock:
            return self._name

    @classmethod
    def get_all_analyzer(cls):
        with cls._class_lock:
            return cls._all_analyzer


class DayAnalyzer(Analyzer):
    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures that StandardAnalyzes follows the singleton pattern.

        :return: StandardAnalyzes (The singleton instance.)
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._db_call = DBHandler().search_window_log
            tmp_df = self._db_call()
            super().__init__(name="DAY_ANALYZER", main_df=tmp_df)
            self._vdf = None
            self._app_vdf_list = None
            self._label_vdf_list = None
            self.empty_df = tmp_df.empty
            self._analyze()

    def _analyze(self):
        """ This methode will analyze the data frame according to the analyzer type."""
        if not self.empty_df:
            self._vdf = ViperDF("DayAnalyzer", self._main_df)
            self._vdf.analyze()
            self._app_vdf_list = self._vdf.split_data_on_app()
            self._label_vdf_list = self._vdf.split_data_on_label()

    def _refresh_data(self):
        """ This methode will refresh the data frame according to the analyzer type."""
        self._main_df = self._db_call()
        self.empty_df = self._main_df.empty

    def print_name(self):
        print(self._name)

    @Classproperty
    def this(self):
        return self._instance


class AnalyzerThread:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._lock = Lock()

            self._check_interval = 60  # Minutes
            self._next_check_timestamp = datetime.now() + timedelta(minutes=self._check_interval)

            self._thread = Thread(target=self._thread_loop)
            self._thread.start()

    def _check_for_action(self):
        """ simple checks for time saved and if its already """
        with self._lock:
            if self._next_check_timestamp >= datetime.now():
                self._next_check_timestamp = datetime.now() + timedelta(minutes=self._check_interval)
                DayAnalyzer.this.refresh()

    def _thread_loop(self):
        do_stop = False
        while not threads_are_stopped():
            inter = 60  # Needs to stay 60
            fifth_timer = inter // 5

            for i in range(fifth_timer):
                sleep(5)
                if threads_are_stopped():
                    do_stop = True
                    break
            if do_stop:
                break
            self._check_for_action()


# # # # External Call functions # # # #
def init_standard_analyzes():
    # ini the threading class, it analyzes on init once.

    pass


if __name__ == "__main__":
    start_db()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)

    test_df = DBHandler().search_window_log(start_time=datetime(2025,1,16,0,0), end_time=datetime(2025,1,17,0,0))


    # FIXME: we need to make all database requests
    #  either return a empty df or handle requests on db different,
    #  because window_logs could be empty on request.
    DayAnalyzer()
    if DayAnalyzer.this._app_vdf_list:
        for df in DayAnalyzer.this._app_vdf_list:
            print(df.name)
            print(df.analysis_results)


    stop_db()


    #print("Please start with the main.py")
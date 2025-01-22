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
        if not self._validate_mainframe():
            raise ValueError("Main frame is not valid.")
        self.analysis_results: dict = {}
        self._is_analyzed = False
        self.is_app_based = name.startswith("app:")
        self.is_label_based = name.startswith("label:")


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

    def __init__(self, analyzer_type: str, main_df: DataFrame):
        self.lock = Lock()
        if len(Analyzer._all_analyzer) == 0 or analyzer_type.upper() not in Analyzer._all_analyzer:
            Analyzer._all_analyzer.append(self)
        else:
            raise ValueError(f'Analyzer of type "{analyzer_type}" already initialized!')

        self._analyzer_type: str = analyzer_type.upper()
        self._main_df = main_df

        self._analyze()

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
    def analyzer_type(self):
        with self.lock:
            return self._analyzer_type

    @classmethod
    def get_analyzer_types_used(cls):
        with cls._class_lock:
            return [a.analyzer_type for a in cls._all_analyzer]


# # # # Stuff to add # # # #



    # def check_after_interval(self):
    #     """ simple checks for time saved and if its already """
    #     if self._next_check_timestamp >= datetime.now():
    #         self._data_refresh()
    #
    # def _thread_actions(self):
    #
    #     do_stop = False
    #     while not threads_are_stopped():
    #         inter = 30  # Needs to stay 60
    #         fifth_timer = inter // 5
    #
    #         for i in range(fifth_timer):
    #             sleep(5)
    #             if threads_are_stopped():
    #                 do_stop = True
    #                 break
    #         if do_stop:
    #             break
    #         self.check_after_interval()
    #     self._thread_closed = True

# # # # # # # # # # # # # # #


class StandardAnalyzer(Analyzer):
    _instance = None

    # FIXME: Check if the new "super().__new__(cls)" compared to "super(cls, cls).__new__(cls)" works
    def __new__(cls, *args, **kwargs):
        """
        Ensures that StandardAnalyzes follows the singleton pattern.

        :return: StandardAnalyzes (The singleton instance.)
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, main_df: DataFrame, time_frame: str = "DAY"):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            if time_frame.upper() not in ("DAY", "WEEK", "MONTH"):
                raise ValueError("time_frame must be one of 'DAY', 'WEEK', 'MONTH'")
            super().__init__(analyzer_type=f"STANDARD_ANALYZER_{time_frame}", main_df=main_df)
            self._time_frame = time_frame

    def _analyze(self):
        """ This methode will analyze the data frame according to the analyzer type."""
        pass

    def _refresh_data(self):
        """ This methode will refresh the data frame according to the analyzer type."""
        pass


# # # # External Call functions # # # #
def init_standard_analyzes():
    pass


if __name__ == "__main__":
    start_db()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)

    test_df = DBHandler().search_window_log(start_time=datetime(2025,1,16,0,0), end_time=datetime(2025,1,17,0,0))

    vdf = ViperDF(name="test", main_df=test_df)
    vdf.analyze()
    outs = vdf.split_data_on_app()
    for o in outs:
        print(o.name)
        print(o.analysis_results)

    stop_db()
    #print("Please start with the main.py")
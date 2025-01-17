"""
Here we handle the storage of data frames from pandas,
the sorting and what else.

Author: sora7672
"""
__author__ = 'sora7672'

from datetime import datetime, timedelta
from threading import Lock, Thread
from time import sleep, gmtime, strftime
from pandas import DataFrame, Series

import pandas as pd
from config_manager import threads_are_stopped, stop_program_threads
from db_connector import DBHandler, stop_db, start_db


class StandardAnalyzes:
    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures that StandardAnalyzes follows the singleton pattern.

        :return: StandardAnalyzes (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the StandardAnalyzes instance, setting attributes and locks.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._day_df = None
            self._day_analyzed_dict = {}
            self._last_check_timestamp = None
            self._next_check_timestamp = None
            self.check_interval_minutes = 1
            self._thread = Thread(target=self._thread_actions)
            self._thread_closed = True

            self._lock = Lock()

            self._data_refresh()

            self._thread.start()

    def _data_refresh(self):
        """
        Refreshes the data in the
        """
        self._last_check_timestamp = datetime.now()
        self._next_check_timestamp = datetime.now() + timedelta(minutes=self.check_interval_minutes)
        # TODO: remove the test timeframe, it auto uses last 24 hours.
        self._day_df = DBHandler().search_window_log(start_time=datetime(2025,1,16,0,0), end_time=datetime(2025,1,17,0,0))

        self._analyze_general_data_day()

    def _analyze_general_data_day(self):
        alltm,activetm, inactivetm, activep = self._df_activity(self._day_df)
        self._day_analyzed_dict["activity"] = {
            "all_minutes": alltm,
            "active_minutes": activetm,
            "inactive_minutes": inactivetm,
            "percent_active": activep
        }
        self._day_analyzed_dict["average"] = self._df_average_inputs(self._day_df)

        print(self._day_analyzed_dict)
        # Todo:
        #  average_active_key_pushes
        #  average_active_mouse_clicks
        #  average_active_mouse_scrolls
        #  -----
        #  number_of_applications
        #  count_all_activities
        #

    def _df_average_inputs(self, df):
        if "activity" not in df.columns:
            raise ValueError("No activity column")
        else:
            only_actives = df[df['activity']]
            num_activities = len(only_actives)
            all_summed = {
                "count_key_pressed": only_actives['count_key_pressed'].sum(),
                "count_mouse_pressed": only_actives['count_mouse_pressed'].sum(),
                "count_direction_key_pressed": only_actives['count_direction_key_pressed'].sum(),
                "count_char_key_pressed": only_actives['count_char_key_pressed'].sum(),
                "count_special_key_pressed": only_actives['count_special_key_pressed'].sum(),
                "count_mouse_scrolls": only_actives['count_mouse_scrolls'].sum(),
                "count_left_mouse_pressed": only_actives['count_left_mouse_pressed'].sum(),
                "count_right_mouse_pressed": only_actives['count_right_mouse_pressed'].sum(),
                "count_middle_mouse_pressed": only_actives['count_middle_mouse_pressed'].sum(),
                "all_activity_count": only_actives['all_activity_count'].sum()

            }
            all_average = {
                key: int((value / num_activities).flat[0])
                for key, value in all_summed.items()
            }

            return all_average
    def _df_activity(self, df:DataFrame):
        if "activity" not in df.columns:
            raise ValueError("No activity column")
        else:

            all_secs = 5 * len(df)
            active_secs = 5 * len(df[df["activity"]])
            inactive_secs = all_secs - active_secs

            all_time_mm_ss = secs_to_mm_ss(all_secs)
            active_time_mm_ss = secs_to_mm_ss(active_secs)
            inactive_time_mm_ss = secs_to_mm_ss(inactive_secs)
            percent_active = int(active_secs / (all_secs / 100))

            return all_time_mm_ss, active_time_mm_ss, inactive_time_mm_ss, percent_active


    def _analyze_application_data_day(self):
        pass
        # Todo: Per window_type
        #  time_tracked_minutes
        #  time_active_minutes
        #  time_inactive_minutes
        #  %active
        #  average_active_key_pushes
        #  average_active_mouse_clicks
        #  average_active_mouse_scrolls

        # TODO: Compare Application data

    def _analyze_label_data_day(self):
        pass
        # Todo: Per label_id in con_window_label
        #  time_tracked_minutes
        #  time_active_minutes
        #  time_inactive_minutes
        #  %active
        #  average_active_key_pushes
        #  average_active_mouse_clicks
        #  average_active_mouse_scrolls
        #  % of all time that day usage
        #  % of all active time that day usage

        # TODO: Compare Label data

    def check_after_interval(self):
        """ simple checks for time saved and if its already """
        if self._next_check_timestamp >= datetime.now():
            self._data_refresh()

    def _thread_actions(self):

        do_stop = False
        while not threads_are_stopped():
            inter = 30  # Needs to stay 60
            fifth_timer = inter // 5

            for i in range(fifth_timer):
                sleep(5)
                if threads_are_stopped():
                    do_stop = True
                    break
            if do_stop:
                break
            self.check_after_interval()
        self._thread_closed = True

    @property
    def thread_closed(self):
        with self._lock:
            return bool(self._thread_closed)

    def wait_for_thread_closed(self):
        """
        After calling this, the function waits till the thread is closed.
        """
        self._thread.join()

# # # # Helper functions # # # #
def secs_to_mm_ss(secs):
    m, s = divmod(secs, 60)
    return f"{m}:{s:02}"


# # # # External Call functions # # # #

def init_standard_analyzes():
    StandardAnalyzes()

if __name__ == "__main__":
    start_db()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)

    init_standard_analyzes()

    stop_db()
    #print("Please start with the main.py")
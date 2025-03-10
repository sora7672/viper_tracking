"""
Module for managing and applying database filters to data.

This module provides:
- The `DatabaseFilter` class for managing filters and retrieving filtered data from the database.
- Methods to create, update, delete, and retrieve filters.
- Utility functions to initialize filters from the database and combine multiple filters.

Author: sora7672
"""

__author__ = 'sora7672'


from datetime import datetime, timedelta
from threading import Thread, Lock
from pandas import DataFrame
import pandas as pd

from helper_classes import DynamicTimeframe
from log_handler import get_logger
from db_connector import DBHandler, start_db, stop_db


class DatabaseFilter:
    """
    Represents a database filter used to retrieve specific subsets of data.

    This class manages filters that can be stored in the database and loaded on program start.
    Filters allow users to apply conditions such as window type, window title, word lists,
    label lists, and time constraints to data queries.

    A filter requires at least one of the following to be initialized:
    - A **dynamic time frame** (e.g., "last_7_days", "current_month").
    - A **fixed time frame** with both `start_datetime` and `end_datetime`.

    Attributes:
        _lock (Lock): Thread lock for synchronizing database operations.
        _name (str): The name of the filter.
        _id (int | None): The unique ID of the filter in the database.
        _window_type (str | None): The window type filter.
        _window_title (str | None): The window title filter.
        _word_list (str | list[str] | None): A list of words used for filtering.
        _label_list (int | list[int] | None): A list of label IDs used for filtering.
        _start_datetime (datetime | None): The start time for filtering (if using a fixed time frame).
        _end_datetime (datetime | None): The end time for filtering (if using a fixed time frame).
        _dynamic_time_frame (DynamicTimeframe | None): A dynamic time frame for filtering.
        _all_filter (list[DatabaseFilter]): A class-level list storing all initialized filter instances.
    """

    _all_filter = []

    def __init__(self, name:str, window_type: str = None, window_title: str = None,
                  word_list: str | list[str] = None, label_list: int | list[int] = None,
                  start_datetime: datetime = None, end_datetime: datetime = None,
                  dynamic_time_frame: DynamicTimeframe| str = None, id: int = None):
        """
        Initializes a `DatabaseFilter` instance.

        A filter requires either a dynamic time frame or a fixed time frame (start and end time).
        If the filter does not exist in the database, it is automatically saved.

        :param name: str (The name of the filter.)
        :param window_type: str | None (Optional window type filter.)
        :param window_title: str | None (Optional window title filter.)
        :param word_list: str | list[str] | None (Optional word-based filter.)
        :param label_list: int | list[int] | None (Optional label-based filter.)
        :param start_datetime: datetime | None (Start time for filtering.)
        :param end_datetime: datetime | None (End time for filtering.)
        :param dynamic_time_frame: DynamicTimeframe | str | None (A dynamic time frame or its string representation.)
        :param id: int | None (Filter ID if loaded from the database.)
        :raises ValueError: If neither a dynamic time frame nor valid start/end times are provided.
        :return: None
        """

        self._lock = Lock()
        self._name = name
        self._id = id

        self._window_type: str = window_type
        self._window_title: str = window_title
        self._word_list: str | list[str] = word_list
        self._label_list: int | list[int] = label_list
        if not dynamic_time_frame and (not start_datetime or not end_datetime):
            raise ValueError("No dynamic time frame given, but also no start and end time given")

        self._start_datetime: datetime = start_datetime
        self._end_datetime: datetime = end_datetime
        if isinstance(dynamic_time_frame, DynamicTimeframe):
            self._dynamic_time_frame = dynamic_time_frame
        else:
            self._dynamic_time_frame = DynamicTimeframe(dynamic_time_frame)

        if self._id is None:
            self.save_to_db()
        DatabaseFilter._all_filter.append(self)

    def get_dataframe(self):
        """
        Retrieves a pandas DataFrame containing data filtered by the current filter settings.

        The method applies the stored filter parameters to the `DBHandler.search_window_log` function.

        :return: DataFrame | None (A pandas DataFrame containing the filtered data, or None if no data is found.)
        """

        if not self._dynamic_time_frame:
            start_datetime = self._start_datetime
            end_datetime = self._end_datetime
        else:
            start_datetime, end_datetime = self._dynamic_time_frame.datetime_range

        out = DBHandler().search_window_log(window_type=self._window_type, window_title=self._window_title,
                                            word_list=self._word_list, label_list=self._label_list,
                                            start_time=start_datetime, end_time=end_datetime)
        return out

    def save_to_db(self):
        """
        Saves the current filter to the database if it has not been stored yet.

        The filter is inserted into the `filter_catalog` table. The ID of the newly created filter
        is then stored in the `_id` attribute.

        :return: None
        """

        if not self._id:
            with self._lock:
                filter_id = DBHandler().add_filter(name=self._name, word_list=self._word_list, window_type=self._window_type,
                                       window_title=self._window_title, label_list=self._label_list,
                                       start_datetime=self._start_datetime, end_datetime=self._end_datetime,
                                       dynamic_time_frame=self._dynamic_time_frame.value)
                self._id = filter_id

    def _update_in_db(self):
        """
        Updates the filter entry in the database with the current values.

        This method modifies the existing filter record in the `filter_catalog` table.

        :return: None
        """

        with self._lock:
            DBHandler().update_filter(id=self._id, name=self._name, word_list=self._word_list,
                                      window_type=self._window_type, window_title=self._window_title,
                                      label_list=self._label_list, dynamic_time_frame=self._dynamic_time_frame.value,
                                      end_datetime=self._end_datetime, start_datetime=self._start_datetime)

    def update(self,name: str = None, word_list: str | list[str] = None, window_type: str = None,
               window_title: str = None, label_list: int | list[int] = None,
               dynamic_time_frame: str | DynamicTimeframe = None, end_datetime: datetime | str = None,
               start_datetime: datetime | str = None):
        """
        Updates specific filter attributes and saves the changes to the database.

        If both `start_datetime`/`end_datetime` and `dynamic_time_frame` are provided,
        an exception is raised since they are mutually exclusive.

        :param name: str | None (Updated name for the filter.)
        :param word_list: str | list[str] | None (Updated word-based filter.)
        :param window_type: str | None (Updated window type filter.)
        :param window_title: str | None (Updated window title filter.)
        :param label_list: int | list[int] | None (Updated label-based filter.)
        :param dynamic_time_frame: str | DynamicTimeframe | None (Updated dynamic time frame.)
        :param start_datetime: datetime | str | None (Updated start time or empty string to reset.)
        :param end_datetime: datetime | str | None (Updated end time or empty string to reset.)
        :raises ValueError: If both `start_datetime`/`end_datetime` and `dynamic_time_frame` are provided.
        :raises ValueError: If no changes were made.
        :return: None
        """

        changed = False
        if (start_datetime or end_datetime) and dynamic_time_frame:
            raise ValueError("Given start_datetime or end_datetime and dynamic_time_frame are mutually exclusive!")
        if name is not None:
            self._name = name
            changed = True
        if word_list is not None:
            self._word_list = word_list
            changed = True
        if window_type is not None:
            self._window_type = window_type
            changed = True
        if window_title is not None:
            self._window_title = window_title
            changed = True
        if label_list is not None:
            self._label_list = label_list
            changed = True

        if dynamic_time_frame is not None:
            if isinstance(dynamic_time_frame, DynamicTimeframe):
                self._dynamic_time_frame = dynamic_time_frame
            elif dynamic_time_frame == "":
                self._dynamic_time_frame = None
            else:
                self._dynamic_time_frame = DynamicTimeframe(dynamic_time_frame)
            self._start_datetime = None
            self._end_datetime = None
            changed = True
        if start_datetime is not None:
            self._start_datetime = None if start_datetime == "" else start_datetime
            changed = True
        if end_datetime is not None:
            self._end_datetime = None if end_datetime == "" else end_datetime
            changed = True

        if not changed:
            raise ValueError("No filters were changed")
        else:
            self._update_in_db()

    def delete(self):
        """
        Deletes the filter from the database and removes it from the internal list.

        The filter is permanently removed from the `filter_catalog` table.

        :return: None
        """

        DBHandler().delete_filter(id=self._id)
        DatabaseFilter._all_filter.remove(self)
        del self

    @classmethod
    def load_from_db(cls):
        """
        Loads all filters stored in the database and initializes them as `DatabaseFilter` instances.

        Each database entry is retrieved and passed as keyword arguments to initialize a new filter object.

        :return: None
        """
        filters = DBHandler().get_all_filters()
        for fil in filters:
            cls(**fil)


    @classmethod
    def get_filter_by_id(cls, filter_id: int) -> 'DatabaseFilter':
        """
        Retrieves a filter instance by its ID.

        :param filter_id: int (The ID of the desired filter.)
        :return: DatabaseFilter | None (The corresponding `DatabaseFilter` instance, or None if not found.)
        """

        for fil in cls._all_filter:
            if fil._id == filter_id:
                return fil

    @classmethod
    def get_filter_by_name(cls, name: str) -> 'DatabaseFilter':
        """
        Retrieves a filter instance by its name.

        :param name: str (The name of the desired filter.)
        :return: DatabaseFilter | None (The corresponding `DatabaseFilter` instance, or None if not found.)
        """

        for fil in cls._all_filter:
            if fil.name == name:
                return fil

    # TODO: think about a deeper way to connect filters. this is just one layer, but we need multilayer
    @classmethod
    def combine_filters(cls, main_filter, sub_filter, subtract: bool = False) -> DataFrame:
        """
        Combines two filters into a single DataFrame, either merging or subtracting their data.

        If `subtract=True`, the resulting DataFrame contains all entries from `main_filter`
        except those present in `sub_filter`. Otherwise, both DataFrames are combined.

        :param main_filter: DatabaseFilter (The main filter to use.)
        :param sub_filter: DatabaseFilter (The secondary filter to combine with the main filter.)
        :param subtract: bool (If True, removes overlapping entries instead of merging.)
        :return: DataFrame (The resulting pandas DataFrame after applying the combination logic.)
        """

        main_df = main_filter.get_dataframe()
        sub_df = sub_filter.get_dataframe()
        if subtract:
            df = main_df[~main_df["window_id"].isin(sub_df["window_id"])]
        else:
            df = pd.concat([main_df, sub_df]).drop_duplicates(subset="window_id", keep="first")

        return df


# # # # External call functions for less import in other files # # # #
def init_all_filter_from_db() -> None:
    """
    Initializes all filters by loading them from the database.

    This function calls `DatabaseFilter.load_from_db()` to retrieve stored filters.

    :return: None
    """

    DatabaseFilter.load_from_db()



if __name__ == "__main__":
    start_db()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    start_analysis = datetime.now()


    init_all_filter_from_db()


    dbf = DatabaseFilter(name="28days", dynamic_time_frame=DynamicTimeframe("last_28_days"))
    #
    # print(dbf.get_dataframe())
    # dbf2 = DatabaseFilter(name="7days", dynamic_time_frame=DynamicTimeframe("last_7_days"))
    # print(dbf2.get_dataframe())
    #
    #
    # subtr = DatabaseFilter.combine_filters(dbf, dbf2, subtract=False)
    # print(subtr)

    end_analysis = datetime.now()
    time_used = (end_analysis - start_analysis).total_seconds()
    print(f"{end_analysis} - {start_analysis} = {time_used}")
    stop_db()



    print("Please start with the main.py")
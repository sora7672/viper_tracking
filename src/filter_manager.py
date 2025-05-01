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


def _return_datetime(str_or_datetime) -> datetime:
    """
    Converts an input value to a datetime object.

    :param str_or_datetime: datetime or str (A datetime object or an ISO-format date/time string.)
    :return: datetime (A datetime object corresponding to the input.)
    """
    return str_or_datetime if isinstance(str_or_datetime, datetime) else datetime.fromisoformat(str_or_datetime)


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

    def __init__(self, name: str, window_type: str = None, window_title: str = None,
                 word_list: str | list[str] = None, label_list: int | list[int] = None,
                 start_datetime: datetime = None, end_datetime: datetime = None,
                 dynamic_time_frame: DynamicTimeframe | str = None, filter_id: int = None):
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
        :param filter_id: int | None (Filter ID if loaded from the database.)
        :raises ValueError: If neither a dynamic time frame nor valid start/end times are provided.
        :return: None
        """

        if not dynamic_time_frame and (not start_datetime or not end_datetime):
            raise ValueError("No dynamic time frame given, but also no start and end time given")

        self._lock = Lock()
        self._name = name
        self._id = filter_id

        self._window_type: str = window_type
        self._window_title: str = window_title
        self._word_list: str | list[str] = word_list
        self._label_list: int | list[int] = label_list

        self._start_datetime: datetime = _return_datetime(start_datetime) if start_datetime else None
        self._end_datetime: datetime = _return_datetime(end_datetime) if end_datetime else None

        if isinstance(dynamic_time_frame, DynamicTimeframe):
            self._dynamic_time_frame = dynamic_time_frame
        elif dynamic_time_frame and isinstance(dynamic_time_frame, str):
            self._dynamic_time_frame = DynamicTimeframe(dynamic_time_frame)
        else:
            self._dynamic_time_frame = None
        if self._id is None:
            self.save_to_db()
        DatabaseFilter._all_filter.append(self)

    def get_dataframe(self) -> DataFrame:
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

    def save_to_db(self) -> None:
        """
        Saves the current filter to the database if it has not been stored yet.

        The filter is inserted into the `filter_catalog` table. The ID of the newly created filter
        is then stored in the `_id` attribute.

        :return: None
        """

        with self._lock:
            _id = DBHandler().add_filter(name=self._name, word_list=self._word_list, window_type=self._window_type,
                                   window_title=self._window_title, label_list=self._label_list,
                                   start_datetime=self._start_datetime, end_datetime=self._end_datetime,
                                   dynamic_time_frame=self._dynamic_time_frame.value if self._dynamic_time_frame else None)
            self._id = _id

    def as_dict(self) -> dict:
        """
        Serializes the filter's parameters into a dictionary.

        :return: dict (Dictionary containing the filter's name, criteria, and time frame settings.)
        """

        with self._lock:
            filter_dict = {
                "name": self._name,
                "id": self._id,
                "window_type": self._window_type,
                "window_title": self._window_title,
                "word_list": self._word_list,
                "label_list": self._label_list,
                "dynamic_time_frame": self._dynamic_time_frame,
                "start_date": self._start_datetime.date() if self._start_datetime else None,
                "start_time": self._start_datetime.time().strftime("%H:%M") if self._start_datetime else None,
                "end_date": self._end_datetime.date() if self._end_datetime else None,
                "end_time": self._end_datetime.time().strftime("%H:%M") if self._end_datetime else None
            }

        return filter_dict

    def _update_in_db(self) -> None:
        """
        Updates the filter entry in the database with the current values.

        This method modifies the existing filter record in the `filter_catalog` table.

        :return: None
        """

        with (self._lock):
            time_frame_value = self._dynamic_time_frame.value if isinstance(self._dynamic_time_frame,
                                                                            DynamicTimeframe) else None
            DBHandler().update_filter(filter_id=self._id, name=self._name, word_list=self._word_list,
                                      window_type=self._window_type, window_title=self._window_title,
                                      label_list=self._label_list, dynamic_time_frame=time_frame_value,
                                      end_datetime=self._end_datetime, start_datetime=self._start_datetime)

    def update(self, name: str = None, word_list: str | list[str] = None, window_type: str = None,
               window_title: str = None, label_list: int | list[int] = None,
               dynamic_time_frame: str | DynamicTimeframe = None, end_datetime: datetime | str = None,
               start_datetime: datetime | str = None):
        """
        Updates specific filter attributes and saves the changes to the database.
        To reset filter attributes the parameter value needs to be "".

        If both `start_datetime`/`end_datetime` and `dynamic_time_frame` are provided,
        a ValueError is raised since they are mutually exclusive.

        If `start_datetime` is bigger equal than `end_datetime` a ValueError is raised.

        :param name: str | None (Updated name for the filter.)
        :param word_list: str | list[str] | None (Updated word-based filter.)
        :param window_type: str | None (Updated window type filter.)
        :param window_title: str | None (Updated window title filter.)
        :param label_list: int | list[int] | None (Updated label-based filter.)
        :param dynamic_time_frame: str | DynamicTimeframe | None (Updated dynamic time frame.)
        :param start_datetime: datetime | str | None (Updated start time or empty string to reset.)
        :param end_datetime: datetime | str | None (Updated end time or empty string to reset.)
        :raises ValueError: If both `start_datetime`/`end_datetime` and `dynamic_time_frame` are provided.
        :return: None
        """

        changed = False
        with self._lock:
            old_start_date = self._start_datetime
            old_end_date = self._end_datetime
            old_dynamic_time_frame = self._dynamic_time_frame

            if dynamic_time_frame == "":
                self._dynamic_time_frame = None
                changed = True
            elif dynamic_time_frame is not None:
                if isinstance(dynamic_time_frame, str):
                    self._dynamic_time_frame = DynamicTimeframe(dynamic_time_frame)
                    changed = True
                elif isinstance(dynamic_time_frame, DynamicTimeframe):
                    self._dynamic_time_frame = dynamic_time_frame
                    changed = True

            if start_datetime is not None and self._start_datetime != start_datetime:
                self._start_datetime = None if start_datetime == "" else start_datetime
                changed = True

            if end_datetime is not None and self._end_datetime != end_datetime:
                self._end_datetime = None if end_datetime == "" else end_datetime
                changed = True

            if (self._end_datetime is not None and self._start_datetime is None) or (
                    self._end_datetime is None and self._start_datetime is not None):
                self._start_datetime = old_start_date
                self._end_datetime = old_end_date
                self._dynamic_time_frame = old_dynamic_time_frame
                raise ValueError("End datetime or start datetime have to be set together.")

            elif (self._end_datetime is not None and self._start_datetime is not None
                  and self._dynamic_time_frame is not None):
                self._start_datetime = old_start_date
                self._end_datetime = old_end_date
                self._dynamic_time_frame = old_dynamic_time_frame
                raise ValueError("Absolute time frame and dynamic time frame can't be set together.")

            elif (self._end_datetime is None and self._start_datetime is None
                  and self._dynamic_time_frame is None):
                self._start_datetime = old_start_date
                self._end_datetime = old_end_date
                self._dynamic_time_frame = old_dynamic_time_frame
                raise ValueError("Absolute time frame or dynamic time frame has to be set.")

            # if "" is the parameter value, it should reset  the attribute to None

            if name is not None and self._name != name:
                self._name = name
                changed = True

            if word_list is not None and self._word_list != word_list:
                self._word_list = word_list
                changed = True

            if window_type is not None and self._window_type != window_type:
                self._window_type = window_type
                changed = True

            if window_title is not None and self._window_title != window_title:
                self._window_title = window_title
                changed = True

            if label_list is not None and self._label_list != label_list:
                self._label_list = label_list
                changed = True

        if changed:
            self._update_in_db()

    def delete_in_db(self) -> None:
        """
        Deletes the filter from the database and removes it from the internal list.

        The filter is permanently removed from the `filter_catalog` table.

        :return: None
        """
        with self.lock():
            DBHandler().delete_filter(filter_id=self._id)
            DatabaseFilter._all_filter.remove(self)
            del self

    @property
    def id(self) -> int:
        """
        Returns the unique database ID of this filter, if it has been saved.

        :return: int | None (The filter’s ID in the database, or None if not saved.)
        """

        with self._lock:
            return self._id

    @property
    def name(self) -> str:
        """
        Returns the name of the filter.

        :return: str (The filter’s name.)
        """

        with self._lock:
            return self._name

    @classmethod
    def load_from_db(cls) -> None:
        """
        Loads all filters stored in the database and initializes them as `DatabaseFilter` instances.

        Each database entry is retrieved and passed as keyword arguments to initialize a new filter object.

        :return: None
        """
        filters = DBHandler().get_all_filters()
        for fil in filters:
            cls(**fil)

    @classmethod
    def get_all_filter(cls) -> list['DatabaseFilter']:
        """
        Returns the list of all initialized `DatabaseFilter` instances.

        :return: list[DatabaseFilter] (All filter instances currently in memory.)
        """

        return cls._all_filter

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

    @classmethod
    def combine_filters(cls, main_filter, sub_filter_list) -> DataFrame:
        """
        Combines a main filter with a list of sub-filters to produce a merged dataset.

        The sub-filters are provided as a 2D list, where each inner list contains a `DatabaseFilter` (or sub-filter) and a boolean flag. If the flag is False, that sub-filter’s data will be subtracted from the main filter’s data; if True, it will be added (with duplicates dropped).

        :param main_filter: DatabaseFilter (The primary filter to apply.)
        :param sub_filter_list: list[list[DatabaseFilter, bool]] (List of [filter, add_flag] pairs to combine with the main filter.)
        :return: DataFrame (The resulting pandas DataFrame after applying the combination logic.)
        """

        main_df = main_filter.get_dataframe()

        for sub_filter, add_it in sub_filter_list:
            sub_df = sub_filter.get_dataframe()
            if sub_df is not None and not sub_df.empty:
                if add_it:
                    # Combine all data without NaN values, so left and right datasets are existing in the output.
                    main_df = pd.concat([main_df, sub_df], ignore_index=True)\
                        .drop_duplicates(subset="window_id", keep="first")
                else:
                    # Subtract ids that exist in sub frame
                    main_df = main_df[~main_df["window_id"].isin(sub_df["window_id"])]

        return main_df.reset_index(drop=True)


# # # # External call functions for less import in other files # # # #
def init_all_filter_from_db() -> None:
    """
    Initializes all filters by loading them from the database.

    This function calls `DatabaseFilter.load_from_db()` to retrieve stored filters.

    :return: None
    """

    DatabaseFilter.load_from_db()


if __name__ == "__main__":
    print("Please start with the main.py")

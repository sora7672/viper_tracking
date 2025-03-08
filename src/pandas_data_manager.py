"""
This module manages the storage and analysis of user activity data using pandas DataFrames.

Features:
- Provides the `ViperDF` class for handling data and generating interactive plots.
- Implements the `DayAnalyzer` singleton for periodic background analysis updates.
- Includes utility functions for splitting text and displaying Matplotlib figures in a GUI.

Author: sora7672
"""

__author__ = 'sora7672'

from datetime import datetime, timedelta
from threading import Lock, Thread
from time import sleep
from pandas import DataFrame, Series
from matplotlib.collections import PolyCollection

# TODO: Minimize this imports to only import methods needed.
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from config_manager import threads_are_stopped
from db_connector import DBHandler, stop_db, start_db
from helper_classes import Classproperty, ColorPicker, Seconds


class ViperDF:
    """
    A class that encapsulates a pandas DataFrame and provides analysis and plotting methods.

    This class can split data by labels or applications, compute various statistics,
    and generate interactive Matplotlib plots (line plots, horizontal bar charts, pie charts)
    for the given dataset.

    Attributes:
        name (str): Name of this dataset (e.g., may start with "app:" or "label:" to indicate type).
        empty (bool): True if the provided DataFrame is empty or invalid.
        analysis_results (dict): Dictionary storing computed results (time frame, counts, etc.) after analysis.
        is_app_based (bool): True if the dataset name starts with "app:", indicating app-specific data.
        is_label_based (bool): True if the dataset name starts with "label:", indicating label-specific data.
        granularity (int): DPI setting used for plot resolution (default is 100).
        mainplot (Figure | None): Combined Matplotlib figure containing all subplots (created after calling plot()).
    """

    def __init__(self, name: str, main_df: DataFrame):
        """
        Initializes the ViperDF instance with a name and a pandas DataFrame.

        :param name: str (The identifier name for this dataset. If prefixed with "app:" or "label:", it indicates the context.)
        :param main_df: DataFrame (The pandas DataFrame containing the data to be analyzed.)
        :return: None
        """


        # NOT USED: do we really need prefix here?
        # Naming should be "name" or "label:blahh" or "app:blahh" if name includes ":" check for app/label
        # and set some flags for further implementation
        self.name = name
        self._lock = Lock()
        self._main_df: DataFrame = main_df
        self.empty = main_df.empty
        if not self.empty and not self._validate_mainframe():
            print("not valid mainframe, created empty DataFrame")
            self.empty = True
        self.analysis_results: dict = {}
        self._number_activity_points = 100
        self._is_analyzed = False
        self.is_app_based = name.startswith("app:")
        self.is_label_based = name.startswith("label:")

        self.granularity = 100
        self.analysis_results["major_formatter_x"] = mdates.DateFormatter("%H:%M:%S")
        self._activity_ax = None
        self._app_ax = None
        self._label_ax = None
        self._is_plotted = False
        self.mainplot = None

        self.__init_label_plot_helper()

    def __init_label_plot_helper(self):
        """
        Initializes internal helper attributes for label plotting, used for resets.

        This sets up default values (e.g., start_y, bar_height, y_spacing) in a helper dictionary for label bar plots.

        :return: None
        """

        self.__label_plot_helper = {
                                    "start_y": -35,
                                    "bar_height": 15,
                                    "y_spacing": 5
        }

    def __repr__(self) -> str:
        """
        Returns a human-readable string with the VDF name and its DataFrame content.

        :return: str (A string representation of the ViperDF, including name and DataFrame info.)
        """

        return f"VDF '{self.name}':\n{str(self._main_df)}"

    def __str__(self) -> str:
        """
        Returns a human-readable string with the VDF name and its DataFrame content.

        :return: str (A string representation of the ViperDF, including name and DataFrame info.)
        """

        return f"VDF '{self.name}':\n{str(self._main_df)}"

    def _validate_mainframe(self) -> bool:
        """
        Checks whether the main DataFrame contains all required columns for analysis.

        :return: bool (True if all required columns are present in the DataFrame, False otherwise.)
        """

        needed_columns = ["window_id", "window_type", "window_title", "word_list", "creation_datetime", "activity",
                          "count_key_pressed", "count_mouse_pressed",  "count_direction_key_pressed",
                          "count_char_key_pressed", "count_special_key_pressed", "count_mouse_scrolls",
                          "count_left_mouse_pressed", "count_right_mouse_pressed", "count_middle_mouse_pressed"]
        if all(ncol in self._main_df.columns for ncol in needed_columns):
            return True
        else:
            return False

    def split_data_on_label(self) -> list:
        """
        Splits the data into multiple ViperDF instances based on each unique label in the data.

        This method creates a new ViperDF for each label found (excluding cases where the filtered data equals the entire dataset).
        Each new ViperDF is analyzed automatically.

        :raises ValueError: If the main DataFrame has not been analyzed yet (`analyze()` not called).
        :return: list[ViperDF] (A list of new ViperDF objects, one for each unique label.)
        """

        # NOT USED: This whole methode. split data on label
        if not self.empty and not self.is_label_based:
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
                n_vdf.append(ViperDF(f"label:{lab}", out_df))
                n_vdf[-1].analyze()

            return n_vdf

    def split_data_on_app(self) -> list:
        """
        Splits the data into multiple ViperDF instances based on each unique application (window type).

        This method creates a new ViperDF for each distinct window_type found (excluding cases where the filtered data equals the entire dataset).
        Each new ViperDF is analyzed automatically.

        :raises ValueError: If the main DataFrame has not been analyzed yet (`analyze()` not called).
        :return: list[ViperDF] (A list of new ViperDF objects, one for each unique application type.)
        """

        # NOT USED: Split data on app needed?
        if not self.empty and not self.is_app_based:
            if not self._is_analyzed:
                raise ValueError("Main frame is not analyzed.")

            n_vdf = []

            for w_type in self.analysis_results["apps"]["entries"].keys():
                out_df = self._main_df[self._main_df['window_type'] == w_type]
                if len(out_df) == self.analysis_results["entry_count"]:
                    # Dont append if the sub DF is the same as the main DF
                    continue
                n_vdf.append(ViperDF(f"app:{w_type}", out_df))
                n_vdf[-1].analyze()

            return n_vdf

    def plot(self):
        """
        Generates all necessary plots for this dataset and combines them into a main figure.

        This method creates the activity line plot, application usage bar chart, and label usage bar chart,
        then combines these axes into a single Matplotlib figure. It must be called before retrieving any figure or axes.

        :raises ValueError: If the main DataFrame has not been analyzed yet (`analyze()` not called).
        :return: None
        """

        if not self._is_analyzed:
            raise ValueError("Main frame is not analyzed.")
        self._get_ax_line_activity()
        self._get_ax_hbar_apps()
        self._update_ax_hbar_labels()
        self._combine_axes()
        self._is_plotted = True

    def change_chosen_labels(self, label_list: str | list[str]):
        """
        Updates which labels are displayed on the combined label plot (main figure), limiting the number shown.

        This method recalculates and redraws the label horizontal bar chart using the specified label or list of labels.
        It ensures that no more than 5 labels are displayed to maintain readability.

        :param label_list: str | list[str] (The label(s) to display on the label plot. Can be a single label or a list of labels (max 5).)
        :raises ValueError: If `label_list` is empty or contains more than 5 labels.
        :return: None
        """

        # TODO: Delete all old used things that change on label change
        if len(label_list) == 0 or len(label_list) > 5:
            raise ValueError("label_list cannot be empty or more than 4")
        self._label_ax = None  # Remove the existing label axis
        self.__init_label_plot_helper()

        self._update_ax_hbar_labels(label_list)
        self._combine_axes()

    def analyze(self):
        """
        Performs all analysis steps on the main DataFrame in the proper sequence.

        This method calls the internal analysis functions in order (time analysis, input analysis, then app and label analysis as applicable).
        As a result, the `analysis_results` dictionary is populated with metrics (time frame, activity counts, etc.), and the data is prepared for plotting.

        :return: None
        """

        if not self.empty:
            self._time_analysis()
            self._input_analysis()
            if not self.is_app_based:
                self._app_analysis()
            if not self.is_label_based:
                self._label_analysis()
            self._is_analyzed = True

    def _time_analysis(self):
        """
        Analyzes time-related data and populates corresponding entries in `analysis_results`.

        Determines the first and last timestamps, total tracked duration, active vs. inactive time,
        and chooses an appropriate time-axis formatter based on the overall time frame.

        :raises ValueError: If the computed time frame interval is not recognized.
        :return: None
        """

        self._main_df.sort_values(by=["creation_datetime"], ascending=True)
        self.analysis_results["first_datetime"] = self._main_df["creation_datetime"].iloc[0]
        self.analysis_results["last_datetime"] = self._main_df["creation_datetime"].iloc[-1]
        self.analysis_results["time_frame_seconds"] = Seconds(int((self.analysis_results["last_datetime"]
                                                                   - self.analysis_results["first_datetime"])
                                                                  .total_seconds()))

        match self.analysis_results["time_frame_seconds"].time_frame:
            case "w":
                self.analysis_results["major_formatter_x"] = mdates.DateFormatter("%b %d")  # Format as "Month Day"
            case "d":
                self.analysis_results["major_formatter_x"] = mdates.DateFormatter(
                    "%d %H")  # Format as "Day Hour"
            case "h":
                self.analysis_results["major_formatter_x"] = mdates.DateFormatter(
                    "%H:%M")  # Format as "Hour:Minute"
            case "m":
                self.analysis_results["major_formatter_x"] = mdates.DateFormatter("%M:%S")  # Format as "Minute:Second"
            case "s":
                self.analysis_results["major_formatter_x"] = mdates.DateFormatter("%S")  # Format as "Seconds"
            case _:
                raise ValueError(f"Invalid time frame: {self.analysis_results['time_frame_seconds'].time_frame}")

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
        """
        Analyzes input-related metrics and populates corresponding entries in `analysis_results`.

        Aggregates key press and mouse activity counts into time bins (using a default of 5-second intervals or adjusted interval based on data size).
        Creates an internal DataFrame `_activity_df` with aggregated activity counts and computes a relative activity percentage for each time bin.

        :return: None
        """

        activity_points = self._number_activity_points or 100

        numeric_columns = [
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

        time_df = self._main_df[numeric_columns + ["creation_datetime"]].fillna(0)
        time_df = time_df.sort_values("creation_datetime")

        time_frame_per_point = max(5, round(self.analysis_results["time_frame_seconds"] / activity_points / 5) * 5)
        self.analysis_results["activity_interval"] = time_frame_per_point

        # param freq uses a deprecated methode with "s" for seconds in the end, don't remove!
        intervals = pd.interval_range(
            start=self.analysis_results["first_datetime"],
            end=self.analysis_results["last_datetime"] + pd.Timedelta(seconds=time_frame_per_point),
            freq=f"{time_frame_per_point}s",  # Comment above
            closed="left"
        )

        time_df["time_bin"] = pd.cut(
            time_df["creation_datetime"],
            bins=intervals,
            labels=range(len(intervals))
        )

        aggregated_data = time_df.groupby("time_bin", observed=True)[numeric_columns].sum()
        aggregated_data = aggregated_data.reset_index(drop=True)

        bins_df = pd.DataFrame({
            "start_time": intervals.left,
            "end_time": intervals.right
        })
        bins_df["middle_time"] = bins_df[["start_time", "end_time"]].mean(axis=1)

        bins_df = bins_df.merge(aggregated_data, left_index=True, right_index=True, how="left").fillna(0)

        bins_df[numeric_columns] = bins_df[numeric_columns].astype(int)

        highest_activity_value = int(round(bins_df["all_activity_count"].max() * 0.75))
        bins_df["activity_percent"] = bins_df["all_activity_count"].apply(
            lambda x: min(round((x / (highest_activity_value / 100))), 100)).astype(int)
        self.analysis_results["highest_activity_value"] = highest_activity_value
        self._activity_df = bins_df

    def _app_analysis(self):
        """
        Analyzes application (window type) usage data and populates corresponding entries in `analysis_results`.

        Computes the number of unique applications and their occurrence counts from the DataFrame,
        storing them under `analysis_results["apps"]`. This prepares the data for further grouping and plotting of app usage.

        :return: None
        """

        app_win_count = self._main_df["window_type"].value_counts().to_dict()
        self.analysis_results["apps"] = {"count_unique": len(app_win_count), "entries": app_win_count}
        self._create_grouped_app_df()

    def _label_analysis(self):
        """
        Analyzes label usage data and populates corresponding entries in `analysis_results`.

        Computes the total number of labeled and unlabeled entries, and counts occurrences of each unique label in the DataFrame.
        Results are stored under `analysis_results["labels"]`. This prepares the data for further grouping and plotting of label usage.

        :return: None
        """

        all_labels = self._main_df["label_list"].dropna().explode()
        label_counts = all_labels.value_counts().to_dict()
        self.analysis_results["entry_count_labeled"] = len(self._main_df["label_list"].dropna())
        self.analysis_results["entry_count_unlabeled"] = (self.analysis_results["entry_count"]
                                                          - self.analysis_results["entry_count_labeled"])

        self.analysis_results["labels"] = {"count_unique": len(label_counts), "entries": label_counts}
        self._create_grouped_label_df()

    def _create_grouped_app_df(self):
        """
        Groups consecutive log entries of the same application into combined time intervals.

        This method condenses the raw 5-second interval data by merging adjacent entries with the same window_type and window_title,
        if they occur in succession (with no more than a 8-second gap). It produces `_grouped_app_df` containing start time, end time,
        mid time, and duration for each continuous application usage segment, and then calculates summary statistics per application.

        :return: None
        """

        app_data = self._main_df[["window_type", "window_title", "creation_datetime"]].copy()

        app_data["start_time"] = app_data["creation_datetime"] - pd.to_timedelta(5, unit='s')
        app_data["end_time"] = app_data["creation_datetime"]

        # Mask is needed for using in PD DFs to faster do stuff then with python iteration.
        # This sets the comparsion, so we only "apply" or combination logic if the previous type, title are the same
        # and the time of the new entry is less than 8 seconds after (because of lag or so, standard is 5 seconds)
        change_mask = (
                (app_data["window_type"] != app_data["window_type"].shift(1)) |
                (app_data["window_title"] != app_data["window_title"].shift(1)) |
                ((app_data["start_time"] - app_data["end_time"].shift(1)).dt.total_seconds() > 8)
        )

        # Assign a unique group ID to each continuous block of identical entries
        app_data["group"] = change_mask.cumsum()
        app_data = app_data.sort_values("creation_datetime")

        # Aggregate start_time (first entry) and end_time (last entry) per group
        # Basically combining the matching groups, sorted by creation_datetime, into one row.
        app_grouped_df = app_data.groupby("group").agg({
            "window_type": "first",
            "window_title": "first",
            "start_time": "first",
            "end_time": "last"
        }).reset_index(drop=True)

        # Get the midpoint of each time frame, for later plotting needed.
        app_grouped_df["mid_time"] = app_grouped_df["start_time"] + (
                app_grouped_df["end_time"] - app_grouped_df["start_time"]) / 2
        # Duration also needed for showing in plot
        app_grouped_df["duration"] = (app_grouped_df["end_time"] - app_grouped_df["start_time"]).dt.total_seconds()

        self._grouped_app_df = app_grouped_df.sort_values("start_time")
        # TODO: Add app colors to the database and create a new app table, that basically holds app names
        #  (link app entrys to the window entrys with id so all have allways the same color and we dont link by name)
        # Generate colors for unique apps
        unique_apps = self._grouped_app_df["window_type"].unique()
        app_colors = ColorPicker.next_color_rgba(len(unique_apps))
        app_color_map = dict(zip(unique_apps, app_colors))

        # Assign colors to DataFrame on each fitting entry
        self._grouped_app_df["rgba_color"] = self._grouped_app_df["window_type"].map(app_color_map)

        # Calculating the % usage based on all time tracked on apps. Also adding the proper rgba_color
        app_summary_df = self._grouped_app_df.groupby("window_type").agg({
            "duration": "sum",
            "rgba_color": "first"
        }).reset_index()
        total_app_time = app_summary_df["duration"].sum()

        app_summary_df["overall_percent"] = (app_summary_df["duration"] / total_app_time) * 100
        app_summary_df["overall_percent"] = app_summary_df["overall_percent"].apply(lambda x: max(x, 0.01))
        app_summary_df["details"] = None

        # saving it in the object and after calling a methode that changes the smaller entrys in the DF
        self._grouped_app_summary_df = app_summary_df.sort_values("overall_percent", ascending=False)
        self._combine_small_app_entries()

    def _combine_small_app_entries(self):
        """
        Combines small application entries into an "Others" category for cleaner visualization.

        Application entries with an overall percentage below a certain threshold (currently 2%) are merged into a single "Others" entry.
        The combined entry accumulates the duration and percentage of these small entries, and stores details of the merged items for tooltip display.

        :return: None
        """

        if self._grouped_app_summary_df is None or self._grouped_app_summary_df.empty:
            return

        combination_threshold = 2.0
        df = self._grouped_app_summary_df.copy()

        mask = df["overall_percent"] < combination_threshold
        small_entries = df[mask].copy()

        if small_entries.empty:
            return

        # Creates the infos needed to be shown inside the plot dynamic functions
        details = small_entries[["window_type", "duration", "overall_percent"]].to_dict(orient="records")
        # Total time that needs to be shown on top of the plots annotation info before details.
        others_total_time = small_entries["duration"].sum()
        others_percent = small_entries["overall_percent"].sum()

        # Then remove the entries we combined, so we dont have duplications, based on the mask used before.
        df = df[~mask]

        # Creates new DF with this infos
        new_row = pd.DataFrame([{
            "window_type": "Others",
            "duration": others_total_time,
            "overall_percent": others_percent,
            "rgba_color": (0.5, 0.5, 0.5, 1.0),  # A neutral gray with full opacity
            "details": details  # Saving the specially used field details for plotting
        }])
        # Combine new data into old DF
        df = pd.concat([df, new_row], ignore_index=True)
        self._grouped_app_summary_df = df


    def _create_grouped_label_df(self):
        """
        Groups consecutive time segments for each label into combined intervals.

        This method filters out unlabeled entries and explodes the list of labels per entry.
        Consecutive entries of the same label (with no more than an 8-second gap between segments) are merged into one segment with a start and end time.
        The result `_grouped_label_df` contains label_name, start_time, end_time, and duration for each continuous label usage segment, and assigns a color to each label.

        :return: None
        """

        if self._main_df is None or self._main_df.empty:
            print("No data available.")
            return pd.DataFrame(columns=["label_name", "start_time", "end_time"])

        # Filter only rows with labels
        label_data = self._main_df.dropna(subset=["label_list"]).copy()


        label_data = label_data.explode("label_list")
        label_data["start_time"] = label_data["creation_datetime"] - pd.to_timedelta(5, unit='s')
        label_data["end_time"] = label_data["creation_datetime"]
        label_data = label_data.sort_values(["label_list", "start_time"])

        # Mask is needed for using in PD DFs to faster do stuff then with python iteration.
        # This sets the comparison, so we only "apply" or combination logic if the previous label is the same
        # and the time of the new entry is less than 8 seconds after (because of lag or so, standard is 5 seconds)
        change_mask = (
                (label_data["label_list"] != label_data["label_list"].shift(1)) |
                ((label_data["start_time"] - label_data["end_time"].shift(1)).dt.total_seconds() > 8)
        )
        label_data["group"] = change_mask.cumsum()

        label_grouped_df = label_data.groupby(["label_list", "group"]).agg({
            "start_time": "first",
            "end_time": "last"
        }).reset_index()

        label_grouped_df = label_grouped_df.rename(columns={"label_list": "label_name"})
        label_grouped_df["duration"] = (label_grouped_df["end_time"] - label_grouped_df["start_time"]).dt.total_seconds()
        label_grouped_df = label_grouped_df.sort_values(["label_name", "start_time"])

        self._grouped_label_df = label_grouped_df[["label_name", "start_time", "end_time", "duration"]]

        # TODO: add databank entry for RGBA colors per label and read them in
        #  also, add it to Labels in logs and for the GUI to add colors per label.
        #  Dont forget manual label adding, just add green color to that as standard (if not changed)
        #  or add a color picker in GUI?

        # Generate colors for unique labels
        unique_labels = self._grouped_label_df["label_name"].unique()
        label_colors = ColorPicker.next_color_rgba(len(unique_labels))
        label_color_map = dict(zip(unique_labels, label_colors))
        self._grouped_label_df["rgba_color"] = self._grouped_label_df["label_name"].map(label_color_map)
        # End of TO DO
        label_summary_df = self._grouped_label_df.groupby("label_name").agg({
            "duration": "sum",
            "rgba_color": "first"
        }).reset_index()

        # Calculations for analyzing % of label use
        total_label_time = label_summary_df["duration"].sum()
        label_summary_df["overall_percent"] = (label_summary_df["duration"] / total_label_time) * 100
        label_summary_df["overall_percent"] = label_summary_df["overall_percent"].apply(lambda x: max(x, 0.01))
        label_summary_df["details"] = None

        # Saving new DF
        self._grouped_label_summary_df = label_summary_df.sort_values("overall_percent", ascending=False)
        self._combine_small_label_entries()

    def _combine_small_label_entries(self):
        """
        Combines labels with very small usage percentages into an "Others" category for plotting clarity.

        Label entries contributing less than 2% of the total labeled time are merged into a single "Others" entry.
        This combined entry accumulates the duration and percentage of these minor labels, and stores details of which labels were merged.

        :return: None
        """

        if self._grouped_label_summary_df is None or self._grouped_label_summary_df.empty:
            return

        df = self._grouped_label_summary_df.copy()
        mask = df["overall_percent"] < 2
        small_entries = df[mask].copy()

        if small_entries.empty:
            return

        details = small_entries[["label_name", "duration", "overall_percent"]].to_dict(orient="records")
        others_total_time = small_entries["duration"].sum()
        others_percent = small_entries["overall_percent"].sum()

        df = df[~mask]
        new_row = pd.DataFrame([{
            "label_name": "Others",
            "duration": others_total_time,
            "overall_percent": others_percent,
            "rgba_color": (0.5, 0.5, 0.5, 1.0),  # A neutral gray with full opacity
            "details": details  # Speichert die kleinen Einträge als Liste von Dicts
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        self._grouped_label_summary_df = df

    def _get_ax_line_activity(self):
        """
        Creates the activity line plot Axes and prepares it for interactivity.

        Generates a Matplotlib Axes (with a line plot of activity percentage over time) at the specified DPI granularity.
        Ensures the first and last data points are zero for closure, adjusts line thickness based on data density, and stores the Axes internally.
        Dynamic hover elements (marker and annotation) are set up via a helper method.

        :return: Axes (The Matplotlib Axes object for the activity line plot. Returns an Axes even if no data is available.)
        """

        fig, ax = plt.subplots(dpi=self.granularity)

        if self._main_df is None or self._main_df.empty:
            # TODO: Needs better error handling
            print("No data available for plotting.")
            return ax

        # TODO: Outsource as settings
        offset_time = 0.3
        main_value_percent = 0.9
        neighbor_value_percent = 0.1
        activity_interval = self.analysis_results["activity_interval"]  # Interval in seconds

        # Calculate left and right offset points
        x1 = self._activity_df["middle_time"] - pd.to_timedelta(offset_time * activity_interval, unit='s')
        x2 = self._activity_df["middle_time"] + pd.to_timedelta(offset_time * activity_interval, unit='s')
        y1 = (self._activity_df["activity_percent"].shift(1, fill_value=0) * neighbor_value_percent) + \
             (self._activity_df["activity_percent"] * main_value_percent)
        y2 = (self._activity_df["activity_percent"].shift(-1, fill_value=0) * neighbor_value_percent) + \
             (self._activity_df["activity_percent"] * main_value_percent)

        # Create DataFrames for left and right offset points
        left_offset_data = pd.DataFrame({"time": x1, "value": y1})
        right_offset_data = pd.DataFrame({"time": x2, "value": y2})
        original_data = pd.DataFrame(
            {"time": self._activity_df["middle_time"], "value": self._activity_df["activity_percent"]})

        # Merge all data
        activity_plot_data = pd.concat([original_data, left_offset_data, right_offset_data])
        activity_plot_data = activity_plot_data.sort_values(by="time").reset_index(drop=True)

        # FIXME: Really needed?
        # Ensure first and last points are zero
        activity_plot_data.iloc[0, activity_plot_data.columns.get_loc("value")] = 0
        activity_plot_data.iloc[-1, activity_plot_data.columns.get_loc("value")] = 0

        # Calculates the line width based on number of entries, so its easier to see the lines on many entries
        # and better to see with thicker line on few entries
        line_width = 1 + (1 - self._number_activity_points/100) if self._number_activity_points <= 100 \
            else max(0.1, 1 - (self._number_activity_points-100)/1000)

        # Plot the line
        ax.plot(activity_plot_data["time"], activity_plot_data["value"], linestyle="-", color="black",
                linewidth=line_width)
        self._set_x_lim(ax)

        # Adding Dynamic functions and saving data for it
        self.__activity_plot_helper = {}
        self.__activity_plot_helper["data"] = activity_plot_data
        self.__init_plot_data_activity(ax)
        self._activity_ax = ax

    def __init_plot_data_activity(self, ax):
        """
        Initializes interactive elements for the activity plot Axes.

        Adds a red marker and annotation text box to the activity Axes for displaying values on hover.
        Also connects the motion_notify_event of the figure canvas to the internal hover callback.

        :param ax: Axes (The Matplotlib Axes on which to initialize hover annotation elements.)
        :return: None
        """

        # Create hover annotation
        self.__activity_plot_helper["marker"], = ax.plot([], [], marker="o", color="red", markersize=3, visible=False)
        self.__activity_plot_helper["annotation"] = ax.annotate("", xy=(0, 0), xytext=(10, 10),
                                    textcoords="offset points",visible=False,
                                    bbox=dict(boxstyle="round", fc="w", ec="red", alpha=0.7))
        self.__activity_plot_helper["ax"] = ax

        # Connect hover event
        ax.figure.canvas.mpl_connect("motion_notify_event", self.__activity_on_hover)

    def __activity_on_hover(self, event):
        """
        Internal callback to handle mouse hover events on the activity line plot.

        Updates the visibility and position of the hover marker and annotation to show the nearest activity percentage value when the cursor moves over the plot.
        Only activates when the cursor is within the y-range of 0-100% on the designated activity Axes.

        :param event: Event (Matplotlib mouse motion event.)
        :return: None
        """


        # This part ensures, that it only runs in the correct axis
        if event.inaxes != self.__activity_plot_helper["ax"]:
            self.__activity_plot_helper["marker"].set_visible(False)
            self.__activity_plot_helper["annotation"].set_visible(False)
            self.__activity_plot_helper["ax"].figure.canvas.draw_idle()
            return

        # This part ensures, that it only runs in the correct y area
        if event.ydata is None or not (-5 <= event.ydata <= 105):
            self.__activity_plot_helper["marker"].set_visible(False)
            self.__activity_plot_helper["annotation"].set_visible(False)
            self.__activity_plot_helper["ax"].figure.canvas.draw_idle()
            return

        x_mouse = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)  # Ensure timezone naive

        # TODO: maybe adding this after saving data directly? so we dont allways use that methodes here.
        # Convert the DataFrame time column to timezone-naive format
        self.__activity_plot_helper["data"]["time"] = self.__activity_plot_helper["data"]["time"].dt.tz_localize(None)

        # Find the closest point based on x position
        closest_index = (self.__activity_plot_helper["data"]["time"] - x_mouse).abs().idxmin()
        closest_time = self.__activity_plot_helper["data"].iloc[closest_index]["time"]
        closest_value = self.__activity_plot_helper["data"].iloc[closest_index]["value"]

        # Update marker and annotation
        self.__activity_plot_helper["marker"].set_data([closest_time], [closest_value])
        self.__activity_plot_helper["marker"].set_visible(True)
        self.__activity_plot_helper["annotation"].xy = (closest_time, closest_value)
        self.__activity_plot_helper["annotation"].set_text(f"{closest_time.strftime('%H:%M:%S')}\n{closest_value:.2f} % Activity")
        self.__activity_plot_helper["annotation"].set_visible(True)

        self.__activity_plot_helper["ax"].figure.canvas.draw_idle()

    def _get_ax_hbar_apps(self):
        """
        Creates the horizontal bar chart Axes for application usage over time.

        Generates a Matplotlib Axes showing colored horizontal bars for each continuous application usage segment (from `_grouped_app_df`).
        Also initializes an internal helper structure for dynamic hover and selection (including a vertical hover line, triangles, and annotation).
        The Axes is stored internally for later combination.

        :return: Axes (The Matplotlib Axes object for the application horizontal bar chart.)
        """

        fig, ax = plt.subplots(dpi=self.granularity)

        if self._main_df is None or self._main_df.empty:
            # TODO: Logging
            print("No data available for plotting.")
            return ax

        self.__app_plot_helper = {}
        self.__app_plot_helper["start_y"] = start_y = -5
        self.__app_plot_helper["end_y"] = end_y = -30

        # Convert times to numeric values for plotting
        x1 = mdates.date2num(self._grouped_app_df["start_time"])
        x2 = mdates.date2num(self._grouped_app_df["end_time"])

        # Create polygons for bar representation
        verts = [np.array([[x1[i], start_y], [x2[i], start_y], [x2[i], end_y], [x1[i], end_y]])
                 for i in range(len(self._grouped_app_df))]

        # Extract colors directly from DataFrame
        colors = np.array(self._grouped_app_df["rgba_color"].tolist())  # Convert to numpy array for alignment

        # Create polygons and the PolyCollection with correct mapping for bar representation (faster visualization)
        verts = [np.array([[x1[i], start_y], [x2[i], start_y], [x2[i], end_y], [x1[i], end_y]]) for i in
                 range(len(self._grouped_app_df))]

        poly = PolyCollection(verts, facecolors=colors, alpha=0.7)
        ax.add_collection(poly)

        self.__init_plot_data_apps(ax)
        self._set_x_lim(ax)

        self._app_ax = ax

    def __init_plot_data_apps(self, ax):
        """
        Initializes interactive elements for the application usage bar chart Axes.

        Sets up a red dotted hover line spanning the full bar height, red triangle markers at the bar ends, and an annotation text box.
        Connects motion, click, and key press events on the figure canvas to internal callbacks for hover and selection.

        :param ax: Axes (The Matplotlib Axes for the application bar chart.)
        :return: None
        """

        self.__app_plot_helper["ax"] = ax
        self.__app_plot_helper["hover_line"], = ax.plot([0, 0], [self.__app_plot_helper["end_y"],
                                                                 self.__app_plot_helper["start_y"]],
                                                        color='red', linestyle='dotted', alpha=0.7, visible=False)

        # Init the artists & variables needed for dynamic viewing
        self.__app_plot_helper["triangle_up"], = ax.plot([], [], marker="v", color="red", markersize=8, visible=False)
        self.__app_plot_helper["triangle_down"], = ax.plot([], [], marker="^", color="red", markersize=8, visible=False)

        self.__app_plot_helper["annotation"] = ax.annotate("", xy=(0, self.__app_plot_helper["start_y"]),
                                                           xytext=(10, 10), textcoords="offset points",
                                                             bbox=dict(boxstyle="round", fc="white",
                                                             ec="purple", alpha=0.9), visible=False)

        self.__app_plot_helper["static_mode"] = False
        self.__app_plot_helper["selected_index"] = None

        ax.figure.canvas.mpl_connect("motion_notify_event", self.__app_on_hover)
        ax.figure.canvas.mpl_connect("button_press_event", self.__app_on_click)
        ax.figure.canvas.mpl_connect("key_press_event", self.__app_on_key)

    def __app_reset_annotation(self):
        """
        Resets all hover and selection indicators on the application bar chart.

        Turns off static mode and clears any selected index.
        Hides the hover line, annotation, and triangle markers, and refreshes the canvas.

        :return: None
        """


        self.__app_plot_helper["static_mode"] = False
        self.__app_plot_helper["selected_index"] = None
        self.__app_plot_helper["hover_line"].set_visible(False)
        self.__app_plot_helper["annotation"].set_visible(False)
        self.__app_plot_helper["triangle_up"].set_visible(False)
        self.__app_plot_helper["triangle_down"].set_visible(False)
        self.__app_plot_helper["ax"].figure.canvas.draw_idle()

    def __app_update_selection(self, index):
        """
        Updates the application bar chart to highlight a specific entry by index.

        Given an index in the `_grouped_app_df`, this sets that entry as selected:
        it draws the vertical hover line at the entry's midpoint, displays red triangle markers at the bar's top and bottom,
        and shows an annotation with the entry’s start time, end time, window type, and window title.
        The annotation position and alignment are adjusted based on the entry’s position in the list.

        :param index: int (The index of the application entry to select and highlight.)
        :return: None
        """

        if index < 0 or index >= len(self._grouped_app_df):
            return

        self.__app_plot_helper["selected_index"] = index

        entry = self._grouped_app_df.iloc[self.__app_plot_helper["selected_index"]]
        start_time = entry["start_time"].strftime("%Y-%m-%d %H:%M:%S")
        end_time = entry["end_time"].strftime("%Y-%m-%d %H:%M:%S")
        window_type = entry["window_type"]
        window_title = entry["window_title"]

        x_pos = mdates.date2num(entry["mid_time"])

        self.__app_plot_helper["hover_line"].set_xdata([x_pos])
        self.__app_plot_helper["hover_line"].set_visible(True)

        # Update triangle positions (centered on the line)
        self.__app_plot_helper["triangle_up"].set_data([x_pos], [self.__app_plot_helper["start_y"]])
        self.__app_plot_helper["triangle_down"].set_data([x_pos], [self.__app_plot_helper["end_y"]])
        self.__app_plot_helper["triangle_up"].set_visible(True)
        self.__app_plot_helper["triangle_down"].set_visible(True)

        # Determine annotation position with right/left shift and horizontal alignment
        midpoint = len(self._grouped_app_df) / 2
        text_offset = 10 if self.__app_plot_helper["selected_index"] < midpoint else -10
        ha = "left" if self.__app_plot_helper["selected_index"] < midpoint else "right"

        self.__app_plot_helper["annotation"].xy = (x_pos, self.__app_plot_helper["start_y"])
        win_title = split_text_by_max_length(window_title, 35)
        self.__app_plot_helper["annotation"].set_text(f"{start_time}\n{end_time}\n{window_type}\n{win_title}")
        self.__app_plot_helper["annotation"].set_visible(True)
        self.__app_plot_helper["annotation"].set_ha(ha)
        self.__app_plot_helper["annotation"].set_position((text_offset, 10))

        self.__app_plot_helper["ax"].figure.canvas.draw_idle()

    def __app_on_hover(self, event):
        """
        Internal callback to handle mouse hover events on the application bar chart.

        If the cursor is over the horizontal bar chart (and not in static selection mode),
        this finds the bar segment nearest to the cursor's X position and highlights it by updating the selection (via __app_update_selection).
        If the cursor moves outside the bar region, it clears the highlight.

        :param event: Event (Matplotlib mouse motion event.)
        :return: None
        """

        if event.inaxes != self.__app_plot_helper["ax"] or self.__app_plot_helper["static_mode"]:
            return

        if event.ydata is None or not (self.__app_plot_helper["end_y"] <= event.ydata <= self.__app_plot_helper["start_y"]):
            self.__app_reset_annotation()
            return

        x_mouse = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)

        # Find the closest index based on mouse x position
        valid_entries = self._grouped_app_df[
            (self._grouped_app_df["start_time"] <= x_mouse) &
            (self._grouped_app_df["end_time"] >= x_mouse)
            ]

        if not valid_entries.empty:
            closest_index = valid_entries.index[0]
        else:
            closest_index = (self._grouped_app_df["start_time"] - x_mouse).abs().idxmin()

        self.__app_update_selection(closest_index)

    def __app_on_click(self, event):
        """
        Internal callback to handle mouse click events on the application bar chart.

        If the left mouse button is clicked within the bar chart area, static mode is enabled and the bar at the clicked position is selected (locking the highlight on that segment).
        If clicked outside any bar, it resets the annotation/highlight.

        :param event: Event (Matplotlib mouse button press event.)
        :return: None
        """

        if event.button == 1 and event.inaxes == self.__app_plot_helper["ax"]:
            if self.__app_plot_helper["end_y"] <= event.ydata <= self.__app_plot_helper["start_y"]:
                x_click = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)
                valid_entries = self._grouped_app_df[
                    (self._grouped_app_df["start_time"] <= x_click) &
                    (self._grouped_app_df["end_time"] >= x_click)
                    ]
                self.__app_plot_helper["static_mode"] = True
                if not valid_entries.empty:
                    closest_index = valid_entries.index[0]
                else:
                    closest_index = (self._grouped_app_df["start_time"] - x_click).abs().idxmin()

                self.__app_update_selection(closest_index)
            else:
                self.__app_reset_annotation()

    def __app_on_key(self, event):
        """
        Internal callback to handle keyboard events for the application bar chart in static mode.

        Only processes events if a bar is currently selected in static mode.
        Left and right arrow keys cycle the selection to the previous or next entry (wrapping around cyclically),
        and the Escape key exits static mode and clears the selection.
        (The keys 'A' and 'D' could be added for alternative left/right control.)

        :param event: Event (Matplotlib key press event.)
        :return: None
        """

        # TODO: maybe add AD also for gamers
        if not self.__app_plot_helper["static_mode"] or self.__app_plot_helper["selected_index"] is None:
            return

        if event.key == "escape":
            self.__app_reset_annotation()
            return

        if event.key in ["right", "left"]:
            step = 1 if event.key == "right" else -1
            new_index = self.__app_plot_helper["selected_index"] + step
            if new_index > len(self._grouped_app_df) - 1:
                new_index = 0

            elif new_index < 0:
                new_index = len(self._grouped_app_df) - 1
            print(new_index)
            self.__app_update_selection(new_index)

    def _update_ax_hbar_labels(self, label_list: list[str] | str = None):
        """
        Creates or updates the horizontal bar chart Axes for label usage segments.

        If `label_list` is provided, the plot will include only those labels (in the given order, up to 5 labels).
        Otherwise, it will default to the first 5 labels in the data.
        Each label's continuous usage segments (from `_grouped_label_df`) are drawn as horizontal bars at a distinct y-level.

        :param label_list: list[str] | str | None (Optional. A label or list of labels to display. If None, the top 5 labels by occurrence are shown.)
        :raises ValueError: If no label data is available or if any requested labels are not found in the data.
        :return: Axes (The Matplotlib Axes object for the label horizontal bar chart.)
        """

        fig, ax = plt.subplots(dpi=self.granularity)

        self.__label_plot_helper["x_start"] = mdates.date2num(self.analysis_results["first_datetime"])
        self.__label_plot_helper["x_end"] = mdates.date2num(self.analysis_results["last_datetime"])

        if self._grouped_label_df is None or self._grouped_label_df.empty:
            raise ValueError("No data available in `_grouped_label_df`.")

        available_labels = self._grouped_label_df["label_name"].unique()

        if label_list is None:
            label_list = available_labels[:5]
        elif isinstance(label_list, str):
            label_list = [label_list]

        # Checks if all param lables exist if not raises error
        missing_labels = [label for label in label_list if label not in available_labels]
        if missing_labels:
            # TODO: Logging
            raise ValueError(f"Labels not found: {missing_labels}")

        lowest_y = (self.__label_plot_helper["start_y"] + len(label_list) *
                    (self.__label_plot_helper["bar_height"] + self.__label_plot_helper["y_spacing"]) * -1)

        # Filters the labels and forces exact order of the inputted params, so the order can be switched by user
        self.__label_plot_helper["label_data"] = self._grouped_label_df[self._grouped_label_df["label_name"]
                                                                                            .isin(label_list)].copy()
        self.__label_plot_helper["label_data"]["label_name"] = pd.Categorical(
            self.__label_plot_helper["label_data"]["label_name"],
            categories=label_list,
            ordered=True
        )

        # Sort by label_list order first, then by start_time (ascending)
        self.__label_plot_helper["label_data"].sort_values(
            by=["label_name", "start_time"],
            ascending=[True, True],
            inplace=True
        )

        self.__label_plot_helper["label_data"].reset_index(drop=True, inplace=True)

        current_y = self.__label_plot_helper["start_y"]
        self.__label_plot_helper["label_y_mapping"] = {}

        for label in label_list:
            df_subset = self.__label_plot_helper["label_data"][self.__label_plot_helper["label_data"]["label_name"] == label]

            self.__label_plot_helper["label_y_mapping"][label] = current_y

            for _, row in df_subset.iterrows():
                x1 = mdates.date2num(row["start_time"])
                x2 = mdates.date2num(row["end_time"])
                rgba_color = row["rgba_color"]

                # Draw horizontal bar
                ax.barh(y=current_y - (self.__label_plot_helper["bar_height"] / 2), width=(x2 - x1), left=x1,
                        height=self.__label_plot_helper["bar_height"], color=rgba_color, alpha=0.7)

            current_y -= self.__label_plot_helper["bar_height"] + self.__label_plot_helper["y_spacing"]

        self.__init_plot_data_label(ax)
        self._set_x_lim(ax)
        ax.set_ylim(lowest_y, 110)

        self._label_ax = ax

    def __init_plot_data_label(self, ax):
        """
        Initializes interactive elements for the label usage bar chart Axes.

        Sets up a red dotted hover line, red triangle markers at the bar boundaries, and an annotation text box for label segments.
        Connects motion, click, and key press events to internal callbacks for hover and selection on the label chart.

        :param ax: Axes (The Matplotlib Axes for the label bar chart.)
        :return: None
        """

        self.__label_plot_helper["ax"] = ax
        self.__label_plot_helper["hover_line"], = ax.plot([0, 0], [0, 0], color='red', linestyle='dotted', alpha=0.7, visible=False)

        # Zwei Dreiecke für die Markierung
        self.__label_plot_helper["triangle_up"], = ax.plot([], [], marker="v", color="red", markersize=8, visible=False)  # Unten
        self.__label_plot_helper["triangle_down"], = ax.plot([], [], marker="^", color="red", markersize=8, visible=False)  # Oben

        self.__label_plot_helper["annotation"] = ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
                                 bbox=dict(boxstyle="round", fc="white", ec="blue", alpha=0.9),
                                 visible=False)

        self.__label_plot_helper["static_mode"] = False
        self.__label_plot_helper["selected_index"] = None

        ax.figure.canvas.mpl_connect("motion_notify_event", self.__label_on_hover)
        ax.figure.canvas.mpl_connect("button_press_event", self.__label_on_click)
        ax.figure.canvas.mpl_connect("key_press_event", self.__label_on_key)

    def __label_reset_annotation(self):
        """
        Resets all hover and selection indicators on the label bar chart.

        Turns off static mode and clears any selected segment index.
        Hides the hover line, annotation, and triangle markers, then refreshes the canvas.

        :return: None
        """

        self.__label_plot_helper["static_mode"] = False
        self.__label_plot_helper["selected_index"] = None
        self.__label_plot_helper["hover_line"].set_visible(False)
        self.__label_plot_helper["annotation"].set_visible(False)
        self.__label_plot_helper["triangle_up"].set_visible(False)
        self.__label_plot_helper["triangle_down"].set_visible(False)
        self.__label_plot_helper["ax"].figure.canvas.draw_idle()

    def __label_update_selection(self, index):
        """
        Updates the label bar chart to highlight a specific time segment by index.

        Given an index in the label data (self.__label_plot_helper["label_data"]), this method selects that segment:
        it draws a red hover line at the segment's midpoint, shows red triangle markers at the segment's top and bottom boundaries,
        and displays an annotation with the label name, start-end time, and total duration (HH:MM:SS format) for that segment.

        :param index: int (The index of the label segment to select and highlight.)
        :return: None
        """

        if index < 0 or index >= len(self.__label_plot_helper["label_data"]):
            return

        self.__label_plot_helper["selected_index"] = index

        entry = self.__label_plot_helper["label_data"].iloc[self.__label_plot_helper["selected_index"]]
        start_time = entry["start_time"].strftime("%H:%M:%S")
        end_time = entry["end_time"].strftime("%H:%M:%S")
        duration_seconds = int((entry["end_time"] - entry["start_time"]).total_seconds())
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration = f"{hours:02}:{minutes:02}:{seconds:02}"

        x_pos = mdates.date2num(entry["start_time"] + (entry["end_time"] - entry["start_time"]) / 2)
        y_pos = self.__label_plot_helper["label_y_mapping"][entry["label_name"]]

        self.__label_plot_helper["hover_line"].set_xdata([x_pos])
        self.__label_plot_helper["hover_line"].set_ydata([y_pos - self.__label_plot_helper["bar_height"], y_pos])

        self.__label_plot_helper["hover_line"].set_visible(True)

        self.__label_plot_helper["triangle_up"].set_data([x_pos], [y_pos])
        self.__label_plot_helper["triangle_down"].set_data([x_pos], [y_pos - self.__label_plot_helper["bar_height"]])
        self.__label_plot_helper["triangle_up"].set_visible(True)
        self.__label_plot_helper["triangle_down"].set_visible(True)

        # Annotation position check
        text_offset = 10 if x_pos < (self.__label_plot_helper["x_start"] + self.__label_plot_helper["x_end"]) / 2 \
            else -10
        ha = "left" if x_pos < (self.__label_plot_helper["x_start"] + self.__label_plot_helper["x_end"]) / 2 \
            else "right"

        self.__label_plot_helper["annotation"].xy = (x_pos, y_pos)
        self.__label_plot_helper["annotation"].set_text(f"{entry['label_name']}\n{start_time} - {end_time}\n{duration}")
        self.__label_plot_helper["annotation"].set_visible(True)
        self.__label_plot_helper["annotation"].set_ha(ha)
        self.__label_plot_helper["annotation"].set_position((text_offset, 10))

        self.__label_plot_helper["ax"].figure.canvas.draw_idle()

    def __label_on_hover(self, event):
        """
        Internal callback to handle mouse hover events on the label bar chart.

        If the cursor is over the region of a label's horizontal bars (and not in static mode),
        this determines which label's bar the cursor is near and highlights the corresponding segment by updating the selection.
        If the cursor moves away from any label bars, it clears the highlight.

        :param event: Event (Matplotlib mouse motion event.)
        :return: None
        """

        if event.inaxes != self.__label_plot_helper["ax"] or self.__label_plot_helper["static_mode"]:
            return

        closest_label = None
        # Gets closest label, if none found, resets the annotations
        for label, y_pos in self.__label_plot_helper["label_y_mapping"].items():
            if (y_pos - self.__label_plot_helper["bar_height"] - int(self.__label_plot_helper["y_spacing"])) <= event.ydata <= (y_pos + int(self.__label_plot_helper["y_spacing"])):
                closest_label = label
                break

        if closest_label is None:
            self.__label_reset_annotation()
            return

        # After label y found this looks for the fitting data entry on that label
        x_mouse = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)
        valid_entries = self.__label_plot_helper["label_data"][
            (self.__label_plot_helper["label_data"]["start_time"] <= x_mouse) &
            (self.__label_plot_helper["label_data"]["end_time"] >= x_mouse) &
            (self.__label_plot_helper["label_data"]["label_name"] == closest_label)
            ]

        if not valid_entries.empty:
            closest_index = valid_entries.index[0]
        else:
            closest_index = (self.__label_plot_helper["label_data"][
                                 self.__label_plot_helper["label_data"]["label_name"] == closest_label
                                 ]["start_time"] - x_mouse).abs().idxmin()

        self.__label_update_selection(closest_index)

    def __label_on_click(self, event):
        """
        Internal callback to handle mouse click events on the label bar chart.

        If a click occurs within the area of a label's bars, static mode is enabled and the nearest label segment is selected (locking the highlight on that segment).
        Clicking outside any label bars will reset the current selection (turn off static mode and clear highlights).

        :param event: Event (Matplotlib mouse button press event.)
        :return: None
        """

        if event.inaxes != self.__label_plot_helper["ax"]:
            return

        closest_label = None
        for label, y_pos in self.__label_plot_helper["label_y_mapping"].items():
            if ((y_pos - self.__label_plot_helper["bar_height"] - self.__label_plot_helper["y_spacing"]) <= event.ydata
                    <= (y_pos - self.__label_plot_helper["y_spacing"])):
                closest_label = label
                break

        if closest_label is None:
            # Falls Klick außerhalb aller Labels → Zurücksetzen
            self.__label_reset_annotation()
            return

        x_click = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)
        valid_entries = self.__label_plot_helper["label_data"][
            (self.__label_plot_helper["label_data"]["start_time"] <= x_click) &
            (self.__label_plot_helper["label_data"]["end_time"] >= x_click) &
            (self.__label_plot_helper["label_data"]["label_name"] == closest_label)
            ]

        self.__label_plot_helper["static_mode"] = True
        if not valid_entries.empty:
            closest_index = valid_entries.index[0]
        else:
            closest_index = (self.__label_plot_helper["label_data"][
                                 self.__label_plot_helper["label_data"]["label_name"] == closest_label
                                 ]["start_time"] - x_click).abs().idxmin()

        self.__label_update_selection(closest_index)

    def __label_on_key(self, event):
        """
        Internal callback to handle keyboard events for the label bar chart in static mode.

        Only active when a label segment is selected in static mode.
        The left and right arrow keys cycle through segments of the currently selected label (with wrap-around),
        and the Escape key exits static mode and clears the selection.

        :param event: Event (Matplotlib key press event.)
        :return: None
        """

        if not self.__label_plot_helper["static_mode"] or self.__label_plot_helper["selected_index"] is None:
            return

        if event.key == "escape":
            self.__label_reset_annotation()
            return

        if event.key in ["right", "left"]:
            step = 1 if event.key == "right" else -1

            current_label = self.__label_plot_helper["label_data"] \
                .iloc[self.__label_plot_helper["selected_index"]]["label_name"]
            same_label_entries = self.__label_plot_helper["label_data"] \
                [self.__label_plot_helper["label_data"]["label_name"] == current_label]

            relative_index = same_label_entries.index.get_loc(self.__label_plot_helper["selected_index"])
            new_relative_index = (relative_index + step) % len(same_label_entries)
            new_index = same_label_entries.index[new_relative_index]

            self.__label_update_selection(new_index)

    def _set_x_lim(self, ax):
        """
        Sets the X-axis limits and formatter for a given Axes based on the analysis time frame.

        The lower limit is the first timestamp and the upper limit is the last timestamp from `analysis_results`.
        Also applies the pre-determined major formatter for the X-axis (stored in `analysis_results["major_formatter_x"]`) for proper time scale labeling.

        :param ax: Axes (The Matplotlib Axes on which to set the X-axis limits and formatter.)
        :return: None
        """

        x_min = mdates.date2num(self.analysis_results["first_datetime"])
        x_max = mdates.date2num(self.analysis_results["last_datetime"])
        ax.set_xlim(x_min, x_max)
        # FIXME: Smart solution for showing time properly(based on interval)
        # TODO: probably fixed allready
        ax.xaxis.set_major_formatter(self.analysis_results["major_formatter_x"])


    def _combine_axes(self):
        """
        Combines the individual plots (activity, app, label) into a single Matplotlib figure.

        This method takes the Axes created for activity, application, and label plots and copies all their lines, patches, and collections into a new Axes on a fresh figure.
        Interactive elements (hover and click callbacks) are reinitialized on the new combined Axes. The resulting figure is stored in `self.mainplot`.

        :raises ValueError: If any of the required Axes (activity, app, label) is missing.
        :return: None
        """

        ax_list = [self._activity_ax, self._app_ax, self._label_ax]
        if not all(ax_list):
            # TODO: Logger
            raise ValueError("All axes must be specified.")

        highest_dpi = max(max(ax.figure.dpi for ax in ax_list), 100)
        highest_x = max(ax.get_xlim()[1] for ax in ax_list)
        lowest_x = min(ax.get_xlim()[0] for ax in ax_list)

        highest_y = max(ax.get_ylim()[1] for ax in ax_list)
        lowest_y = min(ax.get_ylim()[0] for ax in ax_list)

        mirrored_formatter = None
        if isinstance(ax_list[0].xaxis.get_major_formatter(), mdates.DateFormatter):
            # Convert back to datetime for accuracy

            mirrored_formatter = ax_list[0].xaxis.get_major_formatter()
            lowest_x = mdates.num2date(lowest_x)
            highest_x = mdates.num2date(highest_x)

        # Check if y-axis is time-based (labels could use time on y)
        if isinstance(ax_list[0].yaxis.get_major_formatter(), mdates.DateFormatter):
            lowest_y = mdates.num2date(lowest_y)
            highest_y = mdates.num2date(highest_y)

        new_fig, new_ax = plt.subplots(dpi=highest_dpi)

        # Copy elements from each provided axis
        for old_ax in ax_list:
            # Get all Line2D objects
            for line in old_ax.get_lines():
                x_data, y_data = line.get_xdata(), line.get_ydata()
                new_ax.plot(x_data, y_data,
                            linestyle=line.get_linestyle(),
                            color=line.get_color(),
                            linewidth=line.get_linewidth(),
                            alpha=line.get_alpha() if line.get_alpha() else 1.0)

            for patch in old_ax.patches:
                edge_color = patch.get_edgecolor()

                # Ensure no border if the original had no visible edge
                # If fully transparent (RGBA last value == 0)
                if edge_color is None or edge_color[-1] == 0:
                    edge_color = "none"

                new_patch = plt.Rectangle(
                    xy=(patch.get_x(), patch.get_y()),
                    width=patch.get_width(),
                    height=patch.get_height(),
                    facecolor=patch.get_facecolor(),
                    edgecolor=edge_color,  # Ensure correct border handling
                    alpha=patch.get_alpha() if patch.get_alpha() is not None else 1.0,
                    linestyle=patch.get_linestyle(),
                    linewidth=patch.get_linewidth(),
                    zorder=patch.get_zorder()
                )
                new_ax.add_patch(new_patch)

            for collection in old_ax.collections:
                if isinstance(collection, PolyCollection):
                    # Extract the vertices (shape coordinates)
                    verts = [path.vertices for path in collection.get_paths()]

                    # Extract colors in the correct order
                    facecolors = collection.get_facecolors()
                    edgecolors = collection.get_edgecolors()

                    # Ensure proper transparency and styling
                    new_poly = PolyCollection(
                        verts,
                        facecolors=facecolors,
                        edgecolors=edgecolors,
                        alpha=collection.get_alpha() if collection.get_alpha() is not None else 1.0,
                        linewidths=collection.get_linewidths(),
                        linestyles=collection.get_linestyles(),
                        zorder=collection.get_zorder()
                    )

                    # Add to the new axis
                    new_ax.add_collection(new_poly)



        new_ax.set_ylim(lowest_y, highest_y)
        new_ax.set_xlim(lowest_x, highest_x)
        new_ax.xaxis.set_major_formatter(mirrored_formatter)

        # Init the new ax as main ax and binds interactive methods properly
        self.__init_plot_data_activity(new_ax)
        self.__init_plot_data_apps(new_ax)
        self.__init_plot_data_label(new_ax)

        self.mainplot = new_fig

    def get_main_plot(self):
        """
        Returns the combined Matplotlib Figure containing all plots (activity, app, label).

        If the combined figure (`mainplot`) has not been created yet, this method will call `_combine_axes()` to generate it.
        This figure can be used for displaying in a GUI or saving to file.

        :return: Figure (The Matplotlib figure with the combined plots.)
        """

        if self.mainplot is None:
            self._combine_axes()
        return self.mainplot

    def get_vbar_apps(self):
        """
        Creates and returns a Matplotlib Figure with a vertical bar chart of overall app usage percentages.

        Each bar represents an application's total usage percentage (with bars colored accordingly).
        Hover interactivity is enabled on the bars to show precise percentages and durations, with minor entries aggregated under "Others".

        :return: Figure | None (The Matplotlib figure for app usage bar chart, or None if there is no app data.)
        """

        if self._grouped_app_summary_df is None or self._grouped_app_summary_df.empty:
            print("No app data available for plotting.")
            return None

        df = self._grouped_app_summary_df

        # TODO: maybe adding granularity?
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df["window_type"], df["overall_percent"], color=df["rgba_color"])


        # TODO: Maybe not needed infos, check after implementing into GUI
        ax.set_xlabel("Apps")
        ax.set_ylabel("Percent usage")
        ax.set_title("App usage")

        ax.set_ylim(0, df["overall_percent"].max() + 5)

        # Rotate a lil the x axis for better reading
        plt.xticks(rotation=45, ha="right")

        # Elements for interactive methods
        hover_line, = ax.plot([0, 0], [0, 0], color='red', linestyle='dotted', alpha=0.7, visible=False)
        triangle_up, = ax.plot([], [], marker="v", color="red", markersize=8, visible=False)
        annotation = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                                 textcoords="offset points", ha="center", va="bottom",
                                 fontsize=10, color="black",
                                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))
        annotation.set_visible(False)

        # Inline functions because not needed outsourced
        def on_hover(event):
            if event.inaxes != ax:
                annotation.set_visible(False)
                triangle_up.set_visible(False)
                hover_line.set_visible(False)
                fig.canvas.draw_idle()
                return

            for bar, (app_name, percent, duration, details) in zip(bars, zip(df["window_type"], df["overall_percent"],
                                                                             df["duration"], df.get("details", None))):
                bar_x_min = bar.get_x()
                bar_x_max = bar.get_x() + bar.get_width()
                bar_center_x = bar.get_x() + bar.get_width() / 2

                if bar_x_min <= event.xdata <= bar_x_max:
                    # Staying with hours max, because who wants to see days/weeks for usage time?
                    hours, remainder = divmod(duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}(HH:MM:SS)"

                    annotation_text = f"{app_name}: {percent:.2f}%\n{duration_str}"

                    # If "Others", show details
                    if app_name == "Others" and details:
                        detail_texts = [f"{d['window_type']}: {d['overall_percent']:.2f}%" for d in details]
                        annotation_text += "\n" + "\n".join(detail_texts[:5])  # Show max 5 entries
                        n_lines_space = annotation_text.count("\n") * 0.1
                    else:
                        n_lines_space = 0.5

                    # Position annotation at the middle Y range
                    mid_y = ax.get_ylim()[1] / 2
                    annotation.xy = (bar_center_x, mid_y)
                    annotation.set_text(annotation_text)
                    annotation.set_visible(True)

                    hover_line.set_data([bar_center_x, bar_center_x], [mid_y - n_lines_space, 0])
                    hover_line.set_visible(True)

                    triangle_up.set_data([bar_center_x], [mid_y - n_lines_space])
                    triangle_up.set_visible(True)

                    fig.canvas.draw_idle()
                    return

            annotation.set_visible(False)
            triangle_up.set_visible(False)
            hover_line.set_visible(False)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_hover)

        return fig

    def get_vbar_labels(self):
        """
        Creates and returns a Matplotlib Figure with a vertical bar chart of overall label usage percentages.

        Each bar represents a label's total usage percentage (colored accordingly).
        Hover interactivity on the bars shows precise percentages and durations, with minor labels aggregated under "Others".

        :return: Figure | None (The Matplotlib figure for label usage bar chart, or None if there is no label data.)
        """

        if self._grouped_label_summary_df is None or self._grouped_label_summary_df.empty:
            # TODO: Logging
            print("No label data available for plotting.")
            return None

        df = self._grouped_label_summary_df

        # TODO: maybe adding granularity?
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df["label_name"], df["overall_percent"], color=df["rgba_color"])

        # Set axis labels and title
        ax.set_xlabel("Labels")
        ax.set_ylabel("Percent usage")
        ax.set_title("Label usage")

        # Set Y-axis limit slightly above max value for padding
        ax.set_ylim(0, df["overall_percent"].max() + 5)

        # Rotate x-axis labels for readability
        plt.xticks(rotation=45, ha="right")

        # Elements for dynamic functions
        hover_line, = ax.plot([0, 0], [0, 0], color='red', linestyle='dotted', alpha=0.7, visible=False)
        triangle_up, = ax.plot([], [], marker="v", color="red", markersize=8, visible=False)
        annotation = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                                 textcoords="offset points", ha="center", va="bottom",
                                 fontsize=10, color="black",
                                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))
        annotation.set_visible(False)

        def on_hover(event):

            if event.inaxes != ax:
                annotation.set_visible(False)
                triangle_up.set_visible(False)
                hover_line.set_visible(False)
                fig.canvas.draw_idle()
                return

            for bar, (label_name, percent, duration, details) in zip(bars, zip(df["label_name"], df["overall_percent"],
                                                                     df["duration"], df.get("details", None))):
                bar_x_min = bar.get_x()
                bar_x_max = bar.get_x() + bar.get_width()
                bar_center_x = bar.get_x() + bar.get_width() / 2

                # Check if cursor is inside the bar's X range
                if bar_x_min <= event.xdata <= bar_x_max:
                    # Convert `duration` to `HH:MM:SS`, we dont need
                    hours, remainder = divmod(duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02} (HH:MM:SS)"

                    # Base annotation text
                    annotation_text = f"{label_name}: {percent:.2f}%\n{duration_str}"

                    # If "Others", show details, max 5 entries
                    if label_name == "Others" and details:
                        detail_texts = [f"{d['label_name']}: {d['overall_percent']:.2f}%" for d in details]
                        annotation_text += "\n" + "\n".join(detail_texts[:5])
                        n_lines_space = annotation_text.count("\n") * 0.1
                    else:
                        n_lines_space = 0.5

                    mid_y = ax.get_ylim()[1] / 2
                    annotation.xy = (bar_center_x, mid_y)
                    annotation.set_text(annotation_text)
                    annotation.set_visible(True)


                    hover_line.set_data([bar_center_x, bar_center_x], [mid_y - n_lines_space, 0])
                    hover_line.set_visible(True)

                    triangle_up.set_data([bar_center_x], [mid_y - n_lines_space])
                    triangle_up.set_visible(True)

                    fig.canvas.draw_idle()
                    return

            annotation.set_visible(False)
            triangle_up.set_visible(False)
            hover_line.set_visible(False)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_hover)

        return fig

    def get_pie_apps(self):
        """
        Creates and returns a Matplotlib Figure with a pie chart of overall application usage.

        Each wedge represents an application's percentage of total usage (colored accordingly).
        Annotations for each wedge (application name) are placed around the pie, and hovering over a label displays the percentage and duration (with details for "Others" if present).

        :return: Figure | None (The Matplotlib figure for app usage pie chart, or None if there is no app data.)
        """

        if self._grouped_app_summary_df is None or self._grouped_app_summary_df.empty:
            # TODO: Logging
            print("No app data available for plotting.")
            return None

        df = self._grouped_app_summary_df

        # TODO: maybe adding granularity?
        fig, ax = plt.subplots(figsize=(8, 8))

        # Generate wedges with leader lines
        wedges, texts, autotexts = ax.pie(
            df["overall_percent"],
            labels=None,
            autopct="%1.1f%%",
            colors=df["rgba_color"],
            startangle=90,
            counterclock=False,
            wedgeprops={"edgecolor": "black", "linewidth": 0.3, "antialiased": True}
        )

        # Smaller font inside for better readability
        for autotext in autotexts:
            autotext.set_fontsize(8)

        # Store label positions for hover effect
        label_annotations = []

        for i, (wedge, label, percent, duration, color) in enumerate(zip(
                wedges, df["window_type"], df["overall_percent"], df["duration"], df["rgba_color"])):
            # Get angle of the wedge (middle of arc)
            angle = (wedge.theta2 + wedge.theta1) / 2

            # Offset every second label further to prevent overlap
            offset_factor = 1.345 if i % 2 == 1 else 1.2
            x = np.cos(np.deg2rad(angle)) * offset_factor
            y = np.sin(np.deg2rad(angle)) * offset_factor

            ax.plot([np.cos(np.deg2rad(angle)), x], [np.sin(np.deg2rad(angle)), y], color="black", lw=0.8)

            bbox_props = dict(boxstyle="round,pad=0.4", edgecolor=color, facecolor="white", linewidth=1.2)
            text = ax.text(x, y, f"{label}", ha="center", va="center", fontsize=8, bbox=bbox_props)

            label_annotations.append((text, label, percent, duration, angle, x, y, color))

        annotation = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                                 textcoords="offset points", ha="center", va="bottom",
                                 fontsize=10, color="black",
                                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white", alpha=0.95))
        annotation.set_visible(False)

        def on_hover(event):
            if event.inaxes != ax:
                annotation.set_visible(False)
                fig.canvas.draw_idle()
                return

            for text, label_name, percent, duration, angle, x, y, color in label_annotations:
                bbox = text.get_window_extent(renderer=fig.canvas.get_renderer())

                # for better hover detection
                expanded_bbox = bbox.expanded(1.4, 1.6)  # 40% wider, 60% taller
                expanded_bbox.x0 -= 5  # Expand left
                expanded_bbox.x1 += 5  # Expand right
                expanded_bbox.y0 -= 5  # Expand bottom
                expanded_bbox.y1 += 5  # Expand top

                if expanded_bbox.contains(event.x, event.y):
                    # Convert `duration` to `HH:MM:SS`
                    hours, remainder = divmod(duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02} (HH:MM:SS)"

                    annotation_text = f"{label_name}: {percent:.2f}%\n{duration_str}"

                    # Check if "Others" and add details with max 5 entries
                    if label_name == "Others" and "details" in df.columns:
                        details = df.loc[df["window_type"] == "Others", "details"].values[0]
                        if details:
                            detail_texts = [f"{d['window_type']}: {d['overall_percent']:.2f}%" for d in details]
                            annotation_text += "\n" + "\n".join(detail_texts[:5])

                    # Position annotation below the app name in a fixed location
                    annotation.xy = (x, y - 0.1)
                    annotation.set_text(annotation_text)
                    annotation.set_visible(True)

                    fig.canvas.draw_idle()
                    return

            annotation.set_visible(False)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_hover)

        # Expand space to prevent labels from being cut off
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.4, 1.4)

        return fig

    def get_pie_labels(self):
        """
        Creates and returns a Matplotlib Figure with a pie chart of overall label usage.

        Each wedge represents a label's percentage of total usage (colored accordingly).
        Label annotations are placed around the pie, and hovering over a label displays the percentage and duration (with details for "Others" if present).

        :return: Figure | None (The Matplotlib figure for label usage pie chart, or None if there is no label data.)
        """

        if self._grouped_label_summary_df is None or self._grouped_label_summary_df.empty:
            print("No label data available for plotting.")
            return None

        df = self._grouped_label_summary_df

        # TODO: maybe adding granularity?
        fig, ax = plt.subplots(figsize=(8, 8))

        # Generate wedges with leader lines
        wedges, texts, autotexts = ax.pie(
            df["overall_percent"],
            labels=None,
            autopct="%1.1f%%",
            colors=df["rgba_color"],
            startangle=90,
            counterclock=False,
            wedgeprops={"edgecolor": "black", "linewidth": 0.3, "antialiased": True}
        )

        for autotext in autotexts:
            autotext.set_fontsize(8)

        label_annotations = []

        for i, (wedge, label, percent, duration, color) in enumerate(zip(
                wedges, df["label_name"], df["overall_percent"], df["duration"], df["rgba_color"])):
            # Get angle of the wedge (middle of arc)
            angle = (wedge.theta2 + wedge.theta1) / 2

            # Offset every second label further to prevent overlap
            offset_factor = 1.345 if i % 2 == 1 else 1.2
            x = np.cos(np.deg2rad(angle)) * offset_factor
            y = np.sin(np.deg2rad(angle)) * offset_factor

            ax.plot([np.cos(np.deg2rad(angle)), x], [np.sin(np.deg2rad(angle)), y], color="black", lw=0.8)

            bbox_props = dict(boxstyle="round,pad=0.4", edgecolor=color, facecolor="white", linewidth=1.2)
            text = ax.text(x, y, f"{label}", ha="center", va="center", fontsize=8, bbox=bbox_props)

            label_annotations.append((text, label, percent, duration, angle, x, y, color))

        annotation = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                                 textcoords="offset points", ha="center", va="bottom",
                                 fontsize=10, color="black",
                                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white", alpha=0.95))
        annotation.set_visible(False)

        def on_hover(event):
            if event.inaxes != ax:
                annotation.set_visible(False)
                fig.canvas.draw_idle()
                return

            for text, label_name, percent, duration, angle, x, y, color in label_annotations:
                bbox = text.get_window_extent(renderer=fig.canvas.get_renderer())

                expanded_bbox = bbox.expanded(1.4, 1.6)  # 40% wider, 60% taller
                expanded_bbox.x0 -= 5  # Expand left
                expanded_bbox.x1 += 5  # Expand right
                expanded_bbox.y0 -= 5  # Expand bottom
                expanded_bbox.y1 += 5  # Expand top

                if expanded_bbox.contains(event.x, event.y):
                    # Convert `duration` to `HH:MM:SS`
                    hours, remainder = divmod(duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02} (HH:MM:SS)"

                    annotation_text = f"{label_name}: {percent:.2f}%\n{duration_str}"

                    # Check if "Others" and add details for max 5 entries
                    if label_name == "Others" and "details" in df.columns:
                        details = df.loc[df["label_name"] == "Others", "details"].values[0]
                        if details:
                            detail_texts = [f"{d['label_name']}: {d['overall_percent']:.2f}%" for d in details]
                            annotation_text += "\n" + "\n".join(detail_texts[:5])

                    annotation.xy = (x, y - 0.1)
                    annotation.set_text(annotation_text)
                    annotation.set_visible(True)

                    fig.canvas.draw_idle()
                    return

            annotation.set_visible(False)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_hover)

        # Expanding the axis, because the label name is offset to the pie and could be cut off
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-1.4, 1.4)

        return fig


class DayAnalyzer:
    """
    A singleton class for performing continuous daily analysis in a background thread.

    The DayAnalyzer loads the day's data using the database handler and initializes a ViperDF for analysis.
    It runs a background thread that periodically checks whether the data should be refreshed (at a fixed interval),
    automatically updating the ViperDF with new data while the application is running.

    Attributes:
        _instance (DayAnalyzer | None): Class-level singleton instance.
        _lock (Lock): Thread lock to synchronize access to the ViperDF data.
        _db_call (Callable): Reference to the database query function for retrieving window log data.
        _vdf (ViperDF): The ViperDF instance holding the current day's analyzed data.
        _check_interval (int): Interval in minutes between automatic data refresh checks.
        _next_check_timestamp (datetime): Timestamp for the next scheduled data refresh.
        _thread (Thread): Background thread that continuously checks and triggers data refresh.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures that DayAnalyzer follows the singleton pattern.

        If an instance of DayAnalyzer already exists, __new__ returns it; otherwise, it creates a new instance.

        :return: DayAnalyzer (The singleton instance of DayAnalyzer.)
        """

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the DayAnalyzer singleton (only on the first instantiation).

        On first initialization, this sets up a lock, retrieves the current window log data via the database handler,
        creates a ViperDF for "day_analysis" with that data, and immediately calls its analyze() method.
        It also schedules the first check time and starts a background thread for periodic refresh.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            self._lock = Lock()
            self._initialized = True
            self._db_call = DBHandler().search_window_log
            tmp_df = self._db_call()
            self._vdf = ViperDF("day_analysis", tmp_df)
            self._vdf.analyze()

            self._check_interval = 2  # Minutes
            self._next_check_timestamp = datetime.now() + timedelta(minutes=self._check_interval)

            self._thread = Thread(target=self._thread_loop)
            self._thread.start()

    def _check_for_action(self):
        """
        Checks if it is time to refresh the analysis data and triggers a refresh if needed.

        This method should be called periodically (e.g., by the background thread).
        If the current time has passed the scheduled `_next_check_timestamp`, it updates `_next_check_timestamp` to the next interval and calls `DayAnalyzer.this.refresh_data()`.

        :return: None
        """

        with self._lock:

            if not self._next_check_timestamp >= datetime.now():
                return

            self._next_check_timestamp = datetime.now() + timedelta(minutes=self._check_interval)
        DayAnalyzer.this.refresh_data()

    def _thread_loop(self):
        """
        Checks if it is time to refresh the analysis data and triggers a refresh if needed.

        This method should be called periodically (e.g., by the background thread).
        If the current time has passed the scheduled `_next_check_timestamp`, it updates `_next_check_timestamp` to the next interval and calls `DayAnalyzer.this.refresh_data()`.

        :return: None
        """

        do_stop = False
        while not threads_are_stopped():
            inter = 60  # Needs to stay 60 as interval
            fifth_timer = inter // 5
            for i in range(fifth_timer):
                sleep(5)
                if threads_are_stopped():
                    do_stop = True
                    break
            if do_stop:
                break
            self._check_for_action()

    def refresh_data(self):
        """
        Refreshes the internal data by reloading from the database and re-running the analysis.

        Deletes the old ViperDF, fetches fresh data via the database call, creates a new ViperDF for "day_analysis",
        and invokes analyze() on it. This method is thread-safe (guarded by `_lock`).

        :return: None
        """

        with self._lock:
            del self._vdf
            tmp_df = self._db_call()
            self._vdf = ViperDF("day_analysis", tmp_df)
            self._vdf.analyze()

    def get_data(self) -> ViperDF:
        """
        Retrieves the current ViperDF containing the analyzed data in a thread-safe manner.

        Acquires the internal lock and returns the ViperDF instance holding the latest analysis results.

        :return: ViperDF (The current ViperDF instance with up-to-date analysis data.)
        """

        with self._lock:
            return self._vdf

    @Classproperty
    def this(cls):
        """
        Provides convenient access to the DayAnalyzer singleton instance.

        Calling `DayAnalyzer.this` returns the single DayAnalyzer instance, creating it if it doesn't exist yet.
        This allows easy access to the analyzer via `DayAnalyzer.this` instead of constructing a new object.

        :return: DayAnalyzer (The singleton instance of DayAnalyzer.)
        """

        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

# # # # Helper functions # # # #

def split_leading_special_chars(word: str):
    """
    Splits a string into leading special characters and the remaining word.

    This function iterates from the start of the string and separates any leading non-alphanumeric characters from the rest of the word.

    :param word: str (The input string to split.)
    :return: tuple[str, str] (A tuple where the first element is the string of leading special characters, and the second is the remaining word.)
    """

    special_chars = ""
    while word and not word[0].isalnum():
        special_chars += word[0]
        word = word[1:]
    return special_chars, word


def split_text_by_max_length(text: str, max_length: int) -> str:
    """
    Splits a text into multiple lines without exceeding a given maximum length per line.

    The split is done at word boundaries (spaces). If a word starts with punctuation or special characters (e.g., "!", "...", ","),
    those characters are kept attached to the previous line to avoid starting a new line with a special character.
    This is useful for formatting annotation text in interactive plots.

    :param text: str (The input text to be split into lines.)
    :param max_length: int (The maximum allowed length of each line.)
    :return: str (The input text split into lines, separated by newline characters.)
    """

    words = text.split()
    processed_words = []

    previous_word = ""

    for word in words:
        special_chars, cleaned_word = split_leading_special_chars(word)

        if special_chars and processed_words:
           # If there was a special cahr its appended onto the end of the last word
            processed_words[-1] += special_chars

        if cleaned_word:
            processed_words.append(cleaned_word)
    lines = []
    current_line = ""

    for word in processed_words:
        if len(current_line) + len(word) + 1 <= max_length:
            current_line += (" " if current_line else "") + word
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    return "\n".join(lines)


# # # # External Call functions # # # #
def init_day_analyzer():
    """
    Initializes the standard daily analysis by instantiating the DayAnalyzer.

    Calling this function will create the DayAnalyzer singleton (if not already created), which immediately performs an initial analysis
    and starts a background thread for ongoing analysis updates.

    :return: None
    """

    DayAnalyzer()
    pass


import ttkbootstrap as tb
from ttkbootstrap.constants import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg



# # # # # Test functions below! can be ignored! # # # #
def show_figure_in_ttk(figure):
    """Opens a ttkbootstrap window and displays the given Matplotlib figure."""

    # Create a ttkbootstrap window with a modern theme
    root = tb.Window(themename="darkly")  # Change theme if needed
    root.title("Matplotlib in ttkbootstrap")

    # Create a frame to hold the figure
    frame = tb.Frame(root)
    frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

    # Convert Matplotlib figure to a Tk-compatible canvas
    canvas = FigureCanvasTkAgg(figure, master=frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill=BOTH, expand=True)

    # Run the GUI loop
    root.mainloop()


if __name__ == "__main__":
    start_db()
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    start_analysis = datetime.now()


    test_df = DBHandler().search_window_log(start_time=datetime(2025,1,16,0,0), end_time=datetime(2025,1,17,0,0))
    vdf = ViperDF("test", test_df)
    vdf.analyze()
    vdf.plot()


    init_day_analyzer()


    end_analysis = datetime.now()
    time_used = (end_analysis - start_analysis).total_seconds()
    print(f"{end_analysis} - {start_analysis} = {time_used}")

    show_figure_in_ttk(vdf.get_main_plot())

    stop_db()


    #print("Please start with the main.py")
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
from matplotlib.figure import Figure

# TODO: Minimize this imports to only import methods needed.
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from config_manager import threads_are_stopped
from db_connector import DBHandler, stop_db, start_db
from helper_classes import Classproperty, ColorPicker, Seconds


from io import BytesIO
from PIL import Image, ImageTk


def fig_to_tk_image(fig, dpi=100) -> ImageTk.PhotoImage:
    """
    Converts a Matplotlib figure into a Tkinter-compatible PhotoImage.

    This function saves a Matplotlib figure to an in-memory PNG buffer and loads it as a PIL image,
    then converts it into a format suitable for display in Tkinter GUIs.

    :param fig: matplotlib.figure.Figure
        The Matplotlib figure to convert.
    :param dpi: int
        The resolution (dots per inch) for the rendered image. Default is 100.
    :return: ImageTk.PhotoImage
        A Tkinter-compatible image that can be used in GUI widgets like `Label` or `Canvas`.
    """

    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight")
    buf.seek(0)
    pil_image = Image.open(buf)
    return ImageTk.PhotoImage(pil_image)


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
        plot_dpi (int): DPI setting used for plot resolution (default is 100).
        mainplot (Figure | None): Combined Matplotlib figure containing all subplots (created after calling plot()).
    """

    def __init__(self, name: str, main_df: DataFrame):
        """
        Initializes the ViperDF instance with a name and a pandas DataFrame.

        This constructor sets up the analysis structure, label/app detection flags, and plotting attributes.
        It also validates the DataFrame schema and prepares the object for future analysis and plotting.

        :param name: str
            The name identifier for the dataset, typically prefixed with 'app:' or 'label:'.
        :param main_df: pandas.DataFrame
            The primary DataFrame containing window tracking data.
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

        self.main_plot_size = None # (500,300)
        self.sub_plot_size = None # (100, 100)
        self.plot_dpi = 100

        self.image_main_plot = None
        self.image_app_pie_plot = None
        self.image_label_pie_plot = None
        self.image_app_vbar_plot = None
        self.image_label_vbar_plot = None

        self.analysis_results["major_formatter_x"] = mdates.DateFormatter("%H:%M:%S")
        self._activity_ax = None
        self._app_ax = None
        self._label_ax = None
        self._is_plotted = False
        self.mainplot = None

        self.__init_label_plot_helper()

    def __init_label_plot_helper(self) -> None:
        """
        Initializes internal helper attributes for label plotting.

        Sets default plotting offsets such as y-position, bar height, and spacing,
        used for drawing horizontal label bars in the visualization.

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

        This representation is useful for debugging and logs, showing the dataset name
        and the underlying DataFrame.

        :return: str
        """

        return f"VDF '{self.name}':\n{str(self._main_df)}"

    def __str__(self) -> str:
        """
        Returns a human-readable string with the VDF name and its DataFrame content.

        This method mirrors `__repr__` and provides a friendly summary for display.

        :return: str
        """

        return f"VDF '{self.name}':\n{str(self._main_df)}"

    def _validate_mainframe(self) -> bool:
        """
        Checks whether the main DataFrame contains all required columns for analysis.

        This method ensures the DataFrame has all necessary columns used in later computations
        and visualizations (e.g., input counts, timestamps, labels).

        :return: bool
            True if all required columns are present, False otherwise.
        """

        needed_columns = ["window_id", "window_type", "window_title", "word_list", "creation_datetime", "activity",
                          "count_key_pressed", "count_mouse_pressed",  "count_direction_key_pressed",
                          "count_char_key_pressed", "count_special_key_pressed", "count_mouse_scrolls",
                          "count_left_mouse_pressed", "count_right_mouse_pressed", "count_middle_mouse_pressed"]
        if all(ncol in self._main_df.columns for ncol in needed_columns):
            return True
        else:
            return False

    @property
    def time_range_str(self) -> str:
        """
        Provides a human-readable representation of the overall time range in the data.

        Returns the formatted start and end timestamps as a single string.
        If either timestamp is missing, an empty string is returned.

        :return: str
        """

        start = self.analysis_results.get("first_datetime", "")
        end = self.analysis_results.get("last_datetime", "")
        return f"{start} - {end}" if start and end else ""

    def main_infos(self) -> list[tuple[str, str]]:
        """
        Collects key summary metrics from the analysis results.

        Returns high-level statistics such as the number of apps and labels, active time,
        tracked time, and entry counts. Returns an empty list if the dataset is not yet analyzed.

        :return: list[tuple[str, str]]
        """

        if not self._is_analyzed:
            return []

        ar = self.analysis_results
        label_data = ar.get("labels", {})
        app_data = ar.get("apps", {})

        return [
            ("Different apps: ", str(app_data.get("count_unique", ""))),
            ("Different labels: ", str(label_data.get("count_unique", ""))),
            ("Whole timeframe: ", str(ar.get("time_frame_seconds", ""))),
            ("Tracked time: ", str(ar.get("tracked_seconds", ""))),
            ("Untracked time: ", str(ar.get("untracked_seconds", ""))),
            ("Active time: ", str(ar.get("active_secs", ""))),
            ("Inactive time: ", str(ar.get("inactive_secs", ""))),
            ("Active percentage(tracked): ", str(ar.get("percent_active", ""))),
            ("Entry count: ", str(ar.get("entry_count", ""))),
            ("Labeled entries: ", str(ar.get("entry_count_labeled", ""))),
            ("Unlabeled entries: ", str(ar.get("entry_count_unlabeled", ""))),
        ]

    def split_data_on_label(self) -> list['ViperDF']:
        """
        Splits the data into multiple ViperDF instances based on each unique label.

        Each new instance represents a filtered subset of the main DataFrame containing entries
        for a specific label. The method requires prior analysis.

        :raises ValueError: If `analyze()` has not been called.
        :return: list[ViperDF]
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

    def split_data_on_app(self) -> list['ViperDF']:
        """
        Splits the data into multiple ViperDF instances based on each unique application.

        Each new instance is based on the `window_type` field and contains entries for that application only.
        The method requires prior analysis.

        :raises ValueError: If `analyze()` has not been called.
        :return: list[ViperDF]
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
        Generates all necessary plots and assembles them into a single figure.

        This includes the activity line plot, application usage bar chart, and label usage bar chart.
        Must be called after `analyze()`.

        :raises ValueError: If the DataFrame has not been analyzed.
        :return: ViperDF (self)
        """

        if not self._is_analyzed:
            raise ValueError("Main frame is not analyzed.")
        if self.main_plot_size is not None:
            self.main_plot_size = self._px_to_inch(self.main_plot_size[0]), self._px_to_inch(self.main_plot_size[1])
        if self.sub_plot_size is not None:
            self.sub_plot_size = self._px_to_inch(self.sub_plot_size[0]), self._px_to_inch(self.sub_plot_size[1])
        self._get_ax_line_activity()
        self._get_ax_hbar_apps()
        self._update_ax_hbar_labels()
        self._combine_axes()
        self._is_plotted = True
        return self

    def change_chosen_labels(self, label_list: str | list[str]) -> None:
        """
        Updates the label plot to display only the selected labels.

        Accepts a string or list of up to 5 label names and redraws the label plot accordingly.

        :param label_list: str | list[str]
        :raises ValueError: If list is empty or exceeds 5 entries.
        :return: None
        """

        # TODO: Delete all old used things that change on label change
        if len(label_list) == 0 or len(label_list) > 5:
            raise ValueError("label_list cannot be empty or more than 4")
        self._label_ax = None  # Remove the existing label axis
        self.__init_label_plot_helper()

        self._update_ax_hbar_labels(label_list)
        self._combine_axes()

    def analyze(self) -> 'ViperDF':
        """
        Performs full analysis of the dataset including time, input, app, and label metrics.

        This method updates the `analysis_results` dictionary with computed values and prepares
        data for plotting.

        :return: ViperDF (self)
        """

        if not self.empty:
            self._time_analysis()
            self._input_analysis()
            if not self.is_app_based:
                self._app_analysis()
            if not self.is_label_based:
                self._label_analysis()
            self._is_analyzed = True
        return self

    def _time_analysis(self):
        """
        Performs time-based analysis on the dataset and populates time-related metrics.

        Calculates first and last timestamps, total tracked time, active/inactive time,
        and chooses the appropriate x-axis formatter based on the range.

        :raises ValueError: If the time range does not match expected categories.
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
        self.analysis_results["inactive_secs"] = Seconds(self.analysis_results["tracked_seconds"] -
                                                  self.analysis_results["active_secs"])

        self.analysis_results["percent_active"] = round((self.analysis_results["active_secs"]/(
                                                    self.analysis_results["tracked_seconds"]/100)), 2)

    def _input_analysis(self) -> None:
        """
        Aggregates input data over time and stores activity metrics in bins.

        Groups data into intervals, sums input counts, calculates relative activity levels,
        and stores result in `_activity_df`.

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

    def _app_analysis(self) -> None:
        """
        Analyzes application usage by counting occurrences of each window type.

        Stores total counts and prepares data for grouped display and percentage charts.

        :return: None
        """

        app_win_count = self._main_df["window_type"].value_counts().to_dict()
        self.analysis_results["apps"] = {"count_unique": len(app_win_count), "entries": app_win_count}
        self._create_grouped_app_df()

    def _label_analysis(self) -> None:
        """
        Analyzes label usage across entries and computes label-related statistics.

        Counts labeled/unlabeled entries, label frequencies, and prepares grouped data for plots.

        :return: None
        """

        all_labels = self._main_df["label_list"].dropna().explode()
        label_counts = all_labels.value_counts().to_dict()
        self.analysis_results["entry_count_labeled"] = len(self._main_df["label_list"].dropna())
        self.analysis_results["entry_count_unlabeled"] = (self.analysis_results["entry_count"]
                                                          - self.analysis_results["entry_count_labeled"])

        self.analysis_results["labels"] = {"count_unique": len(label_counts), "entries": label_counts}
        self._create_grouped_label_df()

    def _create_grouped_app_df(self) -> None:
        """
        Groups consecutive identical application entries into usage segments.

        Segments are determined based on app name, title, and time continuity.
        Also assigns color and computes overall usage percentages for each app.

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

    def _combine_small_app_entries(self) -> None:
        """
        Combines minor application entries into a single 'Others' category for clarity.

        Merges apps with less than 2% usage into one row, aggregates their data,
        and saves details for tooltip display in plots.

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

    def _create_grouped_label_df(self) -> None:
        """
        Groups continuous labeled entries into segments and assigns colors.

        Explodes the label list, merges entries by label and time proximity,
        calculates durations, and creates summary statistics with color mappings.

        :return: None
        """

        if self._main_df is None or self._main_df.empty:
            print("No data available.")

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

    def _combine_small_label_entries(self) -> None:
        """
        Combines low-percentage labels into an 'Others' entry for better plot readability.

        Merges labels under 2% usage, aggregates durations and details,
        and appends the result to the summary DataFrame.

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

    def _px_to_inch(self, px):
        """
        Converts a pixel value to inches based on current plot DPI.

        Used for scaling Matplotlib plots to match pixel-based dimensions.

        :param px: float (Pixel value to convert.)
        :return: float (Equivalent value in inches.)
        """

        return px / self.plot_dpi

    def _get_ax_line_activity(self) -> None:
        """
        Creates the activity line chart Axes with smoothing and interactive features.

        Builds a time-vs-activity line plot using offset points for better transitions.
        Stores Axes and data for dynamic hover effects.

        :return: None
        """
        if self.main_plot_size is not None:
            fig, ax = plt.subplots(figsize=self.main_plot_size, dpi=self.plot_dpi)
        else:
            fig, ax = plt.subplots(dpi=self.plot_dpi)
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
        self.__activity_plot_helper = {"data": activity_plot_data}
        self.__init_plot_data_activity(ax)
        self._activity_ax = ax

    def __init_plot_data_activity(self, ax) -> None:
        """
        Initializes interactive hover elements for the activity plot.

        Adds a red marker and annotation text to display activity percentage at cursor position.
        Binds the motion event to an internal hover callback.

        :param ax: Axes (Target Matplotlib Axes for hover elements.)
        :return: None
        """

        # Create hover annotation
        self.__activity_plot_helper["marker"], = ax.plot([], [], marker="o", color="red", markersize=3, visible=False)
        self.__activity_plot_helper["annotation"] = ax.annotate("", xy=(0, 0), xytext=(10, 10),
                                    textcoords="offset points", visible=False,
                                    bbox=dict(boxstyle="round", fc="w", ec="red", alpha=0.7))
        self.__activity_plot_helper["ax"] = ax

        # Connect hover event
        ax.figure.canvas.mpl_connect("motion_notify_event", self.__activity_on_hover)

    def __activity_on_hover(self, event):
        """
        Handles mouse hover events for the activity line chart.

        Displays a marker and annotation near the closest activity point if within bounds,
        and hides them when outside the activity area.

        :param event: Event (Matplotlib motion event.)
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
        self.__activity_plot_helper["annotation"].set_text(f"{closest_time.strftime('%H:%M:%S')}\n"
                                                           f"{closest_value:.2f} % Activity")
        self.__activity_plot_helper["annotation"].set_visible(True)

        self.__activity_plot_helper["ax"].figure.canvas.draw_idle()

    def _get_ax_hbar_apps(self) -> None:
        """
        Creates the horizontal bar chart for application usage.

        Generates bars from grouped app intervals and initializes hover/selection interactivity.
        Saves the Axes for further combination in the main plot.

        :return: None
        """

        if self.main_plot_size is not None:
            fig, ax = plt.subplots(figsize=self.main_plot_size, dpi=self.plot_dpi)
        else:
            fig, ax = plt.subplots(dpi=self.plot_dpi)

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

    def __init_plot_data_apps(self, ax) -> None:
        """
        Initializes interactive elements for application usage bars.

        Sets up hover line, selection triangles, and annotation text box.
        Binds events for hover, click, and keyboard control.

        :param ax: Axes (Target Axes for interactivity setup.)
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

    def __app_reset_annotation(self) -> None:
        """
        Clears current selection and hides all interactive elements in the app bar plot.

        Resets static mode and triggers a canvas redraw to update plot display.

        :return: None
        """

        self.__app_plot_helper["static_mode"] = False
        self.__app_plot_helper["selected_index"] = None
        self.__app_plot_helper["hover_line"].set_visible(False)
        self.__app_plot_helper["annotation"].set_visible(False)
        self.__app_plot_helper["triangle_up"].set_visible(False)
        self.__app_plot_helper["triangle_down"].set_visible(False)
        self.__app_plot_helper["ax"].figure.canvas.draw_idle()

    def __app_update_selection(self, index) -> None:
        """
        Highlights a specific application usage entry in the bar chart.

        Draws a vertical line and annotation at the selected entry's midpoint,
        showing start/end time, app name, and title. Adjusts label alignment dynamically.

        :param index: int (Index of the entry in `_grouped_app_df`.)
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
        Handles mouse hover over the application bar chart.

        Selects and highlights the closest application usage segment under the cursor,
        unless static mode is active.

        :param event: Event (Matplotlib motion event.)
        :return: None
        """

        if event.inaxes != self.__app_plot_helper["ax"] or self.__app_plot_helper["static_mode"]:
            return

        if event.ydata is None or not (self.__app_plot_helper["end_y"] <= event.ydata
                                       <= self.__app_plot_helper["start_y"]):
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

    def __app_on_click(self, event) -> None:
        """
        Handles mouse click events on the application bar chart.

        Activates static mode and locks selection if clicked within a valid segment.
        Resets selection if clicked outside.

        :param event: Event (Matplotlib mouse click event.)
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

    def __app_on_key(self, event) -> None:
        """
        Handles keyboard navigation for the application bar chart in static mode.

        Arrow keys move selection left/right, Escape exits static mode.

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

    def _update_ax_hbar_labels(self, label_list: list[str] | str = None) -> None:
        """
        Creates or updates the horizontal bar chart for label usage.

        Filters and plots up to 5 selected labels, drawing continuous usage segments as horizontal bars.
        Raises error if requested labels are not present.

        :param label_list: list[str] | str | None (Optional labels to include.)
        :raises ValueError: If no valid labels found in grouped data.
        :return: Axes (Matplotlib Axes with label bars.)
        """

        if self.main_plot_size is not None:
            fig, ax = plt.subplots(figsize=self.main_plot_size, dpi=self.plot_dpi)
        else:
            fig, ax = plt.subplots(dpi=self.plot_dpi)

        self.__label_plot_helper["x_start"] = mdates.date2num(self.analysis_results["first_datetime"])
        self.__label_plot_helper["x_end"] = mdates.date2num(self.analysis_results["last_datetime"])

        if self._grouped_label_df is None or self._grouped_label_df.empty:
            raise ValueError("No data available in `_grouped_label_df`.")
        # FIXME: error with no data:
        #     Exception in Tkinter
        #     callback
        #     Traceback(most
        #     recent
        #     call
        #     last):
        #     File
        #     "C:\Users\s0rab\AppData\Local\Programs\Python\Python312\Lib\tkinter\__init__.py", line
        #     1968, in __call__
        #     return self.func(*args)
        #     ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^
        #     File
        #     "C:\git\python\viper_tracking\src\gui_views.py", line
        #     1439, in _analyze
        #     self.analyzing_return_function(main_df)
        #     File
        #     "C:\git\python\viper_tracking\src\gui_views.py", line
        #     1525, in add_vdf_to_show
        #     new_vdf.analyze().plot()
        #     File
        #     "C:\git\python\viper_tracking\src\pandas_data_manager.py", line
        #     207, in plot
        #     self._update_ax_hbar_labels()
        #     File
        #     "C:\git\python\viper_tracking\src\pandas_data_manager.py", line
        #     1003, in _update_ax_hbar_labels
        #     raise ValueError("No data available in `_grouped_label_df`.")
        #     ValueError: No
        #     data
        #     available in `_grouped_label_df`.

        available_labels = self._grouped_label_df["label_name"].unique()

        if label_list is None:
            label_list = available_labels[:4]
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

    def __init_plot_data_label(self, ax) -> None:
        """
        Initializes interactive elements for the label bar chart.

        Adds red hover line, triangle markers, and annotation.
        Connects motion, click, and key events for label interactivity.

        :param ax: Axes (Matplotlib Axes for the label bar chart.)
        :return: None
        """

        self.__label_plot_helper["ax"] = ax
        self.__label_plot_helper["hover_line"], = ax.plot([0, 0], [0, 0], color='red', linestyle='dotted',
                                                          alpha=0.7, visible=False)

        # Zwei Dreiecke für die Markierung
        self.__label_plot_helper["triangle_up"], = ax.plot([], [], marker="v", color="red", markersize=8,
                                                           visible=False)  # Unten
        self.__label_plot_helper["triangle_down"], = ax.plot([], [], marker="^", color="red", markersize=8,
                                                             visible=False)  # Oben

        self.__label_plot_helper["annotation"] = ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
                                 bbox=dict(boxstyle="round", fc="white", ec="blue", alpha=0.9),
                                 visible=False)

        self.__label_plot_helper["static_mode"] = False
        self.__label_plot_helper["selected_index"] = None

        ax.figure.canvas.mpl_connect("motion_notify_event", self.__label_on_hover)
        ax.figure.canvas.mpl_connect("button_press_event", self.__label_on_click)
        ax.figure.canvas.mpl_connect("key_press_event", self.__label_on_key)

    def __label_reset_annotation(self) -> None:
        """
        Clears selection and hover visuals on the label bar chart.

        Hides annotation, markers, and resets internal selection state.

        :return: None
        """

        self.__label_plot_helper["static_mode"] = False
        self.__label_plot_helper["selected_index"] = None
        self.__label_plot_helper["hover_line"].set_visible(False)
        self.__label_plot_helper["annotation"].set_visible(False)
        self.__label_plot_helper["triangle_up"].set_visible(False)
        self.__label_plot_helper["triangle_down"].set_visible(False)
        self.__label_plot_helper["ax"].figure.canvas.draw_idle()

    def __label_update_selection(self, index) -> None:
        """
        Highlights a selected label segment on the label bar chart.

        Draws hover line, triangle markers, and annotation showing label name,
        start/end time, and duration.

        :param index: int (Index of the label segment to highlight.)
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

    def __label_on_hover(self, event) -> None:
        """
        Handles mouse hover over the label bar chart.

        Identifies the closest label segment under the cursor and highlights it.
        If no segment is under the cursor, resets the annotation.

        :param event: Event (Matplotlib mouse motion event.)
        :return: None
        """

        if event.inaxes != self.__label_plot_helper["ax"] or self.__label_plot_helper["static_mode"]:
            return

        closest_label = None
        # Gets closest label, if none found, resets the annotations
        for label, y_pos in self.__label_plot_helper["label_y_mapping"].items():
            if ((y_pos - self.__label_plot_helper["bar_height"] - int(self.__label_plot_helper["y_spacing"]))
                    <= event.ydata <= (y_pos + int(self.__label_plot_helper["y_spacing"]))):
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

    def __label_on_click(self, event) -> None:
        """
        Handles mouse click on the label bar chart.

        Enters static mode and locks annotation to the clicked segment.
        Resets annotation if click is outside of label bars.

        :param event: Event (Matplotlib mouse button event.)
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
        Handles key events in static mode for the label bar chart.

        Supports cycling between label segments using left/right arrows,
        and exiting static mode with Escape.

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
        Sets X-axis limits and time formatter for a plot.

        Uses time range and formatter from `analysis_results`.

        :param ax: Axes (Target Matplotlib Axes.)
        :return: None
        """

        x_min = mdates.date2num(self.analysis_results["first_datetime"])
        x_max = mdates.date2num(self.analysis_results["last_datetime"])
        ax.set_xlim(x_min, x_max)
        # FIXME: Smart solution for showing time properly(based on interval)
        # TODO: probably fixed allready
        ax.xaxis.set_major_formatter(self.analysis_results["major_formatter_x"])

    def _combine_axes(self) -> None:
        """
        Combines activity, app, and label Axes into a single figure.

        Copies visual elements from all axes, recreates interactivity,
        and stores the combined figure in `mainplot`.

        :raises ValueError: If any required Axes is missing.
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

        if self.main_plot_size is not None:
            new_fig, new_ax = plt.subplots(figsize=self.main_plot_size, dpi=self.plot_dpi)
        else:
            new_fig, new_ax = plt.subplots(dpi=self.plot_dpi)

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

        new_ax.set_yticks([])
        new_ax.set_yticklabels([])
        new_ax.set_ylim(lowest_y, highest_y)
        new_ax.set_xlim(lowest_x, highest_x)
        new_ax.xaxis.set_major_formatter(mirrored_formatter)

        # Init the new ax as main ax and binds interactive methods properly
        self.__init_plot_data_activity(new_ax)
        self.__init_plot_data_apps(new_ax)
        self.__init_plot_data_label(new_ax)

        new_fig.tight_layout()
        self.image_main_plot = fig_to_tk_image(new_fig, self.plot_dpi)
        self.mainplot = new_fig

    def get_main_plot(self) -> Figure:
        """
        Returns the combined main plot figure, creating it if missing.

        :return: Figure (Matplotlib figure with all combined plots.)
        """

        if self.mainplot is None:
            self._combine_axes()
        return self.mainplot

    def get_vbar_apps(self) -> Figure:
        """
        Generates vertical bar chart for app usage with interactivity.

        Hovering reveals percent usage, duration, and grouped app details.

        :return: Figure | None (App bar chart or None if no data.)
        """

        if self._grouped_app_summary_df is None or self._grouped_app_summary_df.empty:
            print("No app data available for plotting.")
            return None

        df = self._grouped_app_summary_df
        if self.sub_plot_size is not None:
            fig, ax = plt.subplots(figsize=self.sub_plot_size, dpi=self.plot_dpi)
        else:
            fig, ax = plt.subplots(dpi=self.plot_dpi)
        bars = ax.bar(df["window_type"], df["overall_percent"], color=df["rgba_color"])

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
        def on_hover(event) -> None:
            """
            Handles mouse hover events for the applications vertical bar chart.

            When the cursor moves over the app usage bar chart, this function shows or hides interactive elements
            (such as an annotation, a marker triangle, and a hover line) depending on whether the cursor is over a bar.
            If the cursor is not over the chart, it hides all hover indicators and redraws the canvas.

            :param event: MouseEvent (Matplotlib mouse motion event triggered on hover.)
            :return: None
            """

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
        # TODO: Working all fine?
        fig.tight_layout()

        self.image_app_vbar_plot = fig_to_tk_image(fig, self.plot_dpi)

        return fig

    def get_vbar_labels(self) -> Figure:
        """
        Generates vertical bar chart for label usage with interactivity.

        Hovering reveals usage percent, duration, and grouped label details.

        :return: Figure | None (Label bar chart or None if no data.)
        """

        if self._grouped_label_summary_df is None or self._grouped_label_summary_df.empty:
            # TODO: Logging
            print("No label data available for plotting.")
            return None

        df = self._grouped_label_summary_df

        if self.sub_plot_size is not None:
            fig, ax = plt.subplots(figsize=self.sub_plot_size, dpi=self.plot_dpi)
        else:
            fig, ax = plt.subplots(dpi=self.plot_dpi)

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

        def on_hover(event) -> None:
            """
            Handles mouse hover events for the labels vertical bar chart.

            Shows percentage and duration on hover, including grouped entries under "Others".
            Hides annotation and markers when mouse leaves the chart or doesn't hit a bar.

            :param event: MouseEvent (Matplotlib mouse motion event.)
            :return: None
            """

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

        fig.tight_layout()

        self.image_label_vbar_plot = fig_to_tk_image(fig, self.plot_dpi)

        return fig

    def get_pie_apps(self) -> Figure:
        """
        Creates pie chart for overall app usage with label annotations.

        Hovering over labels shows percent, duration, and grouped app details.

        :return: Figure | None (Pie chart for app usage or None if no data.)
        """

        if self._grouped_app_summary_df is None or self._grouped_app_summary_df.empty:
            # TODO: Logging
            print("No app data available for plotting.")
            return None

        df = self._grouped_app_summary_df

        if self.sub_plot_size is not None:
            fig, ax = plt.subplots(figsize=self.sub_plot_size, dpi=self.plot_dpi)
        else:
            fig, ax = plt.subplots(dpi=self.plot_dpi)
        # FIXME: error warning
        #     C:\git\python\viper_tracking\src\pandas_data_manager.py: 1787: RuntimeWarning: More
        #     than
        #     20
        #     figures
        #     have
        #     been
        #     opened.Figures
        #     created
        #     through
        #     the
        #     pyplot
        #     interface(`matplotlib.pyplot.figure`)
        #     are
        #     retained
        #     until
        #     explicitly
        #     closed and may
        #     consume
        #     too
        #     much
        #     memory.(To
        #     control
        #     this
        #     warning, see
        #     the
        #     rcParam
        #     `figure.max_open_warning`).Consider
        #     using
        #     `matplotlib.pyplot.close()`.
        #
        fig, ax = plt.subplots(dpi=self.plot_dpi)


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

        def on_hover(event) -> None:
            """
            Handles mouse hover events for the applications pie chart.

            When hovering over a label near a wedge, shows percentage and duration in an annotation.
            Handles "Others" labels by showing merged app entries as well.

            :param event: MouseEvent (Matplotlib mouse motion event.)
            :return: None
            """

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

        fig.tight_layout()

        self.image_app_pie_plot = fig_to_tk_image(fig, self.plot_dpi)

        return fig

    def get_pie_labels(self) -> Figure:
        """
        Creates pie chart for overall label usage with annotations.

        Hovering reveals usage details and grouped "Others" info.

        :return: Figure | None (Pie chart for label usage or None if no data.)
        """

        if self._grouped_label_summary_df is None or self._grouped_label_summary_df.empty:
            print("No label data available for plotting.")
            return None

        df = self._grouped_label_summary_df

        if self.sub_plot_size is not None:
            fig, ax = plt.subplots(figsize=self.sub_plot_size, dpi=self.plot_dpi)
        else:
            fig, ax = plt.subplots(dpi=self.plot_dpi)

        # Fixme: error happend when subtracting animes from the normal analysis
        # C:\git\python\viper_tracking\src\pandas_data_manager.py:1945: RuntimeWarning: More than 20 figures have been opened.
        # Figures created through the pyplot interface (`matplotlib.pyplot.figure`) are retained until explicitly closed
        # and may consume too much memory. (To control this warning, see the rcParam `figure.max_open_warning`).
        # Consider using `matplotlib.pyplot.close()`.
        #   fig, ax = plt.subplots(dpi=self.plot_dpi)

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

        def on_hover(event) -> None:
            """
            Handles mouse hover events for the labels pie chart.

            When hovering over label annotations, shows usage details including grouped entries under "Others".
            Hides annotation when not hovering over a label.

            :param event: MouseEvent (Matplotlib mouse motion event.)
            :return: None
            """

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

        fig.tight_layout()
        self.image_label_pie_plot = fig_to_tk_image(fig, self.plot_dpi)
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
        _vdf (ViperDF): The ViperDF instance holding the current day's analyzed data.
        _check_interval (int): Interval in minutes between automatic data refresh checks.
        _next_check_timestamp (datetime): Timestamp for the next scheduled data refresh.
        _thread (Thread): Background thread that continuously checks and triggers data refresh.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures singleton behavior by returning the existing instance if one exists.

        If no instance exists, it creates one using the superclass constructor.

        :return: DayAnalyzer (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the singleton instance with database access, a ViperDF, and background analysis.

        Sets up threading and periodic reanalysis for day-based data, only on first initialization.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            self._lock = Lock()
            self._initialized = True
            tmp_df = DBHandler().search_window_log()
            self._vdf = ViperDF("day_analysis", tmp_df)
            self._vdf.analyze()

            self._check_interval = 5  # Minutes
            self._next_check_timestamp = datetime.now() + timedelta(minutes=self._check_interval)

            self._thread = Thread(target=self._thread_loop)
            self._thread.start()

    def _check_for_action(self) -> None:
        """
        Checks if a data refresh is due and triggers it if the interval has passed.

        Updates the next scheduled check timestamp and invokes the data refresh method.

        :return: None
        """

        with self._lock:
            if not self._next_check_timestamp >= datetime.now():
                return

            self._next_check_timestamp = datetime.now() + timedelta(minutes=self._check_interval)
        DayAnalyzer.this.refresh_data()

    def _thread_loop(self) -> None:
        """
        Background loop that runs continuously, sleeping in intervals, to check for data updates.

        Terminates cleanly if the global thread stop flag is set.

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

    def refresh_data(self) -> None:
        """
        Refreshes analysis data by reloading from the database and reinitializing the ViperDF.

        This deletes the existing ViperDF, creates a new one with fresh data, and runs analysis again.

        :return: None
        """

        with self._lock:
            del self._vdf
            tmp_df = DBHandler().search_window_log()
            self._vdf = ViperDF("day_analysis", tmp_df)
            self._vdf.analyze()

    def get_data(self) -> ViperDF:
        """
        Returns the current analyzed ViperDF in a thread-safe way.

        Acquires the internal lock before accessing the ViperDF.

        :return: ViperDF (Analyzed dataset for the current day.)
        """

        with self._lock:
            return self._vdf

    @Classproperty
    def this(cls) -> 'DayAnalyzer':
        """
        Returns the singleton instance of DayAnalyzer (class-level accessor).

        Creates the instance if it doesn't exist yet.

        :return: DayAnalyzer (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# # # # Helper functions # # # #
def split_leading_special_chars(word: str):
    """
    Splits a string into two parts: leading special characters and the remaining alphanumeric portion.

    Iterates from the start of the string and collects non-alphanumeric characters until the first alphanumeric character is found.

    :param word: str (The input string to split.)
    :return: tuple[str, str] (First element is leading special characters, second is the rest of the word.)
    """

    special_chars = ""
    while word and not word[0].isalnum():
        special_chars += word[0]
        word = word[1:]
    return special_chars, word


def split_text_by_max_length(text: str, max_length: int) -> str:
    """
    Breaks a long string into lines without exceeding a maximum line length, preserving word boundaries.

    Special characters at the beginning of words are attached to the previous word to avoid leading punctuation on new lines.

    :param text: str (The input string to format.)
    :param max_length: int (The maximum number of characters allowed per line.)
    :return: str (The formatted string with newline-separated lines.)
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
    Starts the DayAnalyzer singleton for daily analysis and begins background monitoring.

    Instantiates the analyzer if not already created, triggering immediate data analysis and periodic updates.

    :return: None
    """

    DayAnalyzer()

if __name__ == "__main__":
    print("Please start with the main.py")

"""
Here we handle the storage of data frames from pandas,
the sorting and what else.

Author: sora7672
"""
__author__ = 'sora7672'

from datetime import datetime, timedelta
from threading import Lock, Thread
from time import sleep
from pandas import DataFrame, Series
from abc import ABC, abstractmethod
from matplotlib.collections import PolyCollection

# TODO: Minimize this imports to only import methods needed.
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

from config_manager import threads_are_stopped
from db_connector import DBHandler, stop_db, start_db
from helper_classes import Classproperty, ColorPicker


class Seconds(int):

    def __new__(cls, value):
        if not isinstance(value, int):
            raise ValueError("Seconds must be initialized with an integer value.")
        return super().__new__(cls, value)

    def __str__(self):
        if self >= 604800:
            return self.weeks
        elif self >= 86400:
            return self.days
        elif self >= 3600:
            return self.hours
        elif self >= 60:
            return self.mins
        else:
            return f"{self} seconds"

    @property
    def str(self):
        return str(self)

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
        return f"{days} days, {hours}:{mins}:{secs}"

    @property
    def weeks(self):
        mins, secs = divmod(self, 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        weeks, days = divmod(days, 7)
        return f"{weeks} weeks, {days} days {hours}:{mins}:{secs}"


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
        # TODO: better error handeling behaviour with GUI implemention.
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

    def split_data_on_app(self):
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

    def analyze(self):
        """
        calls all protected analyzes functions
        ORDER MATTERS!
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
        activity_points = getattr(self, "_number_activity_points", 100)

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

        start_time = time_df["creation_datetime"].iloc[0]
        end_time = time_df["creation_datetime"].iloc[-1]
        total_seconds = int((end_time - start_time).total_seconds())

        time_frame_per_point = max(5, round(total_seconds / activity_points / 5) * 5)
        self.analysis_results["activity_interval"] = time_frame_per_point

        # param freq uses a deprecated methode with "s" for seconds in the end, don't remove!
        intervals = pd.interval_range(
            start=start_time,
            end=end_time + pd.Timedelta(seconds=time_frame_per_point),
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

        app_win_count = self._main_df["window_type"].value_counts().to_dict()
        self.analysis_results["apps"] = {"count_unique": len(app_win_count), "entries": app_win_count}
        self._create_grouped_app_df()

    def _label_analysis(self):

        all_labels = self._main_df["label_list"].dropna().explode()
        label_counts = all_labels.value_counts().to_dict()
        self.analysis_results["entry_count_labeled"] = len(self._main_df["label_list"].dropna())
        self.analysis_results["entry_count_unlabeled"] = (self.analysis_results["entry_count"]
                                                          - self.analysis_results["entry_count_labeled"])

        self.analysis_results["labels"] = {"count_unique": len(label_counts), "entries": label_counts}
        self._create_grouped_label_df()

    def _create_grouped_app_df(self):
        # Extract only required columns
        app_data = self._main_df[["window_type", "window_title", "creation_datetime"]].copy()

        # Calculate start_time and end_time
        app_data["start_time"] = app_data["creation_datetime"] - pd.to_timedelta(5, unit='s')
        app_data["end_time"] = app_data["creation_datetime"]

        change_mask = (
                (app_data["window_type"] != app_data["window_type"].shift(1)) |
                (app_data["window_title"] != app_data["window_title"].shift(1)) |
                ((app_data["start_time"] - app_data["end_time"].shift(1)).dt.total_seconds() > 8)
        )

        # Assign a unique group ID to each continuous block of identical entries
        app_data["group"] = change_mask.cumsum()
        app_data = app_data.sort_values("creation_datetime")

        # Aggregate start_time (first entry) and end_time (last entry) per group
        app_grouped_df = app_data.groupby("group").agg({
            "window_type": "first",
            "window_title": "first",
            "start_time": "first",
            "end_time": "last"
        }).reset_index(drop=True)

        app_grouped_df["mid_time"] = app_grouped_df["start_time"] + (
                app_grouped_df["end_time"] - app_grouped_df["start_time"]) / 2

        app_grouped_df["duration"] = (app_grouped_df["end_time"] - app_grouped_df["start_time"]).dt.total_seconds()

        self._grouped_app_df = app_grouped_df.sort_values("start_time")
        # Adding colors:
        unique_apps = self._grouped_app_df["window_type"].unique()

        # Generate colors for unique apps
        app_colors = ColorPicker.next_color_rgba(len(unique_apps))
        app_color_map = dict(zip(unique_apps, app_colors))

        # Assign colors to DataFrame
        self._grouped_app_df["rgba_color"] = self._grouped_app_df["window_type"].map(app_color_map)

        # 🔹 NEUES DATAFRAME: Summierte Dauer pro App + Prozentwerte 🔹
        app_summary_df = self._grouped_app_df.groupby("window_type").agg({
            "duration": "sum",
            "rgba_color": "first"
        }).reset_index()
        # Berechne die gesamte Nutzungszeit über alle Apps hinweg
        total_app_time = app_summary_df["duration"].sum()

        # Berechne den prozentualen Anteil für jede App
        app_summary_df["overall_percent"] = (app_summary_df["duration"] / total_app_time) * 100
        app_summary_df["overall_percent"] = app_summary_df["overall_percent"].apply(lambda x: max(x, 0.01))
        app_summary_df["details"] = None

        # Speichern des neuen DataFrames
        self._grouped_app_summary_df = app_summary_df.sort_values("overall_percent", ascending=False)
        self._combine_small_app_entries()

    def _combine_small_app_entries(self):
        if self._grouped_app_summary_df is None or self._grouped_app_summary_df.empty:
            return

        df = self._grouped_app_summary_df.copy()

        # Maske für alle Einträge unter 2%
        mask = df["overall_percent"] < 2
        small_entries = df[mask].copy()

        # Falls es keine kleinen Einträge gibt, beenden
        if small_entries.empty:
            return

        # Erstelle eine Liste mit Details (Dictionary für jede App)
        details = small_entries[["window_type", "duration", "overall_percent"]].to_dict(orient="records")

        # Summiere die Gesamtzeit & den Prozentwert der kleinen Einträge
        others_total_time = small_entries["duration"].sum()
        others_percent = small_entries["overall_percent"].sum()

        # Entferne die kleinen Einträge aus dem Haupt-DF
        df = df[~mask]

        # Füge die "Andere"-Zeile hinzu
        new_row = pd.DataFrame([{
            "window_type": "Others",
            "duration": others_total_time,
            "overall_percent": others_percent,
            "rgba_color": (0.5, 0.5, 0.5, 1.0),  # A neutral gray with full opacity
            "details": details  # Speichert die kleinen Einträge als Liste von Dicts
        }])

        df = pd.concat([df, new_row], ignore_index=True)

        # Speichern des neuen DataFrames mit "Andere"
        self._grouped_app_summary_df = df


    def _create_grouped_label_df(self):
        if self._main_df is None or self._main_df.empty:
            print("No data available.")
            return pd.DataFrame(columns=["label_name", "start_time", "end_time"])

            # 1️⃣ Entferne Zeilen ohne Labels
        label_data = self._main_df.dropna(subset=["label_list"]).copy()

        # 2️⃣ Explodiere `label_list`, damit jede Zeile nur ein Label hat
        label_data = label_data.explode("label_list")

        # 3️⃣ Berechne `start_time` und `end_time`
        label_data["start_time"] = label_data["creation_datetime"] - pd.to_timedelta(5, unit='s')
        label_data["end_time"] = label_data["creation_datetime"]

        # 4️⃣ Sortiere nach Label-Name und Startzeit
        label_data = label_data.sort_values(["label_list", "start_time"])

        # 5️⃣ Gruppiere zusammenhängende Zeiträume mit einer Toleranz von 8 Sekunden
        change_mask = (
                (label_data["label_list"] != label_data["label_list"].shift(1)) |  # Anderes Label -> Neue Gruppe
                ((label_data["start_time"] - label_data["end_time"].shift(1)).dt.total_seconds() > 8)  # Lücke > 8 Sek.
        )
        label_data["group"] = change_mask.cumsum()

        # 6️⃣ Aggregiere Startzeit (erste Zeile) & Endzeit (letzte Zeile) pro Label-Gruppe
        label_grouped_df = label_data.groupby(["label_list", "group"]).agg({
            "start_time": "first",
            "end_time": "last"
        }).reset_index()

        # 7️⃣ Umbenennen der Spalten für bessere Lesbarkeit
        label_grouped_df = label_grouped_df.rename(columns={"label_list": "label_name"})
        label_grouped_df["duration"] = (label_grouped_df["end_time"] - label_grouped_df["start_time"]).dt.total_seconds()
        label_grouped_df = label_grouped_df.sort_values(["label_name", "start_time"])

        self._grouped_label_df = label_grouped_df[["label_name", "start_time", "end_time", "duration"]]

        # TODO: add databank entry for RGBA colors per label and read them in
        #  also, add it to Labels in logs and for the GUI to add colors per label.
        #  Dont forget manual label adding, just add green color to that as standard (if not changed)
        #  or add a color picker in GUI?
        # Adding colors:
        unique_labels = self._grouped_label_df["label_name"].unique()

        # Generate colors for unique apps
        label_colors = ColorPicker.next_color_rgba(len(unique_labels))
        label_color_map = dict(zip(unique_labels, label_colors))

        # Assign colors to DataFrame
        self._grouped_label_df["rgba_color"] = self._grouped_label_df["label_name"].map(label_color_map)
        # END OF TO-DO
        label_summary_df = self._grouped_label_df.groupby("label_name").agg({
            "duration": "sum",
            "rgba_color": "first"
        }).reset_index()
        # Berechne die gesamte Nutzungszeit über alle Labels hinweg
        total_label_time = label_summary_df["duration"].sum()

        # Berechne den prozentualen Anteil für jedes Label
        label_summary_df["overall_percent"] = (label_summary_df["duration"] / total_label_time) * 100
        label_summary_df["overall_percent"] = label_summary_df["overall_percent"].apply(lambda x: max(x, 0.01))
        label_summary_df["details"] = None
        # Speichern des neuen DataFrames
        self._grouped_label_summary_df = label_summary_df.sort_values("overall_percent", ascending=False)

        self._combine_small_label_entries()

    def _combine_small_label_entries(self):
        if self._grouped_label_summary_df is None or self._grouped_label_summary_df.empty:
            return

        df = self._grouped_label_summary_df.copy()

        # Maske für alle Einträge unter 2%
        mask = df["overall_percent"] < 2
        small_entries = df[mask].copy()

        # Falls es keine kleinen Einträge gibt, beenden
        if small_entries.empty:
            return

        # Erstelle eine Liste mit Details (Dictionary für jedes Label)
        details = small_entries[["label_name", "duration", "overall_percent"]].to_dict(orient="records")

        # Summiere die Gesamtzeit & den Prozentwert der kleinen Einträge
        others_total_time = small_entries["duration"].sum()
        others_percent = small_entries["overall_percent"].sum()

        # Entferne die kleinen Einträge aus dem Haupt-DF
        df = df[~mask]

        # Füge die "Andere"-Zeile hinzu
        new_row = pd.DataFrame([{
            "label_name": "Others",
            "duration": others_total_time,
            "overall_percent": others_percent,
            "rgba_color": (0.5, 0.5, 0.5, 1.0),  # A neutral gray with full opacity
            "details": details  # Speichert die kleinen Einträge als Liste von Dicts
        }])

        df = pd.concat([df, new_row], ignore_index=True)

        # Speichern des neuen DataFrames mit "Andere"
        self._grouped_label_summary_df = df

    def _get_ax_line_activity(self, ax=None):
        if ax is None:
            granularity = 100  # Fixed granularity
            fig, ax = plt.subplots(dpi=granularity)

        if self._main_df is None or self._main_df.empty:
            print("No data available for plotting.")
            return ax

        # Define parameters
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

        self.__activity_plot_helper = {}
        self.__activity_plot_helper["data"] = activity_plot_data

        self.__init_helper_activity_plot(ax)

        self._set_x_lim(ax)

        return ax

    def __init_helper_activity_plot(self, ax):
        # Plot the line
        self.__activity_plot_helper["line"], = ax.plot(self.__activity_plot_helper["data"]["time"],
                                                       self.__activity_plot_helper["data"]["value"],
                                                       linestyle="-", color="black", )

        # Create hover annotation
        self.__activity_plot_helper["marker"], = ax.plot([], [], marker="o", color="red", markersize=3, visible=False)
        self.__activity_plot_helper["annotation"] = ax.annotate("", xy=(0, 0), xytext=(10, 10),
                                                                textcoords="offset points",
                                                                bbox=dict(boxstyle="round", fc="w", ec="red",
                                                                          alpha=0.7),
                                                                visible=False)
        self.__activity_plot_helper["ax"] = ax

        # Connect hover event
        ax.figure.canvas.mpl_connect("motion_notify_event", self.__activity_on_hover)

    def __activity_on_hover(self,event):
        if event.inaxes != self.__activity_plot_helper["ax"]:
            self.__activity_plot_helper["marker"].set_visible(False)
            self.__activity_plot_helper["annotation"].set_visible(False)
            self.__activity_plot_helper["ax"].figure.canvas.draw_idle()
            return

        if event.ydata is None or not (-5 <= event.ydata <= 105):
            self.__activity_plot_helper["marker"].set_visible(False)
            self.__activity_plot_helper["annotation"].set_visible(False)
            self.__activity_plot_helper["ax"].figure.canvas.draw_idle()
            return

        x_mouse = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)  # Ensure timezone naive

        # Convert the DataFrame time column to timezone-naive format
        self.__activity_plot_helper["data"]["time"] = self.__activity_plot_helper["data"]["time"].dt.tz_localize(None)

        # Find the closest point
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

    def _get_ax_hbar_apps(self, ax=None):
        if ax is None:
            granularity = 100  # Fixed granularity
            fig, ax = plt.subplots(dpi=granularity)

        if self._main_df is None or self._main_df.empty:
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

        # NEW:
        # Extract colors directly from DataFrame
        colors = np.array(self._grouped_app_df["rgba_color"].tolist())  # Convert to numpy array for alignment

        # Create polygons for bar representation
        verts = [np.array([[x1[i], start_y], [x2[i], start_y], [x2[i], end_y], [x1[i], end_y]]) for i in
                 range(len(self._grouped_app_df))]

        # Create the PolyCollection with correct mapping
        poly = PolyCollection(verts, facecolors=colors, alpha=0.7)
        ax.add_collection(poly)

        self.__init_helper_apps(ax)
        self._set_x_lim(ax)

        return ax

    def __init_helper_apps(self, ax):
        self.__app_plot_helper["ax"] = ax
        self.__app_plot_helper["hover_line"], = ax.plot([0, 0], [self.__app_plot_helper["end_y"], self.__app_plot_helper["start_y"]], color='red', linestyle='dotted', alpha=0.7, visible=False)

        # Two triangles pointing at the hover line
        self.__app_plot_helper["triangle_up"], = ax.plot([], [], marker="v", color="red", markersize=8, visible=False)  # Triangle pointing down
        self.__app_plot_helper["triangle_down"], = ax.plot([], [], marker="^", color="red", markersize=8, visible=False)  # Triangle pointing up

        self.__app_plot_helper["annotation"] = ax.annotate("", xy=(0, self.__app_plot_helper["start_y"]), xytext=(10, 10), textcoords="offset points",
                                 bbox=dict(boxstyle="round", fc="white", ec="purple", alpha=0.9),
                                 visible=False)

        self.__app_plot_helper["static_mode"] = False
        self.__app_plot_helper["selected_index"] = None

        ax.figure.canvas.mpl_connect("motion_notify_event", self.__app_on_hover)
        ax.figure.canvas.mpl_connect("button_press_event", self.__app_on_click)
        ax.figure.canvas.mpl_connect("key_press_event", self.__app_on_key)

    def __app_reset_annotation(self):
        """ Reset all hover and selection elements. """

        self.__app_plot_helper["static_mode"] = False
        self.__app_plot_helper["selected_index"] = None
        self.__app_plot_helper["hover_line"].set_visible(False)
        self.__app_plot_helper["annotation"].set_visible(False)
        self.__app_plot_helper["triangle_up"].set_visible(False)
        self.__app_plot_helper["triangle_down"].set_visible(False)
        self.__app_plot_helper["ax"].figure.canvas.draw_idle()

    def __app_update_selection(self,index):
        """ Update the selection line, annotation, and triangles based on given index """
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
        self.__app_plot_helper["triangle_up"].set_data([x_pos], [self.__app_plot_helper["start_y"]])  # Triangle at top of line
        self.__app_plot_helper["triangle_down"].set_data([x_pos], [self.__app_plot_helper["end_y"]])  # Triangle at bottom of line
        self.__app_plot_helper["triangle_up"].set_visible(True)
        self.__app_plot_helper["triangle_down"].set_visible(True)

        # Determine annotation position
        midpoint = len(self._grouped_app_df) / 2
        text_offset = 10 if self.__app_plot_helper["selected_index"] < midpoint else -10  # Right or left shift
        ha = "left" if self.__app_plot_helper["selected_index"] < midpoint else "right"  # Horizontal alignment

        self.__app_plot_helper["annotation"].xy = (x_pos, self.__app_plot_helper["start_y"])
        win_title = split_text_by_max_length(window_title, 35)
        self.__app_plot_helper["annotation"].set_text(f"{start_time}\n{end_time}\n{window_type}\n{win_title}")
        self.__app_plot_helper["annotation"].set_visible(True)
        self.__app_plot_helper["annotation"].set_ha(ha)  # Align left or right
        self.__app_plot_helper["annotation"].set_position((text_offset, 10))  # Adjust position dynamically

        self.__app_plot_helper["ax"].figure.canvas.draw_idle()

    def __app_on_hover(self, event):
        """ Ensure the hover event only applies to the bar chart's y-range """
        if event.inaxes != self.__app_plot_helper["ax"] or self.__app_plot_helper["static_mode"]:
            return

        if event.ydata is None or not (self.__app_plot_helper["end_y"] <= event.ydata <= self.__app_plot_helper["start_y"]):
            self.__app_reset_annotation()
            return

        x_mouse = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)

        # Find the closest index based on mouse position
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
        """ Ensure clicks are only handled in the bar chart's axis """
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
        """ Ensure keyboard events are only processed when static mode is active """
        if not self.__app_plot_helper["static_mode"] or self.__app_plot_helper["selected_index"] is None:
            a = self.__app_plot_helper["static_mode"]
            b = self.__app_plot_helper["selected_index"]
            return

        if event.key == "escape":
            self.__app_reset_annotation()
            return

        if event.key in ["right", "left"]:
            step = 1 if event.key == "right" else -1
            new_index = self.__app_plot_helper["selected_index"] + step
            new_index = 0 if new_index > len(self._grouped_app_df) - 1 else new_index
            self.__app_update_selection(new_index)

    def _get_ax_hbar_labels(self, ax=None, label_list: list[str] | str = None):
        """Erstellt ein horizontales Balkendiagramm (hbar) für Labels basierend auf `self._grouped_label_df`.
           Integriert Hover- und Click-Funktionen zur Interaktion.
        """

        if ax is None:
            granularity = 100  # Fixed granularity
            fig, ax = plt.subplots(dpi=granularity)

        # Standard-Variablen
        start_y = -35
        bar_height = 15
        y_spacing = 5

        x_start = mdates.date2num(self.analysis_results["first_datetime"])
        x_end = mdates.date2num(self.analysis_results["last_datetime"])

        # Prüfen, ob `self._grouped_label_df` existiert und nicht leer ist
        if self._grouped_label_df is None or self._grouped_label_df.empty:
            raise ValueError("No data available in `_grouped_label_df`.")

        # Falls keine Labels vorgegeben sind, nutze die ersten 5 eindeutigen Labels
        available_labels = self._grouped_label_df["label_name"].unique()

        if label_list is None:
            label_list = available_labels[:5]
        elif isinstance(label_list, str):
            label_list = [label_list]

        lowest_y = start_y + len(label_list) * (bar_height+y_spacing) * -1


        # Prüfen, ob alle angegebenen Labels existieren
        missing_labels = [label for label in label_list if label not in available_labels]
        if missing_labels:
            raise ValueError(f"Labels not found: {missing_labels}")

        # Daten filtern für die gewünschten Labels
        label_data = self._grouped_label_df[self._grouped_label_df["label_name"].isin(label_list)].copy()

        # Initiale Y-Position berechnen
        current_y = start_y

        # Store Y positions for labels
        label_y_mapping = {}

        for label in label_list:
            df_subset = label_data[label_data["label_name"] == label]
            label_y_mapping[label] = current_y  # Store the Y-position for the label

            for _, row in df_subset.iterrows():
                x1 = mdates.date2num(row["start_time"])
                x2 = mdates.date2num(row["end_time"])

                # Fetch color directly from DataFrame
                rgba_color = row["rgba_color"]

                # Draw horizontal bar
                ax.barh(y=current_y - (bar_height / 2), width=(x2 - x1), left=x1, height=bar_height,
                        color=rgba_color, alpha=0.7)

            # Nächste Y-Position berechnen
            current_y -= bar_height + y_spacing

        # Hover & Static Line Elements
        hover_line, = ax.plot([0, 0], [0, 0], color='red', linestyle='dotted', alpha=0.7, visible=False)

        # Zwei Dreiecke für die Markierung
        triangle_up, = ax.plot([], [], marker="v", color="red", markersize=8, visible=False)  # Unten
        triangle_down, = ax.plot([], [], marker="^", color="red", markersize=8, visible=False)  # Oben

        annotation = ax.annotate("", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
                                 bbox=dict(boxstyle="round", fc="white", ec="blue", alpha=0.9),
                                 visible=False)

        static_mode = False
        selected_index = None

        def update_selection(index):
            """ Update selection and annotation. """
            nonlocal selected_index, static_mode
            if index < 0 or index >= len(label_data):
                return

            selected_index = index

            entry = label_data.iloc[selected_index]
            start_time = entry["start_time"].strftime("%H:%M:%S")
            end_time = entry["end_time"].strftime("%H:%M:%S")
            duration_seconds = int((entry["end_time"] - entry["start_time"]).total_seconds())
            hours, remainder = divmod(duration_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            duration = f"{hours:02}:{minutes:02}:{seconds:02}"

            x_pos = mdates.date2num(entry["start_time"] + (entry["end_time"] - entry["start_time"]) / 2)
            y_pos = label_y_mapping[entry["label_name"]]

            hover_line.set_xdata([x_pos])
            hover_line.set_ydata([y_pos - bar_height, y_pos])

            hover_line.set_visible(True)

            # Update triangle positions
            triangle_up.set_data([x_pos], [y_pos])  # Triangle at center
            triangle_down.set_data([x_pos], [y_pos - bar_height])  # Triangle at bottom
            triangle_up.set_visible(True)
            triangle_down.set_visible(True)

            # Annotation position check
            text_offset = 10 if x_pos < (x_start + x_end) / 2 else -10  # Rechts oder links verschieben
            ha = "left" if x_pos < (x_start + x_end) / 2 else "right"

            annotation.xy = (x_pos, y_pos)
            annotation.set_text(f"{entry['label_name']}\n{start_time} - {end_time}\n{duration}")
            annotation.set_visible(True)
            annotation.set_ha(ha)
            annotation.set_position((text_offset, 10))  # Dynamische Positionierung

            ax.figure.canvas.draw_idle()

        def on_hover(event):
            """ Ensure hover event only affects label bars in the correct Y-zone. """
            if event.inaxes != ax or static_mode:
                return

            closest_label = None
            for label, y_pos in label_y_mapping.items():
                if (y_pos - bar_height - int(y_spacing)) <= event.ydata <= (y_pos + int(y_spacing)):
                    closest_label = label
                    break  # Sobald das richtige Label gefunden wurde, abbrechen

            if closest_label is None:
                # Falls keine Übereinstimmung, alles ausblenden
                reset_annotation()
                return

            # Jetzt innerhalb der richtigen Y-Zone nach dem nächsten X-Wert suchen
            x_mouse = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)
            valid_entries = label_data[
                (label_data["start_time"] <= x_mouse) &
                (label_data["end_time"] >= x_mouse) &
                (label_data["label_name"] == closest_label)
                ]

            if not valid_entries.empty:
                closest_index = valid_entries.index[0]
            else:
                closest_index = (label_data[
                                     label_data["label_name"] == closest_label
                                     ]["start_time"] - x_mouse).abs().idxmin()

            update_selection(closest_index)

        def on_click(event):
            """ Ensure click event only affects label bars in the correct Y-zone. """
            nonlocal static_mode
            if event.inaxes != ax:
                return  # Klick außerhalb des Plots ignorieren

            closest_label = None
            for label, y_pos in label_y_mapping.items():
                if (y_pos - bar_height - y_spacing) <= event.ydata <= (y_pos - y_spacing):
                    closest_label = label
                    break  # Sobald das richtige Label gefunden wurde, abbrechen

            if closest_label is None:
                # Falls Klick außerhalb aller Labels → Zurücksetzen
                reset_annotation()
                return

            # Jetzt innerhalb der richtigen Y-Zone nach dem nächsten X-Wert suchen
            x_click = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)
            valid_entries = label_data[
                (label_data["start_time"] <= x_click) &
                (label_data["end_time"] >= x_click) &
                (label_data["label_name"] == closest_label)
                ]

            static_mode = True
            if not valid_entries.empty:
                closest_index = valid_entries.index[0]
            else:
                closest_index = (label_data[
                                     label_data["label_name"] == closest_label
                                     ]["start_time"] - x_click).abs().idxmin()

            update_selection(closest_index)

        def reset_annotation():
            nonlocal static_mode, selected_index
            static_mode = False
            selected_index = None
            hover_line.set_visible(False)
            annotation.set_visible(False)
            triangle_up.set_visible(False)
            triangle_down.set_visible(False)
            ax.figure.canvas.draw_idle()

        def on_key(event):
            """ Handle keyboard navigation in static mode with round-robin effect. """
            nonlocal static_mode, selected_index
            if not static_mode or selected_index is None:
                return

            if event.key == "escape":
                reset_annotation()
                return

            if event.key in ["right", "left"]:
                step = 1 if event.key == "right" else -1

                # Hol das aktuelle Label
                current_label = label_data.iloc[selected_index]["label_name"]

                # Filtere nur die Einträge für dieses Label
                same_label_entries = label_data[label_data["label_name"] == current_label]

                # Bestimme den aktuellen Index innerhalb dieser gefilterten Liste
                relative_index = same_label_entries.index.get_loc(selected_index)

                # Round-Robin Logik: Springt zyklisch durch die Einträge des Labels
                new_relative_index = (relative_index + step) % len(same_label_entries)
                new_index = same_label_entries.index[new_relative_index]

                update_selection(new_index)

        ax.figure.canvas.mpl_connect("motion_notify_event", on_hover)
        ax.figure.canvas.mpl_connect("button_press_event", on_click)
        ax.figure.canvas.mpl_connect("key_press_event", on_key)

        self._set_x_lim(ax)
        ax.set_ylim(lowest_y, 110)

        return ax

    def _set_x_lim(self, ax):
        x_min = mdates.date2num(self.analysis_results["first_datetime"])
        x_max = mdates.date2num(self.analysis_results["last_datetime"])
        ax.set_xlim(x_min, x_max)

        # FIXME: Smart solution for showing time properly(based on interval)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    def _combine_axes(self, ax_list: list):
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

            for line in old_ax.get_lines():  # Get all Line2D objects
                x_data, y_data = line.get_xdata(), line.get_ydata()
                new_ax.plot(x_data, y_data,
                            linestyle=line.get_linestyle(),
                            color=line.get_color(),
                            linewidth=line.get_linewidth(),
                            alpha=line.get_alpha() if line.get_alpha() else 1.0)

            for patch in old_ax.patches:
                edge_color = patch.get_edgecolor()

                # Ensure no border if the original had no visible edge
                if edge_color is None or edge_color[-1] == 0:  # If fully transparent (RGBA last value = 0)
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
                if isinstance(collection, PolyCollection):  # No 'plt.', directly 'PolyCollection'
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

        self.__init_helper_activity_plot(new_ax)
        self.__init_helper_apps(new_ax)

        return new_fig, new_ax

    def get_main_plot(self):
        ax_activity = vdf._get_ax_line_activity()
        ax_apps = vdf._get_ax_hbar_apps()
        ax_labels = vdf._get_ax_hbar_labels()
        fig, _ = self._combine_axes([ax_activity, ax_apps, ax_labels])
        return fig

    def get_vbar_apps(self):
        if self._grouped_app_summary_df is None or self._grouped_app_summary_df.empty:
            print("No app data available for plotting.")
            return None

        df = self._grouped_app_summary_df

        # Erstelle das Diagramm
        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(df["window_type"], df["overall_percent"], color=df["rgba_color"])

        # Achsentitel setzen
        ax.set_xlabel("Apps")
        ax.set_ylabel("Percent usage")
        ax.set_title("App usage")

        ax.set_ylim(0, df["overall_percent"].max() + 5)

        # X-Achse rotieren für bessere Lesbarkeit
        plt.xticks(rotation=45, ha="right")

        # Hover & Static Line Elements
        hover_line, = ax.plot([0, 0], [0, 0], color='red', linestyle='dotted', alpha=0.7, visible=False)

        # Zwei Dreiecke für die Markierung
        triangle_up, = ax.plot([], [], marker="v", color="red", markersize=8, visible=False)  # Unten

        # 🔹 Annotation-Box vorbereiten 🔹
        annotation = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                                 textcoords="offset points", ha="center", va="bottom",
                                 fontsize=10, color="black",
                                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))
        annotation.set_visible(False)

        # 🔹 Hover-Funktion 🔹
        def on_hover(event):
            # Hide annotation if the cursor is outside the axes
            if event.inaxes != ax:
                annotation.set_visible(False)
                triangle_up.set_visible(False)
                hover_line.set_visible(False)
                fig.canvas.draw_idle()
                return

            for bar, (app_name, percent, duration, details) in zip(bars, zip(df["window_type"], df["overall_percent"],
                                                                             df["duration"], df.get("details", None))):
                # Get bar's X range
                bar_x_min = bar.get_x()
                bar_x_max = bar.get_x() + bar.get_width()
                bar_center_x = bar.get_x() + bar.get_width() / 2

                # Check if cursor is inside the bar's X range
                if bar_x_min <= event.xdata <= bar_x_max:
                    # Convert `duration` to `hh:mm:ss`
                    hours, remainder = divmod(duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}(HH:MM:SS)"

                    # Base annotation text
                    annotation_text = f"{app_name}: {percent:.2f}%\n{duration_str}"

                    # If "Others", show details
                    if app_name == "Others" and details:
                        detail_texts = [f"{d['window_type']}: {d['overall_percent']:.2f}%" for d in details]
                        annotation_text += "\n" + "\n".join(detail_texts[:5])  # Show max 5 entries
                        n_lines_space = annotation_text.count("\n") * 0.1
                    else:
                        n_lines_space = 0.5


                    # Position annotation at the middle Y range
                    mid_y = ax.get_ylim()[1] / 2  # Middle of the Y-axis
                    annotation.xy = (bar_center_x, mid_y)
                    annotation.set_text(annotation_text)
                    annotation.set_visible(True)

                    # Position hover line & triangle marker
                    hover_line.set_data([bar_center_x, bar_center_x], [mid_y - n_lines_space, 0])
                    hover_line.set_visible(True)

                    triangle_up.set_data([bar_center_x], [mid_y - n_lines_space])  # Single point (marker)
                    triangle_up.set_visible(True)

                    fig.canvas.draw_idle()
                    return

            # Hide annotation if no bar is hovered
            annotation.set_visible(False)
            triangle_up.set_visible(False)
            hover_line.set_visible(False)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_hover)

        return fig

    def get_vbar_labels(self):
        if self._grouped_label_summary_df is None or self._grouped_label_summary_df.empty:
            print("No label data available for plotting.")
            return None

        df = self._grouped_label_summary_df

        # Create the figure
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

        # Hover & Static Line Elements
        hover_line, = ax.plot([0, 0], [0, 0], color='red', linestyle='dotted', alpha=0.7, visible=False)
        triangle_up, = ax.plot([], [], marker="v", color="red", markersize=8, visible=False)  # Triangle marker

        # 🔹 Annotation Box 🔹
        annotation = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                                 textcoords="offset points", ha="center", va="bottom",
                                 fontsize=10, color="black",
                                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white"))
        annotation.set_visible(False)

        # 🔹 Hover Function 🔹
        def on_hover(event):
            # Hide annotation if the cursor is outside the axes
            if event.inaxes != ax:
                annotation.set_visible(False)
                triangle_up.set_visible(False)
                hover_line.set_visible(False)
                fig.canvas.draw_idle()
                return

            for bar, (label_name, percent, duration, details) in zip(bars, zip(df["label_name"], df["overall_percent"],
                                                                               df["duration"], df.get("details", None))):
                # Get bar's X range
                bar_x_min = bar.get_x()
                bar_x_max = bar.get_x() + bar.get_width()
                bar_center_x = bar.get_x() + bar.get_width() / 2

                # Check if cursor is inside the bar's X range
                if bar_x_min <= event.xdata <= bar_x_max:
                    # Convert `duration` to `HH:MM:SS`
                    hours, remainder = divmod(duration, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02} (HH:MM:SS)"

                    # Base annotation text
                    annotation_text = f"{label_name}: {percent:.2f}%\n{duration_str}"

                    # If "Others", show details
                    if label_name == "Others" and details:
                        detail_texts = [f"{d['label_name']}: {d['overall_percent']:.2f}%" for d in details]
                        annotation_text += "\n" + "\n".join(detail_texts[:5])  # Show max 5 entries
                        n_lines_space = annotation_text.count("\n") * 0.1
                    else:
                        n_lines_space = 0.5

                    # Position annotation at the middle Y range
                    mid_y = ax.get_ylim()[1] / 2  # Middle of the Y-axis
                    annotation.xy = (bar_center_x, mid_y)
                    annotation.set_text(annotation_text)
                    annotation.set_visible(True)

                    # Position hover line & triangle marker
                    hover_line.set_data([bar_center_x, bar_center_x], [mid_y - n_lines_space, 0])
                    hover_line.set_visible(True)

                    triangle_up.set_data([bar_center_x], [mid_y - n_lines_space])  # Single point (marker)
                    triangle_up.set_visible(True)

                    fig.canvas.draw_idle()
                    return

            # Hide annotation if no bar is hovered
            annotation.set_visible(False)
            triangle_up.set_visible(False)
            hover_line.set_visible(False)
            fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_hover)

        return fig

    def get_pie_apps(self):
        if self._grouped_app_summary_df is None or self._grouped_app_summary_df.empty:
            print("No app data available for plotting.")
            return None

        df = self._grouped_app_summary_df

        # Create the pie chart
        fig, ax = plt.subplots(figsize=(8, 8))

        # Generate wedges with leader lines
        wedges, texts, autotexts = ax.pie(
            df["overall_percent"],
            labels=None,  # Labels will be added manually
            autopct="%1.1f%%",
            colors=df["rgba_color"],
            startangle=90,
            counterclock=False,
            wedgeprops={"edgecolor": "black", "linewidth": 0.3, "antialiased": True}
        )

        # 🔹 Reduce Pie Labels Font Size (Inside Pie Chart)
        for autotext in autotexts:
            autotext.set_fontsize(8)

        # Store label positions for hover effect
        label_annotations = []

        for i, (wedge, label, percent, duration, color) in enumerate(zip(
                wedges, df["window_type"], df["overall_percent"], df["duration"], df["rgba_color"])):
            # Get angle of the wedge (middle of arc)
            angle = (wedge.theta2 + wedge.theta1) / 2

            # Offset every second label +10px further to prevent overlap
            offset_factor = 1.345 if i % 2 == 1 else 1.2
            x = np.cos(np.deg2rad(angle)) * offset_factor
            y = np.sin(np.deg2rad(angle)) * offset_factor

            # Add leader line
            ax.plot([np.cos(np.deg2rad(angle)), x], [np.sin(np.deg2rad(angle)), y], color="black", lw=0.8)

            # 🔹 Reduce Label Name Font Size & Adjust Box Size
            bbox_props = dict(boxstyle="round,pad=0.4", edgecolor=color, facecolor="white", linewidth=1.2)
            text = ax.text(x, y, f"{label}", ha="center", va="center", fontsize=8, bbox=bbox_props)

            # Store values for hover effect
            label_annotations.append((text, label, percent, duration, angle, x, y, color))

        # 🔹 Fixed Annotation (95% Opaque) 🔹
        annotation = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                                 textcoords="offset points", ha="center", va="bottom",
                                 fontsize=10, color="black",
                                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white", alpha=0.95))
        annotation.set_visible(False)

        # 🔹 Hover Function 🔹
        def on_hover(event):
            if event.inaxes != ax:
                annotation.set_visible(False)
                fig.canvas.draw_idle()
                return

            for text, label_name, percent, duration, angle, x, y, color in label_annotations:
                bbox = text.get_window_extent(renderer=fig.canvas.get_renderer())

                # 🔹 EXPAND hover detection:
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

                    # Build annotation text
                    annotation_text = f"{label_name}: {percent:.2f}%\n{duration_str}"

                    # Check if "Others" and add details
                    if label_name == "Others" and "details" in df.columns:
                        details = df.loc[df["window_type"] == "Others", "details"].values[0]
                        if details:
                            detail_texts = [f"{d['window_type']}: {d['overall_percent']:.2f}%" for d in details]
                            annotation_text += "\n" + "\n".join(detail_texts[:5])  # Show up to 5

                    # Position annotation **below the label** in a fixed location
                    annotation.xy = (x, y - 0.1)  # Keep annotation below the text box
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
        if self._grouped_label_summary_df is None or self._grouped_label_summary_df.empty:
            print("No label data available for plotting.")
            return None

        df = self._grouped_label_summary_df

        # Create the pie chart
        fig, ax = plt.subplots(figsize=(8, 8))

        # Generate wedges with leader lines
        wedges, texts, autotexts = ax.pie(
            df["overall_percent"],
            labels=None,  # Labels will be added manually
            autopct="%1.1f%%",
            colors=df["rgba_color"],
            startangle=90,
            counterclock=False,
            wedgeprops={"edgecolor": "black", "linewidth": 0.3, "antialiased": True}
        )

        # 🔹 Reduce Pie Labels Font Size (Inside Pie Chart)
        for autotext in autotexts:
            autotext.set_fontsize(8)

        # Store label positions for hover effect
        label_annotations = []

        for i, (wedge, label, percent, duration, color) in enumerate(zip(
                wedges, df["label_name"], df["overall_percent"], df["duration"], df["rgba_color"])):
            # Get angle of the wedge (middle of arc)
            angle = (wedge.theta2 + wedge.theta1) / 2

            # Offset every second label +10px further to prevent overlap
            offset_factor = 1.345 if i % 2 == 1 else 1.2
            x = np.cos(np.deg2rad(angle)) * offset_factor
            y = np.sin(np.deg2rad(angle)) * offset_factor

            # Add leader line
            ax.plot([np.cos(np.deg2rad(angle)), x], [np.sin(np.deg2rad(angle)), y], color="black", lw=0.8)

            # 🔹 Reduce Label Name Font Size & Adjust Box Size
            bbox_props = dict(boxstyle="round,pad=0.4", edgecolor=color, facecolor="white", linewidth=1.2)
            text = ax.text(x, y, f"{label}", ha="center", va="center", fontsize=8, bbox=bbox_props)

            # Store values for hover effect
            label_annotations.append((text, label, percent, duration, angle, x, y, color))

        # 🔹 Fixed Annotation (95% Opaque) 🔹
        annotation = ax.annotate("", xy=(0, 0), xytext=(0, 0),
                                 textcoords="offset points", ha="center", va="bottom",
                                 fontsize=10, color="black",
                                 bbox=dict(boxstyle="round,pad=0.3", edgecolor="black", facecolor="white", alpha=0.95))
        annotation.set_visible(False)

        # 🔹 Hover Function 🔹
        def on_hover(event):
            if event.inaxes != ax:
                annotation.set_visible(False)
                fig.canvas.draw_idle()
                return

            for text, label_name, percent, duration, angle, x, y, color in label_annotations:
                bbox = text.get_window_extent(renderer=fig.canvas.get_renderer())

                # 🔹 EXPAND hover detection:
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

                    # Build annotation text
                    annotation_text = f"{label_name}: {percent:.2f}%\n{duration_str}"

                    # Check if "Others" and add details
                    if label_name == "Others" and "details" in df.columns:
                        details = df.loc[df["label_name"] == "Others", "details"].values[0]
                        if details:
                            detail_texts = [f"{d['label_name']}: {d['overall_percent']:.2f}%" for d in details]
                            annotation_text += "\n" + "\n".join(detail_texts[:5])  # Show up to 5

                    # Position annotation **below the label** in a fixed location
                    annotation.xy = (x, y - 0.1)  # Keep annotation below the text box
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


# # # # Helper functions # # # #

def split_leading_special_chars(word: str):
    """Teilt ein Wort in führende Sonderzeichen und den restlichen Text"""
    special_chars = ""
    while word and not word[0].isalnum():  # Sonderzeichen am Anfang sammeln
        special_chars += word[0]
        word = word[1:]
    return special_chars, word


def split_text_by_max_length(text: str, max_length: int) -> str:
    """Splits text into lines with max_length, breaking at the nearest space.
    Special characters like '!', '...', ',' at the start of words are kept with the previous word.
    """
    words = text.split()  # Wörter anhand von Leerzeichen splitten
    processed_words = []

    previous_word = ""  # Speichert das vorherige Wort, um Sonderzeichen anzuhängen

    # 1️⃣ Verarbeitung der Sonderzeichen vor der eigentlichen Zeilenaufteilung
    for word in words:
        special_chars, cleaned_word = split_leading_special_chars(word)

        if special_chars and processed_words:
            # Falls das Wort Sonderzeichen hatte und nicht am Satzanfang steht, hänge es an das letzte Wort an
            processed_words[-1] += special_chars

        if cleaned_word:  # Falls nach dem Entfernen der Sonderzeichen noch ein Wort übrig bleibt
            processed_words.append(cleaned_word)

    # 2️⃣ Hauptprozess: Zeilenaufteilung basierend auf max_length
    lines = []
    current_line = ""

    for word in processed_words:
        if len(current_line) + len(word) + 1 <= max_length:
            current_line += (" " if current_line else "") + word
        else:
            # Speichere die Zeile und starte eine neue
            lines.append(current_line)
            current_line = word  # Starte mit dem neuen Wort

    # Letzte Zeile speichern, falls sie nicht leer ist
    if current_line:
        lines.append(current_line)

    return "\n".join(lines)



# # # # External Call functions # # # #
def init_standard_analyzes():
    # ini the threading class, it analyzes on init once.

    pass


import ttkbootstrap as tb
from ttkbootstrap.constants import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


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

    test_df = DBHandler().search_window_log(start_time=datetime(2025,1,16,0,0), end_time=datetime(2025,1,17,0,0))

    start_analysis = datetime.now()
    vdf = ViperDF("testing", test_df)
    vdf.analyze()


    fig_ori, ax_all = plt.subplots(dpi=100)
    ax_all = vdf._get_ax_line_activity(ax=ax_all)
    ax_all = vdf._get_ax_hbar_apps(ax=ax_all)
    ax_all = vdf._get_ax_hbar_labels(ax=ax_all)
    show_figure_in_ttk(fig_ori)


    show_figure_in_ttk(vdf.get_main_plot())

    end_analysis = datetime.now()
    time_used = (end_analysis - start_analysis).total_seconds()
    #print(f"{end_analysis} - {start_analysis} = {time_used}")



    stop_db()


    #print("Please start with the main.py")
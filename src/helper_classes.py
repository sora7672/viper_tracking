"""
This module provides helper classes used across various parts of the application.

Features:
- `Classproperty`: Implements a decorator for class-level properties.
- `ColorPicker`: A singleton-based utility for managing color selection.
- `Seconds`: A subclass of `int` that converts seconds into human-readable time formats.

Author: sora7672
"""
__author__ = "sora7672"

from threading import Lock
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class Classproperty:
    """
    A decorator class that enables class-level properties.

    This allows methods decorated with `@Classproperty` to be accessed directly from the class,
    without needing an instance.

    Example:
        class Example:
            @Classproperty
            def name(cls):
                return "ExampleClass"

        print(Example.name)  # Outputs: ExampleClass
    """

    def __init__(self, func):
        """
        Initializes the class property decorator.

        :param func: Callable (The method to be treated as a class-level property.)
        :return: None
        """

        self.func = func

    def __get__(self, instance, owner):
        """
        Retrieves the class-level property value when accessed.

        :param instance: object | None (The instance calling the property, or None when accessed via the class.)
        :param owner: type (The class owning the property.)
        :return: Any (The value returned by the decorated method.)
        """

        return self.func(owner)


class ColorPicker:
    """
    A singleton-based color manager providing sequentially assigned colors.

    This class maintains a rotating selection of predefined colors in both HEX and RGBA formats.
    It ensures that colors are assigned in a round-robin fashion, using a thread-safe locking mechanism.

    Attributes:
        _instance (ColorPicker | None): The singleton instance of the class.
        _lock (Lock): A threading lock to synchronize access.
        _available_colors_hex (list[str]): List of predefined colors in HEX format.
        _available_colors_rgba (list[tuple[float, float, float, float]]): List of predefined colors in RGBA format.
        _next_index (int): Index for tracking the next available color in rotation.
    """

    _instance = None
    _lock = Lock()
    _available_colors_hex = [
        "#1F77B4",  # Blue
        "#FFFF33",  # Neon Yellow
        "#FF7F0E",  # Orange
        "#17BECF",  # Cyan
        "#2CA02C",  # Green
        "#FF1493",  # Deep Pink
        "#9467BD",  # Purple
        "#5A5A5A",  # Dark Gray
        "#A0522D",  # Slightly lighter brown
        "#BCBD22",  # Yellow-Green
        "#D62728",  # Red
        "#8B4513",  # Dark Brown
        "#E377C2",  # Pink
        "#4B0082",  # Dark Purple
        "#B22222",  # More reddish maroon
    ]

    _available_colors_rgba = [
        (0.12156862745098039, 0.4666666666666667, 0.7058823529411765, 1.0),  # Blue
        (1.0, 1.0, 0.2, 1.0),  # Neon Yellow
        (1.0, 0.4980392156862745, 0.054901960784313725, 1.0),  # Orange
        (0.09019607843137255, 0.7450980392156863, 0.8117647058823529, 1.0),  # Cyan
        (0.17254901960784313, 0.6274509803921569, 0.17254901960784313, 1.0),  # Green
        (1.0, 0.0784313725490196, 0.5764705882352941, 1.0),  # Deep Pink
        (0.5803921568627451, 0.403921568627451, 0.7411764705882353, 1.0),  # Purple
        (0.35294117647058826, 0.35294117647058826, 0.35294117647058826, 1.0),  # Dark Gray
        (0.6274509803921569, 0.3215686274509804, 0.17647058823529413, 1.0),  # Slightly lighter brown
        (0.7372549019607844, 0.7411764705882353, 0.13333333333333333, 1.0),  # Yellow-Green
        (0.8392156862745098, 0.15294117647058825, 0.1568627450980392, 1.0),  # Red
        (0.5450980392156862, 0.27058823529411763, 0.07450980392156863, 1.0),  # Dark Brown
        (0.8901960784313725, 0.4666666666666667, 0.7607843137254902, 1.0),  # Pink
        (0.29411764705882354, 0.0, 0.5098039215686274, 1.0),  # Dark Purple
        (0.6980392156862745, 0.13333333333333333, 0.13333333333333333, 1.0)  # More reddish maroon
    ]
    _next_index = 0

    @classmethod
    def next_color_hex(cls, count: int = 1):
        """
        Retrieves the next color(s) in HEX format.

        Colors are assigned sequentially from the `_available_colors_hex` list.
        Once all colors have been used, the index wraps around to the start.

        :param count: int (The number of colors to retrieve.)
        :return: list[str] (A list of HEX color codes.)
        """

        with cls._lock:
            out = []
            for _ in range(count):
                out.append(cls._available_colors_hex[cls._next_index])
                cls._next_index += 1
                if cls._next_index >= len(cls._available_colors_hex):
                    cls._next_index = 0
            return out

    @classmethod
    def next_color_rgba(cls, count: int = 1):
        """
        Retrieves the next color(s) in RGBA format.

        Colors are assigned sequentially from the `_available_colors_rgba` list.
        Once all colors have been used, the index wraps around to the start.

        :param count: int (The number of colors to retrieve.)
        :return: list[tuple[float, float, float, float]] (A list of RGBA color tuples.)
        """

        with cls._lock:
            out = []
            for _ in range(count):
                out.append(cls._available_colors_rgba[cls._next_index])
                cls._next_index += 1
                if cls._next_index >= len(cls._available_colors_rgba):
                    cls._next_index = 0
            return out


class Seconds(int):
    """
    A subclass of `int` that represents time in seconds and provides human-readable formatting.

    This class automatically determines the most appropriate time unit (weeks, days, hours, minutes, seconds)
    and supports string-based representations for easy use.

    Attributes:
        time_frame (str): The detected time unit ('w' for weeks, 'd' for days, 'h' for hours, 'm' for minutes, 's' for seconds).
    """

    def __new__(cls, value):
        """
        Initializes a new `Seconds` instance.

        This validates that the provided value is an integer and determines the appropriate time unit.

        :param value: int (The number of seconds.)
        :raises ValueError: If `value` is not an integer.
        :return: Seconds (A new instance of `Seconds` with an assigned time frame.)
        """

        if not isinstance(value, int):
            raise ValueError("Seconds must be initialized with an integer value.")
        instance = super().__new__(cls, value)
        # Set time frame on creation
        instance.time_frame = instance.__determine_time_frame()
        return instance

    def __determine_time_frame(self):
        """
        Determines the appropriate time unit based on the value.

        - >= 604800 seconds → 'w' (weeks)
        - >= 86400 seconds → 'd' (days)
        - >= 3600 seconds → 'h' (hours)
        - >= 60 seconds → 'm' (minutes)
        - < 60 seconds → 's' (seconds)

        :return: str (The detected time frame.)
        """

        if self >= 604800:
            return "w"
        elif self >= 86400:
            return "d"
        elif self >= 3600:
            return "h"
        elif self >= 60:
            return "m"
        else:
            return "s"

    def __str__(self):
        """
        Converts the `Seconds` object to a human-readable string.

        Returns the formatted time based on the detected time unit.

        :return: str (The formatted time string.)
        """

        match self.time_frame:
            case "w":
                return self.weeks
            case "d":
                return self.days
            case "h":
                return self.hours
            case "m":
                return self.mins
            case "s":
                return f"{self} seconds"

    @property
    def str(self):
        """
        Returns the string representation of the `Seconds` object.

        :return: str (The formatted time string.)
        """

        return str(self)

    @property
    def mins(self):
        """
        Converts seconds into a "minutes:seconds" format.

        Example:
            125 → "2:5"

        :return: str (Formatted minutes and seconds.)
        """

        mins, secs = divmod(self, 60)
        return f"{mins}:{secs}"

    @property
    def hours(self):
        """
        Converts seconds into a "hours:minutes:seconds" format.

        Example:
            3665 → "1:1:5"

        :return: str (Formatted hours, minutes, and seconds.)
        """

        mins, secs = divmod(self, 60)
        hours, mins = divmod(mins, 60)
        return f"{hours}:{mins}:{secs}"

    @property
    def days(self):
        """
        Converts seconds into a "days, hours:minutes:seconds" format.

        Example:
            90000 → "1 days, 1:0:0"

        :return: str (Formatted days, hours, minutes, and seconds.)
        """

        mins, secs = divmod(self, 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        return f"{days} days, {hours}:{mins}:{secs}"

    @property
    def weeks(self):
        """
        Converts seconds into a "weeks, days, hours:minutes:seconds" format.

        Example:
            1209600 → "2 weeks, 0 days 0:0:0"

        :return: str (Formatted weeks, days, hours, minutes, and seconds.)
        """

        mins, secs = divmod(self, 60)
        hours, mins = divmod(mins, 60)
        days, hours = divmod(hours, 24)
        weeks, days = divmod(days, 7)
        return f"{weeks} weeks, {days} days {hours}:{mins}:{secs}"

class DynamicTimeframe:
    """
    A class for handling dynamic timeframes with predefined relative and absolute date ranges.

    This class provides a set of predefined timeframes (e.g., "last_24_hours", "current_week", "previous_month").
    It calculates the start and end datetime based on the selected timeframe.

    Attributes:
        _predefined_dynamic_timeframes (dict): A dictionary defining available timeframes and their corresponding calculations.
        value (str): The selected timeframe identifier.

    Raises:
        ValueError: If an invalid timeframe is provided during initialization.
    """

    _predefined_dynamic_timeframes = {

        "last_hour": {"type": "relative", "unit": "hours", "difference": 1},
        "last_6_hours": {"type": "relative", "unit": "hours", "difference": 6},
        "last_12_hours": {"type": "relative", "unit": "hours", "difference": 12},
        "last_24_hours": {"type": "relative", "unit": "hours", "difference": 24},
        "last_day": {"type": "relative", "unit": "hours", "difference": 24},
        "last_48_hours": {"type": "relative", "unit": "hours", "difference": 48},
        "last_2_days": {"type": "relative", "unit": "hours", "difference": 48},
        "last_72_hours": {"type": "relative", "unit": "hours", "difference": 72},
        "last_3_days": {"type": "relative", "unit": "hours", "difference": 72},
        "last_7_days": {"type": "relative", "unit": "days", "difference": 7},
        "last_week": {"type": "relative", "unit": "days", "difference": 7},
        "last_14_days": {"type": "relative", "unit": "days", "difference": 14},
        "last_2_weeks": {"type": "relative", "unit": "days", "difference": 14},
        "last_month": {"type": "relative", "unit": "days", "difference": 28},
        "last_28_days": {"type": "relative", "unit": "days", "difference": 28},
        "last_year": {"type": "relative", "unit": "days", "difference": 365},

        "current_day": {"type": "absolute", "unit": "days", "difference": 0},
        "current_week": {"type": "absolute", "unit": "weeks", "difference": 0},
        "current_month": {"type": "absolute", "unit": "months", "difference": 0},
        "current_year": {"type": "absolute", "unit": "years", "difference": 0},

        "previous_day": {"type": "absolute", "unit": "days", "difference": 1},
        "previous_week": {"type": "absolute", "unit": "weeks", "difference": 1},
        "previous_month": {"type": "absolute", "unit": "months", "difference": 1},
        "previous_year": {"type": "absolute", "unit": "years", "difference": 1},
    }

    def __init__(self, dynamic_timeframe: str):
        """
        Initializes a DynamicTimeframe instance with a predefined timeframe.

        :param dynamic_timeframe: str (The identifier of the predefined timeframe.)
        :raises ValueError: If the provided timeframe is not in `_predefined_dynamic_timeframes`.
        :return: None
        """

        if dynamic_timeframe not in DynamicTimeframe._predefined_dynamic_timeframes:
            raise ValueError(f"Invalid dynamic timeframe: {dynamic_timeframe}\n"
                             f"Valid values: {DynamicTimeframe._predefined_dynamic_timeframes.keys()}")
        self.value = dynamic_timeframe

    def __get_start_and_end_datetime(self) -> tuple[datetime, datetime]:
        """
        Computes the start and end datetime based on the selected timeframe.

        The method determines whether the timeframe is relative (e.g., "last_7_days") or absolute (e.g., "current_month")
        and calculates the appropriate datetime range accordingly.

        Relative timeframes subtract a fixed duration from the current time.
        Absolute timeframes are adjusted to align with full calendar units (e.g., start of the week, month, or year).

        :raises ValueError: If the timeframe type or unit is invalid.
        :return: tuple[datetime, datetime] (A tuple containing the calculated start and end datetime.)
        """

        time_frame_data = DynamicTimeframe._predefined_dynamic_timeframes[self.value]

        if time_frame_data["type"] == 'relative':
            end_datetime = datetime.now()
            start_datetime = end_datetime - timedelta(**{time_frame_data["unit"]: time_frame_data["difference"]})

        elif time_frame_data["type"] == 'absolute':
            if time_frame_data["unit"] in {"years", "months"}:
                minus = relativedelta(**{time_frame_data["unit"]: time_frame_data["difference"]})
            else:
                minus = timedelta(**{time_frame_data["unit"]: time_frame_data["difference"]})
            tmp_datetime = datetime.now() - minus
            tmp_datetime = tmp_datetime.replace(hour=0, minute=0, second=0, microsecond=0)

            match time_frame_data["unit"]:
                case "days":
                    start_datetime = tmp_datetime

                case "weeks":
                    start_datetime = tmp_datetime - timedelta(
                        days=tmp_datetime.isoweekday() - 1)

                case "months":
                    start_datetime = tmp_datetime.replace(day=1)

                case "years":
                    start_datetime = tmp_datetime.replace(month=1, day=1)

                case _:
                    raise ValueError(f"Invalid dynamic timeframe unit: {time_frame_data['unit']}")

            if time_frame_data["unit"] in {"months", "years"}:
                end_datetime = start_datetime + relativedelta(
                    **{time_frame_data["unit"]: 1}) - timedelta(seconds=1)
            else:
                end_datetime = start_datetime + timedelta(
                    **{time_frame_data["unit"]: 1}) - timedelta(seconds=1)

        else:
            raise ValueError(f"Invalid dynamic timeframe type: {time_frame_data['type']}")

        return start_datetime, end_datetime

    @property
    def start_datetime(self) -> datetime:
        """
        Retrieves the calculated start datetime for the selected timeframe.

        :return: datetime (The start datetime based on the selected timeframe.)
        """

        out, _ = self.__get_start_and_end_datetime()
        return out

    @property
    def end_datetime(self) -> datetime:
        """
        Retrieves the calculated end datetime for the selected timeframe.

        :return: datetime (The end datetime based on the selected timeframe.)
        """

        _, out = self.__get_start_and_end_datetime()
        return out

    @property
    def datetime_range(self) -> tuple[datetime, datetime]:
        """
        Returns the start and end datetime as a tuple.

        :return: tuple[datetime, datetime] (A tuple containing both the start and end datetime.)
        """

        return self.__get_start_and_end_datetime()

    @classmethod
    def get_entries(cls):#
        out = []
        for k in cls._predefined_dynamic_timeframes.keys():
            out.append(k)
        return out

if __name__ == "__main__":
    print("Please start with the main.py")
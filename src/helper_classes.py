# helper class outsourced
from threading import Lock


class Classproperty:
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, owner):
        return self.func(owner)


class ColorPicker:
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
        with cls._lock:
            out = []
            for _ in range(count):
                out.append(cls._available_colors_rgba[cls._next_index])
                cls._next_index += 1
                if cls._next_index >= len(cls._available_colors_rgba):
                    cls._next_index = 0
            return out

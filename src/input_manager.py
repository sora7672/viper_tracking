"""
This file is part of Viper Tracking.

What it does:
- Tracks user inputs, like key presses and mouse clicks, but NOT what is typed or clicked.
- Counts and categorizes inputs for analysis, ensuring privacy.
- Operates in the background and safely saves the counts in a database.

Key Privacy Note:
We NEVER log or track what you type or where you click. We only count how many times certain actions
(like key presses or mouse clicks) happen.

Author: sora7672
"""
__author__ = 'sora7672'

from threading import Thread, Lock
from time import sleep
from pynput import mouse, keyboard
from datetime import datetime, timedelta

from config_manager import threads_are_stopped, interval_inputs
from db_connector import DBHandler
from log_handler import get_logger

# TODO: Maybe change global threads to a class/object based system
mouse_thread: Thread = None
keyboard_thread: Thread = None


class InputManager:
    """
    This class handles tracking of inputs, like key presses and mouse clicks.

    How it works:
    - Counts different types of actions, like character key presses, direction keys, and mouse clicks.
    - Does NOT save the actual text, key names, or mouse positions—only the counts.
    - Keeps everything private and secure, designed to protect your data.

    Key Features:
    - Thread-safe: Multiple parts of the program can use this class without conflicts.
    - Resets counters after saving them, so every session is fresh.
    - Exports the counts to a database for analysis.

    Attributes:
        _count_char_key_pressed (int): Number of character keys pressed.
        _count_direction_key_pressed (int): Number of direction keys (e.g., arrows) pressed.
        _count_special_key_pressed (int): Number of special keys (e.g., Shift, Ctrl) pressed.
        _count_left_mouse_pressed (int): Number of left mouse button clicks.
        _count_right_mouse_pressed (int): Number of right mouse button clicks.
        _count_middle_mouse_pressed (int): Number of middle mouse button clicks.
        _count_mouse_scrolls (int): Number of mouse scroll actions.
        _last_mouse_scroll_datetime (datetime | None): Time of the last mouse scroll action.
        lock (Lock): Ensures that input tracking is safe and error-free.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Implements the singleton pattern by ensuring only one instance of the class exists.

        :return: InputManager (The singleton instance.)
        """
        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the `InputManager` as a thread-safe singleton.

        This method sets up counters for various input events (e.g., key presses, mouse clicks)
        and timestamps for tracking user activity. It also ensures thread-safe operations by
        initializing a lock.

        Attributes Initialized:
        - `_initialized` (bool): Prevents reinitialization of the instance.
        - `_count_char_key_pressed` (int): Tracks the number of character key presses.
        - `_count_direction_key_pressed` (int): Tracks the number of direction key presses.
        - `_count_special_key_pressed` (int): Tracks the number of special key presses.
        - `_count_left_mouse_pressed` (int): Tracks the number of left mouse button presses.
        - `_count_right_mouse_pressed` (int): Tracks the number of right mouse button presses.
        - `_count_middle_mouse_pressed` (int): Tracks the number of middle mouse button presses.
        - `_count_mouse_scrolls` (int): Tracks the number of mouse scroll events.
        - `_last_mouse_scroll_datetime` (datetime | None): Stores the timestamp of the last mouse scroll event.
        - `lock` (Lock): Ensures thread-safe access to the input data.

        Additionally, this method sets the singleton instance (`InputManager._instance`) and
        logs the initialization process for debugging purposes.

        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._count_char_key_pressed = 0
            self._count_direction_key_pressed = 0
            self._count_special_key_pressed = 0

            self._count_left_mouse_pressed = 0
            self._count_right_mouse_pressed = 0
            self._count_middle_mouse_pressed = 0
            self._count_mouse_scrolls = 0

            # Needed for calculating one scroll only
            self._last_mouse_scroll_datetime = None

            self._activity = False

            self.lock = Lock()
            InputManager._instance = self
            get_logger().debug("__init__ InputManager")

    def get_all(self) -> dict:
        """
        Saves all input counts in dict that is returned later and resets the instance.

        How it works:
        - Adds up all counts, like key presses and mouse actions.
        - Includes the time of the last activity.
        - Resets all counts after saving, so every session starts fresh.

        Privacy Note:
        This method only tracks counts. It does NOT track specific keys, clicks, or anything sensitive.

        :return: dict (A dictionary of counts, like "count_key_pressed", "count_mouse_pressed", and "last_activity_datetime".)
        """

        get_logger().debug("InputManager lock use")
        with self.lock:
            tmp_dict: dict = {"count_key_pressed": (
                         self._count_char_key_pressed + self._count_direction_key_pressed +
                         self._count_special_key_pressed),
                         "count_mouse_pressed": (self._count_left_mouse_pressed + self._count_right_mouse_pressed +
                                                 self._count_middle_mouse_pressed),
                         "count_direction_key_pressed": self._count_direction_key_pressed,
                         "count_char_key_pressed": self._count_char_key_pressed,
                         "count_special_key_pressed": self._count_special_key_pressed,
                         "count_mouse_scrolls": self._count_mouse_scrolls,
                         "count_left_mouse_pressed": self._count_left_mouse_pressed,
                         "count_right_mouse_pressed": self._count_right_mouse_pressed,
                         "count_middle_mouse_pressed": self._count_middle_mouse_pressed}
        self.reset()
        get_logger().debug("InputManager lock release")
        tmp_dict["creation_datetime"] = datetime.now()
        return tmp_dict

    def reset(self) -> None:
        """
        Resets all input counters to zero.

        What it does:
        - Clears all counts (e.g., key presses and mouse actions).
        - Keeps the time of the last activity for tracking purposes.

        Privacy Note:
        This method only clears numbers—nothing sensitive is stored.

        :return: None
        """
        with self.lock:
            self._count_char_key_pressed = 0
            self._count_direction_key_pressed = 0
            self._count_special_key_pressed = 0

            self._count_left_mouse_pressed = 0
            self._count_right_mouse_pressed = 0
            self._count_middle_mouse_pressed = 0
            self._count_mouse_scrolls = 0
            self._activity = False

    def add_to_db(self, window_id: int | None) -> None:
        """
        Saves the collected counts into the database.

        How it works:
        - Gathers all the tracked counts using `get_all`.
        - Sends this data to the database for safe storage.

        Privacy Note:
        Only numbers, like "total key presses," are saved. No personal or sensitive data is ever stored.

        :return: None
        """
        if self.activity:
            if window_id:
                DBHandler().add_input_log(window_id, self.get_all())
            else:
                self.reset()

    def add_input(self, user_input_type) -> None:
        """
        Adds a new action to the counters.

        How it works:
        - Takes a type of input (like "char_key" or "mouse_scroll").
        - Updates the right counter based on the type.

        Allowed input types:
        - "char_key": Character key pressed (like letters or numbers).
        - "direction_key": Arrow keys or other movement keys.
        - "special_key": Keys like Shift, Ctrl, or Alt.
        - "mouse_scroll": Mouse scroll action.
        - "left_mouse": Left mouse button click.
        - "right_mouse": Right mouse button click.
        - "middle_mouse": Middle mouse button click.

        Privacy Note:
        We ONLY count the type of action. No actual key names, text, or mouse positions are stored.

        :param user_input_type: str (Type of input to count.)
        :return: None
        """

        get_logger().debug("InputManager lock use")
        with self.lock:
            self._activity = True
            match user_input_type:
                case 'char_key':
                    self._count_char_key_pressed += 1

                case 'direction_key':
                    self._count_direction_key_pressed += 1

                case 'special_key':
                    self._count_special_key_pressed += 1

                case 'left_mouse':
                    self._count_left_mouse_pressed += 1

                case 'right_mouse':
                    self._count_right_mouse_pressed += 1

                case 'middle_mouse':
                    self._count_middle_mouse_pressed += 1

                case 'mouse_scroll':
                    current_datetime = datetime.now()
                    if self._last_mouse_scroll_datetime is not None \
                            and (current_datetime - self._last_mouse_scroll_datetime) >= timedelta(seconds=0.3):
                        self._count_mouse_scrolls += 1
                    self._last_mouse_scroll_datetime = current_datetime

                case _:
                    raise Exception(f'Unexpected input type: {user_input_type}')
        get_logger().debug("InputManager lock released")

    @property
    def activity(self):
        with self.lock:
            tmp = self._activity
        return tmp


# Key lists for different types we want to handle different
# Obvious directions and some keys that don't have the Key.char attribute, but should be counted as
# char / write keys.
direction_keys = [keyboard.Key.up, keyboard.Key.down, keyboard.Key.left, keyboard.Key.right]
other_write_keys = [keyboard.Key.space, keyboard.Key.enter, keyboard.Key.backspace, keyboard.Key.delete]
# TODO: maybe adding game keys ? WASD, space? esc?


def on_key_press(key) -> None | bool:
    """
    Tracks key presses from the keyboard.

    What it does:
    - Listens for keys pressed.
    - Counts them based on their type (e.g., "char_key" or "direction_key").

    Privacy Note:
    We only track the type of key pressed (e.g., "character key" or "special key").
    We NEVER save the actual key pressed or any text you type.

    :return: bool | None (Returns False only when the program is stopping; otherwise, None.)
    """

    if threads_are_stopped():
        get_logger().debug("on_key_press() stop event grabbed")
        return False

    if hasattr(key, 'char') and key.char is not None:
        InputManager().add_input("char_key")
    else:
        if key in direction_keys:
            InputManager().add_input("direction_key")
        elif key in other_write_keys:
            InputManager().add_input("char_key")
        else:
            InputManager().add_input("special_key")


def on_mouse_click(x, y, button, pressed) -> None | bool:
    """
    Tracks mouse clicks.

    What it does:
    - Listens for mouse button clicks.
    - Counts left, right, and middle button clicks separately.

    Privacy Note:
    We only track how many times each button is clicked. No information about where you click is saved.

    :return: bool | None (Returns False only when the program is stopping; otherwise, None.)
    """

    if threads_are_stopped():
        get_logger().debug("on_mouse_click() stop event grabbed")
        return False

    if pressed:
        if button == mouse.Button.left:
            InputManager().add_input("left_mouse")
        elif button == mouse.Button.right:
            InputManager().add_input("right_mouse")
        if button == mouse.Button.middle:
            InputManager().add_input("middle_mouse")


def on_mouse_scroll(x, y, dx, dy) -> None | bool:
    """
    Tracks mouse scroll actions.

    What it does:
    - Counts each scroll action (up or down).

    Privacy Note:
    We only track the scroll count, not where or how it was scrolled.

    :return: bool | None (Returns False only when the program is stopping; otherwise, None.)
    """

    if threads_are_stopped():
        get_logger().debug("on_mouse_scroll() stop event grabbed")
        return False
    InputManager().add_input("mouse_scroll")


def mouse_tracker() -> None:
    """
    Starts tracking mouse events (clicks and scrolls).
    Only checks 10 times per second, to reduce impact on the system.

    What it does:
    - Listens for clicks and scrolls in a separate thread.
    - Passes events to `on_mouse_click` and `on_mouse_scroll`.

    :return: None
    """

    with mouse.Listener(on_click=on_mouse_click, on_scroll=on_mouse_scroll) as listener:
        while not threads_are_stopped():
            sleep(0.1)
        listener.stop()
    get_logger().debug("mouse_tracker() end")


def keyboard_tracker() -> None:
    """
    Starts tracking keyboard events (key presses).

    What it does:
    - Listens for key presses in a separate thread.
    - Passes events to `on_key_press`.

    :return: None
    """

    with keyboard.Listener(on_press=on_key_press) as listener:
        while not threads_are_stopped():
            sleep(0.1)
        listener.stop()
    get_logger().debug("keyboard_tracker() end")


# # # # External call functions for less import in other files # # # #
def stop_done() -> bool:
    """
   Checks if all threads are stopped.

    What it does:
    - Waits for all threads (mouse, keyboard, writer) to finish.
    - Ensures no input is tracked after stopping.

    :return: bool (Returns True when all threads are stopped.)
    """

    global mouse_thread, keyboard_thread, input_writer_thread

    mouse_thread.join()
    keyboard_thread.join()
    return True


def start_input_tracker() -> None:
    """
    Starts input tracking by creating separate threads for mouse and keyboard events.

    What it does:
    - Creates threads for `mouse_tracker`, `keyboard_tracker`, and `input_writer`.
    - Starts tracking mouse clicks, scrolls, and key presses.

    :return: None
    """

    global mouse_thread, keyboard_thread
    mouse_thread = Thread(target=mouse_tracker)
    keyboard_thread = Thread(target=keyboard_tracker)

    mouse_thread.start()
    get_logger().debug("mouse_thread.start()")
    keyboard_thread.start()
    get_logger().debug("keyboard_thread.start()")


def input_to_db(window_id: int | None):
    InputManager().add_to_db(window_id)


def had_input():
    return InputManager().activity


if __name__ == "__main__":
    print("Please start with the main.py")


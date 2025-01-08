"""
This file is part of Viper Tracking.
It will have only the code that tracks input actions of the user.

I described every function, so even a non-programmer can understand it!
We don't track what you input and only count stuff for analyzes.

Author: sora7672
"""


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
input_writer_thread: Thread = None


class InputManager:
    """
    This class will handle the input grabbing of the program.
    It will only track inputs based on type, not which keys exactly got pushed.
    We also don't save any order.
    Mouse only click and scroll count.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._count_char_key_pressed = 0
            self._count_direction_key_pressed = 0
            self._count_special_key_pressed = 0

            self._count_left_mouse_pressed = 0
            self._count_right_mouse_pressed = 0
            self._count_middle_mouse_pressed = 0
            self._count_mouse_scrolls = 0

            self._last_mouse_scroll_datetime = None
            self._last_activity_datetime = None

            self.lock = Lock()
            InputManager._instance = self
            get_logger().debug("__init__ InputManager")

    def get_all(self) -> dict:
        """
        Creates a dictionary with all counters and last_activity_datetime.
        Resets the object back to its original state at the end.
        :return: dict ["last_activity_datetime", "count_key_pressed", "count_mouse_pressed "count_direction_key_pressed",
        "count_special_key_pressed", "count_char_key_pressed", "count_left_mouse_pressed", "count_right_mouse_pressed",
        "count_middle_mouse_pressed"]
        """
        get_logger().debug("InputManager lock use")
        with self.lock:
            tmp_dict: dict = {"last_activity_datetime": self._last_activity_datetime, "count_key_pressed": (
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
        Resets the input manager to its initial state.
        Except last activity datetime.
        :return: None
        """
        self._count_char_key_pressed = 0
        self._count_direction_key_pressed = 0
        self._count_special_key_pressed = 0

        self._count_left_mouse_pressed = 0
        self._count_right_mouse_pressed = 0
        self._count_middle_mouse_pressed = 0
        self._count_mouse_scrolls = 0

    def add_to_db(self) -> None:
        """
        Simple calls the add to DB function of the DB module
        for proper handling the data and easy changes.
        """
        DBHandler().add_input_log(self.get_all())

    def add_input(self, user_input_type) -> None:
        """
        Adds a new input for counting up.
        :param user_input_type: Allowed values ['char_key', 'direction_key', 'special_key', 'mouse_scroll', \n
        'left_mouse_press', 'right_mouse_press', 'middle_mouse_press', 'mouse_scroll']
        :return: None
        """
        get_logger().debug("InputManager lock use")
        with self.lock:
            self._last_activity_datetime = datetime.now()
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


# Key lists for different types we want to handle different
# Obvious directions and some keys that don't have the Key.char attribute, but should be counted as
# char / write keys.
direction_keys = [keyboard.Key.up, keyboard.Key.down, keyboard.Key.left, keyboard.Key.right]
other_write_keys = [keyboard.Key.space, keyboard.Key.enter, keyboard.Key.backspace, keyboard.Key.delete]
# TODO: maybe adding game keys ? WASD, space? esc?
#  TEST also what happens if you game and log! (holding WASD longer and such)


def on_key_press(key) -> None | bool:
    """
    Grabs the standard parameters from the event listener,
    but only calls the InputManagers add_input method (based on key type pressed)
    :return: Only false when thread closing got called, else None
    """
    if threads_are_stopped():
        get_logger().debug("on_key_press() stop event grabbed")
        return False

    # FOR PRIVACY CONCERNS:
    # As you see, we only sort this based on the key type that is pressed,
    # we don't log any key/char that is pressed!
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
    Grabs the standard parameters from the event listener,
    but only calls the InputManagers add_input method (based on click button)
    :return: Only false when thread closing got called, else None
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
    Grabs the standard parameter from the event listener,
    but only calls the InputManagers add_input method (without giving info on where the scroll happend)
    :return: Only false when thread closing got called, else None
    """
    if threads_are_stopped():
        get_logger().debug("on_mouse_scroll() stop event grabbed")
        return False
    InputManager().add_input("mouse_scroll")


def mouse_tracker() -> None:
    """ Used for starting the event listener in a thread
    Calls the on_mouse_click function every time a button of the mouse is pressed
    and the on_mouse_scroll function  every time the user scrolls
    Limited to 10 inputs per second.

    """
    with mouse.Listener(on_click=on_mouse_click, on_scroll=on_mouse_scroll) as listener:
        while not threads_are_stopped():
            sleep(0.1)
        listener.stop()
    get_logger().debug("mouse_tracker() end")


def keyboard_tracker() -> None:
    """ Used for starting the event listener in a thread
    Calls the on_key_press function every time a key is pressed on keyboard
    Limited to 10 inputs per second.
    """
    with keyboard.Listener(on_press=on_key_press) as listener:
        while not threads_are_stopped():
            sleep(0.1)
        listener.stop()
    get_logger().debug("keyboard_tracker() end")


def input_writer() -> None:
    """
    This function is for adding to the thread to run it properly.
    :return: None
    """

    while not threads_are_stopped():
        inter = interval_inputs()
        if inter % 5 != 0:
            raise Exception(f'Unexpected input interval! Needs to be multiple of 5: {inter}')
        fifth_timer = inter // 5
        for i in range(fifth_timer):
            sleep(5)
            if threads_are_stopped():
                break
        InputManager().add_to_db()
    get_logger().debug("input_writer() end")


# # # # External call functions for less import in other files # # # #
def stop_done() -> bool:
    """
    This function is called to stop the thread or better the input tracker.
    :return: None
    """
    global mouse_thread, keyboard_thread, input_writer_thread

    mouse_thread.join()
    keyboard_thread.join()
    input_writer_thread.join()
    return True


def start_input_tracker() -> None:
    """
    Starts the manager thread, which will listen to all key inputs and mouse clicks/scrolls.
    :return:
    """
    global mouse_thread, keyboard_thread, input_writer_thread
    mouse_thread = Thread(target=mouse_tracker)
    keyboard_thread = Thread(target=keyboard_tracker)
    input_writer_thread = Thread(target=input_writer)

    mouse_thread.start()
    get_logger().debug("mouse_thread.start()")
    keyboard_thread.start()
    get_logger().debug("keyboard_thread.start()")
    input_writer_thread.start()
    get_logger().debug("input_writer_thread.start()")


if __name__ == "__main__":
    print("Please start with the main.py")


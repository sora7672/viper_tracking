"""
This file is part of Viper Tracking.
It will have only the code that tracks inputs of the user.

I described every function, so even a not programmer can understand,
that we don't track what you input and only count stuff for analyzes.

"""


from threading import Thread, Event, Lock
from time import time, sleep
from pynput import mouse, keyboard

mouse_thread: Thread = None
keyboard_thread: Thread = None

class InputManager:
    """
    This class will handle the input grabbing of the program.
    It will only track inputs based on type, not which keys exactly and when.
    Mouse only click count.
    """
    _instance = None

    def __init__(self):
        if InputManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self._count_char_key_pressed = 0
            self._count_direction_key_pressed = 0
            self._count_special_key_pressed = 0

            self._count_left_mouse_pressed = 0
            self._count_right_mouse_pressed = 0
            self._count_middle_mouse_pressed = 0
            self._count_mouse_scrolls = 0

            self._last_mouse_scroll_timestamp = None
            self._last_activity_timestamp = None

            self.lock = Lock()
            InputManager._instance = self

    def get_all(self) -> dict:
        """
        Creates a dictionary with all counters and last timestamp.
        Resets the object back to its original state at the end.
        :return: dict ["last_timestamp", "count_key_pressed", "count_mouse_pressed "count_direction_key_pressed",
        "count_special_key_pressed", "count_char_key_pressed", "count_left_mouse_pressed", "count_right_mouse_pressed",
        "count_middle_mouse_pressed"]
        """
        with self.lock:
            tmp_dict: dict = {"last_timestamp": self._last_activity_timestamp, "count_key_pressed": (
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
            return tmp_dict

    def reset(self) -> None:
        """
        Resets the input manager to its initial state.
        Except last activity timestamp.
        :return: None
        """
        self._count_char_key_pressed = 0
        self._count_direction_key_pressed = 0
        self._count_special_key_pressed = 0

        self._count_left_mouse_pressed = 0
        self._count_right_mouse_pressed = 0
        self._count_middle_mouse_pressed = 0
        self._count_mouse_scrolls = 0


    @classmethod
    def get_instance(cls):
        """
        Returns the instance of the InputManager class.
        Only way to access it.
        :return:
        """
        if InputManager._instance is None:
            InputManager()
        return InputManager._instance

    def add_input(self, user_input_type) -> None:
        """
        Adds a new input for counting up.
        :param user_input_type: Allowed values ['char_key', 'direction_key', 'special_key', 'mouse_scroll', \n
        'left_mouse_press', 'right_mouse_press', 'middle_mouse_press', 'mouse_scroll']
        :return: None
        """
        with self.lock:
            self._last_activity_timestamp = time()
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
                    current_time = time()
                    if self._last_mouse_scroll_timestamp is not None \
                            and (current_time - self._last_mouse_scroll_timestamp) >= 0.3:
                        self._count_mouse_scrolls += 1
                    self._last_mouse_scroll_timestamp = current_time

                case _:
                    raise Exception(f'Unexpected input type: {user_input_type}')


# handler for stopping input readings
stop_event = Event()

# Key lists for different types we want to handle different
# Obvious directions and some keys that don't have the Key.char attribute, but should be counted as
# char / write keys.
direction_keys = [keyboard.Key.up, keyboard.Key.down, keyboard.Key.left, keyboard.Key.right]
other_write_keys = [keyboard.Key.space, keyboard.Key.enter, keyboard.Key.backspace, keyboard.Key.delete]


def on_key_press(key) -> None | bool:
    """
    Grabs the standard parameters from the event listener,
    but only calls the InputManagers add_input method (based on key type pressed)
    :return: Only false when thread closing got called, else None
    """
    if stop_event.is_set():
        return False

    # FOR PRIVACY CONCERNS:
    # As you see, we only sort this based on the key type that is pressed,
    # we don't log any key/char that is pressed!
    if hasattr(key, 'char') and key.char is not None:
        InputManager.get_instance().add_input("char_key")
    else:
        if key in direction_keys:
            InputManager.get_instance().add_input("direction_key")
        elif key in other_write_keys:
            InputManager.get_instance().add_input("char_key")
        else:
            InputManager.get_instance().add_input("special_key")


def on_mouse_click(x, y, button, pressed) -> None | bool:
    """
    Grabs the standard parameters from the event listener,
    but only calls the InputManagers add_input method (based on click button)
    :return: Only false when thread closing got called, else None
    """
    if stop_event.is_set():
        return False

    if pressed:
        if button == mouse.Button.left:
            InputManager.get_instance().add_input("left_mouse")
        elif button == mouse.Button.right:
            InputManager.get_instance().add_input("right_mouse")
        if button == mouse.Button.middle:
            InputManager.get_instance().add_input("middle_mouse")


def on_mouse_scroll(x, y, dx, dy) -> None | bool:
    """
    Grabs the standard parameter from the event listener,
    but only calls the InputManagers add_input method (without giving info on where the scroll happend)
    :return: Only false when thread closing got called, else None
    """
    if stop_event.is_set():
        return False
    InputManager.get_instance().add_input("mouse_scroll")


def start_mouse_listener() -> None:
    """ Used for starting the event listener in a thread
    Calls the on_mouse_click function every time a button of the mouse is pressed
    and the on_mouse_scroll function  every time the user scrolls

    """
    with mouse.Listener(on_click=on_mouse_click, on_scroll=on_mouse_scroll) as listener:
        while not stop_event.is_set():
            sleep(0.1)
        listener.stop()


def start_keyboard_listener() -> None:
    """ Used for starting the event listener in a thread
    Calls the on_key_press function every time a key is pressed on keyboard
    """
    with keyboard.Listener(on_press=on_key_press) as listener:
        while not stop_event.is_set():
            sleep(0.1)
        listener.stop()


def stop() -> None:
    """
    This function is called to stop the thread or better the input tracker.
    :return: None
    """
    global keyboard_thread
    global mouse_thread
    stop_event.set()

    mouse_thread.join()
    keyboard_thread.join()


def start() -> None:
    """
    Starts the manager thread, which will listen to all key inputs and mouse clicks/scrolls.
    :return:
    """
    global mouse_thread
    mouse_thread = Thread(target=start_mouse_listener)
    mouse_thread.start()
    global keyboard_thread
    keyboard_thread = Thread(target=start_keyboard_listener)
    keyboard_thread.start()


if __name__ == "__main__":
    print("Please start with the main.py")


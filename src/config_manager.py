"""
This file includes a singleton class to manage all application configurations.

It handles:
- Reading and saving configurations to a JSON file.
- Providing thread-safe access to configuration settings.
- Managing debug mode and application intervals.

Author: sora7672
"""
__author__ = 'sora7672'

from threading import Lock, Event
import json
from warnings import warn
from os import path

"""
Project Note:
This file needs to never load other project modules!
"""

# TODO: Probably when smth here is updated, the other threads need to
#  read in infos new (like interval for input/window tracker)
#  Make sure intervals are allways a multiple of 5! cuz checking regularly on


# TODO: refactor this to a property setup instead of weird method names.
#  make booleans smarter to read
#  make config path absolute with OS path

class ConfigManager:
    """
    A thread-safe singleton class that manages configuration settings for the application.

    This class provides:
    - Methods to read/write settings to a JSON file.
    - Access to application-specific configurations like debug mode and intervals.

    Attributes:
        _lock (Lock): Ensures thread-safe access to configurations.
        _stop_event (Event): Signals thread termination.
        _config_path (str): Path to the configuration file.
        _interval_save_windows (int): Interval for saving window logs.
        _interval_save_inputs (int): Interval for saving input logs.
        _debug (bool): Debug mode status.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Implements the singleton pattern by ensuring only one instance of the class exists.

        :return: ConfigManager (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        Initializes the ConfigManager instance with default settings.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._lock = Lock()
            self._stop_event = Event()
            self._config_path = "config.json"
            self._interval_save_windows = 5
            self._interval_save_inputs = 30
            self._debug = False

    def read_settings(self) -> None:
        """
        Loads the application configuration from a JSON file.

        If the file is missing, empty, or contains invalid JSON, default settings are applied.
        Missing fields in the configuration are also replaced with default values.

        :return: None
        """

        unlock_and_save = False
        with self._lock:
            if path.exists(self._config_path):
                with open(self._config_path, 'r') as file:
                    content = file.read().strip()
                    if content == "":
                        warn(f"The file {self._config_path} is empty. Loading default settings.")
                    else:
                        try:
                            tmp = json.loads(content)
                        except json.JSONDecodeError:
                            warn(f"The file {self._config_path} contains invalid JSON. Loading default settings.")
                            unlock_and_save = True
                        finally:
                            if "interval_save_windows" in tmp:
                                self._interval_save_windows = tmp["interval_save_windows"]
                            else:
                                unlock_and_save = True
                            if "interval_save_inputs" in tmp:
                                self._interval_save_inputs = tmp["interval_save_inputs"]
                            else:
                                unlock_and_save = True
                            if "debug" in tmp:
                                self._debug = tmp["debug"]
                            else:
                                unlock_and_save = True
            else:
                warn(f"The file {self._config_path} does not exist. Loading default settings.")
                unlock_and_save = True
        if unlock_and_save:
            self.save_settings()

    def save_settings(self) -> None:
        """
        Saves the current configuration settings to a JSON file.

        :return: None
        """

        with self._lock:
            dict_to_save = {"interval_save_windows": self._interval_save_windows,
                            "interval_save_inputs": self._interval_save_inputs,
                            "debug": self._debug
                            }
            with open(self._config_path, 'w') as json_file:
                # dump with extra params makes it better readable
                json.dump(dict_to_save, json_file, indent=4, sort_keys=True)

    def get_interval_save_inputs(self) -> int:
        """
        Returns the interval for saving input logs.

        :return: int (The interval in seconds.)
        """

        with self._lock:
            return self._interval_save_inputs

    def get_interval_save_windows(self) -> int:
        """
        Returns the interval for saving window logs.

        :return: int (The interval in seconds.)
        """

        with self._lock:
            return self._interval_save_windows

    def enable_debug(self) -> None:
        """
        Enables debug mode for the application.

        :return: None
        """

        # TODO: Probably needs to restart the logger
        with self._lock:
            self._debug = True

    def disable_debug(self) -> None:
        """
        Disables debug mode for the application.

        :return: None
        """

        # TODO: Probably needs to restart the logger
        with self._lock:
            self._debug = False

    def get_debug(self) -> bool:
        """
        Checks if debug mode is enabled.

        :return: bool (True if debug mode is enabled, False otherwise.)
        """

        return self._debug

    def threads_are_stopped(self) -> bool:
        """
        Checks if the thread stop event is set.

        :return: bool (True if threads are stopped, False otherwise.)
        """

        with self._lock:
            return self._stop_event.is_set()

    def stop_threads(self) -> None:
        """
        Sets the thread stop event.
        """
        with self._lock:
            self._stop_event.set()


# # # # External call functions for less import in other files # # # #
def stop_program_threads() -> None:
    """
    Stops all threads gracefully by setting the thread stop event.

    This function signals all threads to stop and allows for a clean shutdown.

    :return: None
    """

    ConfigManager().stop_threads()


def threads_are_stopped() -> bool:
    """
    Checks if all threads have been stopped.

    :return: bool (True if threads are stopped, False otherwise.)
    """

    return ConfigManager().threads_are_stopped()


def interval_windows() -> int:
    """
    Retrieves the interval for saving window logs from the configuration manager.

    :return: int (The interval in seconds.)
    """

    return ConfigManager().get_interval_save_windows()


def interval_inputs() -> int:
    """
    Retrieves the interval for saving input logs from the configuration manager.

    :return: int (The interval in seconds.)
    """

    return ConfigManager().get_interval_save_inputs()


def is_debug() -> bool:
    """
    Checks if the application is running in debug mode.

    :return: bool (True if debug mode is enabled, False otherwise.)
    """

    return ConfigManager().get_debug()


def initialize_config_manager():
    """
    Initializes the configuration manager by reading the settings file.

    This ensures that the configuration manager is ready before other modules use it.

    :return: None
    """

    ConfigManager().read_settings()


# TODO: Used when settings are updated, dont need to save in the end of program then
def save_settings():
    """
    Saves the current configuration settings to the JSON file.

    :return: None
    """

    ConfigManager().save_settings()


if __name__ == "__main__":
    print("Please start with the main.py")



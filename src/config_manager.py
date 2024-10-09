"""
This file includes a singleton class that holds all configs for all other files.
Its sole purpose is to manage configs for the application.
It will NOT import from other project modules, except non project modules like reader/csv/time.
Author: sora7672
"""


from threading import Lock, Event
import json
from warnings import warn
from os import path

# TODO: Probably when smth here is updated, the other threads need to
#  read in infos new (like interval for input/window tracker)
#  Make sure intervals are allways a multiple of 5! cuz checking regularly on


class ConfigManager:
    """
    This class will hold all settings related to a project.
    Including window/gui settings, intervals for checks
    and the access to the stop event for the application
    Need to be initialized
    """
    _instance = None

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._lock = Lock()
            self._stop_event = Event()
            self._config_path = "config.json"
            self._interval_save_windows = 5
            self._interval_save_inputs = 30
            self._debug = False

    def read_settings(self):
        """
        THis will load the settings from a json file
        into the singleton instance.
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

    def save_settings(self):
        """
        Saves the settings to the json file.
        """
        with self._lock:
            dict_to_save = {"interval_save_windows": self._interval_save_windows,
                            "interval_save_inputs": self._interval_save_inputs,
                            "debug": self._debug
                            }
            with open(self._config_path, 'w') as json_file:
                # dump with extra params makes it better readable
                json.dump(dict_to_save, json_file, indent=4, sort_keys=True)

    def get_interval_save_inputs(self):
        """
        Just returns the interval_save_inputs
        """
        with self._lock:
            return self._interval_save_inputs

    def get_interval_save_windows(self):
        """
        Just returns the interval_save_windows
        """
        with self._lock:
            return self._interval_save_windows

    def enable_debug(self):
        """
        Enable Debug Mode in the whole application.
        """
        # TODO: Probably needs to restart the logger
        with self._lock:
            self._debug = True

    def disable_debug(self):
        """
        Disable Debug Mode in the whole application.
        """
        # TODO: Probably needs to restart the logger
        with self._lock:
            self._debug = False

    def get_debug(self) -> bool:
        """
        Just returns if debug mode is on
        """
        return self._debug

    def threads_are_stopped(self):
        """
        Checks if the thread stop event is set.
        """
        with self._lock:
            return self._stop_event.is_set()

    def stop_threads(self):
        """
        Sets the thread stop event.
        """
        with self._lock:
            self._stop_event.set()


# # # # External call functions for less import in other files # # # #
def stop_program_threads():
    """
    Stopping all threads on call.
    Takes a few seconds to close all threads gracefully.
    """
    ConfigManager().stop_threads()


def threads_are_stopped() -> bool:
    """
    Checks if the thread stop event is set.
    """
    return ConfigManager().threads_are_stopped()


def interval_windows() -> int:
    """
    Returns the set interval in seconds for saving windows to log.
    """
    return ConfigManager().get_interval_save_windows()


def interval_inputs() -> int:
    """
    Returns the set interval in seconds for saving windows to log.
    """
    return ConfigManager().get_interval_save_inputs()


def is_debug() -> bool:
    """
    Returns if debug is enabled.
    """
    return ConfigManager().get_debug()


def initialize_config_manager():
    """
    Needs to be called before using the ConfigManager class.
    It starts all necessary things for the manager.
    """
    ConfigManager().read_settings()


# TODO: Used when settings are updated, dont need to save in the end of program then
def save_settings():
    """
    Saves the settings to the json file.
    """
    ConfigManager().save_settings()


if __name__ == "__main__":
    print("Please start with the main.py")



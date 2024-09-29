"""
This file will include a singleton that holds all configs for all other files.
It will NOT import from other modules, except non project modules like reader/csv/time
"""


from threading import Lock, Thread, Event
import json
from warnings import warn
from os import path

# TODO: Probably when smth here is updated, the other threads need to
#  read in infos new (like interval for input/window tracker)
#  Make sure intervals are allways a multiple of 5! cuz checking regularly on


_config_path = "config.json"

class ConfigManager:
    """
    This class will hold all settings related to a project.
    Including window/gui settings, intervals for checks
    and the access to the stop event for the application
    Need to be initialized"""
    _instance = None
    _lock = Lock()
    _stop_event = Event()

    def __init__(self):
        if ConfigManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            ConfigManager._instance = self
            self._interval_save_windows = 5
            self._interval_save_inputs = 30
            self._debug = False

    def read_settings(self):
        unlock_and_save = False
        with ConfigManager._lock:
            global _config_path
            if path.exists(_config_path):
                with open(_config_path, 'r') as file:
                    content = file.read().strip()
                    if content == "":
                        warn(f"The file {_config_path} is empty. Loading default settings.")
                    else:
                        try:
                            tmp = json.loads(content)
                        except json.JSONDecodeError:
                            warn(f"The file {_config_path} contains invalid JSON. Loading default settings.")
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
                warn(f"The file {_config_path} does not exist. Loading default settings.")
                unlock_and_save = True
        if unlock_and_save:
            self.save_settings()
            # manual setting values we need (if there was some manual tinkering its not set)


    def save_settings(self):
        with ConfigManager._lock:
            global _config_path
            dict_to_save = {"interval_save_windows": self._interval_save_windows,
                            "interval_save_inputs": self._interval_save_inputs,
                            "debug": self._debug
                            }
            with open(_config_path, 'w') as json_file:
                # dump with extra params makes it better readable
                json.dump(dict_to_save, json_file, indent=4, sort_keys=True)

    def get_interval_save_inputs(self):
        with ConfigManager._lock:
            return self._interval_save_inputs

    def get_interval_save_windows(self):
        with ConfigManager._lock:
            return self._interval_save_windows

    def enable_debug(self):
        with ConfigManager._lock:
            self._debug = True

    def disable_debug(self):
        with ConfigManager._lock:
            self._debug = False

    def get_debug(self):
        return self._debug

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls()
            return cls._instance

    @classmethod
    def threads_are_stopped(cls):
        with cls._lock:
            return cls._stop_event.is_set()

    @classmethod
    def stop_threads(cls):
        with cls._lock:
            cls._stop_event.set()


# # # # External call functions for less import in other files # # # #
def stop_program_threads():
    ConfigManager.stop_threads()


def threads_are_stopped() -> bool:
    return ConfigManager.threads_are_stopped()


def interval_windows():
    return ConfigManager.get_instance().get_interval_save_windows()


def interval_inputs():
    return ConfigManager.get_instance().get_interval_save_inputs()

def is_debug():
    return ConfigManager.get_instance().get_debug()

def initialize_config_manager():
    ConfigManager.get_instance().read_settings()
    ConfigManager.get_instance().enable_debug()
    print(is_debug())


# TODO: Used when settings are updated, dont need to save in the end of program then
def save_settings():
    ConfigManager.get_instance().save_settings()






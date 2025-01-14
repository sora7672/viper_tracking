"""
This file includes a singleton class for managing user-configurable settings.

Features:
- Dynamically handles new or existing settings.
- Saves and loads settings from a JSON file.
- Provides thread-safe access to settings.

Author: sora7672
"""
__author__ = 'sora7672'

from threading import Lock
import json
from os import path, makedirs
import inspect
"""
Project Note:
This file needs to never load other project modules!
"""


class AttributeTypeError(Exception):
    """
    Exception raised when an attribute is set to an invalid type in user settings.

    This exception is used to handle cases where a type mismatch occurs during
    attribute assignment, ensuring that only valid types are accepted.
    """
    def __init__(self, message: str = None, error_code=None, needed_type=None, received_type=None):
        """
        Initializes the `AttributeTypeError` exception with details about the type mismatch.

        This method constructs a detailed error message that includes the expected type
        (`needed_type`) and the actual type provided (`received_type`). Additionally,
        it allows for a custom error message or error code to be specified.

        :param message: str (Custom error message. If not provided, a default message is generated
            using the `needed_type` and `received_type`.)
        :param error_code: Any (Optional error code associated with the type error.)
        :param needed_type: type (The expected type for the attribute.)
        :param received_type: type (The type of the value provided, which caused the error.)
        :return: None
        """

        message = message or f"Type Error on setting attribute: {needed_type} != {received_type}"
        super().__init__(message)
        self.error_code = error_code


class UserSettingsManager:
    """
    A thread-safe singleton class for managing user-specific settings.

    Features:
    - Dynamic addition and removal of settings.
    - Automatic handling of attributes as properties.
    - JSON-based persistence for saving and loading settings.

    Attributes in this class are dynamically loaded from a JSON file, meaning the
    available attributes can vary based on the file content. This design ensures
    flexibility and makes the settings easily expandable for future use cases.
    """

    _instance = None
    _ignored_attributes = ["_initialized", "_settings_path", "_settings_file_name", "_settings_file_path", "_lock"]

    def __new__(cls, *args, **kwargs):
        """
        Implements the singleton pattern by ensuring only one instance of the class exists.

        :return: UserSettingsManager (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the `UserSettingsManager` singleton.

        This method sets up the base attributes for managing user-specific settings,
        including paths for saving/loading settings, thread safety mechanisms, and
        default project-specific attributes.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            # Base Attributes
            self._initialized = True
            self._settings_path = path.abspath(path.join(path.dirname(__file__), '..'))
            self._settings_file_name = "user_settings.json"
            self._settings_file_path = path.join(self._settings_path, self._settings_file_name)
            self._lock = Lock()

            # Project specific attributes
            # Set base values here
            self._gui_theme = "darkly"
            self._gui_resolution: list[int] = [800, 600]

    def init_all_properties(self):
        """
        Initializes all attributes of the class as properties for dynamic access.

        :return: None
        """

        for ky, vl in self.get_attributes_as_dict().items():
            self.init_property(ky, vl)

    def init_property(self, property_name, property_default_value):
        """
        Initializes an individual attribute as a property with a getter and setter.

        :param property_name: str (The name of the property.)
        :param property_default_value: Any (The default value for the property.)
        :return: None
        """

        # TODO: new personal exception/error class for setter !
        # FIXME: seems like lists are not given properly or better tuples (maybe sets/frozenset too)
        #  Because of getting
        if property_name[0] == "_":
            property_name = property_name[1:]
        elif property_name[0:2] == "__":
            property_name = property_name[2:]
        elif property_name in UserSettingsManager._ignored_attributes:
            return
        property_type = type(property_default_value)

        # TODO: Check if the functions below can be optimized to use not self, no shadowing
        def getter(self):
            """
            Placeholder for getter methods. Can return any type of attribute
            """
            with self._lock:
                return getattr(self, f"_{property_name}")

        def setter(self, value) -> None:
            """
            Placeholder for setter methods.
            Also checks if the value is the proper parameter type.
            """
            with self._lock:
                if isinstance(value, property_type):
                    setattr(self, f"_{property_name}", value)
                else:
                    raise AttributeTypeError(needed_type=property_type, received_type=type(value))

        setattr(self.__class__, property_name, property(getter, setter))
        setattr(self, f"_{property_name}", getattr(self, property_name))

    def check_path(self) -> bool:
        """
        Checks if the settings path and file exist, creating them if necessary.

        :return: bool (True if the settings file exists, False otherwise.)
        """

        if not path.exists(self._settings_path):
            makedirs(self._settings_path)
        if not path.isfile(self._settings_file_path):
            open(self._settings_file_path, 'w').close()
            return False
        return True

    def get_attributes_as_dict(self) -> dict:
        """
        Converts all class attributes into a dictionary for saving purposes.

        :return: dict (A dictionary of all attributes.)
        """

        attributes_dict = {}
        with self._lock:
            for attr_name, attr_value in self.__dict__.items():
                if attr_name in UserSettingsManager._ignored_attributes:
                    continue
                else:
                    attributes_dict[attr_name] = attr_value
        return attributes_dict

    def set_attributes_from_dict(self, attributes_dict) -> None:
        """
        Sets attributes based on a provided dictionary.

        This method handles both private (`_attr`) and protected (`__attr`) attributes,
        ensuring compatibility with the class structure.

        :param attributes_dict: dict (The dictionary containing attribute names and values.)
        :return: None
        """

        with self._lock:
            for attr_name, attr_value in attributes_dict.items():
                if attr_name in UserSettingsManager._ignored_attributes:
                    continue
                else:
                    setattr(self, attr_name, attr_value)

    def save_broken_file(self) -> None:
        """
        Saves a backup of a broken settings file for debugging or logging purposes.

        This method ensures that even if the settings file cannot be read properly,
        its contents are preserved for later analysis.
        WIP
        :return: None
        """

        # TODO: if file is broken save it for logs
        print("save broken file")
        pass

    def read_settings(self) -> None:
        """
        Loads settings from a JSON file into the class instance.

        :return: None
        """

        if not self.check_path():
            self.save_settings()
            return

        with open(self._settings_file_path, 'r') as file:
            content = file.read().strip()

        if content == "":
            self.save_settings()
            return

        try:
            tmp_json = json.loads(content)
            self.set_attributes_from_dict(tmp_json)
        except json.JSONDecodeError:
            self.save_broken_file()
            self.save_settings()

    def save_settings(self) -> None:
        """
        Saves the current settings to a JSON file.

        :return: None
        """

        self.check_path()
        write_dict = self.get_attributes_as_dict()
        with self._lock:
            try:
                with open(self._settings_file_path, 'w') as json_file:
                    json.dump(write_dict, json_file, indent=4, sort_keys=True)
            except IOError as e:
                print(f"Error saving settings: {e}")

    def print_all_properties(self) -> None:
        """
        Prints all attributes and properties of the instance.
        Important, because the attributes and properties are dynamic.
        :return: None
        """

        properties = {name: getattr(self, name) for name, obj in inspect.getmembers(type(self))
                      if isinstance(obj, property)}

        print("All instance attributes and properties:", properties)


# # # # External call functions for less import in other files # # # #

def init_user_settings():
    """
    Initializes user settings by reading the settings file and setting up all properties.

    :return: None
    """

    UserSettingsManager().read_settings()
    UserSettingsManager().init_all_properties()


if __name__ == "__main__":
    print("Please start with the main.py")



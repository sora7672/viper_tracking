"""
This file includes a singleton class that holds all configs that the user can change.
Its dynamically designed, so you can easy add new settings or delete old ones you dont need.
It will NOT import from other project modules, except non project modules like reader/csv/time.
Author: sora7672
"""


from threading import Lock
import json
from os import path, makedirs
import inspect



class UserSettingsManager:
    """

    """
    _instance = None
    _ignored_attributes = ["_initialized", "_settings_path", "_settings_file_name", "_settings_file_path", "_lock"]

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            # Base Attributes
            self._initialized = True
            self._settings_path = path.abspath(path.join(path.dirname(__file__), '..'))
            self._settings_file_name = "user_settings.json"
            self._settings_file_path = path.join(self._settings_path, self._settings_file_name)
            self._lock = Lock()

            # Project specific attributes
            # Set base values here
            #self._gui_theme = "darkly"
            self._gui_resolution: list[int] = [800, 600]


    def init_all_properties(self):
        for ky, vl in self.get_attributes_as_dict().items():
            self.init_property(ky, vl)


    def init_property(self, property_name, property_default_value):
        # TODO: new personal exception/error class for setter !
        # FIXME: seems like lists are not given properly or better tuples (maybe sets/frozenset too)
        #  Because of getting
        if property_name[0] == "_":
            property_name = property_name[1:]
        elif property_name[0:2] == "__":
            property_name = property_name[2:]
        elif property_name in self._ignored_attributes:
            return
        property_type = type(property_default_value)

        def getter(self):
            with self._lock:
                return getattr(self, f"_{property_name}")

        def setter(self, value):
            with self._lock:
                if isinstance(value, property_type):
                    setattr(self, f"_{property_name}", value)
                else:
                    raise Exception(f"Property value must be of type {property_type}")


        setattr(self.__class__, property_name, property(getter, setter))
        setattr(self, f"_{property_name}", getattr(self, property_name))


    def check_path(self):
        if not path.exists(self._settings_path):
            makedirs(self._settings_path)
        if not path.isfile(self._settings_file_path):
            open(self._settings_file_path, 'w').close()
            return False
        return True

    def get_attributes_as_dict(self):
        attributes_dict = {}
        with self._lock:
            for attr_name, attr_value in self.__dict__.items():
                if attr_name in UserSettingsManager._ignored_attributes:
                    continue
                else:
                    attributes_dict[attr_name] = attr_value
        return attributes_dict

    def set_attributes_from_dict(self, attributes_dict):
        with self._lock:
            for attr_name, attr_value in attributes_dict.items():
                if attr_name in UserSettingsManager._ignored_attributes:
                    continue
                else:
                    setattr(self, attr_name, attr_value)


    def save_broken_file(self):
        # TODO: if file is broken save it for logs
        print("save broken file")
        pass

    def read_settings(self):
        """
        Loads settings from a JSON file into the singleton instance.
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

    def save_settings(self):
        """
        Saves the settings to the JSON file.
        """

        self.check_path()
        write_dict = self.get_attributes_as_dict()
        with self._lock:
            try:
                with open(self._settings_file_path, 'w') as json_file:
                    json.dump(write_dict, json_file, indent=4, sort_keys=True)
            except IOError as e:
                print(f"Error saving settings: {e}")

    def print_all_properties(self):
        """
        Prints all attributes and properties of the instance, excluding callables.
        """

        properties = {name: getattr(self, name) for name, obj in inspect.getmembers(type(self))
                      if isinstance(obj, property)}

        print("All instance attributes and properties:", properties)


# # # # External call functions for less import in other files # # # #

def init_user_settings():
    UserSettingsManager().read_settings()
    UserSettingsManager().init_all_properties()


if __name__ == "__main__":
    print("Please start with the main.py")



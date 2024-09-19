

from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from random import randint
from window_tracker import Label
from threading import Thread, Event, Lock
from tray_helper import sys_add_label, sys_cancel
from gui_handler import open_gui

# TODO:
#  get icon for viper tracking
#  menu should include:
#  Manual Labels -> Every label thats manual -> should include activate (if turned off) and deactivate (when its on)
#  + New label, which will create a new label and directly activate it (use ttkb win)
#  Open App (like opening the main gui)
#  Exit app (turning it off)


class MultiFunction:
    def __init__(self, *functions):
        self.functions = functions

    def __call__(self, *args):
        for func in self.functions:
            func()  # Call each function in sequence


class SystemTrayManager:
    _instance = None
    def __init__(self):
        if SystemTrayManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.icon = Icon("Viper Tracking", tmp_image())  # TODO: replace with image
            self.lock = Lock()
            self.menu = None
            SystemTrayManager._instance = self

    def start_systray(self):
        self.icon.run()

    def stop_systray(self):
        self.icon.stop()



    def update_menu(self):
        self.icon.menu = Menu(self._label_menu(),
                         MenuItem ("Open GUI", open_gui),  # TODO: Add right call for GUI opening
                         MenuItem("Exit Viper Tracking", self.stop_systray))
        self.icon.update_menu()

    def _label_menu(self):
        all_label = Label.get_all_labels()
        menu_labels = []
        for label in all_label:
            if label.manually:

                disable_action = MultiFunction(label.disable, self.update_menu)
                enable_action = MultiFunction(label.enable, self.update_menu)

                menu_labels.append(MenuItem(label.name, Menu(
                    MenuItem("Activate", enable_action, visible=not label.is_active),
                    MenuItem("Deactivate", disable_action, visible=label.is_active)
                )))
        menu_labels.append(MenuItem("Add & start new Label", self.add_new_label))

        tmp_menu = MenuItem("Manual Labels", Menu(*menu_labels))
        return tmp_menu

    def add_new_label(self):
        sys_add_label()


    @classmethod
    def get_instance(cls):
        """
        Returns the instance of the InputManager class.
        Only way to access it.
        :return:
        """
        if cls._instance is None:
            cls()
        return cls._instance




# Function to create an image for the tray icon , just temporary till icon is created :D
def tmp_image():
    # Create a basic image with two colors

    image = Image.new('RGB', (64, 64), "green")
    draw = ImageDraw.Draw(image)
    draw.rectangle((32, 0, 64, 32), fill="purple")
    draw.rectangle((0, 32, 32, 64), fill="purple")
    return image


def start():
    # TODO: Remove!
    ### tmp ###
    # for num in range(1, 6):
    #     Label(f"Label ({randint(0, 100)})", manually=True)
    # Label(f"Label automatically", manually=False)
    #######

    SystemTrayManager.get_instance().update_menu()
    SystemTrayManager.get_instance().start_systray()




if __name__ == "__main__":
    print("Please start with the main.py")


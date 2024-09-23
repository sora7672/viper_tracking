

from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from random import randint
from threading import Thread, Event, Lock

from window_tracker import Label
from gui_handler import GuiHandler



class MultiFunction:
    def __init__(self, *functions):
        self.functions = functions

    # Call each function in sequence
    def __call__(self, *args):
        for func in self.functions:
            func()


class SystemTrayManager:
    _instance = None
    def __init__(self):
        if SystemTrayManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.icon = Icon("Viper Tracking", Image.open("viper_tray.ico"))
            self.lock = Lock()
            self.menu = None
            SystemTrayManager._instance = self

    def start_systray(self):
        self.icon.run_detached()

    def stop_systray(self):
        self.icon.stop()
        GuiHandler.get_instance().stop()



    def update_menu(self):
        self.icon.menu = Menu(self._label_menu(),
                              MenuItem("Open GUI", lambda: GuiHandler.get_instance().main_window()),
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
        menu_labels.append(MenuItem("Add & start new Label", lambda: GuiHandler.get_instance().sys_tray_manual_label()))

        tmp_menu = MenuItem("Manual Labels", Menu(*menu_labels))
        return tmp_menu



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
    # Will get an async error if tested alone, because GUI is not initiated
    start()
    print("Please start with the main.py")




from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from random import randint

from config_manager import stop_program_threads

from input_tracker import stop_done as input_stop_done
from window_tracker import Label, update_all_labels_to_db, stop_done as win_stop_done
from gui_handler import sys_tray_manual_label, open_main_gui, stop_gui
from db_connector import close_db_connection
import threading


class MultiFunction:
    def __init__(self, *functions):
        self.functions = functions

    # Call each function in sequence
    def __call__(self, *args):
        for func in self.functions:
            func()


class SystemTrayManager:
    """
    Does not need to be thread safe, because it runs detached adn will be closed by itself
    """
    _instance = None

    def __init__(self):
        if SystemTrayManager._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.icon = Icon("Viper Tracking", Image.open("src/viper_tray.ico"))
            self.menu = None
            SystemTrayManager._instance = self

    def start_systray(self):
        self.update_menu()
        self.icon.run_detached()


    def stop_program(self):
        """
        This methode is the most important after the program start.
        It handles all that needs to be done when the program gets closed.
        maybe the GUI can call it also, thats why tehre is a import/export function.

        :return:
        """
        # FIXME: Still not closing properly! Threads started without daemon properly?
        stop_program_threads()
        # wait for threads to be done
        if input_stop_done():
            print("Input threads finished")
        if win_stop_done():
            print("Window thread finished")

        stop_gui()
        print("gui finished")

        update_all_labels_to_db()
        print("Labels updated to db")
        close_db_connection()
        print("Db connection closed")
        self.icon.stop()
        print("Icon stopped")
        for th in threading.enumerate():
            print(th)


    def update_menu(self):
        self.icon.menu = Menu(self._label_menu(),
                              MenuItem("Open GUI", open_main_gui),
                              MenuItem("Exit Viper Tracking", self.stop_program))
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

        menu_labels.append(MenuItem("Add & start new Label", sys_tray_manual_label))

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


def start_systray_icon():
    # TODO: Remove!
    ### tmp ###
    # for num in range(1, 6):
    #     Label(f"Label ({randint(0, 100)})", manually=True)
    # Label(f"Label automatically", manually=False)
    #######
    SystemTrayManager.get_instance().start_systray()


# # # # External call functions for less import in other files # # # #

def stop_program():
    SystemTrayManager.get_instance().stop_program()


if __name__ == "__main__":
    # Will get an async error if tested alone, because GUI is not initiated
    print("Please start with the main.py")


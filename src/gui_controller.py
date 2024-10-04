
import ttkbootstrap as tb
from tkinter import Toplevel
from ttkbootstrap import Window
from threading import Thread, Lock, Event
from PIL import Image, ImageTk
from os import path
from log_handler import get_logger



class GuiController:
    """ Does not need to be trhead safe, because it will allways run in mainthread in the background.
    Last thread to start and last to stop then we  have no race conditions."""
    _instance = None

    def __init__(self):
        if GuiController._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            GuiController._instance = self
            self.root = tb.Window()
            self.root.title('Invisible Window(If you see me report me!)')
            # FIXME: Image not working!!

            tmp = Image.open('src/viper_tray.ico')  # TODO: get a better image
            self.window_icon = ImageTk.PhotoImage(tmp)
            self.root.iconphoto = self.window_icon

            self.root.withdraw()
            self.lock = Lock()
            get_logger().debug("__init__ from GuiHandler")

    def run(self):
        self.root.mainloop()
    def stop_helper(self):
        # helper to properly call the stop when called form the systray
        # otherwise you cant exit the mainloop properly! (it needs to be called form inside with .after)
        self.root.after(100, self.stop)

    def stop(self):
        # destroy child windows and then stop the mainloop for not having dead thread elements in cache
        # or other bugs. Last to be called in a closing order.
        get_logger().debug("methode stop from GuiHandler start")
        childs = self.root.winfo_children()
        for chil in childs:
            chil.destroy()
        get_logger().debug("destroyed all childs from GuiHandler")
        self.root.quit()
        get_logger().debug("after root.quit")



        get_logger().debug("methode stop from GuiHandler end")

        # FIXME: shows only if quit is used, if destroy is used we wont see this

    def sys_tray_manual_label(self):
        get_logger().debug("sys_tray_manual_label start")
        win_width = 300
        win_height = 130
        taskbar_height = 70
        sys_tray_add_lbl_win = Toplevel(self.root)
        sys_tray_add_lbl_win.withdraw()

        sys_tray_add_lbl_win.title('Sys Tray Add Label')
        sys_tray_add_lbl_win.iconphoto = self.window_icon
        s_width = sys_tray_add_lbl_win.winfo_screenwidth()
        s_height = sys_tray_add_lbl_win.winfo_screenheight()
        sys_tray_add_lbl_win.geometry(f"{win_width}x{win_height}+{s_width - win_width}+"
                                      f"{s_height - win_height - taskbar_height}")
        sys_tray_add_lbl_win.resizable(width=False, height=False)
        sys_tray_add_lbl_win.attributes('-toolwindow', True)
        sys_tray_add_lbl_win.attributes('-topmost', True)
        sys_tray_add_lbl_win.overrideredirect(True)

        sys_tray_add_lbl_win.grid_rowconfigure(0, weight=1)
        sys_tray_add_lbl_win.grid_columnconfigure(0, weight=1)
        sys_tray_add_lbl_win.attributes('-alpha', 0.7)
        # TODO: Maybe change to transparent background and give widgets a non transparent image,
        #  so it looks like widgets "fly" on the screen

        title_text = tb.Label(sys_tray_add_lbl_win, text="Choose a label name:", font=("Helvetica", 12))
        label_name = tb.Entry(sys_tray_add_lbl_win, width=40)
        # TODO: Add enter & tab functionality, fast saving new tab without much clicking
        add_btn = tb.Button(sys_tray_add_lbl_win, text="Add & Start",
                            command=lambda wind=sys_tray_add_lbl_win, lbl_name=label_name: sys_add(wind, lbl_name))
        cancel_btn = tb.Button(sys_tray_add_lbl_win, text="Cancel",
                               command=lambda wind=sys_tray_add_lbl_win: win_close(wind))

        title_text.grid_configure(row=0, column=0, columnspan=2, sticky='ews', padx=10)
        label_name.grid_configure(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        add_btn.grid_configure(row=2, column=0, sticky='sw', padx=10, pady=10)
        cancel_btn.grid_configure(row=2, column=1, sticky='nw', padx=10, pady=10)

        sys_tray_add_lbl_win.deiconify()  # shows the window again
        get_logger().debug("sys_tray_manual_label end")

    # TODO: create a real main window
    def main_window(self, name: str = "Empty", geo="300x200"):
        get_logger().debug("main_window start")
        n_win = Toplevel(self.root)
        n_win.iconphoto = self.window_icon
        n_win.title(name)
        n_win.geometry(geo)
        get_logger().debug("main_window end")


    @classmethod
    def get_instance(cls):
        """
        Returns the instance of the GuiHandler class.
        Only way to access it.
        :return: instance of GuiHandler
        """
        if cls._instance is None:
            cls()

        return cls._instance


# # # # Helper functions for the widgets # # # #
def win_close(win: Window):
    win.destroy()


def sys_add(win: Window, label_text):
    # TODO: Probably need to make this smoother, because circualr import if import on top
    get_logger().debug("adding manual label by systray start")
    from system_tray_manager import SystemTrayManager
    from window_manager import Label
    Label(label_text.get(), manually=True)
    win_close(win)
    SystemTrayManager.get_instance().update_menu()
    get_logger().debug("adding manual label by systray end")


# # # # External call functions for less import in other files # # # #

def stop_gui():
    GuiController.get_instance().stop_helper()

def init_root_gui():
    GuiController.get_instance()

def start_root_gui():
    GuiController.get_instance().run()


def sys_tray_manual_label():
    GuiController.get_instance().sys_tray_manual_label()


def open_main_gui():
    GuiController.get_instance().main_window()

if __name__ == "__main__":
    print("Please start with the main.py")

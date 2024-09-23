"""
This file only includes the small popup windows on teh right
which will be fixed in position and shown on
call of the system tray icon.
"""

import ttkbootstrap as tb
from window_tracker import Label
from threading import Thread, Event, Lock

tray_helper_thread: Thread = None
tray_helper_lock: Lock = Lock()

# FIXME: Sync error whenever a label was added and the app is closed, it results in a error closing


def create_label_win():

    with tray_helper_lock:
        win_width = 300
        win_height = 130
        taskbar_height = 70
        manual_label = tb.Window()
        s_width = manual_label.winfo_screenwidth()
        s_height = manual_label.winfo_screenheight()
        manual_label.geometry(f"{win_width}x{win_height}+{s_width - win_width}+{s_height - win_height - taskbar_height}")
        manual_label.resizable(width=False, height=False)
        manual_label.attributes('-toolwindow', True)
        manual_label.attributes('-topmost', True)
        manual_label.overrideredirect(True)

        manual_label.grid_rowconfigure(0, weight=1)
        manual_label.grid_columnconfigure(0, weight=1)
        manual_label.attributes('-alpha', 0.7)
        # TODO: Maybe change to transparent background and give widgets a non transparent image,
        #  so it looks like widgets "fly" on the screen

        title_text = tb.Label(manual_label, text="Choose a label name:", font=("Helvetica", 12))
        label_name = tb.Entry(manual_label, width=40)
        # TODO: Add enter & tab functionality, fast saving new tab without much clicking
        add_btn = tb.Button(manual_label, text="Add & Start", command=lambda wind=manual_label, lbl_name=label_name: sys_add(wind, lbl_name))
        cancel_btn = tb.Button(manual_label, text="Cancel", command=lambda wind=manual_label: sys_cancel(wind))

        title_text.grid_configure(row=0, column=0, columnspan=2, sticky='ews', padx=10)
        label_name.grid_configure(row=1, column=0, columnspan=2, sticky='ew', padx=10, pady=10)
        add_btn.grid_configure(row=2, column=0, sticky='sw', padx=10, pady=10)
        cancel_btn.grid_configure(row=2, column=1, sticky='nw', padx=10, pady=10)
        manual_label.mainloop()


# FIXME: Needs to change completely to new Topwindow architecture to work and needs to be created by GUI Handler
def sys_add_label():
    global tray_helper_thread

    tray_helper_thread = Thread(target=create_label_win)
    tray_helper_thread.start()


def sys_add(window, label_text):
    # TODO: Probably need to make this smoother, because circualr import if import on top
    from system_tray_handler import SystemTrayManager
    Label(label_text.get(), manually=True)
    sys_cancel(window)
    SystemTrayManager.get_instance().update_menu()


def sys_cancel(window=None):
    window.destroy()


if __name__ == "__main__":
    print("Please start with the main.py")

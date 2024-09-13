

import ttkbootstrap as tb
from time import sleep
import input_tracker
import window_tracker


def start():
    # start thread for tracking mouse and keyboard signals (only counting & timestamp)
    input_tracker.start()
    # start the thread for reading windows based on configured time frame
    window_tracker.start()

    root_window = tb.Window()
    root_window.geometry(f"{300}x{100}+{100}+{100}")
    root_window.grid_rowconfigure(0, weight=1)
    root_window.grid_columnconfigure(0, weight=1)

    # TODO: If there is a setting change, stop & start again the threads.
    root_window.mainloop()

    # TODO: termination process handeling
    # Stop the inputmanager thread if the program gets terminated
    window_tracker.stop()
    input_tracker.stop()


if __name__ == "__main__":
    start()

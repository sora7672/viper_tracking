

import ttkbootstrap as tb
from input_tracker import start as input_start, stop as input_stop
from window_tracker import start as tracking_start, stop as tracking_stop, setup_labels
import input_tracker
import window_tracker

# TODO:
#   wenn was hinzugefügt, dann update des tracking threads/microservies/Prozess
#   Auswertungen müssen per label, fenster typ, nach text suche, text/word segments
#   oder irgendeiner kombnation dieser machbar sein
#   Advanced conditions, wie z.B. wenn anwendung A hauptfenster & Anwendung B im Hintergrund, dann setz label

def start() -> None:
    """
    The function to start all needed application modules.
    :return: None
    """
    # First get the Label elements from the DB, needs to be called here once,
    # because the start function will be called in between on changes.
    setup_labels()
    # start thread for tracking mouse and keyboard signals (only counting & timestamp)
    input_start()
    # start the thread for reading windows
    tracking_start()

    root_window = tb.Window()
    root_window.geometry(f"{300}x{100}+{100}+{100}")
    root_window.grid_rowconfigure(0, weight=1)
    root_window.grid_columnconfigure(0, weight=1)

    # TODO: If there is a setting change, stop & start again the threads.
    root_window.mainloop()

    # TODO: termination process handeling
    # Stop the inputmanager & window tracker thread if the program gets terminated
    tracking_stop()
    input_stop()


if __name__ == "__main__":
    start()

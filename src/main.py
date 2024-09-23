

import ttkbootstrap as tb
from input_tracker import start as input_start, stop as input_stop
from window_tracker import start as tracking_start, stop as tracking_stop, Label
from system_tray_handler import start as system_tray_start
from gui_handler import GuiHandler


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
    Label.init_all_label_from_db()

    # start thread for tracking mouse and keyboard signals (only counting & timestamp)
    input_start()
    # start the thread for reading windows
    tracking_start()

    # main loop with the system tray
    system_tray_start()

    GuiHandler.get_instance().run()


    # TODO: termination process handeling
    # Stop the inputmanager & window tracker thread if the program gets terminated
    tracking_stop()
    input_stop()


if __name__ == "__main__":
    start()

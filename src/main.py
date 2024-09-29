import ttkbootstrap as tb
from input_tracker import start as input_start, stop as input_stop
from window_tracker import start as tracking_start, stop as tracking_stop, setup_labels
import input_tracker
import window_tracker

#flags
tracking_active = False
input_active = False

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
    global tracking_active, input_active
    # First get the Label elements from the DB, needs to be called here once,
    # because the start function will be called in between on changes.
    setup_labels()
    # start thread for tracking mouse and keyboard signals (only counting & timestamp)
    input_start()
    # start the thread for reading windows
    tracking_start()

    root_window = tb.Window()
    root_window.geometry(f"{400}x{200}+100+100")
    label = tb.Label(root_window, text="Programm läuft", font=("Arial", 14))
    label.grid(row=0, column=0, padx=10, pady=10)

    start_button = tb.Button(root_window, text="Start Tracking", command=lambda: start_tracking(label))
    start_button.grid(row=1, column=0, padx=10, pady=10)

    stop_button = tb.Button(root_window, text="Stop Tracking", command=lambda: stop_tracking(label))
    stop_button.grid(row=2, column=0, padx=10, pady=10)

    #Skalierbarkeit der GUI
    root_window.grid_rowconfigure(0, weight=1)
    root_window.grid_rowconfigure(1, weight=1)
    root_window.grid_rowconfigure(2, weight=1)
    root_window.grid_columnconfigure(0, weight=1)

    # TODO: If there is a setting change, stop & start again the threads.
    root_window.mainloop()

    # TODO: termination process handeling
    # Stop the inputmanager & window tracker thread if the program gets terminated
    tracking_stop()
    input_stop()

def start_tracking(label):
    """Start Tracking Process"""
    global tracking_active, input_active

    if not tracking_active:
        tracking_start()
        label.config(text="Tracking gestartet")
        tracking_active = True
    else:
        label.config(text="Tracking läuft bereits")

    if not input_active:
        input_start()
        label.config(text="Input Tracking gestartet")
        input_active = True
    else:
        label.config(text="Input Tracking läuft bereits")


def stop_tracking(label):
    """Stop Tracking Process"""
    global tracking_active, input_active

    if tracking_active:
        tracking_stop()
        label.config(text="Tracking gestoppt")
        tracking_active = False
    else:
        label.config(text="Tracking war nicht aktiv")

    if input_active:
        input_stop()
        label.config(text="Input Tracking gestoppt")
        input_active = False
    else:
        label.config(text="Input Tracking war nicht aktiv")

if __name__ == "__main__":
    start()


import ttkbootstrap as tb

def open_gui():
    root_window = tb.Window()
    root_window.geometry(f"{300}x{100}+{100}+{100}")
    root_window.grid_rowconfigure(0, weight=1)
    root_window.grid_columnconfigure(0, weight=1)

    # TODO: If there is a setting change, stop & start again the threads.
    root_window.mainloop()


if __name__ == "__main__":
    print("Please start with the main.py")

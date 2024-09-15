

from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
from random import randint


def start_label(icon, item):
    print("I started a label!")


def stop_label(icon, item):
    print("I stopped a label!")


def stop_systray(icon, item):
    icon.stop()


# Function to create an image for the tray icon (just a simple colored square)
def create_image(width=64, height=64, color1="green", color2="purple"):
    # Create a basic image with two colors
    image = Image.new('RGB', (width, height), color1)
    draw = ImageDraw.Draw(image)
    draw.rectangle((width // 2, 0, width, height // 2), fill=color2)
    draw.rectangle((0, height // 2, width // 2, height), fill=color2)
    return image



def start():

    icon_menu = Menu(MenuItem("Start Label", Menu(MenuItem("first", start_label), MenuItem("second", start_label))),
                     MenuItem("Stop Label", stop_label),
                     MenuItem("Stop Systray", stop_systray))

    systray_icon = Icon("Viper Tracking", create_image())
    systray_icon.menu = icon_menu
    systray_icon.run()


def stop():
    pass


if __name__ == "__main__":
    start()
    print("Please start with the main.py")


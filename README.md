# About Viper Tracking

## What is Viper Tracking?
This tool is intended to be used by every kind of person in every area.
It will track your activity on the computer, including active windows,
key press (Only as counter & sorted by type of key: arrow, special and char key),
mouse clicks and scrolls.
Maybe later background windows to (WIP).
You can create labels and conditions for them to apply
or set manually labels, that you can activate

It will be highly configurable, like adding own conditions for the labels,
combine label conditions and more (WIP).

WIP:
You can enable the tool to autostart with your PC,
filter for different labels, window types and/or words for getting a better analysis,
even include time windows you want to check.
Later it could include pattern analysis, like on which things you get distracted the most
(e.g. you set a learning label and then spend multiple hours on YT, no problem, 
but you have watched 3 hours "minecraft" videos in between)

## Use cases
- Track your time on a project (whatever it is!)
- Find inefficent parts of your daily work cycle
- See a difference in your activity speed (Like keypress speed on writing code)
- Just have a easy way to brag about, what time you wasted on your hobbys ;)

## Installation requirements
### Dev area
- Install Mongo DB (Optional smth. like MongoDB Compass to view)
(if you use pycharm and a venv, make sure you install it in your project venv, not gloabl)
- Use a python 3.12 interpreter
- pymongo version: 4.8.0
- pynput version: 1.7.7
- pywin32 version: 306
- psutil  version: 6.0.0
- ttkbootstrap  version: 1.10.1
- pystray version: 0.19.5

You need to configure the mongodb login properly in the db_connector.py
The application will be started via the main.py and there we will include
all different modules that need to be started.
(sooner or later we will change from mongo db to another NoSQL DBMS locally)


### User area
Don't grab the project itself.
There will be a section for the latest installer for windows.
It will be just a standard installation from there on.




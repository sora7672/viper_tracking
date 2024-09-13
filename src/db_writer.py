

from pymongo import MongoClient


CLIENT = MongoClient("localhost", 27017)
DB = CLIENT.viper_tracking



def add_window_dict(window_dict:dict) -> None:
    collection = DB["window_log"]
    collection.insert_one(window_dict)



def get_entity(ent: dict):
    pass

def delete_entity(ent):
    pass


def update_entity(ent):
    pass


def main():

    # {"name": "Paul klaus", "alter": 55, "rolle": "dozent", "schüler_liste": ["Peter streter", "jan meyer", "susanne frank"]}
    # add_entity(my_ent)
    my_ent: dict = {"name": "Paul klaus"}
    dat = get_entity(my_ent)
    for key, value in dat.items():
        print(f"\"{key}\": {value}")



def start():

    pass


if __name__ == "__main__":
    start()


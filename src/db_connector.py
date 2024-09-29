"""
This module will write & read data from/into a MongoDB database.
Authors: Sora_7672 and Vulnona
"""
# TODO: Probably need to safe close the db connection on program exit, depends on DB i guess

from pymongo import MongoClient
from typing import Optional
from os import getenv
from log_handler import get_logger

mongodb_host = getenv('MONGODB_HOST', 'localhost')
mongodb_port = int(getenv('MONGODB_PORT', 27017))
get_logger().debug(f"mongo_db_host: {mongodb_host} | mongodb_port: {mongodb_port}")

# FIXME: Password missing?
#  for soras setup not needed, maybe also not for TinyDB ?
# Init the connection
try:
    m_client = MongoClient(mongodb_host, mongodb_port)
    m_db = m_client.viper_tracking
except MongoClient.errors as err:
    print(f"Could not connect to MongoDB: {err}")
    

# # # # # Window tracker input # # # #


def add_window_dict(window_dict: dict) -> Optional[str]:
    """
    This function will add a window dictionary to the MongoDB database.
    :param window_dict: dict
    :return: _id | None
    """
    if isinstance(window_dict, dict):
        result = m_db.window_collection.insert_one(window_dict)
        return result.inserted_id
    else:
        get_logger().error("add_window_dict(): Invalid parameter type: Expected a dictionary.")
        return None


# # # # Analyzing getter functions # # # #


def get_window_dict_list_by_label(label: str) -> list[dict]:
    """
    This function will return a list of window dictionaries based on a label.
    :param label: str
    :return: list[dict]
    """
    return list(m_db.window_collection.find({"label": label}).collation({"locale": "en", "strength": 2})
                .sort("timestamp"))


def get_window_dict_list_by_time_window(start_time: float, end_time: float) -> list[dict]:
    """
    This function will return a list of window dictionaries based on a time window.
    :param start_time: timestamp float
    :param end_time: timestamp float
    :return:
    """
    return list(m_db.window_collection.find({"timestamp": {"$gte": start_time, "$lte": end_time}}).sort("timestamp"))


def get_window_dict_list_by_window_type(*window_types: str) -> list[dict]:
    """
    This function will return a list of window dictionaries based on one or multiple window types.
    :param window_types: str | str, str, ...
    :return: list[dict]
    """
    return list(m_db.window_collection.find({"window_type": {"$in": window_types}}).sort("timestamp")
                .collation({"locale": "en", "strength": 2}))


def get_window_dict_list_by_words(*words: str) -> list[dict]:
    """
    This function will return a list of window dictionaries based on one or multiple words.
    :param words: str | str, str, ...
    :return:
    """
    return list(m_db.window_collection.find({"window_text_words": {"$in": words}}).sort("timestamp")
                .collation({"locale": "en", "strength": 2}))


# # # # Save and read inputs infos in own collection # # # #

def add_input_infos(input_dict: dict):
    m_db.input_collection.insert_one(input_dict)

def get_input_infos_by_id(input_id) -> dict:
    return m_db.input_collection.find_one({"_id": input_id})

def get_input_infos_by_timeframe(start_time: float, end_time: float) -> list[dict]:
    """
    This function will return a list of window dictionaries based on a time window.
    :param start_time: timestamp float
    :param end_time: timestamp float
    :return:
    """
    return list(m_db.input_collection.find({"timestamp": {"$gte": start_time, "$lte": end_time}}).sort("timestamp"))

# TODO: other getters from input
def get_input_infos_by_activity():
    pass





# # # #  Mixed usage, initial setup of labels and other uses # # # #

def get_label_list() -> list[dict]:
    """
    This function will return a list of all labels in the MongoDB database.
    :return: list[dict]
    """
    return list(m_db.label_collection.find().sort("timestamp"))



# # # # Changes in collection of labels # # # #

def add_label(label_dict: dict):
    """
    This function will add a label dictionary to the MongoDB database.
    returns the inserted id
    :param label_dict:
    :return:
    """
    if "_id" in label_dict.keys():
        raise Exception("db_connector.add_label works only without '_id' in dict!")
    return m_db.label_collection.insert_one(label_dict).inserted_id


def update_label(label_dict: dict) -> None:
    """
    This function will update a label dictionary in the MongoDB database.
    :param label_dict: dict
    :return: _id | None
    """
    if "_id" in label_dict and label_dict["_id"] is not None:
        result = m_db.label_collection.find_one_and_update(
            {"_id": label_dict["_id"]},
            {"$set": label_dict}
        )
        if result is None:
            get_logger().warning(f"Could not update label. Not found: _id={label_dict['_id']}")

    else:
        get_logger().warning(f"Could not update label. _id is not set!")


def delete_label(label_id) -> None:
    """
    This function will delete a label by id from the MongoDB Label Collection.
    :param label_id:
    :return: None
    """
    result = m_db.label_collection.find_one_and_delete({{"_id": label_id}})
    if result is None:
        get_logger().warning(f"Could not delete label.[_id={label_id}]")


# TODO: do what is needed to close the db connection properly
def close_db_connection():
    m_client.close()


if __name__ == "__main__":
    print("This module is not for starting the program!")


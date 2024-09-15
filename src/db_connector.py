"""
This module will write & read data from/into a MongoDB database.
Authors: Sora_7672 and Vulnona
"""

from pymongo import MongoClient
from typing import Optional
import os

mongodb_host = os.getenv('MONGODB_HOST', 'localhost')
mongodb_port = int(os.getenv('MONGODB_PORT', 27017))

# Init the connection
try:
    m_client = MongoClient(mongodb_host, mongodb_port)
    m_db = m_client.viper_tracking
except errors.ConnectionError as e:
    print(f"Could not connect to MongoDB: {e}")
    

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
        print("Invalid parameter type: Expected a dictionary.")
        return None


def get_window_dict_list_by_label(label: str) -> list[dict]:
    """
    This function will return a list of window dictionaries based on a label.
    :param label: str
    :return: list[dict]
    """
    return list(m_db.window_collection.find({"label": label}).collation({"locale": "en", "strength": 2}))


def get_window_dict_list_by_time_window(start_time: float, end_time: float) -> list[dict]:
    """
    This function will return a list of window dictionaries based on a time window.
    :param start_time: timestamp float
    :param end_time: timestamp float
    :return:
    """
    return list(m_db.window_collection.find({"timestamp": {"$gte": start_time, "$lte": end_time}}))


def get_window_dict_list_by_window_type(*window_types: str) -> list[dict]:
    """
    This function will return a list of window dictionaries based on one or multiple window types.
    :param window_types: str | str, str, ...
    :return: list[dict]
    """
    return list(m_db.window_collection.find({"window_type": {"$in": window_types}})
                .collation({"locale": "en", "strength": 2}))


def get_window_dict_list_by_words(*words: str) -> list[dict]:
    """
    This function will return a list of window dictionaries based on one or multiple words.
    :param words: str | str, str, ...
    :return:
    """
    return list(m_db.window_collection.find({"window_text_words": {"$in": words}})
                .collation({"locale": "en", "strength": 2}))


def get_label_list() -> list[dict]:
    """
    This function will return a list of all labels in the MongoDB database.
    :return: list[dict]
    """
    return list(m_db.label_collection.find())


def add_label(label_dict: dict):
    """
    This function will add a label dictionary to the MongoDB database.
    :param label_dict:
    :return:
    """
    return m_db.label_collection.insert_one(label_dict).inserted_id


def update_label(label_dict: dict) -> Optional[str]:
    """
    This function will update a label dictionary in the MongoDB database.
    :param label_dict: dict
    :return: _id | None
    """
    if "_id" in label_dict and label_dict["_id"] is not None:
        result = m_db.label_collection.find_one_and_update(
            {"$and": [{"name": label_dict["name"]}, {"_id": label_dict["_id"]}]},
            {"$set": label_dict}
        )
        return label_dict["_id"] if result else None
    else:
        label_dict.pop("_id", None)
        return add_label(label_dict)


def delete_label(label_dict: dict) -> None:
    """
    This function will delete a label dictionary from the MongoDB database.
    :param label_dict:
    :return: None
    """
    m_db.label_collection.delete_one({"$and": [{"name": label_dict["name"]}, {"_id": label_dict["id"]}]})


if __name__ == "__main__":
    print("This module is not for starting the program!")


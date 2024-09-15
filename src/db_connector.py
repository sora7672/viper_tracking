"""
This module will write & read data from/into a MongoDB database.
Author: Sora_7672
"""

from pymongo import MongoClient

# Init the connection
m_client = MongoClient("localhost", 27017)
m_db = m_client.viper_tracking


def add_window_dict(window_dict: dict):
    """
    This function will add a window dictionary to the MongoDB database.
    :param window_dict: dict
    :return: _id
    """
    return m_db.window_collection.insert_one(window_dict).inserted_id


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


def update_label(label_dict: dict):
    """
    This function will update a label dictionary in the MongoDB database.
    :param label_dict: dict
    :return: _id
    """
    if label_dict["_id"] is not None:
        m_db.label_collection.find_one_and_update({"$and": [{"name": label_dict["name"]}, {"_id": label_dict["_id"]}]},
                                                  {"$set": label_dict})
        return label_dict["_id"]
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


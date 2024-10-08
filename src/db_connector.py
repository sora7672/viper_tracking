"""

Author: sora7672
"""
import sqlite3
from threading import Lock
import json
from time import time
from log_handler import get_logger
from os import path, makedirs

# FIXME: DB is not getting written any table!
# # # # Helper functions internal # # # #
def _make_searchable(text: str) -> str:
    """
    Function makes a text searchable in SQL terms with replacing all non-alphanumeric chars with a "%"
    :param text: str
    :return: str
    """
    return ''.join([char if char.isalnum() else '%' for char in text])


def _create_in_search_term(field_name: str, values: list | str) -> tuple[str, list[int | float | str | None]]:
    """
    Function creates a tuple for adding into a SQL Querry splitted to values and querry.
    :param field_name: str
    :param values: list
    """
    placeholders = ','.join(['?'] * len(values))
    return f"{field_name} IN ({placeholders})", [_make_searchable(val) for val in values]


def _to_json(data: dict) -> str | None:
    """
    Function converts data dictionary to json string
    :param data: dict
    :return: str | None
    """
    try:
        return json.dumps(data)
    except TypeError as e:
        get_logger().warning(f"Serialization TypeError: {e}")
        return None
    except OverflowError as e:
        get_logger().warning(f"OverflowError: {e}")
        return None


def _from_json(json_string: str) -> dict | None:
    """
    Function converts json string back to a dictionary
    :param json_string: str
    :return: str | None
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        get_logger().warning(f"JSONDecodeError: {e}")
        return None
    except ValueError as e:
        get_logger().warning(f"ValueError: {e}")
        return None


# # # # DB Handler Class # # # #
# For all DB stuff
class DBHandler:
    """
    This a singleton that handles all database related things.
    Connecting and closing the connection,
    creating the tables on first init,
    adding, updating, deleting or searching entries in tables.
    Methods are called like:
    DBHandler().methode()
    """
    _instance = None

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.db_path = path.abspath(path.join(path.dirname(path.abspath(__file__)), "database"))
            self.check_db_path()
            self.db_name = "viper_tracking.db"
            self.conn = None
            self.cursor = None
            self.lock = Lock()

    def check_db_path(self):
        if not path.exists(self.db_path):
            makedirs(self.db_path)

    def first_open_db(self):
        """
        This method is executed if there is no tables existing.
        It creates the needed tables & sets the DB to thread safe usage.
        :param self: DBHandler
        :return: None
        """
        try:
            self.cursor.execute("PRAGMA journal_mode=WAL;")  # Enable WAL mode for multithreading
            self.conn.commit()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS window_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    window_type TEXT NOT NULL COLLATE NOCASE,
                    window_title TEXT NOT NULL COLLATE NOCASE,
                    word_list TEXT NOT NULL COLLATE NOCASE,
                    label_list TEXT COLLATE NOCASE,
                    timestamp INTEGER
                )
            ''')
            self.conn.commit()
            self.cursor.execute('''
                       CREATE TABLE IF NOT EXISTS input_log (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           last_activity_timestamp INTEGER,
                           count_key_pressed INTEGER,
                           count_mouse_pressed INTEGER,
                           count_direction_key_pressed INTEGER,
                           count_char_key_pressed INTEGER,
                           count_special_key_pressed INTEGER,
                           count_mouse_scrolls INTEGER,
                           count_left_mouse_pressed INTEGER,
                           count_right_mouse_pressed INTEGER,
                           count_middle_mouse_pressed INTEGER,
                           timestamp INTEGER
                       )
                   ''')
            self.conn.commit()
            self.cursor.execute('''
                                CREATE TABLE IF NOT EXISTS labels (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL COLLATE NOCASE,
                                manually boolean NOT NULL,
                                active boolean NOT NULL,
                                conditions TEXT,
                                creation_timestamp INTEGER NOT NULL 
                               )
                           ''')
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            get_logger().error(f"Integrity error while database init: {e}")
            self.conn.rollback()
            return None

        except sqlite3.OperationalError as e:
            get_logger().error(f"Operational error while database init: {e}")
            self.conn.rollback()
            return None

        except sqlite3.DatabaseError as e:
            get_logger().error(f"Database error while database init: {e}")
            self.conn.rollback()
            return None

        except Exception as e:
            get_logger().error(f"Unexpected error while database init: {e}")
            self.conn.rollback()
            return None

    def check_dbs(self):
        """
        This method is checking for the labels table, if its not existing,
        the first_open_db method was not called before and calls it.
        :param self: DBHandler
        :return: None
        """
        try:
            self.cursor.execute('''
                            SELECT name FROM sqlite_master WHERE type='table' AND name='labels'
                        ''')

        except sqlite3.IntegrityError as e:
            get_logger().error(f"Integrity error while testing database init: {e}")
            raise

        except sqlite3.OperationalError as e:
            get_logger().error(f"Operational error while testing database init: {e}")
            raise

        except sqlite3.DatabaseError as e:
            get_logger().error(f"Database error while testing database init: {e}")
            raise

        except Exception as e:
            get_logger().error(f"Unexpected error while testing database init: {e}")
            raise

        if not self.cursor.fetchone():
            self.first_open_db()

    def connect(self):
        """
        This method initializes the database connection.
        Then it calls the check_dbs() method to ensure on program start, that the DB is existing.
        :param self: DBHandler
        :return: None
        """
        # Connect to the database with WAL mode enabled
        try:
            # Try connecting to the SQLite database
            self.conn = sqlite3.connect(path.join(self.db_path, self.db_name), check_same_thread=False)
            self.cursor = self.conn.cursor()
            get_logger().info("Database connection established successfully.")

        except sqlite3.OperationalError as e:
            get_logger().error(f"Operational error while connecting to the database: {e}")
            raise

        except sqlite3.DatabaseError as e:
            get_logger().error(f"Database error occurred while connecting: {e}")
            raise

        except Exception as e:
            get_logger().error(f"Unexpected error during database connection: {e}")
            raise

        self.check_dbs()

    def close(self):
        """
        This method closes the connection to the DB when the program should egt closed.
        :param self: DBHandler
        :return: None
        """
        with self.lock:
            if self.conn:
                self.conn.close()
        get_logger().info(f"database connection closed.")

    def add_window_log(self, window_dict: dict) -> None:
        """
        This method writes a window dictionary into the database.
        The keys the dictionary needs are:
        window_type, window_title, word_list, label_list, timestamp
        :param self: DBHandler
        :param window_dict: dict
        :return: None
        """
        keys_needed = ['window_type', 'window_title', 'window_text_words', 'label_list', 'timestamp']
        if not all(key in window_dict for key in keys_needed):
            get_logger().warn(f"At least one missing key: {keys_needed}\n"
                              f"window_dict: {window_dict}")
            return None

        words = ",".join(window_dict["window_text_words"])
        labels = ",".join(window_dict["label_list"])
        with self.lock:
            self.cursor.execute('''
                INSERT INTO window_log (window_type, window_title, word_list, label_list, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (window_dict["window_type"], window_dict["window_title"], words, labels, window_dict["timestamp"]))
            self.conn.commit()

    def add_input_log(self, input_dict: dict) -> None:
        """
        This method writes an input dictionary into the database.
        The keys the dictionary needs are:
        last_activity_timestamp, count_key_pressed, count_mouse_pressed,
        count_direction_key_pressed, count_char_key_pressed, count_special_key_pressed, count_mouse_scrolls,
        count_left_mouse_pressed, count_right_mouse_pressed, count_middle_mouse_pressed, timestamp
        :param self: DBHandler
        :param input_dict: dict
        :return: None
        """
        keys_needed = ["last_activity_timestamp", "count_key_pressed", "count_mouse_pressed",
                       "count_direction_key_pressed", "count_char_key_pressed", "count_special_key_pressed",
                       "count_mouse_scrolls", "count_left_mouse_pressed", "count_right_mouse_pressed",
                       "count_middle_mouse_pressed", "timestamp"]
        if not all(key in input_dict for key in keys_needed):
            get_logger().warn(f"At least one missing key: {keys_needed}\n"
                              f"input_dict: {input_dict}")
            return None

        with self.lock:
            self.cursor.execute('''
                INSERT INTO input_log (last_activity_timestamp, count_key_pressed, count_mouse_pressed, 
                count_direction_key_pressed, count_char_key_pressed, count_special_key_pressed, count_mouse_scrolls,
                 count_left_mouse_pressed, count_right_mouse_pressed, count_middle_mouse_pressed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (input_dict["last_activity_timestamp"], input_dict["count_key_pressed"],
                  input_dict["count_mouse_pressed"], input_dict["count_direction_key_pressed"],
                  input_dict["count_char_key_pressed"], input_dict["count_special_key_pressed"],
                  input_dict["count_mouse_scrolls"], input_dict["count_left_mouse_pressed"],
                  input_dict["count_right_mouse_pressed"], input_dict["count_middle_mouse_pressed"],
                  input_dict["timestamp"]))
            self.conn.commit()

    def add_label(self, label_dict: dict) -> None | int:
        """
        This method writes a label dictionary into the database.
        The keys the dictionary needs are:
        name, manually, active, conditions, creation_timestamp
        :param self: DBHandler
        :param label_dict: dict
        :return: None
        """
        keys_needed = ["name", "manually", "active", "conditions", "creation_timestamp"]
        if not all(key in label_dict for key in keys_needed):
            get_logger().warn(f"At least one missing key: {keys_needed}\n"
                              f"label_dict: {label_dict}")
            return None
        conditions = _to_json(label_dict["conditions"])
        if not conditions:
            get_logger().warning(f"There is an error in the conditions dict!\n {label_dict}"
                                 f"\nNot added to the DB!")
            return None

        # TODO: need to add some better error handeling, more visual for the user + the normal log writing
        try:
            with self.lock:
                self.cursor.execute('''
                    INSERT INTO labels (name, manually, active, conditions, creation_timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (label_dict["name"], label_dict["manually"], label_dict["active"],
                      conditions, label_dict["creation_timestamp"]))

                new_id = self.cursor.lastrowid
                self.conn.commit()

        except sqlite3.IntegrityError as e:
            get_logger().error(f"Integrity error while adding label {label_dict}: {e}")
            self.conn.rollback()
            return None

        except sqlite3.OperationalError as e:
            get_logger().error(f"Operational error while adding label {label_dict}: {e}")
            self.conn.rollback()
            return None

        except sqlite3.DatabaseError as e:
            get_logger().error(f"Database error while adding label {label_dict}: {e}")
            self.conn.rollback()
            return None

        except Exception as e:
            get_logger().error(f"Unexpected error while adding label {label_dict}: {e}")
            self.conn.rollback()
            return None

        else:
            get_logger().info(f"{"Manually" if label_dict["manually"] else "Auto"} Label added successfully. ID: {new_id}")
            return new_id

    def update_label(self, label_dict: dict) -> None:
        """
        This method updates a label in the database.
        The keys the dictionary needs are:
        name, manually, active, conditions, creation_timestamp
        :param self: DBHandler
        :param label_dict: dict
        :return: None
        """
        keys_needed = ["name", "manually", "active", "conditions", "creation_timestamp"]
        if not all(key in label_dict for key in keys_needed):
            get_logger().warn(f"At least one missing key: {keys_needed}\n"
                              f"label_dict: {label_dict}")
            return None
        conditions = _to_json(label_dict["conditions"])
        if not conditions:
            get_logger().warning(f"There is an error in the conditions dict!\n {label_dict}"
                                 f"\nNot added to the DB!")
            return None


        # TODO: need to add some better error handling, more visual for the user + the normal log writing
        try:
            with self.lock:
                self.cursor.execute('''
                    UPDATE labels 
                    SET name = ?, manually = ?, active = ?, conditions = ?, creation_timestamp = ?
                    WHERE id = ?
                ''', (label_dict["name"], label_dict["manually"], label_dict["active"],
                      conditions, label_dict["creation_timestamp"], label_dict["id"]))

                self.conn.commit()
        except sqlite3.IntegrityError as e:
            get_logger().error(f"Integrity error while updating label ID {label_dict["id"]}: {e}")
            self.conn.rollback()

        except sqlite3.OperationalError as e:
            get_logger().error(f"Operational error during update of label ID {label_dict["id"]}: {e}")

        except sqlite3.DatabaseError as e:
            get_logger().error(f"Database error while updating label ID {label_dict["id"]}: {e}")
            self.conn.rollback()

        except Exception as e:
            get_logger().error(f"Unexpected error during label update: {e}")
            self.conn.rollback()

    def get_all_labels(self) -> None | list[dict]:
        """
        This method returns all labels in the database.
        Each in the form of a dictionary with the following keys:
        name, manually, active, conditions, creation_timestamp
        :self: DBHandler
        :return: None | list[dict]
        """
        try:
            with self.lock:
                self.cursor.execute('''
                    SELECT id, name, manually, active, conditions, creation_timestamp
                    FROM labels
                    ORDER BY creation_timestamp
                ''')
                rows = self.cursor.fetchall()

        except sqlite3.IntegrityError as e:
            get_logger().error(f"Integrity error while getting all labels: {e}")
            return None

        except sqlite3.OperationalError as e:
            get_logger().error(f"Operational error while getting all labels: {e}")
            return None

        except sqlite3.DatabaseError as e:
            get_logger().error(f"Database error while getting all labels: {e}")
            return None

        except Exception as e:
            get_logger().error(f"Unexpected error while getting all labels: {e}")
            return None

        labels = []
        for row in rows:
            label_dict = {
                "id": row[0],
                "name": row[1],
                "manually": row[2],
                "active": row[3],
                "creation_timestamp": row[5]
            }
            conds = _from_json(row[4])
            if not conds:
                get_logger().warning(f"There is an error in the conditions dict! {label_dict}")
                label_dict = None
            else:
                label_dict["conditions"] = conds
            labels.append(label_dict)

        return labels

    def search_input_log(self, start_time: float = None, end_time: float = None, count_key_pressed: int = None,
                         count_mouse_pressed: int = None, count_direction_key_pressed: int = None,
                         count_char_key_pressed: int = None, count_special_key_pressed: int = None,
                         count_mouse_scrolls: int = None, count_left_mouse_pressed: int = None,
                         count_right_mouse_pressed: int = None, count_middle_mouse_pressed: int = None):
        """
        Returns a list of input dicts with these keys:
        id, last_activity_timestamp,  count_key_pressed, count_mouse_pressed, count_direction_key_pressed,
        count_char_key_pressed, count_special_key_pressed, count_mouse_scrolls, count_left_mouse_pressed,
        count_right_mouse_pressed, count_middle_mouse_pressed, timestamp
        Default parameters will return the last 24 hours input log.
        All parameter except end_time are searched as greater equal then.
        end_time is the only that is searched as less equal then.
        All parameters which are set will be searched as a AND condition.
        If you need a OR you need to run this function 2 times and combine the arrays programmatically.
        :param start_time: float
        :param end_time: float
        :param count_key_pressed: int
        :param count_mouse_pressed: int
        :param count_direction_key_pressed: int
        :param count_char_key_pressed: int
        :param count_special_key_pressed: int
        :param count_mouse_scrolls: int
        :param count_left_mouse_pressed: int
        :param count_right_mouse_pressed: int
        :param count_middle_mouse_pressed: int
        """

        if start_time is None:
            start_time = time() - 86400  # 24 hours = 86400 seconds
        if end_time is None:
            end_time = time()

        query = '''
            SELECT id, last_activity_timestamp,  count_key_pressed, count_mouse_pressed, count_direction_key_pressed,    
                        count_char_key_pressed, count_special_key_pressed, count_mouse_scrolls, 
                        count_left_mouse_pressed, count_right_mouse_pressed, count_middle_mouse_pressed, timestamp         
            FROM input_log
            WHERE timestamp >= ? AND timestamp <= ?
        '''
        params = [start_time, end_time]

        # Work smart not hard ^^
        def add_gt_condition(field_name, value):
            nonlocal query
            if value is not None:
                query += f" AND {field_name} > ?"
                params.append(value)

        add_gt_condition("count_key_pressed", count_key_pressed)
        add_gt_condition("count_mouse_pressed", count_mouse_pressed)
        add_gt_condition("count_direction_key_pressed", count_direction_key_pressed)
        add_gt_condition("count_char_key_pressed", count_char_key_pressed)
        add_gt_condition("count_special_key_pressed", count_special_key_pressed)
        add_gt_condition("count_mouse_scrolls", count_mouse_scrolls)
        add_gt_condition("count_left_mouse_pressed", count_left_mouse_pressed)
        add_gt_condition("count_right_mouse_pressed", count_right_mouse_pressed)
        add_gt_condition("count_middle_mouse_pressed", count_middle_mouse_pressed)


        query += " ORDER BY timestamp ASC"

        try:
            with self.lock:
                out = []
                self.cursor.execute(query, params)
                rows = self.cursor.fetchall()

                for row in rows:
                    out.append({
                        "id": row[0],
                        "last_activity_timestamp": row[1],
                        "count_key_pressed": row[2],
                        "count_mouse_pressed": row[3],
                        "count_direction_key_pressed": row[4],
                        "count_char_key_pressed": row[5],
                        "count_special_key_pressed": row[6],
                        "count_mouse_scrolls": row[7],
                        "count_left_mouse_pressed": row[8],
                        "count_right_mouse_pressed": row[9],
                        "count_middle_mouse_pressed": row[10],
                        "timestamp": row[11]
                    })

        except sqlite3.IntegrityError as e:
            get_logger().error(f"Integrity error while searching input logs: {e}")
            return None

        except sqlite3.OperationalError as e:
            get_logger().error(f"Operational error while searching input logs: {e}")
            return None

        except sqlite3.DatabaseError as e:
            get_logger().error(f"Database error while searching input logs: {e}")
            return None

        except Exception as e:
            get_logger().error(f"Unexpected error while searching input logs: {e}")
            return None
        else:
            return out

    def search_window_log(self, window_type: str = None, window_title: str | list[str] = None,
                          word_list: str | list[str] = None, label_list: str | list[str] = None,
                          start_time: float = None, end_time: float = None):
        """
          Returns a list of window dicts with these keys:
          id, window_type, window_title, word_list, label_list, timestamp
          Default parameters will return the last 24 hours input log.
          All parameter except end_time are searched as greater equal then.
          end_time is the only that is searched as less equal then.
          All parameters which are set will be searched as a AND condition.
          If you need a OR you need to run this function 2 times and combine the arrays programmatically.
          :param start_time: float
          :param end_time: float
          :param window_type: str
          :param window_title: str | list[str]
          :param word_list: str | list[str]
          :param label_list: str | list[str]

        """
        # Set default time to the last 24 hours
        if start_time is None:
            start_time = time() - 86400  # 86400 seconds = 24 hours
        if end_time is None:
            end_time = time()


        query = '''
            SELECT id, window_type, window_title, word_list, label_list, timestamp
            FROM window_log
            WHERE timestamp >= ? AND timestamp <= ?
        '''
        params = [start_time, end_time]

        if window_type:
            query += " AND window_type LIKE ?"
            params.append(f"%{_make_searchable(window_type)}%")

        if window_title:
            if isinstance(window_title, list):
                condition, values = _create_in_search_term('window_title', window_title)
                query += f" AND {condition}"
                params.extend(values)
            else:
                query += " AND window_title LIKE ?"
                params.append(f"%{_make_searchable(window_title)}%")

        if word_list:
            if isinstance(word_list, list):
                condition, values = _create_in_search_term('word_list', word_list)
                query += f" AND {condition}"
                params.extend(values)
            else:
                query += " AND word_list LIKE ?"
                params.append(f"%{_make_searchable(word_list)}%")

        if label_list:
            if isinstance(label_list, list):
                condition, values = _create_in_search_term('label_list', label_list)
                query += f" AND {condition}"
                params.extend(values)
            else:
                query += " AND label_list LIKE ?"
                params.append(f"%{_make_searchable(label_list)}%")

        query += " ORDER BY timestamp ASC"

        try:
            with self.lock:
                self.cursor.execute(query, params)
                results = self.cursor.fetchall()

            out = []
            for row in results:
                out.append({
                    "id": row[0],
                    "window_type": row[1],
                    "window_title": row[2],
                    "word_list": row[3].split(","),
                    "label_list": row[4].split(","),
                    "timestamp": row[5]
                })

        except sqlite3.IntegrityError as e:
            get_logger().error(f"Integrity error while searching input logs: {e}")
            return None

        except sqlite3.OperationalError as e:
            get_logger().error(f"Operational error while searching input logs: {e}")
            return None

        except sqlite3.DatabaseError as e:
            get_logger().error(f"Database error while searching input logs: {e}")
            return None

        except Exception as e:
            get_logger().error(f"Unexpected error while searching input logs: {e}")
            return None
        else:
            return out


# # # # External call functions for less import in other files # # # #
def start_db():
    """
    To minimize the import this function can be imported to start properly.
    """
    DBHandler().connect()


def stop_db():
    """
    To minimize the import this function can be imported to stop properly.
    """
    DBHandler().close()


if __name__ == "__main__":
    print("Please start with the main.py")

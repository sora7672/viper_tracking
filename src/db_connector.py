"""
This module handles all database-related operations, including initialization,
connection handling, and CRUD operations for various tables.

Features:
- Ensures thread-safe database access.
- Handles custom exceptions for better error reporting.
- Provides helper functions for query generation and data serialization.

Author: sora7672
"""
__author__ = 'sora7672'

import sqlite3
from threading import Lock
import json
from log_handler import get_logger
from os import path, makedirs
from datetime import datetime, timedelta
from pandas import DataFrame, merge as pandas_merge
import traceback

class DateTimeTypeError(Exception):
    """Custom exception for invalid datetime format."""
    pass


def string_to_iso_datetime(date_string):
    """
    Converts a string to a datetime object in ISO 8601 format.

    :param date_string: str (The input string to convert.)
    :raises DateTimeTypeError: If the string is not in ISO 8601 format.
    :return: datetime (The converted datetime object.)
    """

    try:
        return datetime.fromisoformat(date_string)
    except ValueError:
        raise DateTimeTypeError(f"Invalid ISO 8601 format: '{date_string}'")


# # # # Helper functions internal # # # #
def _make_searchable(text: str) -> str:
    """
    Converts a text string into an SQL-searchable format by replacing non-alphanumeric characters with '%'.

    :param text: str (The input text to convert.)
    :return: str (The modified string suitable for SQL queries.)
    """

    return ''.join([char if char.isalnum() else '%' for char in text])


def _create_in_search_term(field_name: str, values: list | str) -> tuple[str, list[int | float | str | None]]:
    """
    Generates an SQL IN condition with placeholders and values for a query.

    :param field_name: str (The name of the database field to match.)
    :param values: list | str (The values to include in the IN condition.)
    :return: tuple (SQL condition string and a list of values.)
    """

    placeholders = ','.join(['?'] * len(values))
    return f"{field_name} IN ({placeholders})", [_make_searchable(val) for val in values]


def _to_json(data: dict) -> str | None:
    """
    Serializes a dictionary into a JSON string.

    :param data: dict (The dictionary to serialize.)
    :return: str | None (The serialized JSON string, or None on failure.)
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
    Deserializes a JSON string into a dictionary.

    :param json_string: str (The JSON string to deserialize.)
    :return: dict | None (The deserialized dictionary, or None on failure.)
    """

    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        get_logger().warning(f"JSONDecodeError: {e}")
        return None
    except ValueError as e:
        get_logger().warning(f"ValueError: {e}")
        return None


def error_handling(error_object, db_connection, used_query: str, context_execution:str = "",
                   need_rollback: bool = True):

    error_type = ""
    if isinstance(error_object, sqlite3.IntegrityError):
        error_type = "IntegrityError"

    elif isinstance(error_object, sqlite3.OperationalError):
        error_type = "OperationalError"

    elif isinstance(error_object, sqlite3.DatabaseError):
        error_type = "DatabaseError"

    else:
        error_type = "Unknown(" + type(error_object).__name__ + ")"

    if need_rollback:
        db_connection.rollback()
    context_execution = f"[{context_execution}]" if context_execution else ""
    get_logger().error(f"{context_execution}{error_type}: {error_object}\n"
                       f"Traceback:\n{traceback.format_exc()}"
                       f"with query:\n{used_query}")
    return None


# # # # DB Handler Class # # # #
# For all DB stuff
class DBHandler:
    """
    A thread-safe singleton class for managing database operations.

    This class handles:
    - Connecting to the database.
    - Initializing tables on the first run.
    - CRUD operations for tables: `window_log`, `input_log`, and `labels`.
    - Thread-safe execution using locks.

    Usage:
        DBHandler().method()

    Attributes:
        db_path (str): Path to the database directory.
        db_name (str): Name of the database file.
        conn (sqlite3.Connection): SQLite connection object.
        cursor (sqlite3.Cursor): SQLite cursor for executing queries.
        _lock (Lock): Ensures thread-safe operations.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Ensures that DBHandler follows the singleton pattern.

        :return: DBHandler (The singleton instance.)
        """

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the DBHandler instance, setting up paths and locks.

        :return: None
        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.db_path = path.abspath(path.join(path.dirname(path.abspath(__file__)), "database"))
            self.check_db_path()
            self.db_name = "viper_tracking.db"
            self.conn = None
            self.cursor = None
            self._lock = Lock()

    def check_db_path(self) -> None:
        """
        Checks if the database directory exists and creates it if necessary.

        :return: None
        """

        if not path.exists(self.db_path):
            makedirs(self.db_path)

    def first_open_db(self) -> None:
        """
        Creates database tables on the first run and enables WAL mode for multithreading.

        Tables:
        1. `window_log` - Logs information about application windows.
        2. `input_log` - Logs user input events.
        3. `label_catalog` - Stores metadata about labels and their conditions.

        :return: None
        """

        try:
            query = "PRAGMA journal_mode=WAL;"
            self.cursor.execute(query)  # Enable WAL mode for multithreading

            query = '''
                CREATE TABLE IF NOT EXISTS window_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    window_type TEXT NOT NULL COLLATE NOCASE,
                    window_title TEXT NOT NULL COLLATE NOCASE,
                    word_list TEXT NOT NULL COLLATE NOCASE,
                    creation_datetime TEXT NOT NULL
                )
            '''
            self.cursor.execute(query)

            query = '''
                        CREATE TABLE IF NOT EXISTS con_window_label (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            window_id INTEGER NOT NULL,
                            label_id INTEGER NOT NULL,
                            FOREIGN KEY (window_id) REFERENCES window_log (id),
                            FOREIGN KEY (label_id) REFERENCES label_catalog (id)
                        )
                    '''
            self.cursor.execute(query)

            query = '''
                       CREATE TABLE IF NOT EXISTS input_log (
                           window_id INTEGER PRIMARY KEY,
                           count_key_pressed INTEGER,
                           count_mouse_pressed INTEGER,
                           count_direction_key_pressed INTEGER,
                           count_char_key_pressed INTEGER,
                           count_special_key_pressed INTEGER,
                           count_mouse_scrolls INTEGER,
                           count_left_mouse_pressed INTEGER,
                           count_right_mouse_pressed INTEGER,
                           count_middle_mouse_pressed INTEGER,
                           FOREIGN KEY (window_id) REFERENCES window_log (id) ON DELETE CASCADE
                       )
                   '''
            self.cursor.execute(query)

            query = '''
                                CREATE TABLE IF NOT EXISTS label_catalog (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                                manually boolean NOT NULL,
                                active boolean NOT NULL,
                                conditions TEXT,
                                creation_datetime TEXT NOT NULL,
                                deleted BOOLEAN NOT NULL DEFAULT 0
                               )
                           '''
            self.cursor.execute(query)

            query = '''
                                CREATE TABLE IF NOT EXISTS filter_catalog (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                                dynamic_time_frame TEXT,
                                window_type TEXT COLLATE NOCASE,
                                window_title TEXT COLLATE NOCASE,
                                word_list TEXT COLLATE NOCASE,
                                label_list TEXT,
                                start_datetime TEXT,
                                end_datetime TEXT,
                                creation_datetime TEXT NOT NULL
                               )
                           '''
            self.cursor.execute(query)
            self.conn.commit()

        except Exception as e:
            error_handling(e, self.conn, query, context_execution="DB initialization")
            return None

    def check_dbs(self) -> None:
        """
        Ensures that all required tables exist in the database.

        If tables are missing, it initializes them using `first_open_db`.

        :return: None
        """

        try:
            query = '''
                            SELECT name FROM sqlite_master WHERE type='table' AND name='label_catalog'
                        '''
            self.cursor.execute(query)

        except Exception as e:
            error_handling(e, self.conn, query, context_execution="Check if DB", need_rollback=False)
            raise

        if not self.cursor.fetchone():
            self.first_open_db()

    def connect(self) -> None:
        """
        Establishes a connection to the SQLite database.

        After connecting, it verifies the existence of required tables.

        :return: None
        """

        # Connect to the database with WAL mode enabled
        try:
            self.conn = sqlite3.connect(path.join(self.db_path, self.db_name), check_same_thread=False)
            self.cursor = self.conn.cursor()
            get_logger().info("Database connection established successfully.")

        except Exception as e:
            error_handling(e, self.conn, "NO QUERY", context_execution="DB Connection", need_rollback=False)
            raise

        self.check_dbs()

    def close(self) -> None:
        """
        Closes the connection to the SQLite database safely.

        :return: None
        """

        with self._lock:
            if self.conn:
                self.conn.close()
        get_logger().info(f"database connection closed.")

    def add_window_log(self, window_dict: dict) -> int | None:
        """
        Inserts a window log entry into the `window_log` table.

        Required Keys in `window_dict`:
        - `window_type` (str): The type of the window.
        - `window_title` (str): The title of the window.
        - `window_text_words` (list | set | tuple): Words associated with the window.
        - `label_list` (list | set | tuple): Label_ids applied to window
        - `creation_datetime` (datetime): Timestamp of the log.

        :param window_dict: dict (Details of the window log.)
        :return: None
        """

        keys_needed = ['window_type', 'window_title', 'window_text_words', 'label_list', 'creation_datetime']
        if not all(key in window_dict for key in keys_needed):
            get_logger().warn(f"At least one missing key: {keys_needed}\n"
                              f"window_dict: {window_dict}")
            return None

        if isinstance(window_dict["window_text_words"], (list,tuple,set,frozenset)):
            words = ",".join(window_dict["window_text_words"])
        else:
            raise ValueError("(window_dict['window_text_words'] not a (list,tuple,set,frozenset)")

        if not isinstance(window_dict["label_list"], (list,tuple,set,frozenset)):
            raise ValueError("window_dict['label_list'] not a (list,tuple,set,frozenset)")

        if isinstance(window_dict["creation_datetime"], datetime):
            creation_datetime = window_dict["creation_datetime"].isoformat()
        else:
            raise ValueError("window_dict['creation_datetime'] not a (datetime)")

        with self._lock:
            try:
                query = '''
                    INSERT INTO window_log (window_type, window_title, word_list, creation_datetime)
                    VALUES (?, ?, ?, ?)
                '''
                self.cursor.execute(query, (window_dict["window_type"], window_dict["window_title"], words,
                                            creation_datetime))
                window_id = self.cursor.lastrowid

                if len(window_dict["label_list"]) >= 1:
                    cons = [(window_id, label_id) for label_id in window_dict["label_list"]]

                    # Perform a batch insert with executemany

                    query = '''
                            INSERT INTO con_window_label (window_id, label_id)
                            VALUES (?, ?)
                        '''
                    self.cursor.executemany(query, cons)
                    self.conn.commit()

            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Add Window Log")
                return

        return window_id

    def add_input_log(self, window_id:int, input_dict: dict) -> None:
        """
        Inserts an input log entry into the `input_log` table.

        Required Keys in `input_dict`:
        - `count_key_pressed` (int): Total key presses.
        - `count_mouse_pressed` (int): Total mouse button presses.
        - Additional counters for specific inputs (e.g., `count_char_key_pressed`).

        :param input_dict: dict (Details of the input log.)
        :param window_id: int (The id of the window at time of saving)
        :return: None
        """

        keys_needed = ["count_key_pressed", "count_mouse_pressed",
                       "count_direction_key_pressed", "count_char_key_pressed", "count_special_key_pressed",
                       "count_mouse_scrolls", "count_left_mouse_pressed", "count_right_mouse_pressed",
                       "count_middle_mouse_pressed"]
        if not all(key in input_dict for key in keys_needed):
            get_logger().warn(f"At least one missing key: {keys_needed}\n"
                              f"input_dict: {input_dict}")
            return None

        with self._lock:
            try:
                query = '''
                    INSERT INTO input_log (window_id, count_key_pressed, count_mouse_pressed, 
                    count_direction_key_pressed, count_char_key_pressed, count_special_key_pressed, count_mouse_scrolls,
                     count_left_mouse_pressed, count_right_mouse_pressed, count_middle_mouse_pressed)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                '''
                self.cursor.execute(query, (window_id,  input_dict["count_key_pressed"],
                      input_dict["count_mouse_pressed"], input_dict["count_direction_key_pressed"],
                      input_dict["count_char_key_pressed"], input_dict["count_special_key_pressed"],
                      input_dict["count_mouse_scrolls"], input_dict["count_left_mouse_pressed"],
                      input_dict["count_right_mouse_pressed"], input_dict["count_middle_mouse_pressed"]))
                self.conn.commit()
            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Add Input Log")
                return

    def add_label(self, name: str, manually: bool, active: bool, creation_datetime: datetime,
                  conditions: dict = None) -> None | int:
        """
        Inserts a label entry into the `label_catalog` table.

        The label can be either manually assigned or automatically determined based on conditions.
        If conditions are provided, they will be serialized into a JSON string.

        :param name: str (The name of the label.)
        :param manually: bool (Indicates whether the label is manually assigned.)
        :param active: bool (Indicates if the label is active.)
        :param creation_datetime: datetime (The timestamp when the label was created.)
        :param conditions: dict | None (Optional dictionary containing conditions for automatic labeling.)
        :return: int | None (The ID of the newly inserted label, or None if insertion fails.)
        :raises ValueError: If `creation_datetime` is not a valid datetime object.
        """

        json_conditions = _to_json(conditions) if conditions else "{}"

        if isinstance(creation_datetime, datetime):
            iso_creation_datetime = creation_datetime.isoformat()
        else:
            raise ValueError("creation_datetime not a datetime")

        # TODO: need to add some better error handeling, more visual for the user + the normal log writing

        with self._lock:
            try:
                query = '''
                    INSERT INTO label_catalog (name, manually, active, conditions, creation_datetime)
                    VALUES (?, ?, ?, ?, ?)
                '''
                self.cursor.execute(query, (name, manually, active, json_conditions, iso_creation_datetime))
                new_id = self.cursor.lastrowid  # Needs to be set before commit to get row id
                self.conn.commit()

            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Add new Label")
                return

            get_logger().info(f"{"Manually" if manually else "Auto"} Label added successfully. ID: {new_id}")
            return new_id

    def update_label(self, label_id: int, name: str, manually: bool, active: bool, creation_datetime: datetime,
                     conditions: dict = None) -> None:
        """
        Updates an existing label in the `label_catalog` table.

        The method modifies an existing label entry based on the provided ID. If conditions are
        provided, they will be serialized into a JSON string.

        :param label_id: int (The ID of the label to update.)
        :param name: str (The updated name of the label.)
        :param manually: bool (Specifies if the label is manually assigned.)
        :param active: bool (Indicates whether the label is active.)
        :param creation_datetime: datetime (The timestamp of label creation.)
        :param conditions: dict | None (Optional dictionary defining the label's conditions.)
        :return: None
        :raises ValueError: If `creation_datetime` is not a valid datetime object.
        """

        json_conditions = _to_json(conditions) if conditions else "{}"
        if not json_conditions:
            get_logger().warning(f"There is an error in the conditions!\n"
                                 f"\nNot added to the DB!")
            return None

        if isinstance(creation_datetime, datetime):
            iso_creation_datetime = creation_datetime.isoformat()
        else:
            raise ValueError("label_dict['creation_datetime'] not a datetime")

        # TODO: need to add some better error handling, more visual for the user + the normal log writing
        with self._lock:
            try:
                query = '''
                    UPDATE label_catalog 
                    SET name = ?, manually = ?, active = ?, conditions = ?, creation_datetime = ?
                    WHERE id = ?
                '''
                self.cursor.execute(query, (name, manually, active,
                      json_conditions, iso_creation_datetime, label_id))
                self.conn.commit()

            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Add new Label")
                return

    def delete_label_by_id(self, label_id: int) -> None:
        """
        Deletes a label entry from the `labels` table based on its ID.
        It sets the label as deleted if a window is connected. If not it deletes the row completely.

        :param label_id: int (The ID of the label to delete.)
        :return: None
        """

        # TODO: Check when label id exist in con_window_label then set the labelname to "<Name>_deleted<id>" cuz unique
        with self._lock:
            try:
                query = '''
                             SELECT 1 
                 FROM con_window_label
                 WHERE label_id = ?
                 LIMIT 1;
                 '''
                self.cursor.execute(query, (label_id,))
                found = self.cursor.fetchone()

                if found is None:
                    query = '''
                        DELETE FROM label_catalog 
                        WHERE id = ?
                    '''
                    self.cursor.execute(query, (label_id,))
                else:
                    query = '''
                                       UPDATE label_catalog 
                                       SET deleted = 1 
                                       WHERE id = ?
                                   '''
                    self.cursor.execute(query, (label_id,))
                self.conn.commit()
            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Delete Label")
                return

    def get_all_labels(self) -> None | list[dict]:
        """
        Retrieves all labels from the `labels` table.

        Each label is returned as a dictionary with the following keys:
        - `id`, `name`, `manually`, `active`, `conditions`, `creation_datetime`.

        :return: list[dict] | None (List of labels, or None on failure.)
        """

        try:
            with self._lock:
                query = '''
                    SELECT id, name, manually, active, conditions, creation_datetime
                    FROM label_catalog
                    WHERE deleted = 0
                    ORDER BY creation_datetime
                '''
                self.cursor.execute(query)
                rows = self.cursor.fetchall()

        except Exception as e:
            error_handling(e, self.conn, query, context_execution="Get all Labels", need_rollback=False)
            return

        labels = []
        for row in rows:
            label_dict = {
                "id": row[0],
                "name": row[1],
                "manually": bool(row[2]),
                "active": bool(row[3]),
                "condition_json": row[4],
                "creation_datetime": string_to_iso_datetime(row[5])
            }
            labels.append(label_dict)

        return labels

    def search_input_log(self, count_key_pressed: int = None,
                         count_mouse_pressed: int = None, count_direction_key_pressed: int = None,
                         count_char_key_pressed: int = None, count_special_key_pressed: int = None,
                         count_mouse_scrolls: int = None, count_left_mouse_pressed: int = None,
                         count_right_mouse_pressed: int = None, count_middle_mouse_pressed: int = None) \
            -> list[dict] | None:
        """
        Searches the `input_log` table based on the provided filters.

        This method retrieves logs of user input activities, such as key presses, mouse clicks,
        and directional inputs, from the database. The default behavior (when no parameters are specified)
        returns logs from the last 24 hours.

        All parameters, except `end_time`, are searched using "greater than or equal to" (>=).
        `end_time` is searched using "less than or equal to" (<=).
        Filters that are set are combined using an AND condition.

        If an OR condition is needed, this method must be called multiple times with different parameters,
        and the results combined programmatically.

        :param count_key_pressed: int (Minimum number of total key presses to match.)
        :param count_mouse_pressed: int (Minimum number of total mouse button presses to match.)
        :param count_direction_key_pressed: int (Minimum number of directional key presses to match.)
        :param count_char_key_pressed: int (Minimum number of character key presses to match.)
        :param count_special_key_pressed: int (Minimum number of special key presses to match.)
        :param count_mouse_scrolls: int (Minimum number of mouse scroll actions to match.)
        :param count_left_mouse_pressed: int (Minimum number of left mouse button presses to match.)
        :param count_right_mouse_pressed: int (Minimum number of right mouse button presses to match.)
        :param count_middle_mouse_pressed: int (Minimum number of middle mouse button presses to match.)
        :return: list[dict] | None (A list of matching input logs, or None if an error occurs.)
        """

        query = '''
            SELECT window_id, count_key_pressed, count_mouse_pressed, count_direction_key_pressed,    
                        count_char_key_pressed, count_special_key_pressed, count_mouse_scrolls, 
                        count_left_mouse_pressed, count_right_mouse_pressed, count_middle_mouse_pressed         
            FROM input_log
            WHERE window_id != 0 
        '''
        params = []

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

        try:
            with self._lock:
                out = []
                self.cursor.execute(query, params)
                rows = self.cursor.fetchall()

                for row in rows:
                    out.append({
                        "window_id": row[0],
                        "count_key_pressed": row[1],
                        "count_mouse_pressed": row[2],
                        "count_direction_key_pressed": row[3],
                        "count_char_key_pressed": row[4],
                        "count_special_key_pressed": row[5],
                        "count_mouse_scrolls": row[6],
                        "count_left_mouse_pressed": row[7],
                        "count_right_mouse_pressed": row[8],
                        "count_middle_mouse_pressed": row[9]
                    })
        except Exception as e:
            error_handling(e, self.conn, query, context_execution="Get Input Log", need_rollback=False)
            return

        return out

    def search_window_log(self, window_type: str = None, window_title: str | list[str] = None,
                          word_list: str | list[str] = None, label_list: int | list[int] = None,
                          start_time: datetime = None, end_time: datetime = None) -> DataFrame | None:
        """
        Searches the `window_log` table based on the provided filters.

        This method retrieves logs of windows and their associated metadata, such as window type,
        title, word lists, and labels, from the database. The default behavior (when no parameters
        are specified) returns logs from the last 24 hours.

        All parameters, except `end_time`, are searched using "greater than or equal to" (>=).
        `end_time` is searched using "less than or equal to" (<=).
        Filters that are set are combined using an AND condition.

        If an OR condition is needed, this method must be called multiple times with different parameters,
        and the results combined programmatically.

        :param start_time: datetime (Start of the search range. Defaults to 24 hours ago.)
        :param end_time: datetime (End of the search range. Defaults to the current time.)
        :param window_type: str (Filter for the type of the window. Matches substrings case-insensitively.)
        :param window_title: str | list[str] (Filter for the title of the window. Matches substrings
        or multiple titles.)
        :param word_list: str | list[str] (Filter for specific words associated with the window.
        Matches substrings or multiple words.)
        :param label_list: int | list[int] (Filter for specific labels associated with the window.
        Checking for label_ids)
        :return: list[dict] | None (A list of matching window logs, or None if an error occurs.)
        """

        if start_time is None:
            start_time = datetime.now() - timedelta(days=1)  # 24 hours ago
        if end_time is None:
            end_time = datetime.now()
        query = '''
            SELECT window_log.id, window_log.window_type, window_log.window_title, window_log.word_list, 
            window_log.creation_datetime
            FROM window_log'''
        if label_list:
            query += '''
                       LEFT JOIN con_window_label
                       ON window_log.id = con_window_label.window_id
                     '''
        query += '''
            WHERE creation_datetime >= ? AND creation_datetime <= ?
        '''
        params = [start_time.isoformat(), end_time.isoformat()]

        if label_list:
            if isinstance(label_list, list):
                placeholder = ', '.join('?' for _ in label_list)
                query += f'''
                        AND con_window_label.label_id IN ({placeholder})
                        '''
                params.extend(label_list)
            else:
                query += '''
                        AND con_window_label.label_id = ?
                        '''
                params.append(label_list)

        if window_type:
            query += " AND window_log.window_type LIKE ?"
            params.append(f"%{_make_searchable(window_type)}%")

        if window_title:
            if isinstance(window_title, list):
                condition, values = _create_in_search_term('window_title', window_title)
                query += f" AND {condition}"
                params.extend(values)
            else:
                query += " AND window_log.window_title LIKE ?"
                params.append(f"%{_make_searchable(window_title)}%")

        if word_list:
            if isinstance(word_list, list):
                condition, values = _create_in_search_term('word_list', word_list)
                query += f" AND {condition}"
                params.extend(values)
            else:
                query += " AND window_log.word_list LIKE ?"
                params.append(f"%{_make_searchable(word_list)}%")

        query += " ORDER BY window_log.creation_datetime ASC"

        try:
            with self._lock:
                self.cursor.execute(query, params)
                results = self.cursor.fetchall()

        except Exception as e:
            error_handling(e, self.conn, query, context_execution="Get Wind Log", need_rollback=False)
            return

        window_df = DataFrame(
            [
                {
                    "window_id": row[0],
                    "window_type": row[1],
                    "window_title": row[2],
                    "word_list": row[3].split(","),
                    "creation_datetime": string_to_iso_datetime(row[4]),
                }
                for row in results
            ]
        )
        if not window_df.empty:
            window_ids = tuple(window_df['window_id'].tolist())
            inputs = self.get_inputs_by_window_id(window_ids)
            if inputs is not None:
                input_merged = pandas_merge(window_df, inputs, on="window_id", how="left")
                input_merged["activity"] = input_merged["count_key_pressed"].apply(
                    lambda x: True if x is not None and x >= 0 else False)
                input_merged["all_activity_count"] = input_merged[
                    [
                        "count_key_pressed", "count_mouse_pressed", "count_direction_key_pressed",
                        "count_char_key_pressed",  "count_special_key_pressed", "count_mouse_scrolls",
                        "count_left_mouse_pressed", "count_right_mouse_pressed", "count_middle_mouse_pressed"
                    ]
                ].sum(axis=1)
            else:
                input_merged = window_df

            labels = self.get_labels_by_window_id(window_ids)
            if labels is not None:
                labels_merged = pandas_merge(input_merged, labels, on="window_id", how="left")
            else:
                labels_merged = input_merged

            labels_merged = labels_merged.drop_duplicates(subset=["window_id"], keep="first")

            return labels_merged
        else:
            return DataFrame()

    def get_inputs_by_window_id(self, window_ids: int | tuple[int] | list[int]) -> DataFrame | None:
        """
        Retrieves input logs for a given window ID or multiple window IDs.

        This method fetches input logs from the `input_log` table based on the specified window IDs.

        :param window_ids: int | tuple[int] | list[int] (A single window ID or a tuple of window IDs.)
        :return: DataFrame | None (A pandas DataFrame containing input logs, or None if an error occurs.)
        """

        if window_ids is None:
            get_logger().error(f"Value Error, no window ids provided in get_inputs_by_window_id()")
            return None

        if isinstance(window_ids, int):
            params = (window_ids,)
        elif isinstance(window_ids, (tuple, list)):
            params = window_ids
        else:
            raise TypeError(f"window_ids must be int or tuple, not {type(window_ids)}")

        query = "SELECT * FROM input_log WHERE window_id IN ({})".format(
            ",".join(["?"] * len(params))  # Create placeholders for each ID
        )

        with self._lock:
            try:

                self.cursor.execute(query, params)
                rows = self.cursor.fetchall()
                columns = [desc[0] for desc in self.cursor.description]
            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Get Input Log", need_rollback=False)
                return

        data_out = DataFrame(rows, columns=columns)
        return data_out

    def get_labels_by_window_id(self, window_ids: int | tuple[int]) -> DataFrame | None:
        """
        Retrieves labels assigned to a specific window ID or multiple window IDs.

        The labels are aggregated into a single list for each window.

        :param window_ids: int | tuple[int] (A single window ID or a tuple of window IDs.)
        :return: DataFrame | None (A pandas DataFrame with labels for each window, or None if an error occurs.)
        """

        if window_ids is None:
            get_logger().error(f"Value Error, no window ids provided in get_labels_by_window_id()")
            return None

        if isinstance(window_ids, int):
            params = (window_ids,)
        elif isinstance(window_ids, (tuple, list)):
            params = window_ids
        else:
            raise TypeError(f"window_ids must be int or tuple, not {type(window_ids)}")

        query = """
            SELECT con_window_label.window_id, label_catalog.name
            FROM con_window_label
            LEFT JOIN label_catalog
            ON con_window_label.label_id = label_catalog.id
            WHERE con_window_label.window_id IN ({})
        """.format(",".join(["?"] * len(params)))

        with self._lock:
            try:

                self.cursor.execute(query, params)

            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Get Label by Window", need_rollback=False)
                return

            else:
                columns = [desc[0] for desc in self.cursor.description]
                all_db_data = self.cursor.fetchall()
                data_out = (
                    DataFrame(all_db_data, columns=columns)
                    .rename(columns={"name": "label_list"})
                    .groupby("window_id", as_index=False)
                    .agg({"label_list": lambda x: list(x.dropna().unique())})
                )

                return data_out

    def add_filter(self, name:str, window_type: str = None, window_title: str = None,
                   word_list: str | list[str] = None, label_list: int | list[int] = None,
                   start_datetime: datetime = None, end_datetime: datetime = None,
                   dynamic_time_frame: str = None) -> int:
        """
        Inserts a new filter entry into the `filter_catalog` table.

        A filter can contain multiple conditions based on different attributes like window type,
        title, labels, and time frames.

        :param name: str (The name of the filter.)
        :param window_type: str | None (The type of the window to filter.)
        :param window_title: str | None (The title of the window to filter.)
        :param word_list: str | list[str] | None (A list of words for filtering.)
        :param label_list: int | list[int] | None (A list of label IDs to filter by.)
        :param start_datetime: datetime | None (The start time for filtering.)
        :param end_datetime: datetime | None (The end time for filtering.)
        :param dynamic_time_frame: str | None (An optional dynamic time frame parameter.)
        :return: int | None (The ID of the newly inserted filter, or None if insertion fails.)
        """

        json_label_list = _to_json(label_list) if label_list else "{}"
        json_word_list = _to_json(word_list) if word_list else "{}"

        if isinstance(start_datetime, datetime):
            iso_start_datetime = start_datetime.isoformat()
        else:
            iso_start_datetime = None
        if isinstance(end_datetime, datetime):
            iso_end_datetime = end_datetime.isoformat()
        else:
            iso_end_datetime = None

        # TODO: need to add some better error handeling, more visual for the user + the normal log writing
        with self._lock:
            try:
                query = '''
                            INSERT INTO filter_catalog (name, dynamic_time_frame, window_type, window_title, 
                            word_list, label_list, start_datetime, end_datetime, creation_datetime)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        '''
                self.cursor.execute(query, (name, dynamic_time_frame, window_type, window_title, json_word_list,
                              json_label_list, iso_start_datetime, iso_end_datetime, datetime.now().isoformat()))

                new_id = self.cursor.lastrowid
                self.conn.commit()

            except Exception as e:
                error_handling(e, self.conn, query, context_execution="add Filter")
                return


        get_logger().info(f"Filter added successfully. ID: {new_id}")
        return new_id

    def update_filter(self, filter_id: int, name: str = None, window_type: str = None, window_title: str = None,
                      word_list: str | list[str] = None, label_list: int | list[int] = None,
                      start_datetime: datetime = None, end_datetime: datetime = None,
                      dynamic_time_frame: str = None) -> None:
        """
        Updates an existing filter in the `filter_catalog` table.

        If any attributes are provided, they will replace the existing values for the given filter ID.

        :param filter_id: int (The ID of the filter to update.)
        :param name: str | None (The updated name of the filter.)
        :param window_type: str | None (Updated window type filter.)
        :param window_title: str | None (Updated window title filter.)
        :param word_list: str | list[str] | None (Updated list of words for filtering.)
        :param label_list: int | list[int] | None (Updated list of label IDs.)
        :param start_datetime: datetime | None (Updated start time for the filter.)
        :param end_datetime: datetime | None (Updated end time for the filter.)
        :param dynamic_time_frame: str | None (Updated dynamic time frame.)
        :return: bool (True if the update was successful, False otherwise.)
        """

        json_label_list = _to_json(label_list) if label_list else "{}"
        json_word_list = _to_json(word_list) if word_list else "{}"

        if isinstance(start_datetime, datetime):
            iso_start_datetime = start_datetime.isoformat()
        else:
            iso_start_datetime = None

        if isinstance(end_datetime, datetime):
            iso_end_datetime = end_datetime.isoformat()
        else:
            iso_end_datetime = None

        # TODO: Need to add better error handling, more visual for the user + the normal log writing

        with self._lock:
            try:
                query = '''
                    UPDATE filter_catalog 
                    SET name = ?, dynamic_time_frame = ?, window_type = ?, window_title = ?, word_list = ?, label_list = ?,
                        start_datetime = ?, end_datetime = ?
                    WHERE id = ?
                '''
                self.cursor.execute(query, (name, dynamic_time_frame, window_type, window_title, json_word_list, json_label_list,
                      iso_start_datetime, iso_end_datetime, filter_id))

                if self.cursor.rowcount == 0:
                    get_logger().warning(f"Filter {filter_id} not found. No update performed.")
                    self.conn.rollback()
                    return

                self.conn.commit()

            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Update Filter")
                return

    def delete_filter(self, filter_id: int) -> None:
        """
        Deletes a filter from the `filter_catalog` table.

        If the filter does not exist, a warning is logged.

        :param filter_id: int (The ID of the filter to delete.)
        :return: bool (True if the deletion was successful, False otherwise.)
        """

        with self._lock:
            try:
                query = "DELETE FROM filter_catalog WHERE id = ?"
                self.cursor.execute(query, (filter_id,))
                if self.cursor.rowcount == 0:
                    get_logger().warning(f"Filter {filter_id} not found.")
                    self.conn.rollback()
                    return False

                self.conn.commit()
            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Delete Filter")
                return

        get_logger().info(f"Filter {filter_id} deleted successfully.")
        return True

    def get_all_filters(self) -> list[dict] | bool:
        """
        Retrieves all filters from the `filter_catalog` table.

        The filters are returned as a list of dictionaries, with each dictionary representing a filter entry.

        :return: list[dict] | None (A list of filter dictionaries, or None if an error occurs.)
        """


        with self._lock:
            try:
                query = '''
                    SELECT id, name, dynamic_time_frame, window_type, window_title, word_list, 
                    label_list, start_datetime, end_datetime 
                    FROM filter_catalog
                    '''
                self.cursor.execute(query)
                rows = self.cursor.fetchall()

            except Exception as e:
                error_handling(e, self.conn, query, context_execution="Get all Filters")
                return

        filters = []
        for row in rows:
            filters.append({
                "filter_id": row[0],
                "name": row[1],
                "dynamic_time_frame": row[2],
                "window_type": row[3],
                "window_title": row[4],
                "word_list": _from_json(row[5]) if row[5] else None,
                "label_list": _from_json(row[6]) if row[6] else None,
                "start_datetime": row[7],
                "end_datetime": row[8],
            })

        get_logger().info(f"Retrieved {len(filters)} filters from the database.")
        return filters


# # # # External call functions for less import in other files # # # #
def start_db() -> None:
    """
    Starts the database connection.

    :return: None
    """

    DBHandler().connect()


def stop_db() -> None:
    """
    Closes the database connection.

    :return: None
    """

    DBHandler().close()


if __name__ == "__main__":
    print("Please start with the main.py")

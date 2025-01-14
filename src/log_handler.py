"""
This module handles all aspects of logging for the application, including configuration and log management.

Author: sora7672
"""
__author__ = "sora7672"

import logging

from os import path, makedirs, listdir, remove, rename, pardir
from config_manager import is_debug


class LogHandler:
    """
    A singleton class that manages logging for the application.

    This class is responsible for:
    - Configuring logging settings.
    - Managing log files and backups.
    - Adjusting logging behavior based on debug settings.

    Attributes:
        logger (logging.Logger): The logger instance used for logging messages.
        log_folder (str): Directory where log files are stored.
        log_name (str): Base name of the log files.
        log_path (str): Full path to the log directory.
        max_backups (int): Maximum number of log backups to keep.
        debug (bool): Indicates whether debug mode is enabled.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Implements the singleton pattern by ensuring only one instance of the class exists.

        :return: LogHandler (The singleton instance.)
        """
        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the LogHandler singleton.

        This method ensures that the singleton instance is created only once and
        sets up default configurations for logging, such as file paths and backup limits.
        """

        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.logger = logging.getLogger("viper_tracking")
            self.logger.setLevel(logging.DEBUG)

            self.log_folder = "logs"
            self.log_name = "viper_tracking"

            self.project_dir = path.abspath(path.join(path.dirname(path.abspath(__file__)), pardir))
            self.log_path = path.join(self.project_dir, self.log_folder)
            # path will allways be from src +1 = projectname/logs/log_name.log
            self.max_backups = 5
            self.debug = False

    def init_logging(self) -> None:
        """
        Initializes and configures logging settings for the application.

        Log behavior depends on whether debug mode is enabled:
        - In debug mode, logs are more detailed and include thread information.
        - In non-debug mode, only error logs are recorded.

        :return: None
        """

        self.debug = is_debug()
        debug_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s - '
                                            '(Thread:%(threadName)s | ID:%(thread)d) - %(message)s')
        standard_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(name)s - %(message)s')
        if self.debug:
            formatter = debug_formatter

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

            file_path = self.create_log_file(file_name_extra=f"DEBUG_")
            debug_handler = logging.FileHandler(file_path)
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(formatter)
            self.logger.addHandler(debug_handler)

        else:
            formatter = standard_formatter

            file_path = self.create_log_file()
            error_handler = logging.FileHandler(file_path)
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            self.logger.addHandler(error_handler)

    def create_log_file(self, file_name_extra="") -> str:
        """
        Creates a new log file and handles backups if the file already exists.

        :param file_name_extra: str (An optional string to append to the log file name.)
        :return: str (The absolute path to the newly created log file.)
        """

        log_file_path = path.join(self.log_path, f"{file_name_extra}{self.log_name}.log")
        if not path.exists(self.log_path):
            makedirs(self.log_path)
        if path.isfile(log_file_path):
            self.backup_log(file_path=log_file_path)

        open(log_file_path, 'w').close()
        return log_file_path

    def backup_log(self, file_path) -> None:
        """
        Creates a backup of the current log file if it exists.

        Backups are limited to `max_backups`. When the limit is reached, the oldest backup is deleted.
        New backups are created with a timestamp in the filename to prevent overwriting.

        :param file_path: str (Path to the current log file.)
        :return: None
        """

        file_name = str(path.basename(file_path))

        check_part = file_name.replace(".log", "")
        check_files = [f for f in listdir(self.log_path) if
                       check_part in f and path.isfile(path.join(file_path, f))]
        if len(check_files) >= self.max_backups:
            oldest_file = min(check_files, key=lambda f: path.getmtime(path.join(file_path, f)))
            remove(oldest_file)

        with open(file_path, 'r') as file:
            time_log = file.read(25)  # 23 chars for datetime + 2 for brackets
        if len(time_log) == 0:
            return
        start_date_time = self.log_time_to_file_part(time_log)
        new_file_path = path.join(self.log_path, start_date_time + "_" + file_name)
        if path.isfile(new_file_path):
            # if there were 2 logs started in the same minute, remove the older one
            remove(new_file_path)
        rename(file_path, new_file_path)

    def log_time_to_file_part(self, log_text) -> str:
        """
        Generates a timestamp-based file name for a log file backup.

        :param log_text: str (The first line of the log file, which contains the timestamp.)
        :return: str (A string representing the backup file name, formatted as 'YYYY-MM-DD_HH-MM'.)
        """

        # [2024-09-29 13:09:48,085]
        # out: 2024-09-29_13-09
        name_add_on = log_text[1:11] + "_" + log_text[12:14] + "-" + log_text[15:17]
        return name_add_on


# # # # External call functions for less import in other files # # # #
def init_logging() -> None:
    """
    Configures the logger for the application.

    This function initializes the logging settings by creating an instance of the
    LogHandler class and calling its `init_logging` method.

    :return: None
    """

    LogHandler().init_logging()


def get_logger() -> logging.Logger:
    """
    Retrieves the logger instance for the application.

    The logger can be used to log messages at various levels, including DEBUG,
    INFO, WARNING, ERROR, and CRITICAL.
    Methods to create these are:
    warn(), error(), debug(), info()

    :return: logging.Logger (The logger instance.)
    """

    return LogHandler().logger


if __name__ == '__main__':
    print("Please start the main.py!")

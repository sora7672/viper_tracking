
import logging

from os import path, makedirs, listdir, remove, rename, pardir
from config_manager import is_debug


class LogHandler:
    _instance = None

    def __new__(cls, *args, **kwargs):

        if cls._instance is None:
            cls._instance = super(cls, cls).__new__(cls)
        return cls._instance

    def __init__(self):
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

    def init_logging(self):
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

    def create_log_file(self, file_name_extra=""):
        log_file_path = path.join(self.log_path, f"{file_name_extra}{self.log_name}.log")
        if not path.exists(self.log_path):
            makedirs(self.log_path)
        if path.isfile(log_file_path):
            self.backup_log(file_path=log_file_path)

        open(log_file_path, 'w').close()
        #sleep(0.5)  # To ensure file is there
        return log_file_path

    def backup_log(self, file_path):

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

    def log_time_to_file_part(self, log_text):
        # log text should be like, otherwise this function needs modification!
        # [2024-09-29 13:09:48,085]
        # out: 2024-09-29_13-09
        name_add_on = log_text[1:11] + "_" + log_text[12:14] + "-" + log_text[15:17]
        return name_add_on


def init_logging():
    LogHandler().init_logging()

def get_logger():
    return LogHandler().logger


if __name__ == '__main__':
    print("Please start the main.py!")

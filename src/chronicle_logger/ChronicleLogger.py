# src/chronicle_logger/ChronicleLogger.py
import os
import sys
import ctypes
import tarfile
import re
from datetime import datetime

# Correct import for your actual file: Suroot.py (capital S)
from .Suroot import _Suroot

try:
    basestring
except NameError:
    basestring = str


# baseDir should be independent
# It should never be affected by root/sudo/normal user
# It is for cross-application configuration, not logging
# Getting the parent of logDir() is trivial if needed
# We should not couple them
# 
# baseDir()  → /var/myapp        ← user sets this explicitly
#              /home/user/.myapp
#              /opt/myapp
# 
# logDir()   → /var/log/myapp   ← automatically derived only if not set
#              ~/.app/myapp/log


class ChronicleLogger:
    CLASSNAME = "ChronicleLogger"
    MAJOR_VERSION = 0
    MINOR_VERSION = 1
    PATCH_VERSION = 0

    LOG_ARCHIVE_DAYS = 7
    LOG_REMOVAL_DAYS = 30

    def __init__(self, logname=b"app", logdir=b"", basedir=b""):
        self.__logname__ = None
        self.__basedir__ = None
        self.__logdir__ = None
        self.__old_logfile_path__ = ctypes.c_char_p(b"")
        self.__is_python__ = None

        if not logname or logname in (b"", ""):
            return

        self.logName(logname)
        if logdir:
            self.logDir(logdir)
        else:
            self.logDir("")  # triggers default path + directory creation
        self.baseDir(basedir if basedir else "")

        self.__current_logfile_path__ = self._get_log_filename()
        self.ensure_directory_exists(self.__logdir__)

        if self._has_write_permission(self.__current_logfile_path__):
            self.write_to_file("\n")

    def strToByte(self, value):
        if isinstance(value, basestring):
            return value.encode()
        elif value is None or isinstance(value, bytes):
            return value
        raise TypeError(f"Expected str/bytes/None, got {type(value).__name__}")

    def byteToStr(self, value):
        if value is None or isinstance(value, basestring):
            return value
        elif isinstance(value, bytes):
            return value.decode()
        raise TypeError(f"Expected str/bytes/None, got {type(value).__name__}")

    def inPython(self):
        if self.__is_python__ is None:
            self.__is_python__ = 'python' in sys.executable.lower()
        return self.__is_python__

    def logName(self, logname=None):
        if logname is not None:
            self.__logname__ = self.strToByte(logname)
            if self.inPython():
                name = self.__logname__.decode()
                name = re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()
                self.__logname__ = name.encode()
        else:
            return self.__logname__.decode()

    def __set_base_dir__(self, basedir=b""):
        basedir_str = self.byteToStr(basedir)
        if not basedir_str:
            appname = self.__logname__.decode()
            if _Suroot.should_use_system_paths():
                path = f"/var/{appname}"
            else:
                home = os.path.expanduser("~")
                path = os.path.join(home, f".app/{appname}")
            self.__basedir__ = path
        else:
            self.__basedir__ = basedir_str

    def baseDir(self, basedir=None):
        if basedir is not None:
            self.__set_base_dir__(basedir)
        else:
            if self.__basedir__ is None:
                self.__set_base_dir__()
            return self.__basedir__

    def __set_log_dir__(self, logdir=b""):
        logdir_str = self.byteToStr(logdir)
        if logdir_str:
            self.__logdir__ = logdir_str
        else:
            appname = self.__logname__.decode()
            if _Suroot.should_use_system_paths():
                self.__logdir__ = f"/var/log/{appname}"
            else:
                home = os.path.expanduser("~")
                self.__logdir__ = os.path.join(home, f".app/{appname}", "log")

    def logDir(self, logdir=None):
        if logdir is not None:
            self.__set_log_dir__(logdir)
        else:
            if self.__logdir__ is None:
                self.__set_log_dir__()
            return self.__logdir__

    def isDebug(self):
        if not hasattr(self, '__is_debug__'):
            self.__is_debug__ = (
                os.getenv("DEBUG", "").lower() == "show" or
                os.getenv("debug", "").lower() == "show"
            )
        return self.__is_debug__

    @staticmethod
    def class_version():
        return f"{ChronicleLogger.CLASSNAME} v{ChronicleLogger.MAJOR_VERSION}.{ChronicleLogger.MINOR_VERSION}.{ChronicleLogger.PATCH_VERSION}"

    def ensure_directory_exists(self, dir_path):
        if dir_path and not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path)
                print(f"Created directory: {dir_path}")
            except Exception as e:
                self.log_message(f"Failed to create directory {dir_path}: {e}", level="ERROR")

    def _get_log_filename(self):
        date_str = datetime.now().strftime('%Y%m%d')
        filename = f"{self.__logdir__}/{self.__logname__.decode()}-{date_str}.log"
        return ctypes.c_char_p(filename.encode()).value

    def log_message(self, message, level=b"INFO", component=b""):
        pid = os.getpid()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        component_str = f" @{self.byteToStr(component)}" if component else ""
        message_str = self.byteToStr(message)
        level_str = self.byteToStr(level).upper()

        log_entry = f"[{timestamp}] pid:{pid} [{level_str}]{component_str} :] {message_str}\n"

        new_path = self._get_log_filename()

        if self.__old_logfile_path__ != new_path:
            self.log_rotation()
            self.__old_logfile_path__ = new_path
            if self.isDebug():
                header = f"[{timestamp}] pid:{pid} [INFO] @logger :] Using {new_path.decode()}\n"
                log_entry = header + log_entry

        if self._has_write_permission(new_path):
            if level_str in ("ERROR", "CRITICAL", "FATAL"):
                print(log_entry.strip(), file=sys.stderr)
            else:
                print(log_entry.strip())
            self.write_to_file(log_entry)

    def _has_write_permission(self, file_path):
        try:
            with open(file_path, 'a'):
                return True
        except (PermissionError, IOError):
            print(f"Permission denied for writing to {file_path}", file=sys.stderr)
            return False

    def write_to_file(self, log_entry):
        with open(self.__current_logfile_path__, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def log_rotation(self):
        if not os.path.exists(self.__logdir__) or not os.listdir(self.__logdir__):
            return
        self.archive_old_logs()
        self.remove_old_logs()

    def archive_old_logs(self):
        try:
            for file in os.listdir(self.__logdir__):
                if file.endswith(".log"):
                    date_part = file.split('-')[-1].split('.')[0]
                    try:
                        log_date = datetime.strptime(date_part, '%Y%m%d')
                        if (datetime.now() - log_date).days > self.LOG_ARCHIVE_DAYS:
                            self._archive_log(file)
                    except ValueError:
                        continue
        except Exception as e:
            print(f"Error during archive: {e}", file=sys.stderr)

    def _archive_log(self, filename):
        log_path = os.path.join(self.__logdir__, filename)
        archive_path = log_path + ".tar.gz"
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(log_path, arcname=filename)
            os.remove(log_path)
            print(f"Archived log file: {archive_path}")
        except Exception as e:
            print(f"Error archiving {filename}: {e}", file=sys.stderr)

    def remove_old_logs(self):
        try:
            for file in os.listdir(self.__logdir__):
                if file.endswith(".log"):
                    date_part = file.split('-')[-1].split('.')[0]
                    try:
                        log_date = datetime.strptime(date_part, '%Y%m%d')
                        if (datetime.now() - log_date).days > self.LOG_REMOVAL_DAYS:
                            os.remove(os.path.join(self.__logdir__, file))
                    except ValueError:
                        continue
        except Exception as e:
            print(f"Error during removal: {e}", file=sys.stderr)
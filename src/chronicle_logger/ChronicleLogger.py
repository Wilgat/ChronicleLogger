# -*- coding: utf-8 -*-
# NEW: __future__ imports for Py2/3 compatibility (print_function for print(..., file=), absolute_import for relative ., unicode_literals for str/bytes handling, division for /)
from __future__ import print_function, absolute_import, division, unicode_literals

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

# NEW: io.open fallback for encoding='utf-8' support in Py2 (io.open added in Py2.6; use conditional for safety)
try:
    from io import open as io_open
except ImportError:
    io_open = open

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
# logDir()   → /var/log/myapp   ← automatically derived only if user is root
#              ~/.app/myapp/log ← if user is non-root (no matter is sudo or not )


class ChronicleLogger:
    CLASSNAME = "ChronicleLogger"
    MAJOR_VERSION = 0
    MINOR_VERSION = 1
    PATCH_VERSION = 1

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
        # After this, the logDir() should return the log path
        # for root it's should starts with /etc/appname/log/...
        # for non-root (no matter is sudo or not ) with ~/.app/appname/log
        self.baseDir(basedir if basedir else "")

        self.__current_logfile_path__ = self._get_log_filename()
        self.ensure_directory_exists(self.__logdir__)

        if self._has_write_permission(self.__current_logfile_path__):
            self.write_to_file("\n")

    def strToByte(self, value):
        if isinstance(value, basestring):
            return value.encode('utf-8')  # NEW: Explicit utf-8 for Py3 bytes consistency
        elif value is None or isinstance(value, bytes):
            return value
        # NEW: Replaced f-string with .format() for Py2 compat
        raise TypeError("Expected str/bytes/None, got {0}".format(type(value).__name__))

    def byteToStr(self, value):
        if value is None or isinstance(value, basestring):
            return value
        elif isinstance(value, bytes):
            return value.decode('utf-8')  # NEW: Explicit utf-8 for Py2/3 consistency
        # NEW: Replaced f-string with .format()
        raise TypeError("Expected str/bytes/None, got {0}".format(type(value).__name__))

    def inPython(self):
        if self.__is_python__ is None:
            self.__is_python__ = 'python' in sys.executable.lower()
        return self.__is_python__

    def logName(self, logname=None):
        if logname is not None:
            self.__logname__ = self.strToByte(logname)
            if self.inPython():
                name = self.__logname__.decode('utf-8')  # NEW: Explicit decode
                name = re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()
                self.__logname__ = name.encode('utf-8')  # NEW: Explicit encode
        else:
            return self.__logname__.decode('utf-8')  # NEW: Explicit decode

    def __set_base_dir__(self, basedir=b""):
        basedir_str = self.byteToStr(basedir)
        if not basedir_str or basedir_str=='':
            appname = self.__logname__.decode('utf-8')  # NEW: Explicit decode
            if _Suroot.should_use_system_paths():
                # NEW: Replaced f-string with .format()
                path = "/var/{0}".format(appname)
            else:
                home = os.path.expanduser("~")
                # NEW: Replaced f-string with .format()
                path = os.path.join(home, ".app/{0}".format(appname))
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
        if logdir_str and logdir_str!='':
            self.__logdir__ = logdir_str
        else:
            appname = self.__logname__.decode('utf-8')  # NEW: Explicit decode
            if _Suroot.should_use_system_paths():
                # NEW: Replaced f-string with .format()
                self.__logdir__ = "/var/log/{0}".format(appname)
            else:
                home = os.path.expanduser("~")
                # NEW: Replaced f-string with .format()
                self.__logdir__ = os.path.join(home, ".app/{0}".format(appname), "log")

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
        # NEW: Replaced f-string with .format()
        return "{0.CLASSNAME} v{0.MAJOR_VERSION}.{0.MINOR_VERSION}.{0.PATCH_VERSION}".format(ChronicleLogger)

    def ensure_directory_exists(self, dir_path):
        # Example for ensure_directory_exists (around line 172)
        try:
            os.makedirs(dir_path)
            print("Created directory: {0}".format(dir_path))
        except Exception:
            # NEW: Version-conditional exception syntax for Py2/3 compat (comma in Py2, 'as' in Py3)
            if sys.version_info[0] < 3:
                exc_type, exc_value, exc_tb = sys.exc_info()
                e = exc_value  # Bind e for Py2
            else:
                exc_type, exc_value, exc_tb = sys.exc_info()
                e = exc_value  # Use as e implicitly via exc_info for consistency
            #self.log_message("Failed to create directory {0}: {1}".format(dir_path, e), level="ERROR")

    def _get_log_filename(self):
        date_str = datetime.now().strftime('%Y%m%d')
        # NEW: Replaced f-string with .format(); explicit decode/encode for path handling
        dir_decoded = self.__logdir__.decode('utf-8') if isinstance(self.__logdir__, bytes) else self.__logdir__
        name_decoded = self.__logname__.decode('utf-8')
        filename = "{0}/{1}-{2}.log".format(dir_decoded, name_decoded, date_str)
        return ctypes.c_char_p(filename.encode('utf-8')).value

    def log_message(self, message, level=b"INFO", component=b""):
        pid = os.getpid()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        component_str = " @{0}".format(self.byteToStr(component)) if component else ""  # NEW: Replaced f-string with .format()
        message_str = self.byteToStr(message)
        level_str = self.byteToStr(level).upper()

        # NEW: Replaced f-string with .format()
        log_entry = "[{0}] pid:{1} [{2}]{3} :] {4}\n".format(timestamp, pid, level_str, component_str, message_str)

        new_path = self._get_log_filename()

        if self.__old_logfile_path__ != new_path:
            self.log_rotation()
            self.__old_logfile_path__ = new_path
            if self.isDebug():
                # NEW: Replaced f-string with .format(); handle new_path decode
                new_path_decoded = new_path.decode('utf-8') if isinstance(new_path, bytes) else new_path
                header = "[{0}] pid:{1} [INFO] @logger :] Using {2}\n".format(timestamp, pid, new_path_decoded)
                log_entry = header + log_entry

        if self._has_write_permission(new_path):
            if level_str in ("ERROR", "CRITICAL", "FATAL"):
                print(log_entry.strip(), file=sys.stderr)
            else:
                print(log_entry.strip())
            self.write_to_file(log_entry)

    def _has_write_permission(self, file_path):
        # Example for _has_write_permission
        try:
            with open(file_path, 'a'):
                return True
        except:
            # NEW: Version-conditional for multi-exceptions: tuple in Py3, comma-tuple in Py2
            if sys.version_info[0] < 3:
                exc_type, exc_value, exc_tb = sys.exc_info()
                if issubclass(exc_type, (OSError, IOError)):  # Check Py2 equivalents
                    e = exc_value
                    print("Permission denied for writing to {0}".format(file_path), file=sys.stderr)
                    return False
            else:
                exc_type, exc_value, exc_tb = sys.exc_info()
                if issubclass(exc_type, (OSError, IOError)):
                    e = exc_value
                    print("Permission denied for writing to {0}".format(file_path), file=sys.stderr)
                    return False

    def write_to_file(self, log_entry):
        # NEW: Use io_open for encoding support in Py2/3
        with io_open(self.__current_logfile_path__, 'a', encoding='utf-8') as f:
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
        except Exception:
            # NEW: Cross-version exception handling with sys.exc_info() for Py2/3 compat (avoids comma/as syntax errors; binds e safely)
            exc_type, exc_value, exc_tb = sys.exc_info()
            e = exc_value  # Access e in both Py2 and Py3
            # NEW: Replaced f-string with .format() (already done, but confirmed for compat)
            print("Error during archive: {0}".format(e), file=sys.stderr)
            

    def _archive_log(self, filename):
        log_path = os.path.join(self.__logdir__, filename)
        archive_path = log_path + ".tar.gz"
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(log_path, arcname=filename)
            os.remove(log_path)
            # NEW: Replaced f-string with .format()
            print("Archived log file: {0}".format(archive_path))
        except Exception:
            # NEW: Cross-version exception handling with sys.exc_info() for Py2/3 compat (avoids comma/as syntax errors; binds e safely)
            exc_type, exc_value, exc_tb = sys.exc_info()
            e = exc_value  # Access e in both Py2 and Py3
            # NEW: Replaced f-string with .format()
        print("Error archiving {0}: {1}".format(filename, e), file=sys.stderr)

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
        except Exception:
            # NEW: Cross-version exception handling with sys.exc_info() for Py2/3 compat (avoids comma/as syntax errors; binds e safely)
            exc_type, exc_value, exc_tb = sys.exc_info()
            e = exc_value  # Access e in both Py2 and Py3
            # NEW: Replaced f-string with .format()
            print("Error during removal: {0}".format(e), file=sys.stderr)
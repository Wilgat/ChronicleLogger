# -*- coding: utf-8 -*-
# src/chronicle_logger/ChronicleLogger.py
"""
ChronicleLogger - High-performance, cross-version (Python 2.7 ↔ 3.x) logging utility

Features:
- Daily log rotation: <appname>-YYYYMMDD.log
- Automatic archiving to tar.gz after 7 days
- Removal of logs older than 30 days
- Privilege-aware paths:
  - Real root → /var/<appname>/log
  - Non-root (including sudo) → ~/.app/<appname>/log
- Automatic detection & isolation in venv / pyenv / pyenv-virtualenv / conda
- Console mirroring (stdout + stderr)
- UTF-8 safe byte/string handling
- Lazy evaluation for performance
- No external dependencies except standard library
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import os
import sys
import ctypes
import tarfile
import re
from datetime import datetime
import subprocess

from .Suroot import _Suroot
from .TimeProvider import TimeProvider

try:
    basestring
except NameError:
    basestring = str

try:
    from io import open as io_open
except ImportError:
    io_open = open


class ChronicleLogger:
    """Main logging class with environment-aware, privilege-aware, rotating logs."""

    CLASSNAME = "ChronicleLogger"
    MAJOR_VERSION = 1
    MINOR_VERSION = 2
    PATCH_VERSION = 3

    LOG_ARCHIVE_DAYS = 7
    LOG_REMOVAL_DAYS = 30

    def __init__(self, logname=b"app", logdir=b"", basedir=b"", time_provider=None):
        """
        Initialize the logger with application name and optional custom paths.

        Args:
            logname (bytes or str): Application/logger name
                                   (will be automatically kebab-cased in Python mode)
            logdir (bytes or str, optional): Explicit log directory path.
                                            If empty → auto-detected
            basedir (bytes or str, optional): Explicit base directory (configs).
                                             If empty → auto-detected

        Detection priority when not provided explicitly:
            1. Explicit value
            2. Active conda/pyenv/venv environment + /.app/<appname>
            3. User home: ~/.app/<appname> (non-root) or /var/<appname> (root)

        Side effects:
            - Creates log directory if needed
            - Tests write permission by writing an empty line
        """
        self.__logname__ = None
        self.__basedir__ = None
        self.__logdir__ = None
        self.__old_logfile_path__ = ctypes.c_char_p(b"")
        self.__is_python__ = None
        self.time_provider = time_provider or TimeProvider()
        if not logname or logname in (b"", ""):
            return

        self.logName(logname)
        self.baseDir(basedir if basedir else "")
        if logdir:
            self.logDir(logdir)
        else:
            self.logDir("")  # triggers default path + directory creation

        self.__current_logfile_path__ = self._get_log_filename()
        self.ensure_directory_exists(self.__logdir__)

        if self._has_write_permission(self.__current_logfile_path__):
            self.write_to_file("\n")

    def prn(self, msg):
        """Simple wrapper: print message to stdout."""
        print(msg)

    def prn_err(self, msg):
        """Simple wrapper: print message to stderr."""
        print(msg, file=sys.stderr)

    def strToByte(self, value):
        """
        Convert string, bytes or None → bytes (UTF-8).

        Args:
            value: str, bytes or None

        Returns:
            bytes or None

        Raises:
            TypeError: on unsupported type
        """
        if isinstance(value, basestring):
            return value.encode('utf-8')
        elif value is None or isinstance(value, bytes):
            return value
        raise TypeError("Expected str/bytes/None, got {0}".format(type(value).__name__))

    def byteToStr(self, value):
        """
        Convert bytes, str or None → string (UTF-8 decoded).

        Args:
            value: str, bytes or None

        Returns:
            str or None

        Raises:
            TypeError: on unsupported type
        """
        if value is None or isinstance(value, basestring):
            return value
        elif isinstance(value, bytes):
            return value.decode('utf-8')
        raise TypeError("Expected str/bytes/None, got {0}".format(type(value).__name__))

    def split_cmd(self, cmd_path):
        """Split path into components using OS-appropriate separator."""
        if "/" in cmd_path:
            return cmd_path.split("/")
        if "\\" in cmd_path:
            return cmd_path.split("\\")
        return [cmd_path]

    def cmd_name(self, cmd_path):
        """Extract basename from executable path."""
        return self.split_cmd(cmd_path)[-1]

    def inPython(self):
        """
        Check whether we are running in a Python interpreter (vs Cython compiled binary).

        Returns:
            bool: True if running via python*/python[23].*
        """
        if self.__is_python__ is None:
            exe_name = self.cmd_name(sys.executable)
            if exe_name.startswith("python2.") or exe_name.startswith("python3."):
                self.__is_python__ = True
            else:
                self.__is_python__ = exe_name in ['python', 'python2', 'python3']
        return self.__is_python__

    def inPyenv(self):
        """
        Check if interpreter is managed by pyenv.

        Detection method: '/.pyenv/' substring in sys.executable (case-sensitive)

        Returns:
            bool
        """
        if not hasattr(self, '__is_pyenv__'):
            self.__is_pyenv__ = '/.pyenv/' in sys.executable
        return self.__is_pyenv__

    def venv_path(self):
        """
        Get path of active standard Python virtual environment (venv).

        Returns:
            str: path or empty string
        """
        if not hasattr(self, '__venv_path__'):
            self.__venv_path__ = os.environ.get('VIRTUAL_ENV', '')
        return self.__venv_path__

    def inVenv(self):
        """
        Check if running inside a standard Python venv.

        Returns:
            bool
        """
        if not hasattr(self, '__in_venv__'):
            venv_env = os.environ.get('VIRTUAL_ENV', '')
            self.__in_venv__ = bool(venv_env)
        return self.__in_venv__

    @staticmethod
    def pyenv_versions():
        """Execute 'pyenv versions' command and return output."""
        return subprocess.check_output(['pyenv', 'versions'], stderr=subprocess.STDOUT)

    def grand_path(self, path):
        """Get parent-parent directory (two levels up)."""
        if "/" in path:
            return "/".join(self.split_cmd(path)[:-2])
        if "\\" in path:
            return "\\".join(self.split_cmd(path)[:-2])
        return ''

    def pyenvVenv(self):
        """
        Get path of currently active pyenv-virtualenv environment.

        Uses 'pyenv versions' output to find active (*) venv.
        Caches result.

        Returns:
            str: venv path or empty string
        """
        if not hasattr(self, '__pyenv_venv_path__'):
            self.__pyenv_venv_path__ = ''
            if self.inPyenv():
                if self.split_cmd(sys.executable)[-2] == 'bin':
                    self.__pyenv_venv_path__ = self.grand_path(sys.executable)
                try:
                    result = self.pyenv_versions()
                    if hasattr(result, 'decode'):
                        output = result.decode('utf-8') if sys.version_info[0] < 3 else result.decode('utf-8')
                    else:
                        output = result
                    lines = output.strip().split('\n')
                    for line in lines:
                        if '*' in line and '-->' in line:
                            path_start = line.find('--> ') + 4
                            path = line[path_start:].strip()
                            if ' (' in path:
                                path = path.rsplit(' (', 1)[0].strip()
                            if path and os.path.exists(path):
                                self.__pyenv_venv_path__ = path
                                break
                except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
                    self.__pyenv_venv_path__ = ''
        return self.__pyenv_venv_path__

    def inConda(self):
        """
        Check if running inside a Conda/Anaconda/Miniconda environment.

        Returns:
            bool
        """
        if not hasattr(self, '__in_conda__'):
            conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')
            self.__in_conda__ = bool(conda_env) or 'conda' in sys.executable
        return self.__in_conda__

    @staticmethod
    def conda_env_list():
        """Execute 'conda env list' command and return output."""
        return subprocess.check_output(['conda', 'env', 'list'], stderr=subprocess.STDOUT)

    def condaPath(self):
        """
        Get path of currently active Conda environment.

        Priority: CONDA_DEFAULT_ENV → parse 'conda env list'

        Returns:
            str: env path or empty string
        """
        if not hasattr(self, '__conda_path__'):
            self.__conda_path__ = ''
            try:
                result = ChronicleLogger.conda_env_list()
                output = result.decode('utf-8') if sys.version_info[0] < 3 else result.decode('utf-8')
                lines = output.strip().split('\n')
                for line in lines:
                    if "#" not in line and '*' in line:
                        parts = re.split(r'\s{2,}', line.strip())
                        if len(parts) >= 2:
                            path = parts[-1].strip()
                            if path and os.path.exists(path):
                                self.__conda_path__ = path
                                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.__conda_path__ = ''
        return self.__conda_path__

    def logName(self, logname=None):
        """
        Get or set the logger name.

        In Python mode (not Cython): converts CamelCase → kebab-case

        Args:
            logname (bytes/str/None): new name or None to get current

        Returns:
            str: current name (decoded)
        """
        if logname is not None:
            self.__logname__ = self.strToByte(logname)
            if self.inPython():
                name = self.__logname__.decode('utf-8')
                name = re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()
                self.__logname__ = name.encode('utf-8')
        else:
            return self.__logname__.decode('utf-8')

    def __set_base_dir__(self, basedir=b""):
        """Internal: lazy set base directory according to environment hierarchy."""
        basedir_str = self.byteToStr(basedir)
        if basedir_str and basedir_str != '':
            self.__basedir__ = basedir_str
        else:
            appname = self.byteToStr(self.__logname__)
            if not hasattr(self, '__basedir__') or self.__basedir__ is None:
                conda_path = self.condaPath()
                if self.inConda() and conda_path:
                    self.__basedir__ = os.path.join(conda_path, ".app", appname)
                else:
                    pyenv_path = self.pyenvVenv()
                    if pyenv_path:
                        self.__basedir__ = os.path.join(pyenv_path, ".app", appname)
                    else:
                        venv_path = self.venv_path()
                        if venv_path:
                            self.__basedir__ = os.path.join(venv_path, ".app", appname)
                        else:
                            user_home = ChronicleLogger.user_home()
                            app_path = os.path.join(user_home, ".app", appname)
                            if self.is_root():
                                self.__basedir__ = "/var/{0}".format(appname)
                            else:
                                self.__basedir__ = app_path

    def baseDir(self, basedir=None):
        """
        Get or set base directory (configs, not logs).

        Args:
            basedir (bytes/str/None): new value or None to get

        Returns:
            str: current base directory (decoded)
        """
        if basedir is not None:
            self.__set_base_dir__(basedir)
        else:
            if self.__basedir__ is None:
                self.__set_base_dir__(b"")
            return self.__basedir__

    @staticmethod
    def user_home():
        """Get current user's home directory."""
        return os.path.expanduser("~")

    @staticmethod
    def is_root():
        """Check if current effective user is root."""
        return _Suroot.is_root()

    @staticmethod
    def can_sudo():
        """Check if sudo is available without password."""
        return _Suroot.can_sudo_without_password()

    @staticmethod
    def root_or_sudo():
        """Check if we are root or can become root without password."""
        return _Suroot.can_sudo_without_password() or _Suroot.is_root()

    def __set_log_dir__(self, logdir=b""):
        """Internal: lazy set log directory (defaults to baseDir/log)."""
        logdir_str = self.byteToStr(logdir)
        if logdir_str and logdir_str != '':
            self.__logdir__ = logdir_str
        else:
            self.baseDir()  # ensure baseDir is computed
            appname = self.byteToStr(self.__logname__)
            self.__logdir__ = "{0}/log".format(self.__basedir__)

    def logDir(self, logdir=None):
        """
        Get or set log directory path.

        Default when unset: baseDir() + "/log"

        Args:
            logdir (bytes/str/None): new value or None to get

        Returns:
            str: current log directory (decoded)
        """
        if logdir is not None:
            self.__set_log_dir__(logdir)
        else:
            if self.__logdir__ is None:
                self.__set_log_dir__(b"")
            return self.__logdir__

    def isDebug(self):
        """
        Check if debug mode is enabled via environment variable.

        Accepted values (case-insensitive): "show", "true", "1"

        Returns:
            bool
        """
        if not hasattr(self, '__is_debug__'):
            debug = os.getenv("DEBUG", "").lower()
            if not debug:
                debug = os.getenv("debug", "").lower()
            self.__is_debug__ = (
                debug == "show" or
                debug == "true" or
                debug == "1"
            )
        return self.__is_debug__

    @staticmethod
    def class_version():
        """Return current version string of this class."""
        return "{0.CLASSNAME} v{0.MAJOR_VERSION}.{0.MINOR_VERSION}.{0.PATCH_VERSION}".format(ChronicleLogger)

    def ensure_directory_exists(self, dir_path):
        """
        Create directory recursively if it doesn't exist.

        Args:
            dir_path (str/bytes): directory to create

        Side effects:
            Prints creation message to stdout on success
        """
        try:
            os.makedirs(dir_path)
            self.prn("Created directory: {0}".format(dir_path))
        except Exception:
            if sys.version_info[0] < 3:
                exc_type, exc_value, exc_tb = sys.exc_info()
                e = exc_value
            else:
                exc_type, exc_value, exc_tb = sys.exc_info()
                e = exc_value

    def _get_log_filename(self):
        """
        Generate full path to current daily log file.

        Returns:
            bytes: encoded path
        """
        date_str = self.time_provider.strftime(
            self.time_provider.now(), '%Y%m%d'
        )        
        dir_decoded = self.__logdir__.decode('utf-8') if isinstance(self.__logdir__, bytes) else self.__logdir__
        name_decoded = self.__logname__.decode('utf-8')
        filename = "{0}/{1}-{2}.log".format(dir_decoded, name_decoded, date_str)
        return ctypes.c_char_p(filename.encode('utf-8')).value

    def log_message(self, message, level=b"INFO", component=b""):
        """
        Main logging method.

        Format example:
            [2025-12-25 14:30:45] pid:12345 [INFO] @database :] Connected successfully

        Features:
            - Automatic daily rotation
            - Archiving & cleanup on rotation
            - Console output (stdout/stderr)
            - File write with permission check

        Args:
            message (str/bytes): log content
            level (bytes/str): INFO/WARNING/ERROR/CRITICAL/FATAL/DEBUG
            component (bytes/str): optional subsystem name
        """
        pid = os.getpid()
        timestamp = self.time_provider.strftime(
            self.time_provider.now(), "%Y-%m-%d %H:%M:%S"
        )
        component_str = " @{0}".format(self.byteToStr(component)) if component else ""
        message_str = self.byteToStr(message)
        level_str = self.byteToStr(level).upper()

        log_entry = "[{0}] pid:{1} [{2}]{3} :] {4}\n".format(
            timestamp, pid, level_str, component_str, message_str)

        new_path = self._get_log_filename()

        if self.__old_logfile_path__ != new_path:
            self.log_rotation()
            self.__old_logfile_path__ = new_path
            if self.isDebug():
                new_path_decoded = new_path.decode('utf-8') if isinstance(new_path, bytes) else new_path
                header = "[{0}] pid:{1} [INFO] @logger :] Using {2}\n".format(
                    timestamp, pid, new_path_decoded)
                log_entry = header + log_entry

        if self._has_write_permission(new_path):
            if level_str in ("ERROR", "CRITICAL", "FATAL"):
                self.prn_err(log_entry.strip())
            else:
                self.prn(log_entry.strip())
            self.write_to_file(log_entry)

    def _has_write_permission(self, file_path):
        """
        Test whether we can append to the given file.

        Returns:
            bool: True if writable, False otherwise (prints warning to stderr)
        """
        try:
            with open(file_path, 'a'):
                return True
        except:
            if sys.version_info[0] < 3:
                exc_type, exc_value, exc_tb = sys.exc_info()
                if issubclass(exc_type, (OSError, IOError)):
                    self.prn_err("Permission denied for writing to {0}".format(file_path))
                    return False
            else:
                exc_type, exc_value, exc_tb = sys.exc_info()
                if issubclass(exc_type, (OSError, IOError)):
                    self.prn_err("Permission denied for writing to {0}".format(file_path))
                    return False

    def write_to_file(self, log_entry):
        """Append log entry to current log file using UTF-8 encoding."""
        with io_open(self.__current_logfile_path__, 'a', encoding='utf-8') as f:
            f.write(log_entry)

    def log_rotation(self):
        """
        Trigger log maintenance when date changes:
        - archive old logs
        - remove very old logs
        """
        if not os.path.exists(self.__logdir__) or not os.listdir(self.__logdir__):
            return
        self.archive_old_logs()
        self.remove_old_logs()

    def archive_old_logs(self):
        try:
            now = self.time_provider.now()  # ← Add this
            
            for file in os.listdir(self.__logdir__):
                if file.endswith(".log"):
                    date_part = file.split('-')[-1].split('.')[0]
                    try:
                        log_date = datetime.strptime(date_part, '%Y%m%d')
                        if (now - log_date).days > self.LOG_ARCHIVE_DAYS:
                            self._archive_log(file)
                    except ValueError:
                        continue
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            e = exc_value
            self.prn_err("Error during archive: {0}".format(e))

    def _archive_log(self, filename):
        """Internal: archive single log file to tar.gz and remove original."""
        log_path = os.path.join(self.__logdir__, filename)
        archive_path = log_path + ".tar.gz"
        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(log_path, arcname=filename)
            os.remove(log_path)
            self.prn("Archived log file: {0}".format(archive_path))
        except Exception:
            exc_type, exc_value, exc_tb = sys.exc_info()
            e = exc_value
            self.prn_err("Error archiving {0}: {1}".format(filename, e))

    def remove_old_logs(self):
        """
        Permanently delete:
        - Original .log files older than LOG_REMOVAL_DAYS (30)
        - Archived .tar.gz files older than LOG_REMOVAL_DAYS (30)
        """
        try:
            now = self.time_provider.now()
            removal_threshold = now - self.time_provider.timedelta(days=self.LOG_REMOVAL_DAYS)

            for filename in os.listdir(self.__logdir__):
                full_path = os.path.join(self.__logdir__, filename)

                # Skip if not a log or archive file
                if not (filename.endswith(".log") or filename.endswith(".log.tar.gz")):
                    continue

                # Extract date part (works for both .log and .log.tar.gz)
                try:
                    # Take part before the first .log or .tar.gz
                    base = filename.rsplit('.log', 1)[0]
                    date_part = base.rsplit('-', 1)[-1]
                    log_date = datetime.strptime(date_part, '%Y%m%d')
                except (ValueError, IndexError):
                    continue  # Skip invalid filenames

                if log_date < removal_threshold:
                    if self.isDebug():
                        self.prn(f"Removing old log file: {full_path}")
                    try:
                        os.remove(full_path)
                    except OSError as e:
                        self.prn_err(f"Failed to remove {full_path}: {e}")

        except Exception as e:
            self.prn_err(f"Error during removal process: {e}")

    def currentLogFile(self):
        """
        Return the full path to the current active log file.
        
        Returns:
            str: Absolute path to the log file being written to (e.g. /path/to/test-app-20251225.log)
                 Returns empty string if not initialized properly.
        """
        if self.__current_logfile_path__ is None:
            return ""
        # Convert bytes back to str (since we store it as c_char_p bytes)
        path_bytes = self._get_log_filename()
        return path_bytes.decode('utf-8') if isinstance(path_bytes, bytes) else path_bytes    

    def absoluteLogDir(self):
        """
        Return the absolute path to the current log directory.
        """
        if self.__logdir__ is None:
            return ""
        dir_bytes = self.__logdir__
        return dir_bytes.decode('utf-8') if isinstance(dir_bytes, bytes) else dir_bytes
    
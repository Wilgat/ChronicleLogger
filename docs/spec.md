# Design Document for `ChronicleLogger`

## Overview
The ChronicleLogger is a "CyMaster Binary" type project. It aims to act as a module that provides a `ChronicleLogger` class serving as a robust logging utility for applications, specifically designed for Linux environments. It ensures consistent and reliable logging functionalities while adhering to versioning and dependency management principles. This updated implementation introduces enhanced features such as automatic log rotation based on daily filenames, archiving of old logs into compressed tar.gz files after 7 days (configurable via `LOG_ARCHIVE_DAYS`), and removal of logs older than 30 days (configurable via `LOG_REMOVAL_DAYS`). The class handles byte/string compatibility for Python 2/3, lazy evaluation for attributes like debug mode and execution context (e.g., detecting if running in Python via `inPython()`), and privilege-aware directory resolution using the `Sudoer` module for root vs. user contexts. Log messages include timestamps, process IDs (PID), levels (e.g., INFO, ERROR, DEBUG), optional components, and are written to daily log files with console output. Permission checks ensure safe writing, and the design supports Cython compilation for performance in Linux-specific file handling and permissions.

Key updates in this version (PATCH_VERSION=19) include:
- Improved byte handling with `strToByte()` for cross-version compatibility.
- Dynamic log directory and base directory setup based on user privileges (e.g., `/var/log/<app>` for root, `~/.app/log` for users).
- Log name normalization (e.g., camelCase to kebab-case lowercase if running in Python).
- Debug mode detection via environment variables (e.g., `DEBUG=show`).
- Static `class_version()` method for versioning, similar to usage in dependent classes like HelloWorld.
- Log rotation triggered on new daily files, with archiving and cleanup to manage disk space.
- Enhanced initialization with lazy attribute setup and initial permission checks.
- Refined logging output routing: ERROR, CRITICAL, FATAL levels to stderr; others to stdout.
- Improved archiving and removal logic with error handling and console feedback via stderr for issues.

The class depends on external modules like `Sudoer` for privilege checks and standard libraries such as `os`, `sys`, `ctypes`, `tarfile`, `re`, and `datetime`. For building as a Cython project, the source is in `ChronicleLogger.pyx`, compiled to shared object (`.so`) binaries for architectures like x86_64 or ARM.

### Standard Devices
In the context of logging, standard devices such as `stdin`, `stdout`, and `stderr` play a crucial role:

- **stdout**: Used for regular log messages, such as informational logs and debug messages.
- **stderr**: Used for error logs, including severe issues that require immediate attention (e.g., ERROR, CRITICAL, and FATAL log levels). Additionally, permission errors, archiving/removal failures, and directory creation notices are directed here for immediate visibility.

Using `stderr` for error messages ensures that critical issues are separated from regular output and can be easily monitored or redirected.

### Lazy Evaluation
**Lazy evaluation** is a programming technique where the evaluation of an expression is delayed until its value is needed. This can improve performance by avoiding unnecessary calculations, especially for resource-intensive tasks or operations that may not be needed.

#### Example
In `ChronicleLogger`, lazy evaluation is used for attributes like `__is_python__`, `__basedir__`, and `__logdir__`. The attribute is only evaluated when it's first accessed, preventing unnecessary checks during initialization. For instance, `inPython()` and the getters for `baseDir()` and `logDir()` implement this by checking if the internal attribute is `None` before computing it.

```python
def inPython(self):
    if self.__is_python__ is None:  # Lazy evaluation
        self.__is_python__ = 'python' in sys.executable
    return self.__is_python__

def baseDir(self, basedir=None):
    if basedir is not None:
        # Set base directory logic (detailed below)
        pass
    else:
        if self.__basedir__ is None:  # Lazy evaluation
            user_home = os.path.expanduser("~")
            if Sudoer.is_root():
                self.__basedir__ = '/var/{}'.format(self.__logname__.decode())
            else:
                self.__basedir__ = os.path.join(user_home, ".{}".format(self.__logname__.decode()))
            self.__basedir__ = self.__basedir__.encode()  # Convert to bytes
        return self.__basedir__.decode()
```

Similar lazy evaluation applies to `logDir()` for privilege-based path resolution.

### Method: `inPython()`
The `inPython()` method is designed to determine whether the `ChronicleLogger` is being executed in a Python interpreter or as a compiled Cython binary. This distinction is important for configuring the application’s behavior, particularly regarding naming conventions and directory structures.

#### Functionality
- **Purpose**: To check if the current execution context is a Python interpreter or a compiled Cython binary.
- **Implementation**: It checks the executable path used to run the script. If the path contains the string "python", it infers that the application is being run in a Python environment. This uses lazy evaluation to compute only on first access.

```python
def inPython(self):
    if self.__is_python__ is None:  # Lazy evaluation
        self.__is_python__ = 'python' in sys.executable
    return self.__is_python__
```

#### Implications
- **Naming Conventions**: 
  - When running as a compiled Cython binary, the application name is typically in CamelCase (e.g., `DirTree`).
  - When running in a Python environment, the application name is converted to kebab-case (e.g., `dir-tree`) using regex substitution in `logName()`.
  
- **Base Directory Paths**:
  - For compiled Cython binaries, the base directory for non-root users is set to `$HOME/.DirTree`.
  - For Python environments, the base directory is set to `$HOME/.dir-tree`.

This differentiation allows for better organization of configuration files and log directories depending on the context in which the application is running, which is particularly useful in production environments where the application is expected to run as a compiled binary.

## Target Operating System
- **Linux**: This module is designed specifically for Linux environments and may utilize Linux-specific features for file handling and permissions, such as root-aware paths via `Sudoer.is_root()` and `os.path.expanduser("~")` for user homes. On Ubuntu 24.04 (default assumption), behaviors like directory creation (`os.makedirs()`) and file permissions (`_has_write_permission()`) align with POSIX standards; test on other distros for variations in `/var/log` access. Note that behaviors may differ in non-POSIX environments like Windows (e.g., via Git Bash), where path expansions and permissions could require adjustments.

## Class Structure
The `ChronicleLogger` class is structured as follows, with detailed implementations reflecting the updated code:

```python
import os
import sys
import ctypes
import tarfile
import re
from Sudoer import Sudoer
from datetime import datetime

# Compatibility for Python 2 and 3
try:
    basestring
except NameError:
    basestring = str

class ChronicleLogger:
    CLASSNAME = "ChronicleLogger"
    MAJOR_VERSION = 1
    MINOR_VERSION = 0
    PATCH_VERSION = 19  # Updated PATCH_VERSION

    LOG_ARCHIVE_DAYS = 7  # Number of days to keep log files before archiving
    LOG_REMOVAL_DAYS = 30  # Number of days to keep log files before removal

    def __init__(self, logname=b"app", logdir=b"", basedir=b""):
        self.__logname__ = None  # Initialize as None
        self.__basedir__ = None  # Initialize as None
        self.__logdir__ = None  # Initialize as None
        self.__old_logfile_path__ = ctypes.c_char_p(b"")
        self.__is_python__ = None  # Lazy evaluation attribute

        # Set logname and logdir
        self.logName(logname)
        self.logDir(logdir)
        self.baseDir(basedir)

        self.__current_logfile_path__ = self._get_log_filename()
        self.ensure_directory_exists(self.__logdir__.decode())

        if self._has_write_permission(self.__current_logfile_path__):
            self.write_to_file(b"\n")
    
    def strToByte(self, value):
        if isinstance(value, basestring):  # Check if value is a string
            return value.encode()  # Convert str to bytes
        elif value is None or isinstance(value, bytes):
            return value  # Do nothing, return as is
        else:
            raise TypeError("Expected basestring or None or bytes, got {}".format(type(value).__name__))
    
    def inPython(self):
        if self.__is_python__ is None:  # Lazy evaluation
            self.__is_python__ = 'python' in sys.executable
        return self.__is_python__

    def logName(self, logname=None):
        if logname is not None:
            # Convert logname to bytes using strToByte
            self.__logname__ = self.strToByte(logname)

            # Adjust logname if executed by Python
            if self.inPython():
                # Use regex to add hyphens before capital letters and convert to lowercase
                self.__logname__ = re.sub(r'(?<!^)(?=[A-Z])', '-', self.__logname__.decode()).lower().encode()
        else:
            # Getter
            return self.__logname__.decode()

    def baseDir(self, basedir=None):
        if basedir is not None:
            if basedir == b"":
                # Determine basedir based on user privileges
                user_home = os.path.expanduser("~")  # Use string for user home
                if Sudoer.is_root():
                    self.__basedir__ = '/var/{}'.format(self.__logname__.decode())
                else:
                    self.__basedir__ = os.path.join(user_home, ".{}".format(self.__logname__.decode()))
                self.__basedir__ = self.__basedir__.encode()  # Convert to bytes
            else:
                self.__basedir__ = basedir
        else:
            # Getter with lazy evaluation
            if self.__basedir__ is None:
                user_home = os.path.expanduser("~")  # Use string for user home
                if Sudoer.is_root():
                    self.__basedir__ = '/var/{}'.format(self.__logname__.decode())
                else:
                    self.__basedir__ = os.path.join(user_home, ".{}".format(self.__logname__.decode()))
                self.__basedir__ = self.__basedir__.encode()  # Convert to bytes
            return self.__basedir__.decode()

    def logDir(self, logdir=None):
        if logdir is not None:
            if logdir == b"":
                # Determine logdir based on user privileges
                user_home = os.path.expanduser("~")  # Use string for user home
                if Sudoer.is_root():
                    self.__logdir__ = '/var/log/{}'.format(self.__logname__.decode())
                else:
                    self.__logdir__ = os.path.join(user_home, ".{}".format(self.__logname__.decode()), "log")
                self.__logdir__ = self.__logdir__.encode()  # Convert to bytes
            else:
                self.__logdir__ = logdir
        else:
            # Getter with lazy evaluation
            if self.__logdir__ is None:
                user_home = os.path.expanduser("~")  # Use string for user home
                if Sudoer.is_root():
                    self.__logdir__ = '/var/log/{}'.format(self.__logname__.decode())
                else:
                    self.__logdir__ = os.path.join(user_home, ".{}".format(self.__logname__.decode()), "log")
                self.__logdir__ = self.__logdir__.encode()  # Convert to bytes
            return self.__logdir__.decode()

    def isDebug(self):
        if not hasattr(self, '__is_debug__'):
            self.__is_debug__ = ('DEBUG' in os.environ and os.environ['DEBUG'].lower() == 'show') or \
                                ('debug' in os.environ and os.environ['debug'].lower() == 'show')
        return self.__is_debug__

    @staticmethod
    def class_version():
        return "{} v{}.{}.{}".format(ChronicleLogger.CLASSNAME, ChronicleLogger.MAJOR_VERSION, ChronicleLogger.MINOR_VERSION, ChronicleLogger.PATCH_VERSION)

    def ensure_directory_exists(self, dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            print("Created directory: {}".format(dir_path), file=sys.stderr)

    def print_to_console(self, log_entry):
        print(log_entry.decode().strip())

    def print_to_stderr(self, log_entry):
        print(log_entry.decode().strip(), file=sys.stderr)

    def _get_log_filename(self):
        date_str = datetime.now().strftime('%Y%m%d')
        filename = "{}/{}-{}.log".format(self.__logdir__.decode(), self.__logname__.decode(), date_str)
        return ctypes.c_char_p(filename.encode()).value  # Return as cstring

    def log_message(self, message, level=b"INFO", component=b""):
        pid = os.getpid()
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Convert component, message, and level to bytes using strToByte
        component_str = " @{}".format(self.strToByte(component).decode()) if component else ""
        message_str = self.strToByte(message).decode().strip()
        level_str = self.strToByte(level).decode()

        # Construct log_entry as a byte string
        log_entry = "[{}] pid:{} [{}]{} :] {}\n".format(
            self.timestamp, pid, level_str, component_str, message_str
        ).encode()

        new_logfile_path = self._get_log_filename()

        if self.__old_logfile_path__ != new_logfile_path:
            self.log_rotation()
            self.__old_logfile_path__ = new_logfile_path  # Update old_logfile_path
            self.ensure_directory_exists(os.path.dirname(new_logfile_path))  # Ensure parent dir
            if self.isDebug():
                log_entry_header = "[{}] pid:{} [INFO] @logger :] Using {}\n".format(
                    self.timestamp, pid, new_logfile_path
                ).encode()
                log_entry = log_entry_header + log_entry

        if self._has_write_permission(new_logfile_path):
            if level_str.upper() in ['ERROR', 'CRITICAL', 'FATAL']:
                self.print_to_stderr(log_entry)
            else:
                self.print_to_console(log_entry)
            self.write_to_file(log_entry)

    def _has_write_permission(self, file_path):
        try:
            with open(file_path, 'a'):
                return True
        except (PermissionError, IOError):
            print("Permission denied for writing to {}".format(file_path), file=sys.stderr)
            return False

    def write_to_file(self, log_entry):
        # Write log entry to file without adding extra new line
        with open(self.__current_logfile_path__, 'a', encoding='utf-8') as log_file:
            log_file.write(log_entry.decode())  # No additional newline here

    def log_rotation(self):
        logdir_decoded = self.__logdir__.decode()
        if not os.path.exists(logdir_decoded) or not os.listdir(logdir_decoded):
            print("No log files to rotate in directory: {}".format(logdir_decoded), file=sys.stderr)
            return
        
        self.archive_old_logs()
        self.remove_old_logs()

    def archive_old_logs(self):
        logdir_decoded = self.__logdir__.decode()
        try:
            for file in os.listdir(logdir_decoded):
                if file.endswith(".log"):
                    log_date_str = file.split('-')[-1].split('.')[0]
                    log_date = datetime.strptime(log_date_str, '%Y%m%d')
                    if (datetime.now() - log_date).days > self.LOG_ARCHIVE_DAYS:
                        self._archive_log(file.encode())
        except Exception as e:
            print("Error accessing log files for archiving: {}".format(e), file=sys.stderr)

    def _archive_log(self, log_filename):
        logdir_decoded = self.__logdir__.decode()
        log_file_path = os.path.join(logdir_decoded, log_filename.decode())
        archive_name = log_filename.replace(b'.log', b'.tar.gz')
        archive_path = os.path.join(logdir_decoded, archive_name.decode())

        try:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(log_file_path, arcname=log_filename.decode())
            os.remove(log_file_path)  # Remove the original log file after archiving
            print("Archived log file: {}".format(archive_path), file=sys.stderr)
        except Exception as e:
            print("Error archiving log file {}: {}".format(log_filename.decode(), e), file=sys.stderr)

    def remove_old_logs(self):
        logdir_decoded = self.__logdir__.decode()
        try:
            for file in os.listdir(logdir_decoded):
                if file.endswith(".log"):
                    log_date_str = file.split('-')[-1].split('.')[0]
                    log_date = datetime.strptime(log_date_str, '%Y%m%d')
                    if (datetime.now() - log_date).days > self.LOG_REMOVAL_DAYS:
                        os.remove(os.path.join(logdir_decoded, file))
                        print("Removed old log file: {}".format(file), file=sys.stderr)
        except Exception as e:
            print("Error accessing log files for removal: {}".format(e), file=sys.stderr)
```

This structure supports clean separation of source, build artifacts, and documentation. The `build/lib/` contains platform-specific `.so` files generated via CyMaster, avoiding the need for `resolveSysPath()` in static library usage. For version control, initialize Git with `git init`, create a `.gitignore` file to exclude temporary files (e.g., `*.pyc`, `build/` if not committing binaries, `__pycache__/`), and add an `update-log.md` in `docs/` to track changes like this PATCH_VERSION update—ideal for beginners managing multi-OS projects. Note that file operations use UTF-8 encoding where appropriate for cross-platform compatibility, and error messages follow the recommended `print(..., file=sys.stderr)` pattern.

## Usage Example

### 1. Importing ChronicleLogger.pyx or within the same folder
For development or when the source (`ChronicleLogger.pyx`) or built .so is in the project folder (e.g., via CyMaster build), use a direct import after ensuring the path with `resolveSysPath()` if running as a binary—ideal for local testing on Ubuntu 24.04:
```
__file__ = resolveSysPath()  # Optional for Cython binary path resolution

from ChronicleLogger import ChronicleLogger  # Assumes .so or .pyx in same folder or PYTHONPATH
```

### 2. Importing ChronicleLogger stored at /usr/lib/python3.12/lib-dynload/ChronicleLogger.cpython-312-x86_64-linux-gnu.so for Python 3.12
After system-wide installation (e.g., via `setup.py` or CyMaster), the compiled .so is accessible globally for Python 3.12 on x86_64 Linux, enabling seamless imports without path tweaks:
```
from ChronicleLogger import ChronicleLogger  # Assumes installed .so in lib-dynload for Python 3.12
```

### Simple uses: Calling log_message directly for different levels
Once imported, instantiate with a logname (defaults to privilege-based dirs like `~/.myapp/log` for users), then log at various levels—ERROR/CRITICAL/FATAL route to stderr, others to stdout/console, with automatic daily rotation and archiving after 7 days:
```
from ChronicleLogger import ChronicleLogger  # Assumes .so is importable 

# Create a logger instance
logger = ChronicleLogger(logname="myapp")  # Defaults to user/root-appropriate dirs 
# Log messages at different levels
logger.log_message("Critical Message", level="CRITICAL")  # Severe issue, to stderr
logger.log_message("Fatal Message", level="FATAL")  # Unrecoverable, to stderr
logger.log_message("Application started", level="INFO")  # General info, to stdout
logger.log_message("An error occurred", level="ERROR")  # Failure, to stderr
logger.log_message("Debugging information", level="DEBUG", component="main")  # Optional component, to stdout
```

### Checking debug mode
Debug mode (via env var) adds verbose output for levels like DEBUG or ERROR without changing routing, useful for troubleshooting in Example or HelloWorld classes:
```
from ChronicleLogger import ChronicleLogger  # Assumes .so is importable 

# Create a logger instance (set DEBUG=show in env first)
logger = ChronicleLogger(logname="myapp")  # Defaults to user/root-appropriate dirs 
if logger.isDebug():
    logger.log_message("In debug mode", level="DEBUG")  # Enhanced output if enabled
```

### Changing appname if under Python environment, remain the same for compiled Cython binary
The `logName()` method normalizes to kebab-case/lowercase in Python (via regex), but keeps CamelCase for Cython binaries, affecting log paths (e.g., `~/.hello-world/log` vs. `~/.HelloWorld/log`):
```
from ChronicleLogger import ChronicleLogger  # Assumes .so is importable 

# Create a logger instance
logger = ChronicleLogger(logname="HelloWorld")  # Defaults to user/root-appropriate dirs 
appname = logger.logName()    # Returns "hello-world" under Python environment, "HelloWorld" for Cython binary
```

### Getting the correct base dir
`baseDir()` resolves lazily to root/user paths (e.g., `/var/<app>` for sudo, `~/.app` for users), used for logs/config—combine with `logName()` for dynamic setups in projects like ReverseProxy or PyxPy:
```
from ChronicleLogger import ChronicleLogger  # Assumes .so is importable 

# Create a logger instance
logger = ChronicleLogger(logname="ReverseProxy")  # Defaults to user/root-appropriate dirs 
appname = logger.logName()    # Returns "reverse-proxy" under Python environment
basedir = logger.baseDir()           # Returns "/var/reverse-proxy" for root (any env), "~/.reverse-proxy" for user/Python
```

To run an example like the HelloWorld integration, structure your project with folders (e.g., `src/HelloWorld.py`), and execute via `python3 -m src.HelloWorld` from the root. Logs will appear in daily files (e.g., `myapp-20241001.log`), with rotation/archiving handled automatically. Set `DEBUG=show` env var for debug output on new log files. No venv needed unless adding pip deps; prefer pyenv for Python version isolation as noted. For pyenv setup on Ubuntu 24.04: Install via `curl https://pyenv.run | bash`, add to `~/.bashrc`, then `pyenv install 3.12.0` and `pyenv shell 3.12.0` for isolated environments—better than venv for version flexibility without pip deps here.

### Conclusion
The `ChronicleLogger` class provides a comprehensive solution for managing application logging on Linux systems. Through its logging capabilities, user privilege checks via `Sudoer`, automatic rotation/archiving/removal, and byte-safe handling, it ensures reliable execution of logging tasks, making it suitable for various environments. The design emphasizes efficiency (e.g., lazy evaluation, no extra newlines in writes), clarity (e.g., structured log format with PID/timestamp), and adherence to coding standards, enhancing maintainability and usability. For integration in projects like HelloWorld, it supports versioning logs out-of-the-box. Future updates could extend to configurable archive/removal days or multi-process locking.
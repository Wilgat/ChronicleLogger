# Design Document for `ChronicleLogger`

## Overview
The ChronicleLogger is a "CyMaster Binary" type project. It aims to act as a module that provides a `ChronicleLogger` class serving as a robust logging utility for applications, specifically designed for Linux environments. It ensures consistent and reliable logging functionalities while adhering to versioning and dependency management principles. This updated implementation introduces enhanced features such as automatic log rotation based on daily filenames, archiving of old logs into compressed tar.gz files after 7 days (configurable via `LOG_ARCHIVE_DAYS`), and removal of logs older than 30 days (configurable via `LOG_REMOVAL_DAYS`). The class handles byte/string compatibility for Python 2/3, lazy evaluation for attributes like debug mode and execution context (e.g., detecting if running in Python via `inPython()`), and privilege-aware directory resolution using the `_Suroot` module for root vs. user contexts for `logDir()` only. Log messages include timestamps, process IDs (PID), levels (e.g., INFO, ERROR, DEBUG), optional components, and are written to daily log files with console output. Permission checks ensure safe writing, and the design supports Cython compilation for performance in Linux-specific file handling and permissions.

**Important Clarifications to Avoid Misunderstandings:**
- `baseDir()` is **independent of user privileges** (root, sudo, or normal user). It is designed for cross-application configuration, data storage, or other non-logging purposes. It does not automatically adjust based on privileges and should be set explicitly by the user if needed. If you need the parent of `logDir()`, compute it manually (e.g., `os.path.dirname(logger.logDir())`).
- `logDir()` is privilege-aware: Defaults to `/var/log/<app>` for root or passwordless sudo users, and `~/.app/<app>/log` for normal users. This is separate from `baseDir()`.
- Log name normalization in `logName()`: In Python environment, CamelCase is converted to kebab-case-lowercase (e.g., `TestApp` → `test-app`, `HelloWorld` → `hello-world`). In compiled Cython binary, it remains unchanged (e.g., `TestApp` → `TestApp`).
- Directory creation: The log directory is created during `__init__` if a custom `logdir` is provided or when the default is set. It is not assumed to exist at the beginning; creation is lazy but triggered early if a path is set. Do not assume creation until after `__init__` completes.
- Internal paths use bytes for consistency, but public methods like `baseDir()` and `logDir()` return strings for ease of use.
- Privilege detection via `_Suroot` is non-interactive and silent, using `sudo -n` for passwordless sudo checks. It only affects `logDir()` defaults, not `baseDir()` or other parts.

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

The class depends on external modules like `_Suroot` for privilege checks and standard libraries such as `os`, `sys`, `ctypes`, `tarfile`, `re`, and `datetime`. For building as a Cython project, the source is in `ChronicleLogger.pyx`, compiled to shared object (`.so`) binaries for architectures like x86_64 or ARM.

## The folder structure for the project: ChronicleLogger
 * Project: ChronicleLogger is a Cython (CyMaster type) project!
    ```
    ChronicleLogger/
    ├── .gitignore
    ├── README.md
    ├── build/
    │   └── lib/
    │       └── ChronicleLogger.cpython-312-x86_64-linux-gnu.so
    ├── build.sh
    ├── cy-master
    ├── cy-master.ini
    ├── docs/
    │   ├── CHANGELOG.md
    │   ├── ChronicleLogger-spec.md
    │   └── folder-structure.md
    ├── src/
    │   ├── ChronicleLogger.pyx
    │   ├── chronicle_logger/
    │   │   ├── ChronicleLogger.py
    │   │   ├── Suroot.py
    │   │   └── __init__.py
    │   └── setup.py
    └── test/
        └── test_chronicle_logger.py
    ```

### Standard Devices
In the context of logging, standard devices such as `stdin`, `stdout`, and `stderr` play a crucial role:

- **stdout**: Used for regular log messages, such as informational logs and debug messages.
- **stderr**: Used for error logs, including severe issues that require immediate attention (e.g., ERROR, CRITICAL, and FATAL log levels). Additionally, permission errors, archiving/removal failures, and directory creation notices are directed here for immediate visibility.

Using `stderr` for error messages ensures that critical issues are separated from regular output and can be easily monitored or redirected.

### Lazy Evaluation
**Lazy evaluation** is a programming technique where the evaluation of an expression is delayed until its value is needed. This can improve performance by avoiding unnecessary calculations, especially for resource-intensive tasks or operations that may not be needed.

#### Example
In `ChronicleLogger`, lazy evaluation is used for attributes like `__is_python__`, `__basedir__`, and `__logdir__`. The attribute is only evaluated when it's first accessed, preventing unnecessary checks during initialization. For instance, `inPython()` and the getters for `baseDir()` and `logDir()` implement this by checking if the internal attribute is `None` before computing it.

**Clarification to Avoid Misunderstanding:** Lazy evaluation ensures attributes like `baseDir` and `logDir` are computed only when accessed. Note that `baseDir` is not privilege-aware, unlike `logDir`, to maintain independence.

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
The `inPython()` method is designed to determine whether the `ChronicleLogger` is being executed in a Python interpreter or as a compiled Cython binary. This distinction is important for configuring the app name normalization in `logName()`.

**Clarification to Avoid Misunderstanding:** In Python mode, `logName()` normalizes to kebab-case-lowercase (e.g., `TestApp` → `test-app`). In Cython mode, it remains unchanged (e.g., `TestApp` → `TestApp`). This affects path naming but is only applied in Python environments.

### Method: `logName()`
The `logName()` method sets or gets the application log name, with normalization in Python mode.

**Clarification to Avoid Misunderstanding:** Normalization is CamelCase to kebab-case-lowercase (e.g., `TestApp` → `test-app`, `HelloWorld` → `hello-world`). This ensures consistent naming for paths in Python, but is skipped in Cython binaries to preserve original casing.

### Method: `baseDir()`
The `baseDir()` method sets or gets the base directory for cross-application use, such as configuration or data storage.

**Clarification to Avoid Misunderstanding:** `baseDir()` is **not privilege-aware** and does not automatically adjust based on root/sudo/normal user. It is user-settable and independent of logging paths. Do not confuse it with `logDir()`; if you need the parent of `logDir()`, use `os.path.dirname(logger.logDir())`. This design prevents unintended coupling between config and logging.

### Method: `logDir()`
The `logDir()` method sets or gets the log directory, with privilege-aware defaults.

**Clarification to Avoid Misunderstanding:** `logDir()` is privilege-aware using `_Suroot`: `/var/log/<app>` for root/passwordless sudo, `~/.app/<app>/log` for normal users. Custom values override this. Unlike `baseDir()`, it is specifically for logging and adjusts to system context.

### Standard Devices
In the context of logging, standard devices such as `stdin`, `stdout`, and `stderr` play a crucial role:

- **stdout**: Used for regular log messages, such as informational logs and debug messages.
- **stderr**: Used for error logs, including severe issues that require immediate attention (e.g., ERROR, CRITICAL, and FATAL log levels). Additionally, permission errors, archiving/removal failures, and directory creation notices are directed here for immediate visibility.

Using `stderr` for error messages ensures that critical issues are separated from regular output and can be easily monitored or redirected.


### Directory Creation and Initialization
The log directory is created during `__init__` if a custom `logdir` is provided or when the default is set via `logDir("")`.

**Clarification to Avoid Misunderstanding:** The code does not assume the directory exists at the beginning. Creation is triggered during `__init__` based on the set path, but only if the path is non-empty. This is not lazy in the sense of waiting for first write; it happens early to ensure readiness, but without unnecessary assumptions about existence before setup.

### 1. Importing ChronicleLogger from the source folder for local testing on Ubuntu 24.04
To import ChronicleLogger from the source folder, use the following code to import the module after ensuring the path with `resolveSysPath()` if running as a binary—ideal for local testing on Ubuntu 24.04:
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


## The folder structure for the project: ChronicleLogger
 * Project: ChronicleLogger is a Cython (CyMaster type) project!
    ```
    ChronicleLogger/
    ├── .gitignore
    ├── README.md
    ├── build/
    │   └── lib/
    │       └── ChronicleLogger.cpython-312-x86_64-linux-gnu.so
    ├── build.sh
    ├── cy-master
    ├── cy-master.ini
    ├── docs/
    │   ├── CHANGELOG.md
    │   ├── ChronicleLogger-spec.md
    │   ├── folder-structure.md
    │   └── spec.md
    ├── src/
    │   ├── ChronicleLogger.pyx
    │   ├── chronicle_logger/
    │   │   ├── ChronicleLogger.py
    │   │   ├── Suroot.py
    │   │   └── __init__.py
    │   └── setup.py
    └── test/
        └── test_chronicle_logger.py
    ```

### cy-master.ini
 * The cy-master.ini file serves as the primary configuration file for CyMaster-type Cython projects:
    ```
    [project]
    srcFolder = src
    buildFolder = build
    targetName = ChronicleLogger
    targetType = so
    ```
## Target Operating System
- **Linux**: This module is designed specifically for Linux environments and may utilize Linux-specific features for file handling and permissions, such as root-aware paths via `Sudoer.is_root()` and `os.path.expanduser("~")` for user homes. On Ubuntu 24.04 (default assumption), behaviors like directory creation (`os.makedirs()`) and file permissions (`_has_write_permission()`) align with POSIX standards; test on other distros for variations in `/var/log` access. Note that behaviors may differ in non-POSIX environments like Windows (e.g., via Git Bash), where path expansions and permissions could require adjustments.

## Class Structure
The `ChronicleLogger` class is structured as follows, with detailed implementations reflecting the updated code:

```

class ChronicleLogger:
    CLASSNAME = "ChronicleLogger"
    MAJOR_VERSION = 0
    MINOR_VERSION = 1
    PATCH_VERSION = 0

    LOG_ARCHIVE_DAYS = 7
    LOG_REMOVAL_DAYS = 30

    def __init__(self, logname=b"app", logdir=b"", basedir=b""):
        ...

    def strToByte(self, value):
        ...

    def byteToStr(self, value):
        ...

    def inPython(self):
        ...

    def logName(self, logname=None):
        ...

    def __set_base_dir__(self, basedir=b""):
        ...

    def baseDir(self, basedir=None):
        ...

    def __set_log_dir__(self, logdir=b""):
        ...

    def logDir(self, logdir=None):
        ...

    def isDebug(self):
        ...

    @staticmethod
    def class_version():
        ...

    def ensure_directory_exists(self, dir_path):
        ...

    def _get_log_filename(self):
        ...

    def log_message(self, message, level=b"INFO", component=b""):
        ...

    def _has_write_permission(self, file_path):
        ...

    def write_to_file(self, log_entry):
        ...

    def log_rotation(self):
        ...

    def archive_old_logs(self):
        ...

    def _archive_log(self, filename):
        ...

    def remove_old_logs(self):
        ...

```

This structure supports clean separation of source, build artifacts, and documentation. The `build/lib/` contains platform-specific `.so` files generated via CyMaster, avoiding the need for `resolveSysPath()` in static library usage. For version control, initialize Git with `git init`, create a `.gitignore` file to exclude temporary files (e.g., `*.pyc`, `build/` if not committing binaries, `__pycache__/`), and add an `update-log.md` in `docs/` to track changes like this PATCH_VERSION update—ideal for beginners managing multi-OS projects. Note that file operations use UTF-8 encoding where appropriate for cross-platform compatibility, and error messages follow the recommended `print(..., file=sys.stderr)` pattern.


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


### Changing appname if under Python environment, remain the same for compiled Cython binary
The `logName()` method normalizes to kebab-case/lowercase in Python (via regex), but keeps CamelCase for Cython binaries, affecting log paths (e.g., `~/.hello-world/log` vs. `~/.HelloWorld/log`):
```
from ChronicleLogger import ChronicleLogger  # Assumes .so is importable 

# Create a logger instance
logger = ChronicleLogger(logname="HelloWorld")  # Defaults to user/root-appropriate dirs 
appname = logger.logName()    # Returns "hello-world" under Python environment, "HelloWorld" for Cython binary
```

### Conclusion
The `ChronicleLogger` class provides a comprehensive solution for managing application logging on Linux systems. Through its logging capabilities, user privilege checks via `Sudoer`, automatic rotation/archiving/removal, and byte-safe handling, it ensures reliable execution of logging tasks, making it suitable for various environments. The design emphasizes efficiency (e.g., lazy evaluation, no extra newlines in writes), clarity (e.g., structured log format with PID/timestamp), and adherence to coding standards, enhancing maintainability and usability. For integration in projects like HelloWorld, it supports versioning logs out-of-the-box. Future updates could extend to configurable archive/removal days or multi-process locking.

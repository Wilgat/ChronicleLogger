# Design Document for `ChronicleLogger`

## Overview
The ChronicleLogger is a "CyMaster Binary" type project designed as a robust logging utility module for applications, particularly tailored for Linux environments . It provides a `ChronicleLogger` class that ensures consistent logging with features like daily log rotation using date-based filenames (e.g., `cf-ddns-20250926.log`), automatic archiving of logs older than 7 days into compressed tar.gz files (configurable via `LOG_ARCHIVE_DAYS=7`), and removal of logs older than 30 days (configurable via `LOG_REMOVAL_DAYS=30`) . The implementation maintains byte/string compatibility across Python 2.7 and Python 3.x, with lazy evaluation for attributes such as debug mode detection via environment variables (`DEBUG=show`) and execution context checking through `inPython()` to identify if running in a Python interpreter . Privilege-aware directory resolution is handled via the internal `_Suroot` module, distinguishing root contexts (using `/var/log/<app>`) from user contexts (using `~/.app/<app>/log`), without interactive prompts and ensuring non-blocking behavior in CI/CD or tests . Log entries include timestamps in `YYYY-MM-DD HH:MM:SS` format, process IDs (PID), log levels (e.g., INFO, ERROR, DEBUG), optional components (e.g., `main`), and are written to daily files with concurrent console output (stdout for INFO/DEBUG, stderr for ERROR/CRITICAL/FATAL) . Permission checks prevent writes to inaccessible paths, and the class supports semantic versioning at v1.1.0 for backward compatibility .

This version (1.1.0) emphasizes POSIX compliance for Linux deployment, with no external pip dependencies beyond built-in modules and Cythonized internals for performance (e.g., via `ChronicleLogger.pyx` and `ChronicleLogger.c` in the build process) . It integrates with projects like cf-ddns, GaBase, and CyMaster by providing structured logging for API interactions, error handling, and system checks, while avoiding bash-specific features for broad shell compatibility (e.g., Git Bash on Windows) .

## Key Features
- **Log Formatting and Output**: Each log entry follows the structure `[YYYY-MM-DD HH:MM:SS] pid:<PID> [<LEVEL>] @<COMPONENT> :] <MESSAGE>`, appended to daily files without extra newlines for efficiency. Console mirroring uses `print(..., file=sys.stderr)` for errors and `print(...)` for others, ensuring compatibility with Python 2.7's print statement via `__future__` imports .
- **Daily Rotation and Maintenance**: On first write or rotation trigger, the class checks and switches to a new file (e.g., `<app>-YYYYMMDD.log`). The `log_rotation()` method invokes `archive_old_logs()` (tar.gz compression for files >7 days) and `remove_old_logs()` (deletion for files >30 days), parsing filenames for date extraction via `datetime.strptime('%Y%m%d')` . Archiving uses `tarfile.open(..., "w:gz")` to bundle and remove originals, with error handling via `sys.exc_info()` for cross-version exception binding .
- **Privilege Detection**: The `_Suroot` class (version 1.1.0) provides static methods like `is_root()` (via `os.geteuid() == 0`), `can_sudo_without_password()` (non-interactive `sudo -n true` via `subprocess.Popen` with 5s timeout in Py3.3+), and `should_use_system_paths()` to decide paths: `/var/log/<app>` for true root (not sudo), else `~/.app/<app>/log` . It uses a Py2-compatible DEVNULL shim (`open(os.devnull, 'wb')` if unavailable) and avoids type hints for Py2 syntax compatibility .
- **Path Resolution and Customization**: `logDir()` defaults to privilege-based paths but accepts overrides (e.g., custom `logdir`). `baseDir()` is independent, defaulting to `/var/<app>` or `~/.app/<app>` but user-settable for configs (e.g., `/opt/myapp`). Directories are created via `os.makedirs()` with error logging . Log names are kebab-cased in Python mode (e.g., "TestApp" → "test-app") via regex `re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()`, but preserved in Cython binaries .
- **Debug and Versioning**: `isDebug()` checks `os.getenv("DEBUG", "").lower() == "show"`. In debug mode, it logs headers with file paths on rotation and can output dependency versions (e.g., from `AppBase`, `CyMasterCore`) when integrated . Class version is `"ChronicleLogger v1.1.0"`, following semantic versioning .
- **Byte/String Handling**: Methods `strToByte()` and `byteToStr()` ensure UTF-8 encoding/decoding, with `io.open(..., encoding='utf-8')` for writes (fallback to `open` in older Py2). Paths use `ctypes.c_char_p` for C-interop compatibility .
- **Error and Permission Handling**: `_has_write_permission()` tests append mode; failures print to stderr without crashing. Exceptions use version-conditional `sys.exc_info()` to bind `exc_value` safely across Py2/3 .
- **Integration Hooks**: Supports command-line args for API management, IP/subdomain updates, and daemon forking via related modules like `ServiceManager` and `Systemd`, with all output routed through ChronicleLogger . No multi-process locking yet, but future extensions could add it.

## Project Structure
The project follows a standard Python package layout optimized for Cython builds and distribution, supporting isolated environments (e.g., pyenv for version 3.12.0) without pip deps for core functionality . The tree structure is:

```
./
├── build.sh
├── cy-master
├── cy-master.ini
├── dependency-merge
├── dist
│   ├── chroniclelogger-0.1.3-py3-none-any.whl
│   └── chroniclelogger-0.1.3.tar.gz
├── docs
│   ├── CHANGELOG.md
│   ├── ChronicleLogger-spec.md
│   ├── folder-structure.md
│   └── spec.md
├── README.md
├── setup.py
├── src
│   ├── ChronicleLogger
│   │   ├── ChronicleLogger.py
│   │   ├── __init__.py
│   │   └── Suroot.py
│   ├── ChronicleLogger.c
│   ├── ChronicleLogger.pyx
│   └── setup.py
└── test
    └── test_chronicle_logger.py
```

- **src/**: Core source with `ChronicleLogger.pyx` for Cython compilation to `ChronicleLogger.c`, producing bytecode in `__pycache__` (e.g., for Python 3.12). The `ChronicleLogger/` subpackage includes `__init__.py` exposing `ChronicleLogger` via `__all__ = ['ChronicleLogger.ChronicleLogger']` and `__version__ = "1.1.0"`.
- **build/** and **dist/**: Artifacts from `setup.py` builds, including wheel/tar.gz for v0.1.3 (pre-v1.1.0; update via semantic versioning), and bdist for Linux x86_64.
- **docs/**: Specifications like `ChronicleLogger-spec.md` for integration details, `CHANGELOG.md` for updates (recommend appending entries for v1.1.0 changes, e.g., Py2 compat shims), and `folder-structure.md` mirroring this tree .
- **test/**: Unit tests in `test_chronicle_logger.py` using pytest (pinned to 4.6.11 for Py2 compat), with fixtures like `tmpdir` for path mocking, covering init, rotation, debug, and privilege paths. Uses `unittest.mock.patch` (fallback to `mock` for Py2) and `capsys` for output capture.
- **Other**: `build.sh` for automated builds, `setup.py` for packaging (egg-info metadata), `cy-master.ini` for CyMaster integration, and `.gitignore`-recommended ignores for `__pycache__`, `dist/`, etc. .

For setup, recommend pyenv: `pyenv install 3.12.0 && pyenv shell 3.12.0` for isolation, then `python setup.py build_ext --inplace` for Cython, or `pip install -e .` for editable install. Confirm active Python with `which python3` on Linux/macOS or `where python` on Windows; use virtualenvs for deps like pytest==4.6.11 if testing Py2 .

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

## Implementation Details
- **Initialization**: `__init__(logname=b"app", logdir=b"", basedir=b"")` sets kebab-cased name (Py mode only), derives paths, creates dirs via `ensure_directory_exists()`, and tests write with a newline. Uses `ctypes.c_char_p` for internal paths to support Cython shims.
- **Logging Flow**: `log_message(message, level=b"INFO", component=b"")` builds entries, checks rotation via `_get_log_filename()`, writes via `write_to_file()` with `io_open('a', encoding='utf-8')`, and handles permissions.
- **Compatibility Shims**: `__future__` for print/division/unicode; conditional `io.open`; no f-strings (use `.format()`); `sys.exc_info()` for exceptions; `basestring` fallback; Py2 DEVNULL.
- **POSIX Compliance**: All ops use `os.path.join()`, `subprocess.Popen` without bashisms; safe for dash/ash/BusyBox. No arrays or process substitution.

## Testing and Validation
Tests in `test_chronicle_logger.py` verify directory creation, kebab-casing (skipped in Cython mock), path overrides, system/user dirs (mocked `_Suroot`), filename generation, stderr routing for errors, archiving (creates mock old file, checks tar.gz), and debug env. Run with `pytest test/test_chronicle_logger.py -v`, ensuring Py2/3 compat via str paths and open/write over Path objects .

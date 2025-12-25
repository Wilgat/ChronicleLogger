# Design Document for `ChronicleLogger`

## Overview
**ChronicleLogger** is a high-performance, cross-version compatible logging utility designed as a **"CyMaster Binary"** type project. It is published both as a standard **PyPI package** (installable via `pip install ChronicleLogger`) and as a **Cython-optimized module** (compiled to `.so` or `.pyd` binaries for superior speed in production environments).

- **PyPI Package URL**: https://pypi.org/project/ChronicleLogger/
- **Supported Python versions**: Python 2.7 and Python 3.x (full backward and forward compatibility maintained through extensive shims, `__future__` imports, conditional imports, and careful byte/string handling)

The module provides a robust `ChronicleLogger` class with the following core capabilities:
- Daily log rotation using date-based filenames (e.g., `cf-ddns-20250926.log`)
- Automatic archiving of logs older than 7 days into compressed `tar.gz` files (configurable via `LOG_ARCHIVE_DAYS=7`)
- Removal of logs older than 30 days (configurable via `LOG_REMOVAL_DAYS=30`)
- Lazy evaluation for performance-critical attributes (debug mode, paths, environment detection)
- Privilege-aware directory resolution via the internal `_Suroot` module:
  - True root (euid == 0) → system paths like `/var/log/<app>`
  - Non-root (including sudo) → user paths like `~/.app/<app>/log`
- Non-interactive, non-blocking privilege detection (safe in CI/CD, containers, and tests)
- Log entries formatted as: `[YYYY-MM-DD HH:MM:SS] pid:<PID> [<LEVEL>] @<COMPONENT> :] <MESSAGE>`
- Concurrent output: console mirroring (stdout for INFO/DEBUG, stderr for ERROR/CRITICAL/FATAL)
- Strict permission checking to prevent write failures from crashing the application
- Semantic versioning (current: v1.1.0) with strong emphasis on backward compatibility

This version (1.1.0) is specifically engineered for **POSIX-compliant Linux environments** with zero external pip dependencies beyond the Python standard library and Cython (used only for optional compilation). The package supports both:
- Pure-Python usage (great for rapid development, prototyping, and environments where compilation is not desired)
- Cython-compiled usage (recommended for production systems requiring maximum performance)

ChronicleLogger is actively used in projects such as `cf-ddns`, `GaBase`, and `CyMaster`, providing structured, reliable logging for API interactions, error handling, system monitoring, and daemon operations.

It deliberately avoids bashisms and shell-specific features to maintain broad shell compatibility (dash, ash, BusyBox, Git Bash, etc.).

**Installation options** (choose based on your needs):
```bash
# Standard PyPI installation (pure Python - recommended for most users)
pip install ChronicleLogger

# For Cython compilation (faster execution - recommended for production)
# (requires Cython and a C compiler)
pip install cython
pip install ChronicleLogger --no-binary :all:   # forces source build
# or build from source after cloning the repository
python setup.py build_ext --inplace
```

Whether you're working in a simple script, a long-running service, or a performance-critical application, ChronicleLogger delivers consistent, safe, and efficient logging across Python 2.7 and all modern Python 3 versions.

## Key Features
- **Log Formatting and Output**: Each log entry follows the structure `[YYYY-MM-DD HH:MM:SS] pid:<PID> [<LEVEL>] @<COMPONENT> :] <MESSAGE>`, appended to daily files without extra newlines for efficiency. Console mirroring uses `print(..., file=sys.stderr)` for errors and `print(...)` for others, ensuring compatibility with Python 2.7's print statement via `__future__` imports .
- **Daily Rotation and Maintenance**: On first write or rotation trigger, the class checks and switches to a new file (e.g., `<app>-YYYYMMDD.log`). The `log_rotation()` method invokes `archive_old_logs()` (tar.gz compression for files >7 days) and `remove_old_logs()` (deletion for files >30 days), parsing filenames for date extraction via `datetime.strptime('%Y%m%d')` . Archiving uses `tarfile.open(..., "w:gz")` to bundle and remove originals, with error handling via `sys.exc_info()` for cross-version exception binding .
- **Privilege Detection**: The `_Suroot` class (version 1.1.0) provides static methods like `is_root()` (via `os.geteuid() == 0`), `can_sudo_without_password()` (non-interactive `sudo -n true` via `subprocess.Popen` with 5s timeout in Py3.3+), and decides paths: `/var/log/<app>` for true root (not sudo), else `~/.app/<app>/log` . It uses a Py2-compatible DEVNULL shim and avoids type hints for Py2 syntax compatibility .
- **Path Resolution and Customization**: `logDir()` defaults to privilege-based paths but accepts overrides (e.g., custom `logdir`). `baseDir()` is independent, defaulting to `/var/<app>` or `~/.app/<app>` but user-settable for configs (e.g., `/opt/myapp`). Directories are created via `os.makedirs()` with error logging . Log names are kebab-cased in Python mode (e.g., "TestApp" → "test-app") via regex `re.sub(r'(?<!^)(?=[A-Z])', '-', name).lower()`, but preserved in Cython binaries .

  To support isolated Python environments commonly used by developers (such as virtual environments for project-specific dependencies), ChronicleLogger now detects and integrates with popular environment managers like venv (built-in Python virtual environments), pyenv (for managing multiple Python versions), pyenv-virtualenv (pyenv plugin for virtualenvs), and Conda-based environments (including Anaconda and Miniconda, which use Conda for package and environment management). This detection uses lazy evaluation to avoid unnecessary checks and ensures that `baseDir()` and `logDir()` adapt to the active environment, placing logs and configs within the environment's directory to prevent pollution of the global system or user home. This is especially useful for beginners working in isolated setups, as it keeps project files contained—e.g., logs won't mix with system logs even when running as root in a containerized or virtual env.

  The path resolution hierarchy for `baseDir()` (which influences `logDir()` if not explicitly set) is as follows, checked in order:
  1. If an explicit `basedir` is provided during initialization or via `baseDir(basedir)`, use that directly.
  2. If running in a Conda environment (Anaconda or Miniconda, detected via `inConda()`), use the active Conda env path + `/.app/{appname}` (kebab-cased in Python mode).
  3. If running in pyenv and an active pyenv-managed virtualenv (detected via `inPyenv()` and `pyenvVenv()`), use the pyenv venv path + `/.app/{appname}`.
  4. If running in a standard venv (detected via `inVenv()`), use the venv path + `/.app/{appname}`.
  5. Fallback to privilege-based defaults: `/var/{appname}` for root users (preserved case in binary mode), or `~/.app/{appname}` for non-root users (kebab-cased in Python mode).

  `logDir()` is derived from `baseDir() + /log` unless explicitly overridden. Privilege detection (`is_root()`) applies across all cases—for root users in environments, paths still respect the env but may use system-like structures if no env is detected.

  **Examples of Locations (assuming appname="TestApp", kebab-cased to "test-app" in Python mode):**
  - **Explicit basedir/logdir (overrides everything, root or non-root):** `baseDir="/custom/base"`, `logDir="/custom/base/log"`.
  - **Conda (Anaconda/Miniconda) env, non-root:** If active Conda env is `/home/user/miniconda3/envs/myenv`, then `baseDir="/home/user/miniconda3/envs/myenv/.app/test-app"`, `logDir="/home/user/miniconda3/envs/myenv/.app/test-app/log"`.
  - **Conda env, root:** Similar to non-root, but if no env detected, falls back to `/var/test-app` for `baseDir` (and `/var/test-app/log` for `logDir`).
  - **pyenv with virtualenv, non-root:** If pyenv active venv is `/home/user/.pyenv/versions/3.12/envs/myenv`, then `baseDir="/home/user/.pyenv/versions/3.12/envs/myenv/.app/test-app"`, `logDir="/home/user/.pyenv/versions/3.12/envs/myenv/.app/test-app/log"`.
  - **pyenv with virtualenv, root:** Env-based like non-root; fallback to `/var/test-app` if no env.
  - **Standard venv, non-root:** If venv is `/home/user/myproject/venv`, then `baseDir="/home/user/myproject/venv/.app/test-app"`, `logDir="/home/user/myproject/venv/.app/test-app/log"`.
  - **Standard venv, root:** Env-based; fallback to `/var/test-app`.
  - **No env (fallback), non-root:** `baseDir="/home/user/.app/test-app"`, `logDir="/home/user/.app/test-app/log"`.
  - **No env (fallback), root:** `baseDir="/var/TestApp"` (preserved case in binary), `logDir="/var/TestApp/log"`.

  For beginners: These environments (venv, pyenv, Conda) help isolate your project's Python version and packages from the system Python, avoiding conflicts. ChronicleLogger automatically detects them to keep logs within your project space—e.g., run `python -m venv myenv` to create a venv, activate it, and logs will go inside `myenv/.app/test-app/log`.

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

### Method: `inPyenv()`
The `inPyenv()` method checks if the current execution is within a pyenv-managed environment. Pyenv is a tool for managing multiple Python versions on a single system, popular among developers for switching between Python versions easily.

#### Functionality
- **Purpose**: To detect if pyenv is active, helping isolate paths within the pyenv structure.
- **Implementation**: It performs a case-sensitive substring check for '.pyenv' in `sys.executable`. Uses lazy evaluation and caches the result.

```python
def inPyenv(self):
    if not hasattr(self, '__is_pyenv__'):
        self.__is_pyenv__ = '.pyenv' in sys.executable
    return self.__is_pyenv__
```

For beginners: If you're using pyenv (installed via `curl https://pyenv.run | bash`), this method ensures logs stay within your pyenv-managed Python version's directory.

### Method: `venv_path()`
The `venv_path()` method retrieves the path to the active virtual environment (venv), if any. Venv is Python's built-in tool for creating isolated environments.

#### Functionality
- **Purpose**: To get the full path of the active venv for path resolution.
- **Implementation**: Returns `os.environ.get('VIRTUAL_ENV', '')` if set; caches the result with lazy evaluation.

```python
def venv_path(self):
    if not hasattr(self, '__venv_path__'):
        self.__venv_path__ = os.environ.get('VIRTUAL_ENV', '')
    return self.__venv_path__
```

### Method: `inVenv()`
The `inVenv()` method checks if running in a virtual environment.

#### Functionality
- **Purpose**: Boolean check for venv activation.
- **Implementation**: True if `VIRTUAL_ENV` is set and non-empty; lazy evaluation with caching.

```python
def inVenv(self):
    if not hasattr(self, '__in_venv__'):
        venv_env = os.environ.get('VIRTUAL_ENV', '')
        self.__in_venv__ = bool(venv_env)
    return self.__in_venv__
```

For beginners: Create a venv with `python -m venv myenv` and activate it (`source myenv/bin/activate`); this keeps your project's dependencies separate.

### Method: `pyenvVenv()`
The `pyenvVenv()` method gets the path to the active pyenv-managed virtualenv (using pyenv-virtualenv plugin).

#### Functionality
- **Purpose**: To locate the specific virtualenv within pyenv for isolated paths.
- **Implementation**: If `inPyenv()` is True, runs `pyenv versions` via subprocess to parse the active (*) venv path; returns '' if not found. Lazy evaluation with caching; handles path trimming and existence checks.

```python
def pyenvVenv(self):
    if not hasattr(self, '__pyenv_venv_path__'):
        if not self.inPyenv():
            self.__pyenv_venv_path__ = ''
        else:
            try:
                result = subprocess.check_output(['pyenv', 'versions'], stderr=subprocess.STDOUT)
                output = result.decode('utf-8') if sys.version_info[0] < 3 else result.decode('utf-8')
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
                else:
                    self.__pyenv_venv_path__ = ''
            except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
                self.__pyenv_venv_path__ = ''
    return self.__pyenv_venv_path__
```

### Method: `inConda()`
The `inConda()` method checks if running in a Conda environment (covers Anaconda and Miniconda).

#### Functionality
- **Purpose**: To detect Conda for environment-specific paths.
- **Implementation**: True if `CONDA_DEFAULT_ENV` is set or 'conda' in `sys.executable`; lazy evaluation with caching.

```python
def inConda(self):
    if not hasattr(self, '__in_conda__'):
        conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')
        self.__in_conda__ = bool(conda_env) or 'conda' in sys.executable
    return self.__in_conda__
```

For beginners: Anaconda/Miniconda provide Conda for managing environments and packages, especially for data science. Install Miniconda for a lightweight version.

### Method: `condaPath()`
The `condaPath()` method retrieves the path to the active Conda environment.

#### Functionality
- **Purpose**: To get the Conda env path for isolation.
- **Implementation**: Prioritizes `CONDA_DEFAULT_ENV`; else runs `conda env list` via subprocess to parse active (*) path. Lazy evaluation with caching; handles decoding and existence.

```python
def condaPath(self):
    if not hasattr(self, '__conda_path__'):
        conda_env = os.environ.get('CONDA_DEFAULT_ENV', '')
        # ... (truncated for brevity; full logic in code)
    return self.__conda_path__
```

## Target Operating System
- **Linux**: This module is designed specifically for Linux environments and may utilize Linux-specific features for file handling and permissions, such as root-aware paths via `Suroot.is_root()` and `os.path.expanduser("~")` for user homes. On Ubuntu 24.04 (default assumption), behaviors like directory creation (`os.makedirs()`) and file permissions (`_has_write_permission()`) align with POSIX standards; test on other distros for variations in `/var/log` access. Note that behaviors may differ in non-POSIX environments like Windows (e.g., via Git Bash), where path expansions and permissions could require adjustments.

## Implementation Details
- **Initialization**: `__init__(logname=b"app", logdir=b"", basedir=b"")` sets kebab-cased name (Py mode only), derives paths, creates dirs via `ensure_directory_exists()`, and tests write with a newline. Uses `ctypes.c_char_p` for internal paths to support Cython shims.
- **Logging Flow**: `log_message(message, level=b"INFO", component=b"")` builds entries, checks rotation via `_get_log_filename()`, writes via `write_to_file()` with `io_open('a', encoding='utf-8')`, and handles permissions.
- **Compatibility Shims**: `__future__` for print/division/unicode; conditional `io.open`; no f-strings (use `.format()`); `sys.exc_info()` for exceptions; `basestring` fallback; Py2 DEVNULL.
- **POSIX Compliance**: All ops use `os.path.join()`, `subprocess.Popen` without bashisms; safe for dash/ash/BusyBox. No arrays or process substitution.

## Testing and Validation
Tests in `test_chronicle_logger.py` verify directory creation, kebab-casing (skipped in Cython mock), path overrides, system/user dirs (mocked `_Suroot`), filename generation, stderr routing for errors, archiving (creates mock old file, checks tar.gz), and debug env. Run with `pytest test/test_chronicle_logger.py -v`, ensuring Py2/3 compat via str paths and open/write over Path objects.

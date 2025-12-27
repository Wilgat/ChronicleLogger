# ChronicleLogger

A robust, POSIX-compliant logging utility for Python applications, supporting Python 2.7 and 3.x with optional Cython compilation for enhanced performance. It handles daily log rotation, automatic archiving (tar.gz for logs >7 days), removal (>30 days), privilege-aware paths (/var/log for root, ~/.app for users), and structured output with timestamps, PIDs, levels, and components. No external dependencies beyond the standard library; semantic version 1.2.3.

- **PyPI Package URL**: https://pypi.org/project/ChronicleLogger/
- **Supported Environments**: Seamlessly integrates with venv, pyenv, pyenv-virtualenv, Anaconda, and Miniconda for isolated logging paths.

## Features
- Daily log files: `<app>-YYYYMMDD.log` with format `[YYYY-MM-DD HH:MM:SS] pid:<PID> [<LEVEL>] @<COMPONENT> :] <MESSAGE>`.
- Rotation on date change; archive via `tarfile.open("w:gz")`; remove via `os.remove()`.
- Privilege detection via `_Suroot`: `is_root()` (os.geteuid()==0), `can_sudo_without_password()` (subprocess.Popen(["sudo", "-n", "true"])).
- Lazy evaluation for paths (`baseDir()`, `logDir()`), debug (`os.getenv("DEBUG")=="show"`), and context (`inPython()` checks sys.executable).
- Environment detection: Supports venv (`inVenv()`), pyenv (`inPyenv()`, `pyenvVenv()`), Conda/Anaconda/Miniconda (`inConda()`, `condaPath()`) for isolated paths (e.g., `<env>/.app/<app>/log`).
- Byte/string handling with UTF-8 via `strToByte()`/`byteToStr()`; `io.open(encoding='utf-8')` for writes.
- Console output: stdout for INFO/DEBUG, stderr for ERROR/CRITICAL/FATAL via `print(..., file=sys.stderr)`.
- Compatibility: `__future__` imports, no f-strings (use .format()), `sys.exc_info()` for exceptions, DEVNULL shim.

## Installation
Install via pip for system-wide or virtual environment use:

```
pip install ChronicleLogger
```

For isolated environments (recommended for development):
- **venv**: `python -m venv myenv && source myenv/bin/activate`
- **pyenv**: `pyenv install 3.12.0 && pyenv shell 3.12.0`
- **Conda/Miniconda/Anaconda**: `conda create -n myenv python=3.12 && conda activate myenv`

ChronicleLogger automatically detects these environments and places logs/configs inside (e.g., `myenv/.app/test-app/log` for non-root).

For testing dependencies (optional):
```
pytest==4.6.11  # For Py2 compat
mock  # For Py2 unittest.mock fallback
```
Install: `pip install -r requirements.txt`.

## Installation by Building from Source (Cython .so)
For performance-critical setups, build the Cython .so from source:

```bash
# Install build tools
pip install cython setuptools hatchling

# Build extensions in-place (compiles .pyx to .c and .so)
python setup.py build_ext --inplace

# Or full packaging: sdist and wheel
python setup.py sdist bdist_wheel

# Editable install (for development)
pip install -e .
```

Using `pyproject.toml` (hatchling backend):

```toml
[build-system]
requires = ["hatchling >= 1.18"]
build-backend = "hatchling.build"

[project]
name = "chroniclelogger"
version = "1.1.1"
description = "POSIX-compliant logger with rotation and privilege paths"
readme = "README.md"
requires-python = ">=2.7"
license = {text = "MIT"}
dependencies = []  # No external deps
```

Build: `hatch build`. Install wheel: `pip install dist/chroniclelogger-1.1.1-py3-none-any.whl`.

## Demo Application: LoggedExample
**LoggedExample** is a simple, practical demonstration application that uses **ChronicleLogger** as its logging backend. It shows real-world usage patterns including:

- Initialization with custom app name
- Logging at different levels (INFO, DEBUG, ERROR)
- Debug mode activation via environment variable
- Integration with environment-aware path resolution
- Basic command-line interface

**PyPI URL**: https://pypi.org/project/LoggedExample/

### How to Install and Run LoggedExample
```bash
# Install the demo application (automatically pulls ChronicleLogger as dependency)
pip install LoggedExample

# Run the demo
LoggedExample --help

# Example with debug mode enabled
DEBUG=show LoggedExample run
```

This will create log files in your current environment's isolated path (e.g. `~/.app/logged-example/log/` or inside your venv/conda/pyenv environment), showing structured, timestamped logs with rotation and archiving in action.

Great for beginners who want to see ChronicleLogger in a complete, runnable application!

## Project Structure
The project adopts a clean, maintainable layout for Cython utilities:

```
./
├── build/          # Build artifacts (bdist.linux-x86_64, lib/)
├── dist/           # Wheels/tar.gz (e.g., chroniclelogger-1.1.1-py3-none-any.whl)
├── docs/           # CHANGELOG.md, ChronicleLogger-spec.md, folder-structure.md, update-log.md
├── src/
│   ├── ChronicleLogger/  # Package: ChronicleLogger.py, Suroot.py, __init__.py (__version__="1.1.1")
│   ├── ChronicleLogger.pyx  # Cython source
│   ├── ChronicleLogger.c    # Compiled
│   └── setup.py             # Packaging
├── test/           # test_chronicle_logger.py, __pycache__/
├── .gitignore      # Ignore __pycache__/, .env, *.pyc, dist/, build/
├── README.md
├── pyproject.toml  # Optional, for hatchling
├── setup.py
└── requirements.txt  # Testing deps only
```

`.gitignore` example:

```
.env
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
dist/
*.egg-info/
.coverage
htmlcov/
```

Initialize Git: `git init && git add . && git commit -m "Initial commit"`.

## Usage
Import and instantiate:

```python
from ChronicleLogger import ChronicleLogger
```

Default (privilege- and environment-aware paths, kebab-case in Python mode):

```python
logger = ChronicleLogger(logname="TestApp")
print(logger.logName())  # "test-app" (in Python mode)
print(logger.logDir())   # E.g., "/home/user/miniconda3/envs/myenv/.app/test-app/log" if in Conda env

# Custom paths
logger = ChronicleLogger(logname="MyApp", logdir="/custom/logs", basedir="/opt/myapp")

# Log (auto-rotates, writes to file + console)
logger.log_message("Started", level="INFO", component="main")
logger.log_message("Error occurred", level="ERROR")  # To stderr

# Debug mode (set env DEBUG=show)
if logger.isDebug():
    logger.log_message("Debug info", level="DEBUG")

# Environment checks
print(logger.inVenv())     # True if in venv
print(logger.inPyenv())    # True if in pyenv
print(logger.inConda())    # True if in Conda

# Version
print(ChronicleLogger.class_version())  # "ChronicleLogger v1.1.1"
```

Path Examples (for "TestApp"):
- In venv `/path/to/venv`: `baseDir="/path/to/venv/.app/test-app"`, `logDir="/path/to/venv/.app/test-app/log"`
- In pyenv venv `/home/user/.pyenv/versions/3.12/envs/myenv`: Similar with `/.app/test-app`
- In Conda `/home/user/miniconda3/envs/myenv`: Similar
- Fallback non-root: `~/.app/test-app/log`
- Root (no env): `/var/log/test-app`

## Building and Cython
For performance: `python setup.py build_ext --inplace`.

`build.sh` example:

```sh
#!/bin/sh
python setup.py build_ext --inplace
python setup.py sdist bdist_wheel
```

Run: `chmod +x build.sh && ./build.sh`.

## Testing
```bash
pip install -r requirements.txt
pytest test/ -v
```

## Changelog
See [docs/CHANGELOG.md](docs/CHANGELOG.md) for updates: v1.1.1 - Added environment support, Py2 shims, etc.

For issues: Ensure isolated env; run `which python` to confirm.

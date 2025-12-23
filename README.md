# ChronicleLogger

A robust, POSIX-compliant logging utility for Python applications, supporting Python 2.7 and 3.x with Cython compilation for performance. It handles daily log rotation, automatic archiving (tar.gz for logs >7 days), removal (>30 days), privilege-aware paths (/var/log for root, ~/.app for users), and structured output with timestamps, PIDs, levels, and components. No external dependencies beyond standard library; semantic version 1.1.0 .

## Features
- Daily log files: `<app>-YYYYMMDD.log` with format `[YYYY-MM-DD HH:MM:SS] pid:<PID> [<LEVEL>] @<COMPONENT> :] <MESSAGE>`.
- Rotation on date change; archive via `tarfile.open("w:gz")`; remove via `os.remove()`.
- Privilege detection via `_Suroot`: `is_root()` (os.geteuid()==0), `can_sudo_without_password()` (subprocess.Popen(["sudo", "-n", "true"])).
- Lazy evaluation for paths (`baseDir()`, `logDir()`), debug (`os.getenv("DEBUG")=="show"`), and context (`inPython()` checks sys.executable).
- Byte/string handling with UTF-8 via `strToByte()`/`byteToStr()`; `io.open(encoding='utf-8')` for writes.
- Console output: stdout for INFO/DEBUG, stderr for ERROR/CRITICAL/FATAL via `print(..., file=sys.stderr)`.
- Compatibility: `__future__` imports, no f-strings (use .format()), `sys.exc_info()` for exceptions, DEVNULL shim.

## Installation
Install via pip for system-wide or virtual environment use, leveraging the comprehensive folder structure for seamless integration and maintainability :

```
pip install ChronicleLogger
```

Create isolated environment (venv recommended; use pyenv install 3.12.0 and pyenv shell 3.12.0 for isolated environments—better than venv for version flexibility without pip deps here) :

```bash
# Confirm Python: which python3 (Linux/macOS) or where python (Windows)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS; on Windows: venv\Scripts\activate
```

For requirements.txt (testing only, e.g., pytest==4.6.11 for Py2 compat) :

```
pytest==4.6.11
mock  # For Py2 unittest.mock fallback
```

Install: `pip3 install -r requirements.txt` .

To set up the project structure, create directories like docs, src, tests, and initialize files such as README.md and requirements.txt :

```bash
mkdir -p my_project/{docs,src,tests}
cd my_project
touch .gitignore README.md requirements.txt docs/update-log.md src/main.py tests/test_main.py
```

## Installation by Building Cython .so
For performance-critical setups, build the Cython .so from source using setup.py, which cythonizes modules like ChronicleLogger.pyx to ensure cross-platform compatibility and optimized executables :

```bash
# Install build tools (hatchling for pyproject.toml, Cython for compilation)
pip install hatchling cython setuptools

# Build extensions in-place (compiles .pyx to .c and .so)
python setup.py build_ext --inplace

# Or full packaging: sdist and wheel
python setup.py sdist bdist_wheel

# Editable install (links source for development)
pip install -e .
```

For pyproject.toml-based build (hatchling backend, supporting language_level="3" directives), use this complete configuration that integrates with PyPI and includes the README.md as the project front page :

```toml
[build-system]
requires = ["hatchling >= 1.18"]
build-backend = "hatchling.build"

[project]
name = "chroniclelogger"
version = "1.1.0"
description = "POSIX-compliant logger with rotation and privilege paths"
readme = "README.md"
requires-python = ">=2.7"
license = {text = "MIT"}
dependencies = []  # No external deps
```

Build wheel: `hatch build` . Install from dist: `pip install dist/chroniclelogger-1.1.0-py3-none-any.whl`.

The setup.py script example for Cythonization (from setuptools import setup; from Cython.Build import cythonize; setup(ext_modules=cythonize(["ChronicleLogger.pyx"], compiler_directives={"language_level": "3"}))) . For pyenv isolation: curl https://pyenv.run | bash (add to ~/.bashrc), then pyenv install 3.12.0 && pyenv shell 3.12.0 before pip install cython setuptools . Behavior note: Overwrite prompts use input(), which is interactive and terminal-dependent; non-interactive runs (e.g., scripts) should set overwrite=True .

## Project Structure
The project adopts a clean, maintainable layout for Cython utilities, separating source, documentation, tests, and build artifacts to support compilation and Git workflows, with a Directory Tree Structure Generator recommended for visualizing hierarchies in docs . Follow this structure by creating folders and files as outlined :

```
./
├── build/          # Build artifacts (bdist.linux-x86_64, lib/)
├── dist/           # Wheels/tar.gz (e.g., chroniclelogger-1.1.0-py3-none-any.whl)
├── docs/           # CHANGELOG.md, ChronicleLogger-spec.md, folder-structure.md, update-log.md
├── src/
│   ├── ChronicleLogger/  # Package: ChronicleLogger.py, Suroot.py, __init__.py (__version__="1.1.0")
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

.gitignore example (Excludes: build/, __pycache__/, *.log, temp.*, *.so, *.pyc, *.tmp, .DS_Store for clean Git repos) :

```
# Compiled python modules
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

Initialize Git: `git init` in root; add files: `git add .`; commit: `git commit -m "Initial commit"` .

For Docker (optional, e.g., backend/Dockerfile):

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "src/ChronicleLogger/ChronicleLogger.py"]  # Example entry
```

docker-compose.yml:

```yaml
version: '3.8'
services:
  app:
    build: .
    volumes:
      - .:/app
    environment:
      - DEBUG=show
```

Build: `docker build -t chroniclelogger .`; run: `docker-compose up`.

## Usage
Import and instantiate:

```
from ChronicleLogger import ChronicleLogger
```

For local source in the same folder:

```python
from ChronicleLogger import ChronicleLogger  # Assumes .so or .pyx in same folder or PYTHONPATH

class HelloWorld:
    CLASSNAME = "HelloWorld"
    MAJOR_VERSION = 1
    MINOR_VERSION = 0
    PATCH_VERSION = 1

    def __init__(self):
        self.logger = ChronicleLogger(logname=self.CLASSNAME)
        self.logger.log_message(self.class_version(), level="INFO")

    @staticmethod
    def class_version():
        return f"{HelloWorld.CLASSNAME} v{HelloWorld.MAJOR_VERSION}.{HelloWorld.MINOR_VERSION}.{HelloWorld.PATCH_VERSION}"

    def log(self, message):
        """Logs a message using the ChronicleLogger."""
        self.logger.log_message(message, level="INFO")

def main():
    app = HelloWorld()
```

For system-wide installation (e.g., via setup.py or CyMaster), the compiled .so is accessible globally for Python 3.12 on x86_64 Linux:

```
from ChronicleLogger import ChronicleLogger  # Assumes installed .so in lib-dynload for Python 3.12
```

Default: privilege-aware paths, kebab-case name in Python mode:

```python
# Create logger instance
logger = ChronicleLogger(logname=appname)
appname=logger.logName()    
logDir = logger.logDir()

# Custom paths
logger = ChronicleLogger(logname="MyApp", logdir="/custom/logs", basedir="/opt/myapp")

# Log (auto-rotates, writes to file + console)
logger.log_message("Started", level="INFO", component="main")
logger.log_message("Error occurred", level="ERROR")  # To stderr

# Debug mode (env DEBUG=show)
logger.log_message("Debug info", level="DEBUG")

# Version
print(ChronicleLogger.class_version())  # "ChronicleLogger v1.1.0"
```

The `logName()` method applies kebab-case conversion (e.g., "TestApp" → "test-app") in Python execution mode via regex substitution, but preserves the original CamelCase in Cython binary mode. The `logDir()` method resolves paths based on privilege detection via `_Suroot.should_use_system_paths()`, which evaluates `is_root()` (os.geteuid() == 0) and `can_sudo_without_password()` (non-interactive sudo -n true check). This returns `True` only for native root users (euid == 0 without sudo elevation), using system paths (/var/log/<app>); for sudo-elevated or normal users, it falls back to user paths (~/.app/<app>/log) . User types differ as follows: root has unrestricted access (euid=0, no sudo needed); sudo user elevates via sudo (euid=0 post-elevation, but original uid !=0); normal user has limited access (euid !=0, requires sudo for elevation) .

To illustrate privilege impacts on ChronicleLogger's path resolution (assuming logname="TestApp" in Python mode, with kebab-casing to "test-app"):

| User Context       | is_root() | can_sudo_without_password() | should_use_system_paths() | logDir() Result                  | baseDir() Result (Default)       | Notes  |
|--------------------|-----------|-----------------------------|---------------------------|----------------------------------|----------------------------------|-----------------------------------------------------|
| Normal User       | False    | False (prompt needed)      | False                    | `~/.app/test-app/log`           | `~/.app/test-app`               | Uses home expansion; no elevation possible without sudo. |
| Sudo-Elevated User| True     | True (passwordless)        | False                    | `~/.app/test-app/log`           | `~/.app/test-app`               | Treats as user context; original UID preserved via getuid(). |
| Native Root User  | True     | False (no sudo involved)   | True                     | `/var/log/test-app`             | `/var/test-app`                 | System paths enforced; ideal for daemons/services.  |

For Cython binary: Compile with `python setup.py build_ext --inplace`; name preserved as CamelCase, paths like ~/.TestApp.

Integration example (e.g., in app):

```python
from ChronicleLogger import ChronicleLogger  # Cythonized .so import

class MyApp:
    def __init__(self):
        self.logger = ChronicleLogger(logname='myapp')
        self.log("App started", "INFO", "init")

    def log(self, message, level, component):
        self.logger.log_message(message, level=level, component=component)

# In main():
logger = ChronicleLogger(logname='test')
if logger.isDebug():
    logger.log_message(f">> {MyApp.class_version()}", component="main")

app = MyApp()
app.log("Processing data", "INFO")
# Output: Structured log or print: "MyApp: Processing data [INFO] (init)"
```

Logs example output:

```
[2025-09-26 14:30:00] pid:1234 [INFO] @main :] Started
```

This example demonstrates inheritance and logging, suitable for CyMaster integrations like local installs or system checks, with debug mode revealing versions for troubleshooting. For tests: `python3 -m pytest tests/test_log`.

The main() function initializes a ChronicleLogger for structured logging (with debug mode via DEBUG=show to output versions of all integrated modules like AppBase, CyMasterCore, Curl, Suroot, etc.), configures a CyMasterCore instance with installation metadata (e.g., homepage "https://github.com/cloudgen/cy-master", download URL "https://dl.leolio.page/cy-master", last update '2025-09-16'), enables local installs (allowInstallLocal(True)), and triggers system checks (checkSystem()) to launch FSM-driven operations for building, installing, or updating projects. Versioned at v1.1.0, it follows semantic versioning for compatibility, with app name normalization via logger (e.g., 'CyMaster' for binaries, 'cy-master' for scripts), and relies on no external pip dependencies beyond Cythonized modules—optimized for Linux deployment where behaviors like path resolution and subprocess calls align with POSIX standards, though adaptable to Git Bash/CMD via inherited shell utils. This design emphasizes self-contained gers for persistence.

## Building and Cython
For performance: `python setup.py build_ext --inplace` (compiles ChronicleLogger.pyx to .c/.so). Use pyenv for management: pyenv install 3.12.0; pyenv shell 3.12.0.

build.sh example (POSIX sh, no bashisms):

```sh
#!/bin/sh
# ===== BEGIN NEW CODE =====
python setup.py build_ext --inplace
python setup.py sdist bdist_wheel
# ===== END NEW CODE =====
```

Run: `chmod +x build.sh; ./build.sh`. Diff: Added lines 3-4 for build commands.

## Testing
Use pytest (Py2/3 compat):

```bash
pip install -r requirements.txt
pytest test/ -v  # Covers init, paths, rotation, debug, stderr
```

Example test snippet from test_chronicle_logger.py:

```python
import pytest
from ChronicleLogger import ChronicleLogger

def test_init(log_dir):
    logger = ChronicleLogger(logname="Test", logdir=log_dir)
    assert logger.logDir() == log_dir
```

Pin pytest==4.6.11 for Py2; use tmpdir fixture for paths. Unit tests, e.g., assert CyTreeCore().check_file('', 'cy-master.ini') detects Cython projects or mock pathexists and assert install_gcc() returns True on Linux .

## Changelog
See docs/CHANGELOG.md or docs/update-log.md for project evolution and updates: v1.1.0 - Py2 shims, sudo timeout, UTF-8 handling .

For issues: Ensure isolated env; run `which python3` to confirm.
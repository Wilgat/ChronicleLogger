# CHANGELOG.md

## [Unreleased]
### Added
- Initial support for semantic versioning tracking in documentation .
- Recommendations for Git initialization and .gitignore integration to track changelog updates .

### Changed
- Updated changelog structure to follow standard categories (Added, Changed, Deprecated, Removed, Fixed, Security) for better readability and reverse chronological order .
- Renamed file header to "CHANGELOG.md" for consistency with common project conventions .

### Fixed
- Corrected version dates and descriptions for clarity; ensured concise, informative entries .

---

## [Version 1.1.0] - 2025-09-26
### Added
- Python 2.7 compatibility shims, including DEVNULL fallback, sys.exc_info() handling, and io.open conditional for UTF-8 writes .
- Sudo timeout (5s in Py3.3+) and non-interactive privilege detection via subprocess.Popen(["sudo", "-n", "true"]) .
- Lazy evaluation for paths, debug mode, and inPython() context checking .

### Changed
- Log name kebab-casing in Python mode (e.g., "TestApp" → "test-app") via regex, preserved in Cython binaries .
- Path resolution: should_use_system_paths() now True for native root (euid==0 without sudo), using /var/log/<app>; user paths (~/.app/<app>/log) for sudo-elevated or normal users .
- Exception handling with version-conditional sys.exc_info() for Py2/3 cross-compatibility .

### Fixed
- f-string replacements with .format() for Py2 support; basestring fallback and __future__ imports for print/division/unicode .
- Permission checks and directory creation with os.makedirs() and error logging to stderr .

### Security
- Non-blocking sudo checks to avoid hangs in CI/CD; DEVNULL shim prevents output leaks .

---

## [Version 0.1.1] - 2025-12-12
### Changed
- Added tests for Python 2.7 compatibility, including mock fallback and tmpdir fixtures .
- Enhanced compatibility for both Python 2+ and 3+, with conditional imports and string/byte handling .

---

## [Version 0.1.0] - 2025-12-05
### Changed
- Initial commit with core logging functionality, daily rotation, and basic privilege detection .
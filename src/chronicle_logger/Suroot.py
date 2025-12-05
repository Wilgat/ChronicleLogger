# src/ChronicleLogger/Suroot.py  # Note: Filename without underscore for consistency
# Minimal, safe, non-interactive root/sudo detector
# ONLY for internal use by ChronicleLogger
import os
from subprocess import Popen, DEVNULL

class _Suroot:
    """
    Tiny, zero-dependency, non-interactive privilege detector.
    Used by ChronicleLogger to decide log directory (/var/log vs ~/.app).
    NEVER prompts, NEVER prints, safe in CI/CD and tests.
    """

    CLASSNAME = "Suroot"
    MAJOR_VERSION = 0
    MINOR_VERSION = 1
    PATCH_VERSION = 0

    _is_root = None
    _can_sudo_nopasswd = None

    @staticmethod
    def class_version():
        """Return the class name and version string."""
        return f"{_Suroot.CLASSNAME} v{_Suroot.MAJOR_VERSION}.{_Suroot.MINOR_VERSION}.{_Suroot.PATCH_VERSION}"

    @staticmethod
    def is_root() -> bool:
        """Are we currently running as root (euid == 0)?"""
        if _Suroot._is_root is None:
            _Suroot._is_root = os.geteuid() == 0
        return _Suroot._is_root

    @staticmethod
    def can_sudo_without_password() -> bool:
        """Can we run 'sudo' commands without being asked for a password?"""
        if _Suroot._can_sudo_nopasswd is not None:
            return _Suroot._can_sudo_nopasswd

        if _Suroot.is_root():
            _Suroot._can_sudo_nopasswd = True
            return True

        try:
            proc = Popen(
                ["sudo", "-n", "true"],
                stdin=DEVNULL,
                stdout=DEVNULL,
                stderr=DEVNULL,
            )
            proc.communicate(timeout=5)
            _Suroot._can_sudo_nopasswd = proc.returncode == 0
        except Exception:
            _Suroot._can_sudo_nopasswd = False

        return _Suroot._can_sudo_nopasswd

    @staticmethod
    def should_use_system_paths() -> bool:
        """
        Final decision method used by ChronicleLogger.
        Returns True → use /var/log and /var/<app>
        Returns False → use ~/.app/<app>/log
        """
        return _Suroot.is_root() or _Suroot.can_sudo_without_password()
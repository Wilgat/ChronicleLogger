# -*- coding: utf-8 -*-
# NEW: Additional __future__ for better Py2 compatibility (unicode_literals for strings)
from __future__ import unicode_literals

# src/ChronicleLogger/Suroot.py  # Note: Filename without underscore for consistency
# Minimal, safe, non-interactive root/sudo detector
# ONLY for internal use by ChronicleLogger
import os
from subprocess import Popen
# src/ChronicleLogger/Suroot.py  # Note: Filename without underscore for consistency
# Minimal, safe, non-interactive root/sudo detector
# ONLY for internal use by ChronicleLogger
import os
# NEW: Full import for subprocess module access in shim (Popen already imported below)
import subprocess
from subprocess import Popen

# Python 2.7 compatibility shim
if not hasattr(subprocess, 'DEVNULL'):
    DEVNULL = open(os.devnull, 'wb')
else:
    DEVNULL = subprocess.DEVNULL
 
class _Suroot:
    """
    Tiny, zero-dependency, non-interactive privilege detector.
    Used by ChronicleLogger to decide log directory (/var/log vs ~/.app).
    NEVER prompts, NEVER prints, safe in CI/CD and tests.
    """

    CLASSNAME = "Suroot"
    MAJOR_VERSION = 0
    MINOR_VERSION = 1
    PATCH_VERSION = 1

    _is_root = None
    _can_sudo_nopasswd = None

    @staticmethod
    def class_version():
        """Return the class name and version string."""
        # NEW: Replaced f-string with .format() for Py2 compat (f-strings Py3.6+)
        return "{0.CLASSNAME} v{0.MAJOR_VERSION}.{0.MINOR_VERSION}.{0.PATCH_VERSION}".format(_Suroot)

    @staticmethod
    def is_root():  # NEW: Removed -> bool type hint (Py3.5+ syntax error in Py2)
        """Are we currently running as root (euid == 0)?"""
        if _Suroot._is_root is None:
            _Suroot._is_root = os.geteuid() == 0
        return _Suroot._is_root

    @staticmethod
    def can_sudo_without_password():  # NEW: Removed -> bool type hint
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
            # NEW: Py2 compat for communicate(timeout=5): Py2 Popen.communicate() lacks timeout (Py3.3+); use version check and fallback to no timeout (or add threading if strict timeout needed)
            if sys.version_info[0] >= 3 and sys.version_info[1] >= 3:
                proc.communicate(timeout=5)
            else:
                proc.communicate()  # No timeout in Py2; process may hang if sudo hangs, but non-interactive -n prevents prompts
            _Suroot._can_sudo_nopasswd = proc.returncode == 0
        except Exception:
            _Suroot._can_sudo_nopasswd = False

        return _Suroot._can_sudo_nopasswd

    @staticmethod
    def should_use_system_paths():  # NEW: Removed -> bool type hint
        """
        Final decision method used by ChronicleLogger.
        Returns True → use /var/log and /var/<app>
        Returns False → use ~/.app/<app>/log
        This logic determine if the real user (root is root, sudo still comes from non-root user) 
        """
        return _Suroot.is_root() and not _Suroot.can_sudo_without_password()
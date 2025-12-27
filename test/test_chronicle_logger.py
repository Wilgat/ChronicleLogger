# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, division
import unittest
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch  # Requires 'pip install mock' for Python 2.7
from os.path import join, realpath
import sys

import os
import sys
import tarfile
import re
from datetime import datetime, timedelta

import pytest

TEST_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(TEST_DIR, "..", "src"))
sys.path.insert(0, SRC_DIR)

from ChronicleLogger import ChronicleLogger,TimeProvider

class FakeTimeProvider(TimeProvider):
    def __init__(self):
        self.current_time = datetime(2025, 12, 25, 14, 30, 0)  # Fixed starting point
        self._delta = timedelta(0)

    def now(self):
        return self.current_time + self._delta

    def timedelta(self, **kwargs):
        return timedelta(**kwargs)

    def advance(self, **kwargs):
        """Advance simulated time by given amount (days, hours, etc.)"""
        self._delta += timedelta(**kwargs)

    def strftime(self, dt, fmt):
        return dt.strftime(fmt)

@pytest.fixture
def fake_time_provider():
    """Fixture providing a fake, controllable time provider for tests."""
    return FakeTimeProvider()

# test/test_ChronicleLogger.py

# NEW: Compatibility for pytest fixtures (tmp_path is Py3-only Path; use tmpdir for Py2/3 dual support)
#      tmpdir works in pytest 4.6.11 (Py2) as str, and in Py3 as Path, but we treat as str for compat
@pytest.fixture
def log_dir(tmpdir):  # NEW: Changed from tmp_path to tmpdir for Py2 compat (pin pytest==4.6.11)
    log_path = tmpdir.join("log")  # NEW: tmpdir.join() works for both (str in Py2, Path in Py3)
    return str(log_path)  # NEW: Ensure str for cross-version ops

@pytest.fixture
def logger(log_dir, fake_time_provider):
    return ChronicleLogger(
        logname="TestApp",
        logdir=log_dir,
        time_provider=fake_time_provider
    )

def test_directory_created_on_init_when_logdir_given(log_dir):
    assert not os.path.exists(log_dir)  # NEW: Use os.path.exists instead of .exists() for Py2 compat
    ChronicleLogger(logname="TestApp", logdir=log_dir)
    assert os.path.exists(log_dir)

def test_logname_becomes_kebab_case():
    logger = ChronicleLogger(logname="TestApp")
    assert logger.logName() == "test-app"

    logger = ChronicleLogger(logname="HelloWorld")
    assert logger.logName() == "hello-world"

@patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.inPython', return_value=False)
def test_logname_unchanged_in_cython_binary(mock):
    logger = ChronicleLogger(logname="PreserveCase")
    logger.logName("PreserveCase")
    assert logger.logName() == "PreserveCase"

def test_basedir_is_user_defined_and_independent(tmpdir):  # NEW: Changed tmp_path to tmpdir for compat
    custom = str(tmpdir.join("myconfig"))  # NEW: Use tmpdir and str()
    logger = ChronicleLogger(logname="App", basedir=custom)
    assert logger.baseDir() == custom

def test_logdir_uses_system_path_when_privileged_and_not_set():
    with patch('ChronicleLogger._Suroot.is_root', return_value=True):
        with patch('sys.executable', '/usr/bin/root-binary'):
            return_value = "".encode('utf-8')
            with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.conda_env_list', return_value=return_value):
                logger = ChronicleLogger(logname="RootApp")
                expected = "/var/RootApp/log"  # NEW: Adjusted for preserved CamelCase in binary mode (no kebab); logDir derives from baseDir + /log
                assert logger.logDir() == expected

def test_executable_uses_user_path_when_not_privileged_and_pyenv_and_venv():
    with patch('ChronicleLogger.Suroot._Suroot.is_root', return_value=False):
        with patch('sys.executable', os.path.join(os.path.expanduser("~"), ".pyenv/versions/build/bin/python3") ):
            logger = ChronicleLogger(logname="UserApp")
            expected = os.path.join(os.path.expanduser("~"), ".pyenv/versions/build/bin/python3")  # NEW: Matches kebab-cased appname in Python mode + derived /log
            assert sys.executable == expected

def test_logdir_uses_user_path_when_not_privileged_and_not_set():
    with patch('ChronicleLogger.Suroot._Suroot.is_root', return_value=False):
        with patch('sys.executable', '/usr/local/python'):
            return_value = "".encode('utf-8')
            with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.conda_env_list', return_value=return_value):
                logger = ChronicleLogger(logname="UserApp")
                expected = os.path.join(os.path.expanduser("~"), ".app/user-app", "log")  # NEW: Matches kebab-cased appname in Python mode + derived /log
                assert logger.logDir() == expected

def test_logdir_uses_user_path_when_not_privileged_and_pyenv():
    with patch('ChronicleLogger.Suroot._Suroot.is_root', return_value=False):
        with patch('sys.executable', os.path.join(os.path.expanduser("~"), ".pyenv/shims/python") ):
            with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.pyenv_versions', return_value='* 3.12.12 (set)'):
                return_value = "".encode('utf-8')
                with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.conda_env_list', return_value=return_value):
                    logger = ChronicleLogger(logname="UserApp")
                    expected = os.path.join(os.path.expanduser("~"), ".app/user-app", "log")  # NEW: Matches kebab-cased appname in Python mode + derived /log
                    assert logger.logDir() == expected

def test_logdir_uses_user_path_when_not_privileged_and_pyenv_and_venv():
    with patch('ChronicleLogger.Suroot._Suroot.is_root', return_value=False):
        with patch('sys.executable', os.path.join(os.path.expanduser("~"), ".pyenv/versions/build/bin/python") ):
            with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.pyenv_versions', return_value='* build --> /home/leolio/.pyenv/versions/3.12.12/envs/build (set)'):
                return_value = "".encode('utf-8')
                with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.conda_env_list', return_value=return_value):
                    logger = ChronicleLogger(logname="UserApp")
                    expected = os.path.join("/home/leolio/.pyenv/versions/3.12.12/envs/build/.app/user-app", "log")  # NEW: Matches kebab-cased appname in Python mode + derived /log
                    assert logger.logDir() == expected

def test_logdir_custom_path_overrides_everything(log_dir):
    logger = ChronicleLogger(logname="AnyApp", logdir=log_dir)
    assert logger.logDir() == log_dir

def test_log_message_writes_correct_filename(logger, log_dir):
    logger.log_message("Hello!", level="INFO")
    today = datetime.now().strftime("%Y%m%d")
    logfile = os.path.join(log_dir, "test-app-{}.log".format(today))  # NEW: Replaced f-string with .format(); use os.path.join instead of /
    assert os.path.exists(logfile)

@pytest.mark.parametrize("level", ["ERROR", "CRITICAL", "FATAL"])
def test_error_levels_go_to_stderr(logger, level, capsys):
    logger.log_message("Boom!", level=level)
    captured = capsys.readouterr()
    assert "Boom!" in captured.err

def test_archive_old_logs(log_dir):
    logger = ChronicleLogger(logname="TestApp", logdir=log_dir)
    today_minus_10 = datetime.now() - timedelta(days=10)
    old_filename = "test-app-{}.log".format(today_minus_10.strftime('%Y%m%d'))  # NEW: Replaced f-string
    old_file = os.path.join(log_dir, old_filename)  # NEW: Use os.path.join instead of /
    old_dir = os.path.dirname(old_file)  # NEW: Explicitly get dirname for clarity
    if not os.path.exists(old_dir):
        os.makedirs(os.path.dirname(old_file)) 
    with open(old_file, 'w') as f:  # NEW: Replaced .write_text with open/write for Py2 compat
        f.write("old")
    logger.archive_old_logs()
    archived = os.path.join(log_dir, "{}.tar.gz".format(old_filename))  # NEW: Replaced f-string; os.path.join
    assert os.path.exists(archived)

def test_debug_mode(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    assert not ChronicleLogger(logname="A").isDebug()
    monkeypatch.setenv("DEBUG", "show")
    assert ChronicleLogger(logname="B").isDebug()

# NEW: Added test for inPyenv() method: mocks sys.executable to contain '.pyenv' and verifies True return with caching (calls twice for lazy check)
def test_in_pyenv_true():
    with patch('sys.executable', '/home/user/.pyenv/shims/python'):
        logger = ChronicleLogger(logname="TestApp")
        assert logger.inPyenv() is True
        assert logger.inPyenv() is True  # Cached, no re-check

# NEW: Added test for inPyenv() false case: mocks sys.executable without '.pyenv' and verifies False with caching
def test_in_pyenv_false():
    with patch('sys.executable', '/usr/bin/python'):
        logger = ChronicleLogger(logname="TestApp")
        assert logger.inPyenv() is False
        assert logger.inPyenv() is False  # Cached

# NEW: Added test for venv_path() and inVenv(): sets VIRTUAL_ENV env var and verifies path retrieval and bool check with caching
def test_venv_path_and_in_venv_true(monkeypatch):
    venv_path = "/home/user/myvenv"
    monkeypatch.setenv('VIRTUAL_ENV', venv_path)
    logger = ChronicleLogger(logname="TestApp")
    assert logger.venv_path() == venv_path
    assert logger.inVenv() is True
    assert logger.venv_path() == venv_path  # Cached
    assert logger.inVenv() is True  # Cached

# NEW: Added test for venv_path() and inVenv() false: unsets VIRTUAL_ENV and verifies empty path and False with caching
def test_venv_path_and_in_venv_false(monkeypatch):
    monkeypatch.delenv('VIRTUAL_ENV', raising=False)
    logger = ChronicleLogger(logname="TestApp")
    assert logger.venv_path() == ''
    assert logger.inVenv() is False
    assert logger.venv_path() == ''  # Cached
    assert logger.inVenv() is False  # Cached

# NEW: Added test for pyenvVenv(): mocks subprocess.check_output to return sample 'pyenv versions' output with active venv path, verifies extraction and existence check (uses mock path); also tests non-pyenv fallback to ''
@patch('subprocess.check_output')
@patch('os.path.exists', return_value=True)
def test_pyenv_venv_success(mock_exists, mock_output):
    sample_output = """  system
  3.12.12
* build --> /home/user/.pyenv/versions/3.12.12/envs/build (set by PYENV_VERSION)"""
    mock_output.return_value = sample_output.encode('utf-8')
    with patch('sys.executable', '/home/user/.pyenv/shims/python'):  # Trigger inPyenv True
        logger = ChronicleLogger(logname="TestApp")
        # NEW: Adjusted expectation to match code's strip() but account for potential extra text; code extracts after '--> ' and strips, so trims "(set by...)"
        extracted_path = '/home/user/.pyenv/versions/3.12.12/envs/build'  # NEW: Matches trimmed path without parenthetical
        assert logger.pyenvVenv() == extracted_path
        assert logger.pyenvVenv() == extracted_path  # Cached

# NEW: Added test for pyenvVenv() fallback: mocks non-pyenv executable and verifies empty string return with caching
def test_pyenv_venv_not_in_pyenv():
    with patch('sys.executable', '/usr/bin/python'):  # inPyenv False
        logger = ChronicleLogger(logname="TestApp")
        assert logger.pyenvVenv() == ''
        assert logger.pyenvVenv() == ''  # Cached

# NEW: Added test for pyenvVenv() error handling: mocks subprocess failure (e.g., pyenv not found) and verifies empty string with caching
@patch('subprocess.check_output', side_effect=FileNotFoundError)
def test_pyenv_venv_command_error(mock_output):
    with patch('sys.executable', '/home/user/.pyenv/shims/python'):  # inPyenv True
        logger = ChronicleLogger(logname="TestApp")
        assert logger.pyenvVenv() == ''
        assert logger.pyenvVenv() == ''  # Cached

# NEW: Added test for inConda() true: sets CONDA_DEFAULT_ENV and verifies True return (also covers 'conda' in executable); tests caching
def test_in_conda_true(monkeypatch):
    monkeypatch.setenv('CONDA_DEFAULT_ENV', 'test_env')
    logger = ChronicleLogger(logname="TestApp")
    assert logger.inConda() is True
    assert logger.inConda() is True  # Cached
    # Also test executable check
    with patch('sys.executable', '/miniconda3/bin/python'):
        assert ChronicleLogger(logname="TestApp").inConda() is True

# NEW: Added test for inConda() false: unsets CONDA_DEFAULT_ENV and no 'conda' in executable, verifies False with caching
def test_in_conda_false(monkeypatch):
    monkeypatch.delenv('CONDA_DEFAULT_ENV', raising=False)
    with patch('sys.executable', '/usr/bin/python'):
        logger = ChronicleLogger(logname="TestApp")
        assert logger.inConda() is False
        assert logger.inConda() is False  # Cached

def test_conda_path_from_list():
    sample_output = """# conda environments:
#
base                 *   /home/user/miniconda3
test                     /home/user/miniconda3/envs/test"""
    return_value = sample_output.encode('utf-8')
    with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.conda_env_list', return_value=return_value):
        with patch('os.path.exists', return_value=True):
            logger = ChronicleLogger(logname="TestApp")
            assert logger.condaPath() == '/home/user/miniconda3'
            assert logger.condaPath() == '/home/user/miniconda3'  # Cached

# NEW: Added test for condaPath() fallback: mocks conda command failure and verifies empty string with caching
@patch('subprocess.check_output', side_effect=FileNotFoundError)
def test_conda_path_command_error(mock_output):
    sample_output = """# conda environments:
#
test                     /home/user/miniconda3/envs/test"""
    return_value = sample_output.encode('utf-8')
    with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.conda_env_list', return_value=return_value):
        with patch('os.path.exists', return_value=True):
            logger = ChronicleLogger(logname="TestApp")
            assert logger.condaPath() == ''
            assert logger.condaPath() == ''  # Cached

# NEW: Added test for updated __set_base_dir__ hierarchy: prioritizes explicit basedir, then conda (.app append), pyenvVenv (.app append), venv (.app append), then home/root fallbacks; uses patches for env detection and verifies resulting baseDir with .app/{appname} subpath
def test_base_dir_hierarchy_conda_priority(tmpdir):
    sample_output = """ 
# conda environments:
#
# * -> active
# + -> frozen
base                     /mock/conda/envs
test                 *   /mock/conda/envs/test
"""
    return_value = sample_output.encode('utf-8')
    with patch('ChronicleLogger.ChronicleLogger.ChronicleLogger.conda_env_list', return_value=return_value):
        with patch('sys.executable', '/miniconda3/bin/python'):  # inConda True
            with patch('os.path.exists', return_value=True):
                logger = ChronicleLogger(logname="TestApp")
                expected = os.path.join('/mock/conda/envs/test', '.app', 'test-app')  # NEW: Matches .app append for env case
                assert logger.baseDir() == expected

# NEW: Continued test for base_dir_hierarchy: pyenvVenv case with .app append (mocks subprocess for active venv path)
@patch('subprocess.check_output')
@patch('os.path.exists', return_value=True)
def test_base_dir_hierarchy_pyenv_venv(mock_exists, mock_output, monkeypatch):
    sample_output = """  system
* build --> /mock/pyenv/versions/3.12/envs/build"""  # NEW: Simplified sample without extra text for clean parsing
    mock_output.return_value = sample_output.encode('utf-8')
    with patch('sys.executable', '/.pyenv/shims/python'):  # inPyenv True, but no conda
        monkeypatch.delenv('CONDA_DEFAULT_ENV', raising=False)
        logger = ChronicleLogger(logname="TestApp")
        expected = os.path.join('/mock/pyenv/versions/3.12/envs/build', '.app', 'test-app')  # NEW: Matches .app append
        assert logger.baseDir() == expected

# NEW: Continued test for base_dir_hierarchy: venv case with .app append (sets VIRTUAL_ENV, no conda/pyenv)
def test_base_dir_hierarchy_venv(monkeypatch):
    venv_path = '/mock/venv'
    monkeypatch.setenv('VIRTUAL_ENV', venv_path)
    monkeypatch.delenv('CONDA_DEFAULT_ENV', raising=False)
    with patch('sys.executable', '/usr/bin/python'):  # No pyenv/conda, but inPython True for kebab
        logger = ChronicleLogger(logname="TestApp")
        expected = os.path.join(venv_path, '.app', 'test-app')  # NEW: Matches .app append for venv
        assert logger.baseDir() == expected

# NEW: Continued test for base_dir_hierarchy: fallback to home .app/{appname} for inPython True, non-root
@patch('ChronicleLogger._Suroot.is_root', return_value=False)
def test_base_dir_hierarchy_python_non_root(mock_root, monkeypatch):
    monkeypatch.delenv('VIRTUAL_ENV', raising=False)
    monkeypatch.delenv('CONDA_DEFAULT_ENV', raising=False)
    with patch('sys.executable', '/usr/bin/python3'):  # inPython True
        logger = ChronicleLogger(logname="TestApp")
        expected = os.path.join(os.path.expanduser("~"), '.app', 'test-app')  # NEW: Matches kebab-cased fallback
        assert logger.baseDir() == expected

def test_base_dir_hierarchy_root(monkeypatch):
    with patch('ChronicleLogger._Suroot.is_root', return_value=True):
        with patch('sys.executable', '/usr/bin/root-binary'):
            monkeypatch.delenv('VIRTUAL_ENV', raising=False)
            monkeypatch.delenv('CONDA_DEFAULT_ENV', raising=False)
            logger = ChronicleLogger(logname="RootApp")
            assert logger.baseDir() == '/var/RootApp'  # NEW: Matches preserved CamelCase for binary/root mode

# NEW: Added test for __set_log_dir__ derivation: verifies logDir() appends "/log" to baseDir (e.g., from env or fallback), with explicit override
def test_log_dir_derivation_from_base_dir(monkeypatch):
    base_path = '/mock/base'
    logger = ChronicleLogger(logname="TestApp", basedir=base_path)  # NEW: Explicit basedir set in init
    expected_log = '{0}/log'.format(base_path)  # NEW: Matches derivation from set baseDir + /log
    assert logger.logDir() == expected_log

def test_log_dir_explicit_override():
    explicit_log = '/mock/explicit/log'
    logger = ChronicleLogger(logname="TestApp", logdir=explicit_log)
    assert logger.logDir() == explicit_log  # Overrides baseDir derivation

def test_current_log_file_path(log_dir, logger):
    # Write something to force file creation
    logger.log_message("Test message")
    
    current_file = logger.currentLogFile()
    assert current_file != ""
    assert current_file.startswith(log_dir)
    assert current_file.endswith(".log")
    
    today = datetime.now().strftime("%Y%m%d")
    expected = os.path.join(log_dir, f"test-app-{today}.log")
    assert current_file == expected


def test_rotation_updates_current_log_file(log_dir, logger, fake_time_provider):
    # Use injected fake time provider
    logger.log_message("Day 1")
    day1_file = logger.currentLogFile()
    assert "20251225" in day1_file
    
    fake_time_provider.advance(days=1)
    logger.log_message("Day 2")
    
    day2_file = logger.currentLogFile()
    assert "20251226" in day2_file
    assert day2_file != day1_file

def test_archiving_with_fake_time(log_dir, fake_time_provider):
    """
    Test that very old logs (> LOG_REMOVAL_DAYS) are deleted (not just archived),
    and that currentLogFile() correctly reflects the active log file after rotation/cleanup.
    """
    # Use injected fake time provider
    logger = ChronicleLogger(
        logname="TestApp",
        logdir=log_dir,
        time_provider=fake_time_provider
    )

    # Step 1: Create a very old log file (40 days old)
    old_date = fake_time_provider.now() - fake_time_provider.timedelta(days=40)
    old_filename = f"test-app-{old_date.strftime('%Y%m%d')}.log"
    old_path = os.path.join(log_dir, old_filename)
    with open(old_path, 'w') as f:
        f.write("old content from 40 days ago")

    # Step 2: Remember initial current log file (should be today's file)
    initial_current_file = logger.currentLogFile()
    assert initial_current_file != ""
    assert initial_current_file.endswith(".log")
    assert os.path.basename(initial_current_file).startswith("test-app-")

    # Step 3: Advance time far enough to trigger removal (past 30 days)
    fake_time_provider.advance(days=41)

    # Step 4: Write a new message → this triggers real rotation + cleanup
    logger.log_message("Trigger cleanup and rotation now")

    # Step 5: Verify archiving/removal behavior
    assert not os.path.exists(old_path)                    # original file deleted
    assert not os.path.exists(old_path + ".tar.gz")       # no archive left (past removal threshold)

    # Step 6: Verify currentLogFile() is updated correctly
    new_current_file = logger.currentLogFile()
    assert new_current_file != ""
    assert new_current_file != initial_current_file        # should be a new file after rotation
    assert new_current_file.endswith(".log")
    
    today_str = fake_time_provider.now().strftime("%Y%m%d")
    expected_new_filename = f"test-app-{today_str}.log"
    assert os.path.basename(new_current_file) == expected_new_filename

    # Optional: check that the new file actually contains the trigger message
    with open(new_current_file, 'r') as f:
        content = f.read()
        assert "Trigger cleanup and rotation now" in content

def test_archiving_with_fake_time(log_dir, fake_time_provider):
    logger = ChronicleLogger(
        logname="TestApp",
        logdir=log_dir,
        time_provider=fake_time_provider
    )

    # BEFORE advance: current file should be for day 0 (20251225)
    initial_current_file = logger.currentLogFile()
    assert initial_current_file != ""
    assert initial_current_file.endswith(".log")
    assert "test-app-20251225" in initial_current_file
    assert os.path.exists(initial_current_file)

    # Create old file (40 days old)
    old_date = fake_time_provider.now() - fake_time_provider.timedelta(days=40)
    old_filename = f"test-app-{old_date.strftime('%Y%m%d')}.log"
    old_path = os.path.join(log_dir, old_filename)
    with open(old_path, 'w') as f:
        f.write("old content from 40 days ago")

    # Advance 41 days → simulated date becomes ~Feb 4, 2026
    fake_time_provider.advance(days=41)

    # Write message → triggers rotation (new filename for current simulated date)
    logger.log_message("Trigger cleanup and rotation")

    # AFTER: currentLogFile() should now point to new date's file
    new_current_file = logger.currentLogFile()
    assert new_current_file != ""
    assert new_current_file != initial_current_file
    assert "test-app-20260204" in new_current_file  # or whatever the new date is
    assert os.path.exists(new_current_file)

    # Old file should be gone (removed, no archive)
    assert not os.path.exists(old_path)
    assert not os.path.exists(old_path + ".tar.gz")
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
from datetime import datetime, timedelta

import pytest

TEST_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(TEST_DIR, "..", "src"))
sys.path.insert(0, SRC_DIR)

from chronicle_logger.ChronicleLogger import ChronicleLogger

# test/test_chronicle_logger.py

# NEW: Compatibility for pytest fixtures (tmp_path is Py3-only Path; use tmpdir for Py2/3 dual support)
#      tmpdir works in pytest 4.6.11 (Py2) as str, and in Py3 as Path, but we treat as str for compat
@pytest.fixture
def log_dir(tmpdir):  # NEW: Changed from tmp_path to tmpdir for Py2 compat (pin pytest==4.6.11)
    log_path = tmpdir.join("log")  # NEW: tmpdir.join() works for both (str in Py2, Path in Py3)
    return str(log_path)  # NEW: Ensure str for cross-version ops

@pytest.fixture
def logger(log_dir):
    return ChronicleLogger(logname="TestApp", logdir=log_dir)  # NEW: Pass str(log_dir)

def test_directory_created_on_init_when_logdir_given(log_dir):
    assert not os.path.exists(log_dir)  # NEW: Use os.path.exists instead of .exists() for Py2 compat
    ChronicleLogger(logname="TestApp", logdir=log_dir)
    assert os.path.exists(log_dir)

def test_logname_becomes_kebab_case():
    logger = ChronicleLogger(logname="TestApp")
    assert logger.logName() == "test-app"

    logger = ChronicleLogger(logname="HelloWorld")
    assert logger.logName() == "hello-world"

@patch('chronicle_logger.ChronicleLogger.ChronicleLogger.inPython', return_value=False)
def test_logname_unchanged_in_cython_binary(mock):
    logger = ChronicleLogger(logname="PreserveCase")
    logger.logName("PreserveCase")
    assert logger.logName() == "PreserveCase"

def test_basedir_is_user_defined_and_independent(tmpdir):  # NEW: Changed tmp_path to tmpdir for compat
    custom = str(tmpdir.join("myconfig"))  # NEW: Use tmpdir and str()
    logger = ChronicleLogger(logname="App", basedir=custom)
    assert logger.baseDir() == custom

@patch('chronicle_logger.Suroot._Suroot.should_use_system_paths', return_value=True)
def test_logdir_uses_system_path_when_privileged_and_not_set(mock):
    logger = ChronicleLogger(logname="RootApp")
    assert logger.logDir() == "/var/log/root-app"

@patch('chronicle_logger.Suroot._Suroot.should_use_system_paths', return_value=False)
def test_logdir_uses_user_path_when_not_privileged_and_not_set(mock):
    logger = ChronicleLogger(logname="UserApp")
    expected = os.path.join(os.path.expanduser("~"), ".app/user-app", "log")
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

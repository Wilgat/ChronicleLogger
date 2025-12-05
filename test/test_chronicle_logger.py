# test/test_chronicle_logger.py
import os
import sys
import tarfile
from datetime import datetime, timedelta

import pytest
from unittest.mock import patch

TEST_DIR = os.path.dirname(__file__)
SRC_DIR = os.path.abspath(os.path.join(TEST_DIR, "..", "src"))
sys.path.insert(0, SRC_DIR)

from chronicle_logger.ChronicleLogger import ChronicleLogger


@pytest.fixture
def log_dir(tmp_path):
    return tmp_path / "log"


@pytest.fixture
def logger(log_dir):
    return ChronicleLogger(logname="TestApp", logdir=str(log_dir))


def test_directory_created_on_init_when_logdir_given(log_dir):
    assert not log_dir.exists()
    ChronicleLogger(logname="TestApp", logdir=str(log_dir))
    assert log_dir.exists()


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


def test_basedir_is_user_defined_and_independent(tmp_path):
    custom = str(tmp_path / "myconfig")
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
    logger = ChronicleLogger(logname="AnyApp", logdir=str(log_dir))
    assert logger.logDir() == str(log_dir)


def test_log_message_writes_correct_filename(logger, log_dir):
    logger.log_message("Hello!", level="INFO")
    today = datetime.now().strftime("%Y%m%d")
    logfile = log_dir / f"test-app-{today}.log"  # ← test-app, not testapp
    assert logfile.exists()


@pytest.mark.parametrize("level", ["ERROR", "CRITICAL", "FATAL"])
def test_error_levels_go_to_stderr(logger, level, capsys):
    logger.log_message("Boom!", level=level)
    captured = capsys.readouterr()
    assert "Boom!" in captured.err


def test_archive_old_logs(log_dir):
    logger = ChronicleLogger(logname="TestApp", logdir=str(log_dir))
    old_file = log_dir / f"test-app-{(datetime.now() - timedelta(days=10)).strftime('%Y%m%d')}.log"
    old_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.write_text("old")
    logger.archive_old_logs()
    assert (log_dir / f"{old_file.name}.tar.gz").exists()


def test_debug_mode(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    assert not ChronicleLogger(logname="A").isDebug()
    monkeypatch.setenv("DEBUG", "show")
    assert ChronicleLogger(logname="B").isDebug()
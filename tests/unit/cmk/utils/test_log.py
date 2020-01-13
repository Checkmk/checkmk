# encoding: utf-8

import sys
import logging
import pytest  # type: ignore
import cmk.utils.log as log

from testlib import on_time


def test_get_logger():
    l = logging.getLogger("cmk.asd")
    assert l.parent == log.logger


def test_setup_console_logging(capsys):
    out, err = capsys.readouterr()
    log.clear_console_logging()

    assert out == ""
    assert err == ""

    logging.getLogger("cmk.test").info("test123")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    log.setup_console_logging()
    l = logging.getLogger("cmk.test")
    l.info("test123")

    # Cleanup handler registered with log.setup_console_logging()
    log.logger.handlers.pop()

    out, err = capsys.readouterr()
    assert out == "test123\n"
    assert err == ""


def test_open_log(tmp_path):
    log_file = tmp_path / "test.log"
    log.open_log(log_file)

    with on_time('2018-04-15 16:50', 'CET'):
        log.logger.warning("abc")
        log.logger.warning(u"äbc")
        # With python 3 we do not have the implicit conversion from byte strings
        # to text strings anymore: No need to test this.
        if sys.version_info[0] >= 3:
            log.logger.warning("äbc")
        else:
            log.logger.warning(b"\xc3\xa4bc")

    with log_file.open("rb") as f:
        assert f.read() == \
            b"2018-04-15 18:50:00,000 [30] [cmk] abc\n" \
            b"2018-04-15 18:50:00,000 [30] [cmk] \xc3\xa4bc\n" \
            b"2018-04-15 18:50:00,000 [30] [cmk] \xc3\xa4bc\n"


def test_set_verbosity():
    root = logging.getLogger('cmk')
    root.setLevel(logging.INFO)

    l = logging.getLogger("cmk.test_logger")
    assert l.getEffectiveLevel() == logging.INFO
    assert l.isEnabledFor(log.VERBOSE) is False
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(0))
    assert l.getEffectiveLevel() == logging.INFO
    assert l.isEnabledFor(log.VERBOSE) is False
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(1))
    assert l.getEffectiveLevel() == log.VERBOSE
    assert l.isEnabledFor(log.VERBOSE) is True
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(2))
    assert l.getEffectiveLevel() == logging.DEBUG
    assert l.isEnabledFor(log.VERBOSE) is True
    assert l.isEnabledFor(logging.DEBUG) is True

    with pytest.raises(ValueError):
        log.logger.setLevel(log.verbosity_to_log_level(3))

    # Reset verbosity for next test run.
    log.logger.setLevel(log.verbosity_to_log_level(0))

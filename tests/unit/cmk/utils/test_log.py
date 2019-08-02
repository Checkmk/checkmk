import logging
import pytest  # type: ignore
import cmk.utils.log as log


def test_get_logger():
    l = log.get_logger("asd")
    assert l.name == "cmk.asd"
    assert l.parent == log.logger

    l = log.get_logger("asd.aaa")
    assert l.name == "cmk.asd.aaa"


def test_setup_console_logging(capsys):
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    log.get_logger("test").info("test123")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    log.setup_console_logging()
    l = log.get_logger("test")
    l.info("test123")

    # Cleanup handler registered with log.setup_console_logging()
    log.logger.handlers.pop()

    out, err = capsys.readouterr()
    assert out == "test123\n"
    assert err == ""


def test_set_verbosity():
    l = log.get_logger("test_logger")
    assert l.getEffectiveLevel() == logging.INFO
    assert l.is_verbose() is False
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(0))
    assert l.getEffectiveLevel() == logging.INFO
    assert l.is_verbose() is False
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(1))
    assert l.getEffectiveLevel() == log.VERBOSE
    assert l.is_verbose() is True
    assert l.isEnabledFor(logging.DEBUG) is False

    log.logger.setLevel(log.verbosity_to_log_level(2))
    assert l.getEffectiveLevel() == logging.DEBUG
    assert l.is_verbose() is True
    assert l.isEnabledFor(logging.DEBUG) is True

    with pytest.raises(ValueError):
        log.logger.setLevel(log.verbosity_to_log_level(3))

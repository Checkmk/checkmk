import logging
import pytest  # type: ignore
import cmk.utils.log as log


def test_get_logger():
    l = logging.getLogger("cmk.asd")
    assert l.parent == log.logger


def test_setup_console_logging(capsys):
    out, err = capsys.readouterr()
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


def test_set_verbosity():
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

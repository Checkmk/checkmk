import logging
import pytest  # type: ignore
import cmk.utils.log


def test_get_logger():
    l = cmk.utils.log.get_logger("asd")
    assert l.name == "cmk.asd"
    assert l.parent == cmk.utils.log.logger

    l = cmk.utils.log.get_logger("asd.aaa")
    assert l.name == "cmk.asd.aaa"


def test_setup_console_logging(capsys):
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    cmk.utils.log.get_logger("test").info("test123")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    cmk.utils.log.setup_console_logging()
    l = cmk.utils.log.get_logger("test")
    l.info("test123")

    # Cleanup handler registered with cmk.utils.log.setup_console_logging()
    cmk.utils.log.logger.handlers.pop()

    out, err = capsys.readouterr()
    assert out == "test123\n"
    assert err == ""


def test_set_verbosity():
    l = cmk.utils.log.get_logger("test_logger")
    assert l.getEffectiveLevel() == logging.INFO
    assert l.is_verbose() is False
    assert l.isEnabledFor(logging.DEBUG) is False

    cmk.utils.log.set_verbosity(0)
    assert l.getEffectiveLevel() == logging.INFO
    assert l.is_verbose() is False
    assert l.isEnabledFor(logging.DEBUG) is False

    cmk.utils.log.set_verbosity(1)
    assert l.getEffectiveLevel() == cmk.utils.log.VERBOSE
    assert l.is_verbose() is True
    assert l.isEnabledFor(logging.DEBUG) is False

    cmk.utils.log.set_verbosity(2)
    assert l.getEffectiveLevel() == logging.DEBUG
    assert l.is_verbose() is True
    assert l.isEnabledFor(logging.DEBUG) is True

    with pytest.raises(NotImplementedError):
        cmk.utils.log.set_verbosity(3)

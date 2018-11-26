import pytest
import cmk.log


def test_get_logger():
    l = cmk.log.get_logger("asd")
    assert l.name == "cmk.asd"
    assert l.parent == cmk.log.logger

    l = cmk.log.get_logger("asd.aaa")
    assert l.name == "cmk.asd.aaa"


def test_setup_console_logging(capsys):
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    cmk.log.get_logger("test").info("test123")

    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""

    cmk.log.setup_console_logging()
    l = cmk.log.get_logger("test")
    l.info("test123")

    # Cleanup handler registered with cmk.log.setup_console_logging()
    cmk.log.logger.handlers.pop()

    out, err = capsys.readouterr()
    assert out == "test123\n"
    assert err == ""


def test_set_verbosity():
    l = cmk.log.get_logger("test_logger")
    assert l.getEffectiveLevel() == cmk.log.INFO
    assert l.is_verbose() == False
    assert l.is_very_verbose() == False

    cmk.log.set_verbosity(0)
    assert l.getEffectiveLevel() == cmk.log.INFO
    assert l.is_verbose() == False
    assert l.is_very_verbose() == False

    cmk.log.set_verbosity(1)
    assert l.getEffectiveLevel() == cmk.log.VERBOSE
    assert l.is_verbose() == True
    assert l.is_very_verbose() == False

    cmk.log.set_verbosity(2)
    assert l.getEffectiveLevel() == cmk.log.DEBUG
    assert l.is_verbose() == True
    assert l.is_very_verbose() == True

    with pytest.raises(NotImplementedError):
        cmk.log.set_verbosity(3)

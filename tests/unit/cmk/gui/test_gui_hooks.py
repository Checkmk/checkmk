from __future__ import division
import pytest

import cmk.gui.hooks as hooks


@pytest.fixture(autouse=True)
def reset_hooks():
    hooks.hooks.clear()


def test_hook_registration():
    assert hooks.hooks == {}

    # pre 1.6 API
    hooks.register("bla", lambda: True)
    assert hooks.get("bla")[0].is_builtin == False

    hooks.register_builtin("blub", lambda: True)
    hooks.register_from_plugin("blub", lambda: False)
    assert hooks.get("blub")[0].is_builtin == True
    assert hooks.get("blub")[1].is_builtin == False

    assert hooks.registered("bla") == True
    assert hooks.registered("blub") == True
    assert hooks.registered("bli") == False

    assert len(hooks.get("bla")) == 1
    assert len(hooks.get("blub")) == 2
    assert len(hooks.get("bli")) == 0


def test_call(mocker):
    hook1_mock = mocker.Mock()
    hook2_mock = mocker.Mock()
    hooks.register("bla", hook1_mock)
    hooks.register("blub", hook2_mock)

    hooks.call("bla")
    hook1_mock.assert_called_once()
    hook2_mock.assert_not_called()

    hooks.call("blub")
    hook1_mock.assert_called_once()
    hook2_mock.assert_called_once()


def test_call_exception_handling(mocker):
    hooks.register_builtin("bli", lambda: 1.0 / 0.0)
    hook3_mock = mocker.Mock()
    hooks.register("bli", hook3_mock)
    with pytest.raises(ZeroDivisionError, match="float division by zero"):
        hooks.call("bli")
    hook3_mock.assert_not_called()


def test_builtin_vs_plugin_hooks():
    hooks.register_builtin("bla", lambda: True)
    assert hooks.registered("bla") == True

    hooks.register_from_plugin("blub", lambda: True)
    assert hooks.registered("blub") == True

    hooks.load_plugins(force=True)

    assert hooks.registered("bla") == True
    assert hooks.registered("blub") == False

import cmk.utils.debug


def test_default():
    assert cmk.utils.debug.enabled() is False


def test_toggle():
    assert cmk.utils.debug.enabled() is False
    assert cmk.utils.debug.disabled() is True

    cmk.utils.debug.enable()

    assert cmk.utils.debug.enabled() is True
    assert cmk.utils.debug.disabled() is False

    cmk.utils.debug.disable()

    assert cmk.utils.debug.enabled() is False
    assert cmk.utils.debug.disabled() is True

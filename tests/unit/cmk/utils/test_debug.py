import cmk.utils.debug


def test_default():
    assert cmk.utils.debug.enabled() == False


def test_toggle():
    assert cmk.utils.debug.enabled() == False
    assert cmk.utils.debug.disabled() == True

    cmk.utils.debug.enable()

    assert cmk.utils.debug.enabled() == True
    assert cmk.utils.debug.disabled() == False

    cmk.utils.debug.disable()

    assert cmk.utils.debug.enabled() == False
    assert cmk.utils.debug.disabled() == True

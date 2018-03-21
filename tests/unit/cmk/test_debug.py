
import cmk.debug

def test_default():
    assert cmk.debug.enabled() == False


def test_toggle():
    assert cmk.debug.enabled() == False
    assert cmk.debug.disabled() == True

    cmk.debug.enable()

    assert cmk.debug.enabled() == True
    assert cmk.debug.disabled() == False

    cmk.debug.disable()

    assert cmk.debug.enabled() == False
    assert cmk.debug.disabled() == True

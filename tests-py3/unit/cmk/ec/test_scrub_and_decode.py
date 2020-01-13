# encoding: utf-8

import cmk.ec.main


def test_scrub_and_decode():
    result = cmk.ec.main.scrub_and_decode("0123bla\nbla\tbla\0blub\1buh\2boh\3")
    assert result == "0123blabla blablubbuhboh\3"
    assert isinstance(result, str)

    result = cmk.ec.main.scrub_and_decode(u"0123bla\nbla\tbla\0blub\1buh\2boh\3")
    assert result == u"0123blabla blablubbuhboh\3"
    assert isinstance(result, str)

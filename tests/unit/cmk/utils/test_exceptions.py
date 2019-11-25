# -*- coding: utf-8 -*-

import six
import pytest  # type: ignore
from cmk.utils.exceptions import MKException


@pytest.mark.parametrize("sources, expected", [
    ((123,), "123"),
    ((123.4,), "123.4"),
    ((b"h\xc3\xa9 \xc3\x9f\xc3\x9f",), u"h\xe9 \xdf\xdf"),
    ((u"hé ßß",), u"h\xe9 \xdf\xdf"),
    ((b"sdffg\xed",), "b'sdffg\\xed'"),
    ((
        b"h\xc3\xa9 \xc3\x9f\xc3\x9f",
        123,
        123.4,
        u"hé ßß",
        b"sdffg\xed",
    ), "('h\\xc3\\xa9 \\xc3\\x9f\\xc3\\x9f', 123, 123.4, u'h\\xe9 \\xdf\\xdf', 'sdffg\\xed')"),
])
def test_mkexception(sources, expected):
    exc = MKException(*sources)
    assert six.text_type(exc) == expected
    assert six.text_type(MKException(exc)) == expected

# -*- coding: utf-8 -*-

import pytest  # type: ignore
from cmk.utils.encoding import (
    ensure_unicode,
    ensure_bytestr,
)


@pytest.mark.parametrize("source, utf8str", [
    ('hi', u'hi'),
    ("há li", u"há li"),
    (u"hé ßß", u"hé ßß"),
])
def test_ensure_unicode(source, utf8str):
    assert ensure_unicode(source) == utf8str


@pytest.mark.parametrize("source, bytestr", [
    ('hi', b'hi'),
    ("há li", b"h\xc3\xa1 li"),
    (u"hé ßß", b"h\xc3\xa9 \xc3\x9f\xc3\x9f"),
])
def test_ensure_bytestr(source, bytestr):
    assert ensure_bytestr(source) == bytestr

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
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

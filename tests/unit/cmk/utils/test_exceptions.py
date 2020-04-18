#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import six
import pytest  # type: ignore[import]
from cmk.utils.exceptions import MKException


@pytest.mark.parametrize("sources, expected_py2, expected_py3", [
    ((123,), "123", "123"),
    ((123.4,), "123.4", "123.4"),
    ((b"h\xc3\xa9 \xc3\x9f\xc3\x9f",), u"h\xe9 \xdf\xdf", "b'h\\xc3\\xa9 \\xc3\\x9f\\xc3\\x9f'"),
    ((u"hé ßß",), u"h\xe9 \xdf\xdf", u'hé ßß'),
    ((b"sdffg\xed",), "b'sdffg\\xed'", "b'sdffg\\xed'"),
    ((
        b"h\xc3\xa9 \xc3\x9f\xc3\x9f",
        123,
        123.4,
        u"hé ßß",
        b"sdffg\xed",
    ), "('h\\xc3\\xa9 \\xc3\\x9f\\xc3\\x9f', 123, 123.4, u'h\\xe9 \\xdf\\xdf', 'sdffg\\xed')",
     "(b'h\\xc3\\xa9 \\xc3\\x9f\\xc3\\x9f', 123, 123.4, 'hé ßß', b'sdffg\\xed')"),
])
def test_mkexception(sources, expected_py2, expected_py3):
    expected = expected_py3 if sys.version_info[0] >= 3 else expected_py2

    exc = MKException(*sources)
    assert six.text_type(exc) == expected
    assert six.text_type(MKException(exc)) == expected

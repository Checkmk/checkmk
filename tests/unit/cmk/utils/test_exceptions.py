#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.exceptions import MKException


@pytest.mark.parametrize(
    "sources, expected",
    [
        ((123,), "123"),
        ((123.4,), "123.4"),
        ((b"h\xc3\xa9 \xc3\x9f\xc3\x9f",), "b'h\\xc3\\xa9 \\xc3\\x9f\\xc3\\x9f'"),
        (("hé ßß",), "hé ßß"),
        ((b"sdffg\xed",), "b'sdffg\\xed'"),
        (
            (
                b"h\xc3\xa9 \xc3\x9f\xc3\x9f",
                123,
                123.4,
                "hé ßß",
                b"sdffg\xed",
            ),
            "(b'h\\xc3\\xa9 \\xc3\\x9f\\xc3\\x9f', 123, 123.4, 'hé ßß', b'sdffg\\xed')",
        ),
    ],
)
def test_mkexception(sources, expected):
    exc = MKException(*sources)
    assert str(exc) == expected
    assert str(MKException(exc)) == expected

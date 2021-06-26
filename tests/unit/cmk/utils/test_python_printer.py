#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from typing import List
import pytest
from cmk.utils.python_printer import pformat


def test_same_as_repr():
    objs: List[object] = [
        None,
        True,
        False,
        1,
        -2,
        3.1415,
        (),
        (11,),
        (11, 22, 33),
        ((11,), (22, (1.25, -44))),
        [],
        [[], [11, (22, []), 3.5]],
        {},
        {
            11: 22,
            (33, 44): [-8],
        },
        {
            (11,): (33, 44, 22),
        },
    ]
    for obj in objs:
        assert pformat(obj) == repr(obj)


@pytest.mark.parametrize('obj, result', [
    (set(), "set()"),
    ({11}, "{11}"),
    ({11, -22, 33}, "{-22, 11, 33}"),
    ({(11, 22, (33, 44))}, "{(11, 22, (33, 44))}"),
])
def test_sets(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize(
    'obj, result',
    [
        (b'', "b''"),  #
        (u'bläh'.encode('utf-8'), "b'bl\\xc3\\xa4h'"),
        (((11,), (22, (u'bläh'.encode('utf-8'), -44))), "((11,), (22, (b'bl\\xc3\\xa4h', -44)))"),
        ([[], [11, (u'blöh'.encode('utf-8'), []), 3.5]], "[[], [11, (b'bl\\xc3\\xb6h', []), 3.5]]"),
        ({u'bläh'.encode('utf-8')}, "{b'bl\\xc3\\xa4h'}"),
        ({
            u'Kontiomäki'.encode('utf-8'): {b'Wassersee'},
            u'Vesijärvi'.encode('utf-8'): [(u'Bärenhügel'.encode('utf-8'), True), 42],
        },
         "{b'Kontiom\\xc3\\xa4ki': {b'Wassersee'}, b'Vesij\\xc3\\xa4rvi': [(b'B\\xc3\\xa4renh\\xc3\\xbcgel', True), 42]}"
        )
    ])
def test_byte_strings_are_prefixed(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize('obj, result', [
    (u'', "u''"),
    (u'bläh', "u'bl\\xe4h'"),
    (((11,), (22, (u'bläh', -44))), "((11,), (22, (u'bl\\xe4h', -44)))"),
    ([[], [11, (u'blöh', []), 3.5]], "[[], [11, (u'bl\\xf6h', []), 3.5]]"),
    ({
        u'Kontiomäki': {u'Wassersee'},
        u'Vesijärvi': [(u'Bärenhügel', True), 42],
    },
     "{u'Kontiom\\xe4ki': {u'Wassersee'}, u'Vesij\\xe4rvi': [(u'B\\xe4renh\\xfcgel', True), 42]}"),
])
def test_unicode_strings_are_prefixed(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize('obj, result', [
    (u'bl\'ah', 'u\"bl\'ah"'),
    (u'"bl\'ah', "u'\"bl\\'ah'"),
])
def test_unicode_strings_quote_escaping(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize('obj, result', [
    (u'bl\0ah', "u'bl\\x00ah'"),
    (u'bl\nah', "u'bl\\nah'"),
    (u'bl\r\nah', "u'bl\\r\\nah'"),
    (u'bl\n\rah', "u'bl\\n\\rah'"),
])
def test_unicode_strings_newline_escaping(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize('obj', [
    (frozenset([11, 22]),),
    (NotImplemented,),
    (sys,),
    (memoryview(b'blabla'),),
    (type("Hurz", (), {}),),
])
def test_raise_when_unknown(obj):
    with pytest.raises(ValueError):
        pformat(obj)

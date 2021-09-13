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


@pytest.mark.parametrize(
    "obj, result",
    [
        (set(), "set()"),
        ({11}, "{11}"),
        ({11, -22, 33}, "{-22, 11, 33}"),
        ({(11, 22, (33, 44))}, "{(11, 22, (33, 44))}"),
    ],
)
def test_sets(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize(
    "obj, result",
    [
        (b"", "b''"),  #
        ("bläh".encode("utf-8"), "b'bl\\xc3\\xa4h'"),
        (((11,), (22, ("bläh".encode("utf-8"), -44))), "((11,), (22, (b'bl\\xc3\\xa4h', -44)))"),
        ([[], [11, ("blöh".encode("utf-8"), []), 3.5]], "[[], [11, (b'bl\\xc3\\xb6h', []), 3.5]]"),
        ({"bläh".encode("utf-8")}, "{b'bl\\xc3\\xa4h'}"),
        (
            {
                "Kontiomäki".encode("utf-8"): {b"Wassersee"},
                "Vesijärvi".encode("utf-8"): [("Bärenhügel".encode("utf-8"), True), 42],
            },
            "{b'Kontiom\\xc3\\xa4ki': {b'Wassersee'}, b'Vesij\\xc3\\xa4rvi': [(b'B\\xc3\\xa4renh\\xc3\\xbcgel', True), 42]}",
        ),
    ],
)
def test_byte_strings_are_prefixed(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize(
    "obj, result",
    [
        ("", "u''"),
        ("bläh", "u'bl\\xe4h'"),
        (((11,), (22, ("bläh", -44))), "((11,), (22, (u'bl\\xe4h', -44)))"),
        ([[], [11, ("blöh", []), 3.5]], "[[], [11, (u'bl\\xf6h', []), 3.5]]"),
        (
            {
                "Kontiomäki": {"Wassersee"},
                "Vesijärvi": [("Bärenhügel", True), 42],
            },
            "{u'Kontiom\\xe4ki': {u'Wassersee'}, u'Vesij\\xe4rvi': [(u'B\\xe4renh\\xfcgel', True), 42]}",
        ),
    ],
)
def test_unicode_strings_are_prefixed(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize(
    "obj, result",
    [
        ("bl'ah", 'u"bl\'ah"'),
        ("\"bl'ah", "u'\"bl\\'ah'"),
    ],
)
def test_unicode_strings_quote_escaping(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize(
    "obj, result",
    [
        ("bl\0ah", "u'bl\\x00ah'"),
        ("bl\nah", "u'bl\\nah'"),
        ("bl\r\nah", "u'bl\\r\\nah'"),
        ("bl\n\rah", "u'bl\\n\\rah'"),
    ],
)
def test_unicode_strings_newline_escaping(obj, result):
    assert pformat(obj) == result


@pytest.mark.parametrize(
    "obj",
    [
        (frozenset([11, 22]),),
        (NotImplemented,),
        (sys,),
        (memoryview(b"blabla"),),
        (type("Hurz", (), {}),),
    ],
)
def test_raise_when_unknown(obj):
    with pytest.raises(ValueError):
        pformat(obj)

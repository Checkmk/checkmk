#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-

import sys
import pytest  # type: ignore[import]
from cmk.utils.python_printer import pformat


def test_same_as_repr():
    for obj in [
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
            set(),
        {11, -22, 33},
        {(11, 22, (33, 44))},
        {},
        {
            11: 22,
            (33, 44): [-8],
        },
        {
            (11,): {22},
        },
    ]:
        assert pformat(obj) == repr(obj)


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
@pytest.mark.skipif(sys.version_info[0] < 3, reason="Not yet done...")
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
     "{u'Kontiom\\xe4ki': set([u'Wassersee']), u'Vesij\\xe4rvi': [(u'B\\xe4renh\\xfcgel', True), 42]}"
    ),
])
@pytest.mark.skipif(sys.version_info[0] >= 3, reason="Not yet done...")
def test_unicode_strings_are_prefixed(obj, result):
    assert pformat(obj) == result

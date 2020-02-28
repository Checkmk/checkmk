#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Print (a subset of) Python values independent of the Python version. The
main change is that all strings get a prefix. Basically a dumbed-down version
of Python's own pprint module plus the prefix change."""

import sys
from typing import Any, Callable, Dict, IO, Iterable, Optional, Tuple  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from io import StringIO as StrIO
    _bytes = bytes
    _str = str
    _long = int
    _bytes_prefix_to_add = ''
    _str_prefix_to_add = 'u'
else:
    from io import BytesIO as StrIO
    _bytes = str
    _str = unicode
    _long = long
    _bytes_prefix_to_add = 'b'
    _str_prefix_to_add = ''


def pprint(obj, stream=None):
    PythonPrinter(stream=stream).pprint(obj)


def pformat(obj):
    return PythonPrinter().pformat(obj)


class PythonPrinter(object):
    def __init__(self, stream=None):
        # type: (Optional[IO[str]]) -> None
        self._stream = sys.stdout if stream is None else stream

    def pprint(self, obj):
        # type: (object) -> None
        self._format(obj)
        self._write('\n')

    def _write(self, s):
        # type: (str) -> None
        self._stream.write(s)

    def pformat(self, obj):
        # type: (object) -> str
        sio = StrIO()
        PythonPrinter(stream=sio)._format(obj)
        return sio.getvalue()

    def _format(self, obj):
        # type: (object) -> None
        # NOTE: Fail early! We only want exact type matches here, no instance
        # checks and no magic calls to repr. Only this way we can ensure that
        # we don't miss any recursive calls down the line.
        _dispatch.get(type(obj), _format_unhandled_type)(self, obj)


def _format_unhandled_type(printer, obj):
    # type: (PythonPrinter, object) -> None
    raise ValueError('unhandled type %r' % type(obj))


def _format_via_repr(printer, obj):
    # type: (PythonPrinter, object) -> None
    printer._write(repr(obj))


def _format_byte_string(printer, obj):
    # type: (PythonPrinter, _bytes) -> None
    printer._write(_bytes_prefix_to_add)
    printer._write(repr(obj))


def _format_unicode_string(printer, obj):
    # type: (PythonPrinter, _str) -> None
    printer._write(_str_prefix_to_add)
    printer._write(repr(obj))


def _format_tuple(printer, obj):
    # type: (PythonPrinter, tuple) -> None
    if len(obj) == 1:
        printer._write('(')
        printer._format(obj[0])
        printer._write(',)')
    else:
        _format_sequence(printer, obj, _format_object, '(', ')')


def _format_list(printer, obj):
    # type: (PythonPrinter, list) -> None
    _format_sequence(printer, obj, _format_object, '[', ']')


def _format_set(printer, obj):
    # type: (PythonPrinter, set) -> None
    if obj:
        _format_sequence(printer, sorted(obj, key=_safe_key), _format_object, '{', '}')
    else:
        printer._write('set()')


def _format_dict(printer, obj):
    # type: (PythonPrinter, dict) -> None
    _format_sequence(printer, sorted(obj.items(), key=_safe_tuple), _format_dict_item, '{', '}')


def _format_object(printer, obj):
    # type: (PythonPrinter, object) -> None
    printer._format(obj)


def _format_dict_item(printer, item):
    # type: (PythonPrinter, Tuple[object, object]) -> None
    printer._format(item[0])
    printer._write(': ')
    printer._format(item[1])


def _format_sequence(printer, seq, format_element, open_str, close_str):
    # type: (PythonPrinter, Iterable[object], Callable[[PythonPrinter, Any], None], str, str) -> None
    printer._write(open_str)
    separator = ''
    for obj in seq:
        printer._write(separator)
        separator = ', '
        format_element(printer, obj)
    printer._write(close_str)


_dispatch = {
    bytearray: _format_via_repr,
    float: _format_via_repr,
    complex: _format_via_repr,
    bool: _format_via_repr,
    type(None): _format_via_repr,
    int: _format_via_repr,
    _long: _format_via_repr,
    _bytes: _format_byte_string,
    _str: _format_unicode_string,
    tuple: _format_tuple,
    list: _format_list,
    set: _format_set,
    dict: _format_dict,
}  # type: Dict[Any, Any]


# Python 3 is a bit picky about comparing objects of different types.
class _safe_key(object):
    __slots__ = ['obj']

    def __init__(self, obj):
        self.obj = obj

    def __lt__(self, other):
        try:
            return self.obj < other.obj
        except TypeError:
            return (str(type(self.obj)), id(self.obj)) < (str(type(other.obj)), id(other.obj))


def _safe_tuple(t):
    return _safe_key(t[0]), _safe_key(t[1])

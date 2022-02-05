#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Print (a subset of) Python values independent of the Python version. The
main change is that all strings get a prefix. Basically a dumbed-down version
of Python's own pprint module plus the prefix change."""

import sys
from io import StringIO as StrIO
from typing import Any, Callable, Dict, IO, Iterable, List, Optional, Tuple

from cmk.utils.type_defs import EvalableFloat

_bytes = bytes
_str = str
_long = int
_bytes_prefix_to_add = ""
_str_prefix_to_add = "u"


def pprint(obj, stream=None):
    PythonPrinter(stream=stream).pprint(obj)


def pformat(obj):
    return PythonPrinter().pformat(obj)


class PythonPrinter:
    def __init__(self, stream: Optional[IO[str]] = None) -> None:
        self._stream = sys.stdout if stream is None else stream

    def pprint(self, obj: object) -> None:
        self._format(obj)
        self._write("\n")

    def _write(self, s: str) -> None:
        self._stream.write(s)

    def pformat(self, obj: object) -> str:
        sio = StrIO()
        PythonPrinter(stream=sio)._format(obj)
        return sio.getvalue()

    def _format(self, obj: object) -> None:
        # NOTE: Fail early! We only want exact type matches here, no instance
        # checks and no magic calls to repr. Only this way we can ensure that
        # we don't miss any recursive calls down the line.
        _dispatch.get(type(obj), _format_unhandled_type)(self, obj)


def _format_unhandled_type(printer: PythonPrinter, obj: object) -> None:
    raise ValueError("unhandled type %r" % type(obj))


def _format_via_repr(printer: PythonPrinter, obj: object) -> None:
    printer._write(repr(obj))


def _format_byte_string(printer: PythonPrinter, obj: _bytes) -> None:
    printer._write(_bytes_prefix_to_add)
    printer._write(repr(obj))


def _format_unicode_string(printer: PythonPrinter, obj: _str) -> None:
    printer._write(_str_prefix_to_add)

    if "'" in obj and '"' not in obj:
        closure = '"'
        quotes: Dict = {'"': '\\"'}
    else:
        closure = "'"
        quotes = {"'": "\\'"}

    # When Python 3 creates a repr which is interpreted by Python 2, we need to produce
    # a repr-string where non ascii characters are hex escaped as Python 2 usually does.
    chars: List[str] = []
    for c in obj:
        if 127 < (unicode_code := ord(c)) < 256:
            chars.append("\\x{:02x}".format(unicode_code))
        elif unicode_code >= 256:
            chars.append("\\u{:04x}".format(unicode_code))
        elif c.isalpha():
            chars.append(str(c))
        elif c in quotes:
            chars.append(quotes[c])
        else:
            chars.append(repr(str(c))[1:-1])

    printer._write("".join([closure, "".join(chars), closure]))


def _format_tuple(printer: PythonPrinter, obj: tuple) -> None:
    if len(obj) == 1:
        printer._write("(")
        printer._format(obj[0])
        printer._write(",)")
    else:
        _format_sequence(printer, obj, _format_object, "(", ")")


def _format_list(printer: PythonPrinter, obj: list) -> None:
    _format_sequence(printer, obj, _format_object, "[", "]")


def _format_set(printer: PythonPrinter, obj: set) -> None:
    if obj:
        _format_sequence(printer, sorted(obj, key=_safe_key), _format_object, "{", "}")
    else:
        printer._write("set()")


def _format_dict(printer: PythonPrinter, obj: dict) -> None:
    _format_sequence(printer, sorted(obj.items(), key=_safe_tuple), _format_dict_item, "{", "}")


def _format_object(printer: PythonPrinter, obj: object) -> None:
    printer._format(obj)


def _format_dict_item(printer: PythonPrinter, item: Tuple[object, object]) -> None:
    printer._format(item[0])
    printer._write(": ")
    printer._format(item[1])


def _format_sequence(
    printer: PythonPrinter,
    seq: Iterable[object],
    format_element: Callable[[PythonPrinter, Any], None],
    open_str: str,
    close_str: str,
) -> None:
    printer._write(open_str)
    separator = ""
    for obj in seq:
        printer._write(separator)
        separator = ", "
        format_element(printer, obj)
    printer._write(close_str)


_dispatch: Dict[Any, Any] = {
    bool: _format_via_repr,
    bytearray: _format_via_repr,
    _bytes: _format_byte_string,
    complex: _format_via_repr,
    dict: _format_dict,
    EvalableFloat: _format_via_repr,
    float: _format_via_repr,
    int: _format_via_repr,
    list: _format_list,
    _long: _format_via_repr,
    set: _format_set,
    _str: _format_unicode_string,
    tuple: _format_tuple,
    type(None): _format_via_repr,
}


# Python 3 is a bit picky about comparing objects of different types.
class _safe_key:
    __slots__ = ["obj"]

    def __init__(self, obj):
        self.obj = obj

    def __lt__(self, other):
        try:
            return self.obj < other.obj
        except TypeError:
            return (str(type(self.obj)), id(self.obj)) < (str(type(other.obj)), id(other.obj))


def _safe_tuple(t):
    return _safe_key(t[0]), _safe_key(t[1])

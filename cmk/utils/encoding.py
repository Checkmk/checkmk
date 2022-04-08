#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""This module provides some bytes-unicode encoding functions"""
import json
import typing
from typing import AnyStr

from six import ensure_str


def ensure_str_with_fallback(value: AnyStr, *, encoding: str, fallback: str) -> str:
    try:
        return ensure_str(value, encoding)  # pylint: disable= six-ensure-str-bin-call
    except UnicodeDecodeError:
        return ensure_str(value, fallback)  # pylint: disable= six-ensure-str-bin-call


def json_encode(value: typing.Any) -> str:
    """Encode a value to JSON

    Examples:

        >>> class Fake:
        ...     def __init__(self, _value):
        ...         self._value = _value

        >>> class FakeJson(Fake):
        ...     def __json__(self):
        ...          return self._value

        >>> class FakeHTML(Fake):
        ...     def to_json(self):
        ...          return self._value


        >>> json_encode(FakeJson({"foo": "bar"}))
        '{"foo": "bar"}'

        >>> json_encode(FakeHTML({"foo": "bar"}))
        '{"foo": "bar"}'

        >>> json_encode(Fake("won't work"))  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        TypeError: Object (...) of type 'Fake' is not JSON serializable

        >>> json_encode(None)
        'null'

        >>> json_encode(True)
        'true'

        >>> json_encode([True, False])
        '[true, false]'

        >>> json_encode({"a": 1, "b": 2})
        '{"a": 1, "b": 2}'

    Args:
        value:
            The value to encode

    Returns:
        The encoded value

    """

    def _json_serializer(obj):
        if hasattr(obj, "__json__") and callable(obj.__json__):
            return obj.__json__()

        if hasattr(obj, "to_json") and callable(obj.to_json):
            return obj.to_json()

        raise TypeError(f"Object ({obj}) of type '{type(obj).__name__}' is not JSON serializable")

    return json.dumps(value, default=_json_serializer)

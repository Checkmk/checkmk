#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import html
from typing import Any, Iterable, Optional, Union

HTMLInput = Union["HTML", str]


# TODO: In case one tries to __add__ or __iadd__ a str to a HTML object, this should fail by default
# or, in case we have to be more graceful, we should enforce the escaping of the added str unless
# one wrapps the str into a HTML object manually. This would enforce the caller to care more
# explicitly about escaping and would help prevent XSS issues.
class HTML:
    """HTML code wrapper to prevent escaping

    This is a simple class which wraps a string provided by the caller to make
    escaping.escape_attribute() know that this string should not be escaped.

    This way we can implement escaping while still allowing HTML code. This is useful when one needs
    to print out HTML tables in messages or help texts.
    """

    def __init__(self, value: HTMLInput = "") -> None:
        # Type hints are not used everywhere. So better be sure that we really have
        # the types we want.
        assert value is not None
        assert not isinstance(value, (float, int))
        self.value = value if isinstance(value, str) else str(value)

    def _ensure_str(self, value: HTMLInput) -> str:
        """return escaped string or HTML as str

        >>> HTML()._ensure_str("foo<b>bar</b>")
        'foo&lt;b&gt;bar&lt;/b&gt;'
        >>> HTML()._ensure_str(HTML("foo<b>bar</b>"))
        'foo<b>bar</b>'
        """
        return html.escape(value) if isinstance(value, str) else str(value)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return 'HTML("%s")' % self.value

    def __hash__(self) -> int:
        return hash(self.value)

    def to_json(self) -> str:
        return self.value

    def __add__(self, other: HTMLInput) -> HTML:
        return HTML(self.value + self._ensure_str(other))

    def __iadd__(self, other: HTMLInput) -> HTML:
        return self.__add__(other)

    def __radd__(self, other: HTMLInput) -> HTML:
        return HTML(self._ensure_str(other) + self.value)

    def join(self, iterable: Iterable[HTMLInput]) -> HTML:
        """add to the HTML object but escape if str"""
        return HTML(self.value.join(map(self._ensure_str, iterable)))

    def __eq__(self, other: Any) -> bool:
        return self.value == self._ensure_str(other)

    def __ne__(self, other: Any) -> bool:
        return self.value != self._ensure_str(other)

    def __len__(self) -> int:
        return len(self.value)

    def __getitem__(self, index: int) -> HTML:
        return HTML(self.value[index])

    def __contains__(self, item: HTMLInput) -> bool:
        return self._ensure_str(item) in self.value

    def count(
        self, x: HTMLInput, __start: Optional[int] = None, __end: Optional[int] = None
    ) -> int:
        return self.value.count(self._ensure_str(x), __start, __end)

    def index(
        self, sub: HTMLInput, __start: Optional[int] = None, __end: Optional[int] = None
    ) -> int:
        return self.value.index(self._ensure_str(sub), __start, __end)

    def lstrip(self, chars: Optional[HTMLInput] = None) -> HTML:
        return HTML(self.value.lstrip(self._ensure_str(chars) if chars is not None else None))

    def rstrip(self, chars: Optional[HTMLInput] = None) -> HTML:
        return HTML(self.value.rstrip(self._ensure_str(chars) if chars is not None else None))

    def strip(self, chars: Optional[HTMLInput] = None) -> HTML:
        return HTML(self.value.strip(self._ensure_str(chars) if chars is not None else None))

    def lower(self) -> HTML:
        return HTML(self.value.lower())

    def upper(self) -> HTML:
        return HTML(self.value.upper())

    def startswith(
        self, prefix: HTMLInput, start: Optional[int] = None, end: Optional[int] = None
    ) -> bool:
        return self.value.startswith(self._ensure_str(prefix), start, end)

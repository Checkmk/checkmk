#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: A005

from __future__ import annotations

import html
from collections.abc import Iterable
from typing import Any


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

    def __init__(self, value: HTML | str, escape: bool) -> None:
        if isinstance(value, HTML):
            self._value = str(value)
        elif isinstance(value, str):
            if escape:
                self._value = self._ensure_str(value)
            else:
                self._value = value
        else:
            raise TypeError("value must be a str or HTML object")

    @classmethod
    def empty(cls) -> HTML:
        # let's skip escaping if we know it's safe, saving some computations...
        return cls("", escape=False)

    @classmethod
    def without_escaping(cls, value: str | HTML) -> HTML:
        """If we know it's safe and we want html tags

        >>> str(HTML.without_escaping("foo<b>bar</b>"))
        'foo<b>bar</b>'
        """
        return cls(value, escape=False)

    @classmethod
    def with_escaping(cls, value: str | HTML) -> HTML:
        """For (potentially) untrusted data

        >>> str(HTML.with_escaping("foo<b>bar</b>"))
        'foo&lt;b&gt;bar&lt;/b&gt;'
        """
        return cls(value, escape=True)

    @staticmethod
    def _ensure_str(value: HTML | str) -> str:
        """return escaped string or HTML as str

        >>> HTML._ensure_str("foo<b>bar</b>")
        'foo&lt;b&gt;bar&lt;/b&gt;'
        >>> HTML._ensure_str(HTML.without_escaping("foo<b>bar</b>"))
        'foo<b>bar</b>'
        """
        if not isinstance(value, str | HTML):
            raise TypeError("value must be a str or HTML object")

        return str(value) if isinstance(value, HTML) else html.escape(value)

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return 'HTML("%s")' % self._value

    def __hash__(self) -> int:
        """Return the hash of the value

        Not sure if we want that...
        >>> hash("<h1>foo</h1>") == hash(HTML.without_escaping("<h1>foo</h1>"))
        True
        """
        return hash(self._value)

    def to_json(self) -> str:
        return self._value

    def __add__(self, other: HTML | str) -> HTML:
        return HTML(self._value + self._ensure_str(other), escape=False)

    def __iadd__(self, other: HTML | str) -> HTML:
        return self.__add__(other)

    def __radd__(self, other: HTML | str) -> HTML:
        return HTML(self._ensure_str(other) + self._value, escape=False)

    def join(self, iterable: Iterable[HTML | str]) -> HTML:
        """add to the HTML object but escape if str

        >>> str(HTML.empty().join(("<b>foo</b>", HTML.without_escaping("<b>bar</b>"))))
        '&lt;b&gt;foo&lt;/b&gt;<b>bar</b>'
        """
        return HTML(self._value.join(map(self._ensure_str, iterable)), escape=False)

    def __eq__(self, other: Any) -> bool:
        return self._value == self._ensure_str(other)

    def __ne__(self, other: Any) -> bool:
        return self._value != self._ensure_str(other)

    def __len__(self) -> int:
        return len(self._value)

    def __getitem__(self, index: int | slice) -> HTML:
        return HTML(self._value[index], escape=False)

    def __contains__(self, item: HTML | str) -> bool:
        return self._ensure_str(item) in self._value

    def count(self, x: HTML | str, __start: int | None = None, __end: int | None = None) -> int:
        return self._value.count(self._ensure_str(x), __start, __end)

    def index(self, sub: HTML | str, __start: int | None = None, __end: int | None = None) -> int:
        return self._value.index(self._ensure_str(sub), __start, __end)

    def lstrip(self, chars: HTML | str | None = None) -> HTML:
        return HTML(
            self._value.lstrip(self._ensure_str(chars) if chars is not None else None), escape=False
        )

    def rstrip(self, chars: HTML | str | None = None) -> HTML:
        return HTML(
            self._value.rstrip(self._ensure_str(chars) if chars is not None else None), escape=False
        )

    def strip(self, chars: HTML | str | None = None) -> HTML:
        return HTML(
            self._value.strip(self._ensure_str(chars) if chars is not None else None), escape=False
        )

    def lower(self) -> HTML:
        return HTML(self._value.lower(), escape=False)

    def upper(self) -> HTML:
        return HTML(self._value.upper(), escape=False)

    def startswith(
        self, prefix: HTML | str, start: int | None = None, end: int | None = None
    ) -> bool:
        return self._value.startswith(self._ensure_str(prefix), start, end)

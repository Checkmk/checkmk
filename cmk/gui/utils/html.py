#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union, Any, Iterable

HTMLInput = Union["HTML", int, float, None, str]


class HTML:
    """This is a simple class which wraps a unicode string provided by
    the caller to make escaping.escape_attribute() know that this string should
    not be escaped.

    This way we can implement encodings while still allowing HTML code.
    This is useful when one needs to print out HTML tables in messages
    or help texts.

    The HTML class is implemented as an immutable type.
    Every instance of the class is a unicode string.
    Only utf-8 compatible encodings are supported."""
    def __init__(self, value: HTMLInput = u'') -> None:
        super(HTML, self).__init__()
        self.value = self._ensure_str(value)

    def _ensure_str(self, value: HTMLInput) -> str:
        # value can of of any type: HTML, int, float, None, str, ...
        # TODO cleanup call sites
        return value if isinstance(value, str) else str(value)

    def __html__(self) -> str:
        return "%s" % self

    # TODO: This is broken! Cleanup once we are using Python 3.
    # NOTE: Return type "unicode" of "__str__" incompatible with return type "str" in supertype "object"
    def __str__(self) -> str:  # type: ignore[override]
        # Against the sense of the __str__() method, we need to return the value
        # as unicode here. Why? There are many cases where something like
        # "%s" % HTML(...) is done in the GUI code. This calls the __str__ function
        # because the origin is a str() object. The call will then return a UTF-8
        # encoded str() object. This brings a lot of compatbility issues to the code
        # which can not be solved easily.
        # To deal with this situation we need the implicit conversion from str to
        # unicode that happens when we return a unicode value here. In all relevant
        # cases this does exactly what we need. It would only fail if the origin
        # string contained characters that can not be decoded with the ascii codec
        # which is not relevant for us here.
        #
        # This is problematic:
        #   html.write("%s" % HTML("ä"))
        #
        # Bottom line: We should really cleanup internal unicode/str handling.
        return self.value

    def __repr__(self) -> str:
        return "HTML(\"%s\")" % self.value

    def to_json(self) -> str:
        return self.value

    def __add__(self, other: HTMLInput) -> 'HTML':
        return HTML(self.value + self._ensure_str(other))

    def __iadd__(self, other: HTMLInput) -> 'HTML':
        return self.__add__(other)

    def __radd__(self, other: HTMLInput) -> 'HTML':
        return HTML(self._ensure_str(other) + self.value)

    def join(self, iterable: Iterable[HTMLInput]) -> 'HTML':
        return HTML(self.value.join(map(self._ensure_str, iterable)))

    def __eq__(self, other: Any) -> bool:
        return self.value == self._ensure_str(other)

    def __ne__(self, other: Any) -> bool:
        return self.value != self._ensure_str(other)

    def __len__(self) -> int:
        return len(self.value)

    def __getitem__(self, index: int) -> 'HTML':
        return HTML(self.value[index])

    def __contains__(self, item: HTMLInput) -> bool:
        return self._ensure_str(item) in self.value

    def count(self, sub, *args):
        return self.value.count(self._ensure_str(sub), *args)

    def index(self, sub, *args):
        return self.value.index(self._ensure_str(sub), *args)

    def lstrip(self, *args):
        args = tuple(map(self._ensure_str, args[:1])) + args[1:]
        return HTML(self.value.lstrip(*args))

    def rstrip(self, *args):
        args = tuple(map(self._ensure_str, args[:1])) + args[1:]
        return HTML(self.value.rstrip(*args))

    def strip(self, *args):
        args = tuple(map(self._ensure_str, args[:1])) + args[1:]
        return HTML(self.value.strip(*args))

    def lower(self) -> 'HTML':
        return HTML(self.value.lower())

    def upper(self) -> 'HTML':
        return HTML(self.value.upper())

    def startswith(self, prefix, *args):
        return self.value.startswith(self._ensure_str(prefix), *args)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Union, Any, Iterable, Text  # pylint: disable=unused-import
import six

from cmk.utils.encoding import ensure_unicode

HTMLInput = Union["HTML", int, float, None, str, Text]


class HTML(object):  # pylint: disable=useless-object-inheritance
    """This is a simple class which wraps a unicode string provided by
    the caller to make escaping.escape_attribute() know that this string should
    not be escaped.

    This way we can implement encodings while still allowing HTML code.
    This is useful when one needs to print out HTML tables in messages
    or help texts.

    The HTML class is implemented as an immutable type.
    Every instance of the class is a unicode string.
    Only utf-8 compatible encodings are supported."""
    def __init__(self, value=u''):
        # type: (HTMLInput) -> None
        super(HTML, self).__init__()
        self.value = self._ensure_unicode(value)

    def _ensure_unicode(self, value):
        # type: (HTMLInput) -> Text
        # value can of of any type: HTML, int, float, None, str, ...
        # TODO cleanup call sites
        if not isinstance(value, six.string_types):
            value = six.text_type(value)
        return ensure_unicode(value)

    def __html__(self):
        # type: () -> Text
        return "%s" % self

    # TODO: This is broken! Cleanup once we are using Python 3.
    # NOTE: Return type "unicode" of "__str__" incompatible with return type "str" in supertype "object"
    def __str__(self):  # type: ignore[override]
        # type: () -> Text
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

    def __repr__(self):
        # type: () -> str
        repr_val = "HTML(\"%s\")" % self.value
        return six.ensure_str(repr_val)

    def to_json(self):
        # type: () -> Text
        return self.value

    def __add__(self, other):
        # type: (HTMLInput) -> HTML
        return HTML(self.value + self._ensure_unicode(other))

    def __iadd__(self, other):
        # type: (HTMLInput) -> HTML
        return self.__add__(other)

    def __radd__(self, other):
        # type: (HTMLInput) -> HTML
        return HTML(self._ensure_unicode(other) + self.value)

    def join(self, iterable):
        # type: (Iterable[HTMLInput]) -> HTML
        return HTML(self.value.join(map(self._ensure_unicode, iterable)))

    def __eq__(self, other):
        # type: (Any) -> bool
        return self.value == self._ensure_unicode(other)

    def __ne__(self, other):
        # type: (Any) -> bool
        return self.value != self._ensure_unicode(other)

    def __len__(self):
        # type: () -> int
        return len(self.value)

    def __getitem__(self, index):
        # type: (int) -> HTML
        return HTML(self.value[index])

    def __contains__(self, item):
        # type: (HTMLInput) -> bool
        return self._ensure_unicode(item) in self.value

    def count(self, sub, *args):
        return self.value.count(self._ensure_unicode(sub), *args)

    def index(self, sub, *args):
        return self.value.index(self._ensure_unicode(sub), *args)

    def lstrip(self, *args):
        args = tuple(map(self._ensure_unicode, args[:1])) + args[1:]
        return HTML(self.value.lstrip(*args))

    def rstrip(self, *args):
        args = tuple(map(self._ensure_unicode, args[:1])) + args[1:]
        return HTML(self.value.rstrip(*args))

    def strip(self, *args):
        args = tuple(map(self._ensure_unicode, args[:1])) + args[1:]
        return HTML(self.value.strip(*args))

    def lower(self):
        # type: () -> HTML
        return HTML(self.value.lower())

    def upper(self):
        # type: () -> HTML
        return HTML(self.value.upper())

    def startswith(self, prefix, *args):
        return self.value.startswith(self._ensure_unicode(prefix), *args)

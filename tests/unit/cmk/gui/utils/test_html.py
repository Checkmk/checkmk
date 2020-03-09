#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import pytest  # type: ignore[import]
import six

from cmk.gui.utils.html import HTML


# Monkey patch in order to make the HTML class below json-serializable without changing the default json calls.
def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)


_default.default = json.JSONEncoder().default  # Save unmodified default.
json.JSONEncoder.default = _default  # replacement


@pytest.mark.parametrize("value", [
    None,
    "",
    123,
    123.4,
    "one",
    "Oneüლ,ᔑ•ﺪ͟͠•ᔐ.ლ",
])
def test_class_HTML_value(value):
    assert isinstance(HTML(value).value, six.text_type)
    assert HTML(HTML(value)) == HTML(value)


# TODO: Split this up into multiple tests
def test_class_HTML():
    a = "Oneüლ,ᔑ•ﺪ͟͠•ᔐ.ლ"
    b = "two"
    c = "Three"
    d = six.text_type('u')

    A = HTML(a)
    B = HTML(b)
    C = HTML(c)
    D = HTML(d)

    assert HTML() == HTML('')
    assert HTML(HTML()) == HTML()
    # One day we will fix this!
    assert six.text_type(A) == a.decode("utf-8"), six.text_type(A)
    assert "%s" % A == a.decode("utf-8"), "%s" % A
    assert json.loads(json.dumps(A)) == A
    assert repr(A) == 'HTML(\"%s\")' % A.value.encode("utf-8")
    assert len(B) == len(b)
    assert six.text_type(B) == six.text_type(b)

    assert "1" + B + "2" + C == "1" + b + "2" + c

    assert (A + B) == (a + b)
    assert HTML().join([A, B]) == A + B
    assert HTML().join([a, b]) == a + b
    assert HTML("jo").join([A, B]) == A + "jo" + B
    assert HTML("jo").join([a, b]) == a + "jo" + b
    assert ''.join(map(six.text_type, [A, B])) == A + B

    assert isinstance(A, HTML), type(A)
    #    assert isinstance(A, six.text_type), type(A)
    assert not isinstance(A, str), type(A)
    assert isinstance(u"%s" % A, six.text_type), u"%s" % A
    # One day we will fix this!
    assert isinstance(u"%s" % A, six.text_type), u"%s" % A
    assert isinstance(A + B, HTML), type(A + B)
    assert isinstance(HTML('').join([A, B]), HTML)
    assert isinstance(HTML().join([A, B]), HTML)
    assert isinstance(HTML('').join([a, b]), HTML)
    assert isinstance("TEST" + HTML(), HTML)
    assert isinstance(HTML() + "TEST", HTML)
    assert isinstance("TEST" + HTML() + "TEST", HTML)

    #assert "<div>" + HTML("content") + "</div>" == "&lt;div&gt;content&lt;/div&gt;"
    #assert HTML().join(["<div>", HTML("</br>"), HTML("<input/>"), "</div>"]) ==\
    #        "&lt;div&gt;</br><input/>&lt;/div&gt;"

    A += B
    a += b
    assert isinstance(A, HTML), A
    assert A == a, A

    assert a in A, A
    assert A.count(a) == 1
    assert A.index(a) == 0

    assert isinstance(A[1:3], HTML)
    assert A[1:3] == a[1:3], A[1:3]

    assert A == a

    assert ("%s" % A) == a.decode("utf-8")

    assert B + C != C + B

    assert HTML(A) == A, "%s %s" % (HTML(A), A)
    assert HTML(a) == A, "%s %s" % (HTML(a), A)

    # Not supported any more!
    # assert  (A < B) == (a < b), "%s %s" % (A < B, a < b)
    # assert (A > B) == (a > b)

    assert A != B

    assert isinstance(HTML(HTML(A)), HTML)
    assert isinstance("%s" % HTML(HTML(A)), six.text_type)

    assert isinstance(A, HTML)
    A += (" JO PICASSO! ")
    assert isinstance(A, HTML)

    assert isinstance(A + "TEST", HTML)

    assert isinstance("TEST%s" % A, six.text_type)

    assert "test" + C == "test" + c

    assert D == d
    assert "%s" % D == "%s" % d
    assert isinstance(u"%s" % D, six.text_type)
    assert isinstance("%s" % D, six.text_type)

    E = A + B
    e = "%s" % E
    assert E.lstrip(E[0]) == e.lstrip(e[0])
    assert E == e
    assert E.rstrip(E[0]) == e.rstrip(e[0])
    assert E == e
    assert E.strip(E[0]) == e.strip(e[0])
    assert E == e

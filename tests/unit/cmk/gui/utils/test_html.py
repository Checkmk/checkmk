#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import json.encoder

import pytest  # type: ignore[import]
from six import ensure_str

from cmk.gui.utils.html import HTML


# TODO: Cleanup this dirty hack. Import of htmllib must not magically modify the behaviour of
# the json module. Better would be to create a JSON wrapper in cmk.utils.json which uses a
# custom subclass of the JSONEncoder.
#
# Monkey patch in order to make the HTML class below json-serializable without changing the default json calls.
def _default(self: json.JSONEncoder, obj: object) -> str:
    # ignore attr-defined: See hack below
    return getattr(obj.__class__, "to_json", _default.default)(obj)  # type: ignore[attr-defined]


# TODO: suppress mypy warnings for this monkey patch right now. See also:
# https://github.com/python/mypy/issues/2087
# Save unmodified default:
_default.default = json.JSONEncoder().default  # type: ignore[attr-defined]
# replacement:
json.JSONEncoder.default = _default  # type: ignore[assignment]


@pytest.mark.parametrize("value", [
    None,
    "",
    123,
    123.4,
    "one",
    "Oneüლ,ᔑ•ﺪ͟͠•ᔐ.ლ",
])
def test_class_HTML_value(value):
    assert isinstance(HTML(value).value, str)
    assert HTML(HTML(value)) == HTML(value)


# TODO: Split this up into multiple tests
def test_class_HTML():
    a = "Oneüლ,ᔑ•ﺪ͟͠•ᔐ.ლ"
    b = "two"
    c = "Three"
    d = str('u')

    A = HTML(a)
    B = HTML(b)
    C = HTML(c)
    D = HTML(d)

    assert HTML() == HTML('')
    assert HTML(HTML()) == HTML()
    # One day we will fix this!
    assert str(A) == ensure_str(a), str(A)
    assert "%s" % A == ensure_str(a), "%s" % A
    assert json.loads(json.dumps(A)) == A
    assert repr(A) == 'HTML(\"%s\")' % ensure_str(A.value)
    assert len(B) == len(b)
    assert str(B) == str(b)

    # TODO: Investigate
    assert "1" + B + "2" + C == "1" + b + "2" + c  # type: ignore[type-var]

    assert (A + B) == (a + b)
    assert HTML().join([A, B]) == A + B
    assert HTML().join([a, b]) == a + b
    assert HTML("jo").join([A, B]) == A + "jo" + B
    assert HTML("jo").join([a, b]) == a + "jo" + b
    assert ''.join(map(str, [A, B])) == A + B

    assert isinstance(A, HTML), type(A)
    #    assert isinstance(A, str), type(A)
    assert not isinstance(A, str), type(A)
    assert isinstance(u"%s" % A, str), u"%s" % A
    # One day we will fix this!
    assert isinstance(u"%s" % A, str), u"%s" % A
    assert isinstance(A + B, HTML), type(A + B)
    assert isinstance(HTML('').join([A, B]), HTML)
    assert isinstance(HTML().join([A, B]), HTML)
    assert isinstance(HTML('').join([a, b]), HTML)
    # TODO: Investigate
    assert isinstance("TEST" + HTML(), HTML)  # type: ignore[type-var]
    assert isinstance(HTML() + "TEST", HTML)
    # TODO: Investigate
    assert isinstance("TEST" + HTML() + "TEST", HTML)  # type: ignore[type-var]

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

    # TODO: Investigate type annotation
    assert isinstance(A[1:3], HTML)  # type: ignore[index]
    assert A[1:3] == a[1:3], A[1:3]  # type: ignore[index]

    assert A == a

    assert ("%s" % A) == ensure_str(a)

    assert B + C != C + B

    assert HTML(A) == A, "%s %s" % (HTML(A), A)
    assert HTML(a) == A, "%s %s" % (HTML(a), A)

    # Not supported any more!
    # assert  (A < B) == (a < b), "%s %s" % (A < B, a < b)
    # assert (A > B) == (a > b)

    assert A != B

    assert isinstance(HTML(HTML(A)), HTML)
    assert isinstance("%s" % HTML(HTML(A)), str)

    assert isinstance(A, HTML)
    A += (" JO PICASSO! ")
    assert isinstance(A, HTML)

    assert isinstance(A + "TEST", HTML)

    assert isinstance("TEST%s" % A, str)

    assert "test" + C == "test" + c  # type: ignore[type-var]

    assert D == d
    assert "%s" % D == "%s" % d
    assert isinstance(u"%s" % D, str)
    assert isinstance("%s" % D, str)

    E = A + B
    e = "%s" % E
    assert E.lstrip(E[0]) == e.lstrip(e[0])
    assert E == e
    assert E.rstrip(E[0]) == e.rstrip(e[0])
    assert E == e
    assert E.strip(E[0]) == e.strip(e[0])
    assert E == e

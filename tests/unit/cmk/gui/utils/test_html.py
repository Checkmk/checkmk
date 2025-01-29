#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.utils.html import HTML


def test_HTML_value() -> None:
    """test that strings and HTML inputs work and others not"""
    with pytest.raises(TypeError):
        HTML(42, escape=False)  # type: ignore[arg-type]

    assert str(HTML("42", escape=False)) == "42"
    assert str(HTML(HTML("42", escape=False), escape=False)) == "42"
    assert isinstance("%s" % HTML("42", escape=False), str)


@pytest.mark.parametrize(
    "value",
    ("a",),
)
def test_repr(value: str) -> None:
    assert repr(HTML.without_escaping(value)) == 'HTML("%s")' % value


def test_adding() -> None:
    # __radd__
    a = "a" + HTML.without_escaping("b")
    assert isinstance(a, HTML)
    assert str(a) == "ab"

    # __add__
    b = HTML.without_escaping("a") + "b"
    assert isinstance(b, HTML)
    assert str(b) == "ab"

    # escaping and adding
    c = HTML.without_escaping("a") + "<script>alert('XSS')</script>"
    assert isinstance(c, HTML)
    assert str(c) == "a&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;"

    d = "a" + HTML.without_escaping("b") + "c"
    assert isinstance(d, HTML)
    assert str(d) == "abc"

    e = HTML.without_escaping("a") + "b" + HTML.without_escaping("c")
    assert isinstance(e, HTML)
    assert str(e) == "abc"

    f = HTML.without_escaping("a")
    f += "b"
    assert isinstance(f, HTML)
    assert str(f) == "ab"


def test_eq() -> None:
    # Is that really a good idea?
    a = "Oneüლ,ᔑ•ﺪ͟͠•ᔐ.ლ"
    b = "two"

    A = HTML.without_escaping(a)
    B = HTML.without_escaping(b)

    assert "1" + B + "2" + A == "1" + b + "2" + a
    assert (A + B) == (a + b)

    assert B + A != A + B


def test_join() -> None:
    assert str(HTML.empty().join(["a", HTML.without_escaping("b")])) == "ab"

    a = HTML.without_escaping("c").join(("a", HTML.without_escaping("b")))
    assert isinstance(a, HTML)
    assert str(a) == "acb"


def test_other_protocols() -> None:
    a = HTML.without_escaping("abcdef")
    assert a.count("b") == 1
    assert a.index("b") == 1
    assert "c" in a

    assert isinstance(a[1:3], HTML)
    assert str(a[1:3]) == "bc"

    assert a.lstrip("ab") == "cdef"
    assert a.rstrip("ef") == "abcd"
    assert a.strip("a") == "bcdef"
    assert a.strip("f") == "abcde"

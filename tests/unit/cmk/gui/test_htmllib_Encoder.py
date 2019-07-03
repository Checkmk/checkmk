#!/usr/bin/env python
# encoding: utf-8

import pytest

import cmk.gui.htmllib as htmllib
from cmk.gui.globals import html


def test_htmllib_integration(register_builtin_html):
    assert isinstance(html.encoder, htmllib.Encoder)

    assert html.urlencode_vars([]) == ""
    assert html.urlencode("") == ""


@pytest.mark.parametrize("inp,out", [
    ([("c", "d"), ("a", "b")], "a=b&c=d"),
    ([("a", 1), ("c", "d")], "a=1&c=d"),
    ([("a", u"ä"), ("c", "d")], "a=%C3%A4&c=d"),
    ([("a", u"abcä")], "a=abc%C3%A4"),
    ([("a", "_-.")], "a=_-."),
    ([("a", "#")], "a=%23"),
    ([("a", "+")], "a=%2B"),
    ([("a", " ")], "a=+"),
    ([("a", "/")], "a=%2F"),
    ([("a", None)], "a="),
])
def test_urlencode_vars(inp, out):
    result = htmllib.Encoder().urlencode_vars(inp)
    assert isinstance(result, str)
    assert result == out


@pytest.mark.parametrize(
    "inp,out",
    [
        (u"välue", "v%C3%A4lue"),
        # TODO: None / int handling inconsistent with urlencode_vars()
        (None, ""),
        ("ä", "%C3%A4"),
        ("_-.", "_-."),
        ("#", "%23"),
        ("+", "%2B"),
        (" ", "+"),
        ("/", "%2F"),
    ])
def test_urlencode(inp, out):
    result = htmllib.Encoder().urlencode(inp)
    assert isinstance(result, str)
    assert result == out

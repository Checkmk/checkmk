#!/usr/bin/env python
# encoding: utf-8

import pytest

import htmllib

def test_htmllib_integration(register_builtin_html):
    assert type(html.encoder) == htmllib.Encoder

    assert html.urlencode_vars([]) == ""
    assert html.urlencode("") == ""
    assert html.urlencode_plus("") == ""


@pytest.mark.parametrize("inp,out", [
    ([("c", "d"), ("a", "b")], "a=b&c=d"),
    ([("a", 1), ("c", "d")], "a=1&c=d"),
    ([("a", u"ä"), ("c", "d")], "a=%C3%A4&c=d"),
    ([("a", u"abcä")], "a=abc%C3%A4"),
    ([("a", "_-.")], "a=_-."),
    ([("a", "#")], "a=%23"),
    ([("a", "+")], "a=%2B"),
    ([("a", " ")], "a=%20"),
    ([("a", "/")], "a=/"),
])
def test_urlencode_vars(inp, out):
    result = htmllib.Encoder().urlencode_vars(inp)
    assert type(result) == str
    assert result == out


@pytest.mark.parametrize("inp,out", [
    (u"välue", "v%c3%a4lue"),
    # TODO: None / int handling inconsistent with urlencode_vars()
    (None, ""),
    ("ä", "%c3%a4"),
    ("_-.", "_-."),
    ("#", "%23"),
    ("+", "%2b"),
    # TODO: Why + instead of %20?
    (" ", "+"),
    ("/", "/"),
])
def test_urlencode(inp, out):
    result = htmllib.Encoder().urlencode(inp)
    assert type(result) == str
    assert result == out


@pytest.mark.parametrize("inp,out", [
    (u"välue", "v%C3%A4lue"),
    # TODO: None / int handling inconsistent with urlencode_vars()
    (None, ""),
    ("ä", "%C3%A4"),
    ("_-.", "_-."),
    ("#", "%23"),
    ("+", "%2B"),
    # TODO: Why + instead of %20?
    (" ", "+"),
    ("/", "%2F"),
])
def test_urlencode_plus(inp, out):
    result = htmllib.Encoder().urlencode_plus(inp)
    assert type(result) == str
    assert result == out

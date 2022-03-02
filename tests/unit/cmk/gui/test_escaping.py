#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString


def test_escape_html() -> None:
    assert isinstance(escaping.escape_html(""), HTML)
    assert str(escaping.escape_html("")) == ""
    assert str(escaping.escape_html("<script>")) == "&lt;script&gt;"
    assert str(escaping.escape_html("<b>")) == "&lt;b&gt;"


def test_escape_html_permissive() -> None:
    assert isinstance(escaping.escape_html_permissive(""), HTML)
    assert str(escaping.escape_html_permissive("")) == ""
    assert str(escaping.escape_html_permissive("<script>")) == "&lt;script&gt;"
    assert str(escaping.escape_html_permissive("<b>")) == "<b>"


def test_htmllib_integration():
    assert escaping.escape_attribute("") == ""
    assert escaping.escape_text("") == ""


@pytest.mark.parametrize(
    "inp,out",
    [
        ('">alert(1)', "&quot;&gt;alert(1)"),
        (None, ""),
        (1, "1"),
        (HTML('">alert(1)'), '">alert(1)'),
        (1.1, "1.1"),
        ("<", "&lt;"),
        ("'", "&#x27;"),
        (LazyString(str, "'"), "&#x27;"),
    ],
)
def test_escape_attribute(inp, out):
    assert escaping.escape_attribute(inp) == out


@pytest.mark.parametrize(
    "inp,out",
    [
        ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
        ("<h1>abc</h1>", None),
        ("<h2>abc</h2>", None),
        ("<b>abc</b>", None),
        ("<tt>abc</tt>", None),
        ("<i>abc</i>", None),
        ("<u>abc</u>", None),
        ("<br>", None),
        ("<nobr></nobr>", None),
        ("<pre></pre>", None),
        ("<sup></sup>", None),
        ("<p></p>", None),
        ("<li></li>", None),
        ("<ul></ul>", None),
        ("<ol></ol>", None),
        ('<a href="xyz">abc</a>', None),
        ('<a href="xyz" target="123">abc</a>', None),
        # Links with target 1st and href 2nd will not be unescaped
        (
            '<a target="123" href="xyz">abc</a>',
            "&lt;a target=&quot;123&quot; href=&quot;xyz&quot;&gt;abc</a>",
        ),
        ('blah<a href="link0">aaa</a>blah<a href="link1" target="ttt">bbb</a>', None),
        (
            '"I am not a link" target="still not a link"',
            "&quot;I am not a link&quot; target=&quot;still not a link&quot;",
        ),
        # The next test is perverse: it contains the string `target=` inside of an
        # <a> tag (which must be unescaped) as well as outside (which must not).
        (
            '<a href="aaa">bbb</a>"not a link" target="really"<a href="ccc" target="ttt">ddd</a>',
            '<a href="aaa">bbb</a>&quot;not a link&quot; target=&quot;really&quot;<a href="ccc" target="ttt">ddd</a>',
        ),
        (
            '<a href="xyz">abc</a><script>alert(1)</script><a href="xyz">abc</a>',
            '<a href="xyz">abc</a>&lt;script&gt;alert(1)&lt;/script&gt;<a href="xyz">abc</a>',
        ),
        ("&nbsp;", None),
        # Only http/https/mailto are allowed as schemes
        ('<a href="http://checkmk.com/">abc</a>', None),
        ('<a href="https://checkmk.com/">abc</a>', None),
        ('<a href="HTTP://CHECKMK.COM/">abc</a>', None),
        (
            'Please download it manually and send it to <a href="mailto:feedback@checkmk.com?subject=Checkmk+Crash+Report+-+2021.11.12">feedback@checkmk.com</a>',
            'Please download it manually and send it to <a href="mailto:feedback@checkmk.com?subject=Checkmk+Crash+Report+-+2021.11.12">feedback@checkmk.com</a>',
        ),
        (
            '<a href="ftp://checkmk.com/">abc</a>',
            "&lt;a href=&quot;ftp://checkmk.com/&quot;&gt;abc</a>",
        ),
        (
            '<a href="javascript:alert(1)">abc</a>',
            "&lt;a href=&quot;javascript:alert(1)&quot;&gt;abc</a>",
        ),
        (
            LazyString(str, '<a href="javascript:alert(1)">abc</a>'),
            "&lt;a href=&quot;javascript:alert(1)&quot;&gt;abc</a>",
        ),
    ],
)
def test_escape_text(inp, out):
    if out is None:
        out = inp
    assert escaping.escape_text(inp) == out


@pytest.mark.parametrize(
    "inp,out",
    [
        ("foo bar", "foo bar"),
        ("some <a>link</a> in text", "some link in text"),
        (HTML("some <a>link</a> in html text"), "some link in html text"),
        (LazyString(str, "some <a>link</a> in lazy text"), "some link in lazy text"),
    ],
)
def test_strip_tags(inp, out):
    assert escaping.strip_tags(inp) == out

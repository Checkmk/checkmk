#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.gui.htmllib as htmllib
from cmk.gui import escaping


def test_htmllib_integration(register_builtin_html):
    assert escaping.escape_attribute("") == ""
    assert escaping.escape_text("") == ""


@pytest.mark.parametrize("inp,out", [
    ("\">alert(1)", "&quot;&gt;alert(1)"),
    (None, ""),
    (1, "1"),
    (htmllib.HTML("\">alert(1)"), "\">alert(1)"),
    (1.1, "1.1"),
    ("<", "&lt;"),
    ("'", "&#x27;"),
])
def test_escape_attribute(inp, out):
    assert escaping.escape_attribute(inp) == out


@pytest.mark.parametrize("inp,out", [
    ("&quot;&gt;alert(1)", "\">alert(1)"),
    ("&lt;", "<"),
])
def test_unescape_attribute(inp, out):
    assert escaping.unescape_attributes(inp) == out


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
        ("<a href=\"xyz\">abc</a>", None),
        ("<a href=\"xyz\" target=\"123\">abc</a>", None),
        # Links with target 1st and href 2nd will not be unescaped
        ("<a target=\"123\" href=\"xyz\">abc</a>",
         "&lt;a target=&quot;123&quot; href=&quot;xyz&quot;&gt;abc</a>"),
        ("blah<a href=\"link0\">aaa</a>blah<a href=\"link1\" target=\"ttt\">bbb</a>", None),
        ("\"I am not a link\" target=\"still not a link\"",
         "&quot;I am not a link&quot; target=&quot;still not a link&quot;"),
        # The next test is perverse: it contains the string `target=` inside of an
        # <a> tag (which must be unescaped) as well as outside (which must not).
        ("<a href=\"aaa\">bbb</a>\"not a link\" target=\"really\"<a href=\"ccc\" target=\"ttt\">ddd</a>",
         "<a href=\"aaa\">bbb</a>&quot;not a link&quot; target=&quot;really&quot;<a href=\"ccc\" target=\"ttt\">ddd</a>"
        ),
        (
            "<a href=\"xyz\">abc</a><script>alert(1)</script><a href=\"xyz\">abc</a>",
            "<a href=\"xyz\">abc</a>&lt;script&gt;alert(1)&lt;/script&gt;<a href=\"xyz\">abc</a>",
        ),
        ("&nbsp;", None),
        # Only http/https are allowed as schemes
        ("<a href=\"http://checkmk.com/\">abc</a>", None),
        ("<a href=\"https://checkmk.com/\">abc</a>", None),
        ("<a href=\"HTTP://CHECKMK.COM/\">abc</a>", None),
        ("<a href=\"ftp://checkmk.com/\">abc</a>",
         "&lt;a href=&quot;ftp://checkmk.com/&quot;&gt;abc</a>"),
        ("<a href=\"javascript:alert(1)\">abc</a>",
         "&lt;a href=&quot;javascript:alert(1)&quot;&gt;abc</a>"),
    ])
def test_escape_text(inp, out):
    if out is None:
        out = inp
    assert escaping.escape_text(inp) == out

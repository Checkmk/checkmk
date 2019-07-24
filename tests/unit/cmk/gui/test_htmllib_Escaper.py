#!/usr/bin/env python

import pytest  # type: ignore

import cmk.gui.htmllib as htmllib
from cmk.gui.globals import html


def test_htmllib_integration(register_builtin_html):
    assert isinstance(html.escaper, htmllib.Escaper)

    assert html.attrencode("") == ""
    assert html.permissive_attrencode("") == ""


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
    assert htmllib.Escaper().escape_attribute(inp) == out


@pytest.mark.parametrize("inp,out", [
    ("&quot;&gt;alert(1)", "\">alert(1)"),
    ("&lt;", "<"),
])
def test_unescape_attribute(inp, out):
    assert htmllib.Escaper().unescape_attributes(inp) == out


@pytest.mark.parametrize("inp,out", [
    ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
    ("<h1>abc</h1>", "<h1>abc</h1>"),
    ("<h2>abc</h2>", "<h2>abc</h2>"),
    ("<b>abc</b>", "<b>abc</b>"),
    ("<tt>abc</tt>", "<tt>abc</tt>"),
    ("<i>abc</i>", "<i>abc</i>"),
    ("<u>abc</u>", "<u>abc</u>"),
    ("<br>", "<br>"),
    ("<nobr></nobr>", "<nobr></nobr>"),
    ("<pre></pre>", "<pre></pre>"),
    ("<sup></sup>", "<sup></sup>"),
    ("<p></p>", "<p></p>"),
    ("<li></li>", "<li></li>"),
    ("<ul></ul>", "<ul></ul>"),
    ("<ol></ol>", "<ol></ol>"),
    ("<a href=\"xyz\">abc</a>", "<a href=\"xyz\">abc</a>"),
    ("<a href=\"xyz\" target=\"123\">abc</a>", "<a href=\"xyz\" target=\"123\">abc</a>"),
    ("&nbsp;", "&nbsp;"),
])
def test_escape_text(inp, out):
    assert htmllib.Escaper().escape_text(inp) == out

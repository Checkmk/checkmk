#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.web.utils import escaping
from cmk.web.utils.html import HTML
from cmk.web.utils.speaklater import LazyString


def test_empty() -> None:
    assert escaping.escape_permissive("") == ""


def test_escape_to_html_permissive() -> None:
    assert isinstance(escaping.escape_to_html_permissive(""), HTML)
    assert str(escaping.escape_to_html_permissive("")) == ""
    assert str(escaping.escape_to_html_permissive("<script>")) == "&lt;script&gt;"
    assert str(escaping.escape_to_html_permissive("<b>")) == "<b>"


def test_htmllib_integration() -> None:
    assert escaping.escape_attribute("") == ""
    assert escaping.escape_text("") == ""


@pytest.mark.parametrize(
    "inp,out",
    [
        ('">alert(1)', "&quot;&gt;alert(1)"),
        (None, ""),
        (1, "1"),
        (HTML.without_escaping('">alert(1)'), '">alert(1)'),
        (1.1, "1.1"),
        ("<", "&lt;"),
        ("'", "&#x27;"),
        (LazyString(str, "'"), "&#x27;"),
    ],
)
def test_escape_attribute(inp: escaping.EscapableEntity, out: str) -> None:
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
        ('<a href="xyz">abc</a>', "&lt;a href=&quot;xyz&quot;&gt;abc&lt;/a&gt;"),
        (
            '<a href="xyz" target="123">abc</a>',
            "&lt;a href=&quot;xyz&quot; target=&quot;123&quot;&gt;abc&lt;/a&gt;",
        ),
        # Links with target 1st and href 2nd will not be unescaped
        (
            '<a target="123" href="xyz">abc</a>',
            "&lt;a target=&quot;123&quot; href=&quot;xyz&quot;&gt;abc&lt;/a&gt;",
        ),
        (
            '"I am not a link" target="still not a link"',
            "&quot;I am not a link&quot; target=&quot;still not a link&quot;",
        ),
        ("&nbsp;", None),
        (
            '<a href="ftp://checkmk.com/">abc</a>',
            "&lt;a href=&quot;ftp://checkmk.com/&quot;&gt;abc&lt;/a&gt;",
        ),
        (
            '<a href="javascript:alert(1)">abc</a>',
            "&lt;a href=&quot;javascript:alert(1)&quot;&gt;abc&lt;/a&gt;",
        ),
        (
            "<b/onclick=alert(1)>abc</b>",
            "&lt;b/onclick=alert(1)&gt;abc</b>",
        ),
    ],
)
def test_escape_text(inp: str, out: str | None) -> None:
    if out is None:
        assert escaping.escape_permissive(inp) == inp
    else:
        assert escaping.escape_permissive(inp) == out


@pytest.mark.parametrize(
    "inp,out",
    [
        ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
        ("<h1>abc</h1>", None),
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
            '<a/href="http://checkmk.com/">abc</a>',
            "&lt;a/href=&quot;http://checkmk.com/&quot;&gt;abc</a>",
        ),
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
    ],
)
def test_escape_text_with_links(inp: str, out: str | None) -> None:
    if out is None:
        assert escaping.escape_permissive(inp, escape_links=False) == inp
    else:
        assert escaping.escape_permissive(inp, escape_links=False) == out


@pytest.mark.parametrize(
    "inp,out",
    [
        ("<h1>abc</h1>", None),
        ('<a href="xyz">abc</a>', None),
        ('<a href="xyz" target="123">abc</a>', None),
        # Links with target 1st and href 2nd will not be unescaped
        (
            '<a target="123" href="xyz">abc</a>',
            "&lt;a target=&quot;123&quot; href=&quot;xyz&quot;&gt;abc</a>",
        ),
        (
            '<a href="xyz">abc</a><script>alert(1)</script><a href="xyz">abc</a>',
            '<a href="xyz">abc</a>&lt;script&gt;alert(1)&lt;/script&gt;<a href="xyz">abc</a>',
        ),
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
        # EscapableEntity types
        (None, ""),
        (
            LazyString(str, '<a href="javascript:alert(1)">abc</a>'),
            "&lt;a href=&quot;javascript:alert(1)&quot;&gt;abc</a>",
        ),
    ],
)
def test_escape_text_entity(inp: escaping.EscapableEntity, out: str | None) -> None:
    if out is None:
        assert escaping.escape_text(inp) == inp
    else:
        assert escaping.escape_text(inp) == out


@pytest.mark.parametrize(
    "tagname",
    ("h1", "h2", "b", "tt", "i", "u", "hr", "br", "nobr", "pre", "sup", "p", "li", "ul", "ol"),
)
def test_permissive_tags(tagname: str) -> None:
    """test for which tags are 'allowed' aka unescaped after escaping"""

    opening = f"<{tagname}>"
    assert escaping.escape_permissive(opening) == opening

    closing = f"</{tagname}>"
    assert escaping.escape_permissive(closing) == closing

    assert escaping.escape_permissive(opening + "foo" + closing) == opening + "foo" + closing


def test_a_unescaping() -> None:
    test_str = "<a>foo</a>"
    assert escaping.escape_permissive("<a>foo</a>", escape_links=False) == "&lt;a&gt;foo</a>"

    test_str = '<a href="bar">foo</a>'
    assert escaping.escape_permissive(test_str, escape_links=False) == test_str

    assert (
        escaping.escape_permissive('<a href="bar" target="">foo</a>', escape_links=False)
        == '<a href="bar">foo</a>'
    )

    # I guess this should be considered a bug
    assert (
        escaping.escape_permissive('<a href="bar" style="">foo</a>', escape_links=False)
        == "&lt;a href=&quot;bar&quot; style=&quot;&quot;&gt;foo</a>"
    )
    assert (
        escaping.escape_permissive('<a style=""href="bar">foo</a>', escape_links=False)
        == "&lt;a style=&quot;&quot;href=&quot;bar&quot;&gt;foo</a>"
    )


@pytest.mark.parametrize(
    "inp,out",
    [
        ("foo bar", "foo bar"),
        ("some <a>link</a> in text", "some link in text"),
        (HTML.without_escaping("some <a>link</a> in html text"), "some link in html text"),
        (LazyString(str, "some <a>link</a> in lazy text"), "some link in lazy text"),
    ],
)
def test_strip_tags(inp: escaping.EscapableEntity, out: str) -> None:
    assert escaping.strip_tags(inp) == out


@pytest.mark.parametrize(
    "inp,out",
    [
        # Icon button links with cmk-url-icon-link class should be replaced
        pytest.param(
            '<a href="https://example.com" class="cmk-url-icon-link">icon</a>',
            "https://example.com",
            id="icon_button_link_simple",
        ),
        pytest.param(
            'See <a href="https://example.com" class="cmk-url-icon-link" target="_blank">icon</a> for more',
            "See https://example.com for more",
            id="icon_button_link_with_surrounding_text",
        ),
        pytest.param(
            '<a href="https://example.com">regular link</a>',
            '<a href="https://example.com">regular link</a>',
            id="regular_link_preserved",
        ),
        pytest.param(
            '<a href="https://first.com" class="cmk-url-icon-link">icon1</a> <a href="https://second.com" class="cmk-url-icon-link">icon2</a>',
            "https://first.com https://second.com",
            id="multiple_icon_button_links",
        ),
        pytest.param(
            "No links here",
            "No links here",
            id="no_links",
        ),
        pytest.param(
            '<a href="https://regular.com">text</a> and <a href="https://icon.com" class="cmk-url-icon-link">icon</a>',
            '<a href="https://regular.com">text</a> and https://icon.com',
            id="mixed_regular_and_icon_button_links",
        ),
    ],
)
def test_replace_anchor_tags_with_urls(inp: str, out: str) -> None:
    assert escaping.replace_anchor_tags_with_urls(inp) == out


@pytest.mark.parametrize(
    "inp,out",
    [
        pytest.param(
            "Line 1<br>Line 2",
            "Line 1\nLine 2",
            id="basic_br_tag",
        ),
        pytest.param(
            "Line 1<br/>Line 2",
            "Line 1\nLine 2",
            id="self_closing_br_tag",
        ),
        pytest.param(
            "Line 1<br />Line 2",
            "Line 1\nLine 2",
            id="self_closing_br_with_space",
        ),
        pytest.param(
            "Line 1<BR>Line 2",
            "Line 1\nLine 2",
            id="uppercase_BR_tag",
        ),
        pytest.param(
            "Line 1<Br/>Line 2",
            "Line 1\nLine 2",
            id="mixed_case_Br_self_closing",
        ),
        pytest.param(
            "A<br>B<br>C",
            "A\nB\nC",
            id="multiple_line_breaks",
        ),
        pytest.param(
            "No breaks",
            "No breaks",
            id="no_line_breaks",
        ),
        pytest.param(
            "Start<br><b>bold</b><br>end",
            "Start\n<b>bold</b>\nend",
            id="mixed_with_other_html_tags",
        ),
    ],
)
def test_replace_br_with_newlines(inp: str, out: str) -> None:
    assert escaping.replace_br_with_newlines(inp) == out

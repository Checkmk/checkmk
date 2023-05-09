#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from html import escape as html_escape

from cmk.utils.urls import is_allowed_url

_UNESCAPER_TEXT = re.compile(
    r"&lt;(/?)(h1|h2|b|tt|i|u|br(?: /)?|nobr(?: /)?|pre|sup|p|li|ul|ol)&gt;")
_CLOSING_A = re.compile(r"&lt;/a&gt;")
_A_HREF = re.compile(
    r"&lt;a href=(?:(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;))(?: target=(?:(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;)))?&gt;"
)


class HTMLEscapedStr(str):
    """str in which all HTML entities are escaped

    Not sure if this class really makes sense. I would only use this for
    strings in which all entities are escaped. So as soon as we go the
    permissive way, we shouldn't use this class anymore. Perhaps we should use
    another? In `cmk.gui` we have the HTML object which is more or less exactly
    that... I keep it for now, it shouldn't hurt let's see where this
    goes...
    """


def escape(value: str) -> HTMLEscapedStr:
    """escape text for HTML (e.g. `< -> &lt;`)"""
    return HTMLEscapedStr(html_escape(value, quote=True))


def _unescape_link(escaped_str: str) -> str:
    """helper for escape_text to unescape links

    all `</a>` tags are unescaped, even the ones with no opening...

    >>> _unescape_link('&lt;/a&gt;')
    '</a>'
    >>> _unescape_link('foo&lt;a href=&quot;&quot;&gt;bar&lt;/a&gt;foobar')
    'foo&lt;a href=&quot;&quot;&gt;bar</a>foobar'
    >>> _unescape_link('foo&lt;a href=&quot;mailto:security@checkmk.com&quot;&gt;bar')
    'foo<a href="mailto:security@checkmk.com">bar'
    """
    escaped_str = _CLOSING_A.sub(r"</a>", escaped_str)
    for a_href in _A_HREF.finditer(escaped_str):
        href = a_href.group(1)

        if not href:
            continue
        if not is_allowed_url(href, cross_domain=True, schemes=["http", "https", "mailto"]):
            continue  # Do not unescape links containing disallowed URLs

        target = a_href.group(2)

        if target:
            unescaped_tag = f'<a href="{href}" target="{target}">'
        else:
            unescaped_tag = '<a href="%s">' % href

        escaped_str = escaped_str.replace(a_href.group(0), unescaped_tag)
    return escaped_str


def escape_permissive(text: str, escape_links: bool = True) -> str:
    """Escape HTML text

    We only strip some tags and allow some simple tags such as <h1>, <b> or <i>
    to be part of the string. (See: _UNESCAPER_TEXT) This is useful for
    messages where we want to keep formatting options. (Formerly known as
    'permissive_attrencode', 'escape_text') You should probably also checkout
    cmk.gui.utils.escaping

    >>> escape_permissive("Hello this is dog!")
    'Hello this is dog!'

    >>> text = 'Hello this <a href="http://some.site">is dog</a>!'
    >>> escape_permissive(text, escape_links=False)
    'Hello this <a href="http://some.site">is dog</a>!'
    >>> escape_permissive(text)
    'Hello this &lt;a href=&quot;http://some.site&quot;&gt;is dog&lt;/a&gt;!'
    """

    text = escape(text)
    text = _UNESCAPER_TEXT.sub(r"<\1\2>", text)
    if not escape_links:
        text = _unescape_link(text)
    return text.replace("&amp;nbsp;", "&nbsp;")

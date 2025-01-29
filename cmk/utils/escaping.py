#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from html import escape as html_escape

from cmk.utils.urls import is_allowed_url

ALLOWED_TAGS = r"h1|h2|b|tt|i|u|hr|br(?: /)?|nobr(?: /)?|pre|sup|p|li|ul|ol"
_UNESCAPER_TEXT = re.compile(rf"&lt;(/?)({ALLOWED_TAGS})&gt;")
_CLOSING_A = re.compile(r"&lt;/a&gt;")
_A_HREF = re.compile(
    r"&lt;a href=(?:(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;))(?: target=(?:(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;)))?&gt;"
)


def escape(value: str) -> str:
    """escape text for HTML (e.g. `< -> &lt;`)"""
    return html_escape(value, quote=True)


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

        if target := a_href.group(2):
            unescaped_tag = f'<a href="{href}" target="{target}">'
        else:
            unescaped_tag = f'<a href="{href}">'

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

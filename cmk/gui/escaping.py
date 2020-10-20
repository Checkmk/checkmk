#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from html import escape as html_escape
import re
from typing import Union

from six import ensure_str

from cmk.gui.utils.html import HTML

#.
#   .--Escaper-------------------------------------------------------------.
#   |                 _____                                                |
#   |                | ____|___  ___ __ _ _ __   ___ _ __                  |
#   |                |  _| / __|/ __/ _` | '_ \ / _ \ '__|                 |
#   |                | |___\__ \ (_| (_| | |_) |  __/ |                    |
#   |                |_____|___/\___\__,_| .__/ \___|_|                    |
#   |                                    |_|                               |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------

# TODO: Figure out if this should actually be HTMLTagValue or HTMLContent or...
# All the HTML-related types are slightly chaotic...
EscapableEntity = Union[None, int, HTML, str]

_UNESCAPER_TEXT = re.compile(
    r'&lt;(/?)(h1|h2|b|tt|i|u|br(?: /)?|nobr(?: /)?|pre|a|sup|p|li|ul|ol)&gt;')
_A_HREF = re.compile(
    r'&lt;a href=(?:(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;))(?: target=(?:(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;)))?&gt;'
)


# TODO: Cleanup the accepted types!
def escape_attribute(value: EscapableEntity) -> str:
    """Escape HTML attributes.

    For example: replace '"' with '&quot;', '<' with '&lt;'.
    This code is slow. Works on str and unicode without changing
    the type. Also works on things that can be converted with '%s'.

    Args:
        value:

    Examples:

        >>> escape_attribute("Hello this is <b>dog</b>!")
        'Hello this is &lt;b&gt;dog&lt;/b&gt;!'

        >>> escape_attribute("Hello this is <foo>dog</foo>!")
        'Hello this is &lt;foo&gt;dog&lt;/foo&gt;!'


    Returns:

    """
    attr_type = type(value)
    if value is None:
        return u''
    if attr_type == int:
        return str(value)
    if isinstance(value, HTML):
        return value.__html__()  # This is HTML code which must not be escaped
    if isinstance(attr_type, str):
        return html_escape(value, quote=True)
    if isinstance(attr_type, bytes):  # TODO: Not in the signature!
        return html_escape(ensure_str(value), quote=True)
    # TODO: What is this case for? Exception?
    return html_escape(u"%s" % value, quote=True)  # TODO: Not in the signature!


def unescape_attributes(value: str) -> str:
    # In python3 use html.unescape
    return ensure_str(value  #
                      .replace("&amp;", "&")  #
                      .replace("&quot;", "\"")  #
                      .replace("&lt;", "<")  #
                      .replace("&gt;", ">"))


def escape_text(text: EscapableEntity) -> str:
    """Escape HTML text

    We only strip some tags and allow some simple tags
    such as <h1>, <b> or <i> to be part of the string.
    This is useful for messages where we want to keep formatting
    options. (Formerly known as 'permissive_attrencode')

    Args:
        text:

    Examples:

        >>> escape_text("Hello this is dog!")
        'Hello this is dog!'

        This is lame.

        >>> escape_text("Hello this <a href=\"\">is dog</a>!")
        'Hello this &lt;a href=&gt;is dog</a>!'

    Returns:

    """
    if isinstance(text, HTML):
        return text.__html__()

    text = escape_attribute(text)
    text = _UNESCAPER_TEXT.sub(r'<\1\2>', text)
    for a_href in _A_HREF.finditer(text):
        href = a_href.group(1)
        target = a_href.group(2)

        if target:
            unescaped_tag = "<a href=\"%s\" target=\"%s\">" % (href, target)
        else:
            unescaped_tag = "<a href=\"%s\">" % href

        text = text.replace(a_href.group(0), unescaped_tag)
    return text.replace("&amp;nbsp;", u"&nbsp;")


def strip_scripts(ht: str) -> str:
    """Strip script tags from text.

    This function does not handle all the possible edge cases. Beware.

    Args:
        ht: A text with possible html in it.

    Examples:
        >>> strip_scripts('')
        ''

        >>> strip_scripts('foo <script>baz</script> bar')
        'foo  bar'

        Edge cases.

        >>> strip_scripts('foo <scr<script></script>ipt>alert()</SCRIPT> bar')
        'foo  bar'

    Returns:
        A text without html in it.

    """
    prev = None
    while prev != ht:
        prev = ht
        x = ht.lower().find('<script')
        if x == -1:
            break
        y = ht.lower().find('</script')
        if y == -1:
            break
        ht = ht[0:x] + ht[y + 9:]

    return ht


def strip_tags(ht: EscapableEntity) -> str:
    """Strip all HTML tags from a text.

    Args:
        ht: A text with possible HTML tags in it.

    Examples:
        >>> strip_tags("<b>foobar</b> blah")
        'foobar blah'

        Edge cases.

        >>> strip_tags("<p<b<>re>foobar</</b>b> blah")
        're>foobarb> blah'

    Returns:
        A string without working HTML tags.

    """
    if isinstance(ht, HTML):
        ht = ht.__html__()

    if not isinstance(ht, str):
        return u"%s" % ht

    ht = ensure_str(ht)

    while True:
        x = ht.find('<')
        if x == -1:
            break
        y = ht.find('>', x)
        if y == -1:
            break
        ht = ht[0:x] + ht[y + 1:]
    return ht.replace("&nbsp;", " ")

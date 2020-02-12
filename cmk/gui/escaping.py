#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
import re
from typing import Text, Union  # pylint: disable=unused-import
import six

if sys.version_info[0] >= 3:
    from html import escape as html_escape
else:
    from future.moves.html import escape as html_escape  # type: ignore[import]

from cmk.utils.encoding import ensure_unicode
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

_UNESCAPER_TEXT = re.compile(
    r'&lt;(/?)(h1|h2|b|tt|i|u|br(?: /)?|nobr(?: /)?|pre|a|sup|p|li|ul|ol)&gt;')
_QUOTE = re.compile(r"(?:&quot;|&#x27;)")
_A_HREF = re.compile(r'&lt;a href=((?:&quot;|&#x27;).*?(?:&quot;|&#x27;))&gt;')


# TODO: Cleanup the accepted types!
def escape_attribute(value):
    # type: (Union[None, int, HTML, str, Text]) -> Text
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
    elif attr_type == int:
        return six.text_type(value)
    elif isinstance(value, HTML):
        return value.__html__()  # This is HTML code which must not be escaped
    elif not isinstance(attr_type, six.string_types):  # also possible: type Exception!
        value = u"%s" % value
    return ensure_unicode(html_escape(value, quote=True))


def unescape_attributes(value):
    # type: (str) -> Text
    # In python3 use html.unescape
    return ensure_unicode(value  #
                          .replace("&amp;", "&")  #
                          .replace("&quot;", "\"")  #
                          .replace("&lt;", "<")  #
                          .replace("&gt;", ">"))


def escape_text(text):
    # type: (Union[None, int, HTML, str, Text]) -> Text
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
        text = text.replace(a_href.group(0), u"<a href=%s>" % _QUOTE.sub(u"\"", a_href.group(1)))
    return text.replace(u"&amp;nbsp;", u"&nbsp;")


def strip_scripts(ht):
    # type: (Text) -> Text
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


def strip_tags(ht):
    # type: (Union[HTML, str, Text]) -> Text
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

    if not isinstance(ht, six.string_types):
        return u"%s" % ht

    ht = ensure_unicode(ht)

    while True:
        x = ht.find('<')
        if x == -1:
            break
        y = ht.find('>', x)
        if y == -1:
            break
        ht = ht[0:x] + ht[y + 1:]
    return ht.replace("&nbsp;", " ")

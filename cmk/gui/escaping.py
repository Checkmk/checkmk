#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
import re

import six

from future.moves.html import escape as html_escape  # type: ignore

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


def escape_attribute(value):
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
        return ''
    elif attr_type == int:
        return str(value)
    elif hasattr(value, '__html__'):
        return value.__html__()  # This is HTML code which must not be escaped
    elif not isinstance(attr_type, six.string_types):  # also possible: type Exception!
        value = "%s" % value  # Note: this allows Unicode. value might not have type str now
    return html_escape(value, quote=True)


def unescape_attributes(value):
    # In python3 use html.unescape
    return value.replace("&amp;", "&")\
                .replace("&quot;", "\"")\
                .replace("&lt;", "<")\
                .replace("&gt;", ">")


def escape_text(text):
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
    if hasattr(text, '__html__'):  # This is HTML code which must not be escaped
        return text.__html__()

    text = escape_attribute(text)
    text = _UNESCAPER_TEXT.sub(r'<\1\2>', text)
    for a_href in _A_HREF.finditer(text):
        text = text.replace(a_href.group(0), "<a href=%s>" % _QUOTE.sub("\"", a_href.group(1)))
    return text.replace("&amp;nbsp;", "&nbsp;")


def strip_scripts(ht):
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
    if hasattr(ht, '__html__'):
        ht = ht.__html__()

    if not isinstance(ht, six.string_types):
        return ht

    while True:
        x = ht.find('<')
        if x == -1:
            break
        y = ht.find('>', x)
        if y == -1:
            break
        ht = ht[0:x] + ht[y + 1:]
    return ht.replace("&nbsp;", " ")

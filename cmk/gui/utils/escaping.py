#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from functools import lru_cache

from cmk.utils.escaping import escape, escape_permissive

from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString

# .
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
EscapableEntity = int | HTML | str | LazyString | None

_COMMENT_RE = re.compile("(<!--.*?-->)")
_TAG_RE = re.compile(r"(<[^>]+?>)")


def escape_to_html_permissive(value: str, escape_links: bool = True) -> HTML:
    """Escape HTML in permissive mode (keep simple markup tags) and return as HTML object

    >>> escape_to_html_permissive("Hello this is <b>dog</b>!")
    HTML("Hello this is <b>dog</b>!")

    >>> escape_to_html_permissive('<a href="mailto:security@checkmk.com">')
    HTML("&lt;a href=&quot;mailto:security@checkmk.com&quot;&gt;")

    >>> escape_to_html_permissive('<a href="mailto:security@checkmk.com">', escape_links=True)
    HTML("&lt;a href=&quot;mailto:security@checkmk.com&quot;&gt;")

    >>> escape_to_html_permissive('<a href="mailto:security@checkmk.com">no closing a', escape_links=False)
    HTML("<a href="mailto:security@checkmk.com">no closing a")
    """
    return HTML.without_escaping(escape_text(value, escape_links=escape_links))


# TODO: Cleanup the accepted types!
# TODO: The name of the function is missleading. This does not care about HTML tag attribute
# escaping.
@lru_cache(maxsize=8192)
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
    if isinstance(value, str):
        return escape(value)
    if isinstance(value, HTML):
        return str(value)  # HTML code which must not be escaped
    if value is None:
        return ""
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, LazyString):
        return escape(str(value))
    raise TypeError(f"Unsupported type {type(value)}")


def escape_text(value: EscapableEntity, escape_links: bool = False) -> str:
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

        >>> escape_text(None)
        ''

        >>> text = "Hello this <a href=>is dog</a>!"
        >>> escape_text(text, escape_links=False)
        'Hello this &lt;a href=&gt;is dog</a>!'

        >>> text = 'Hello this <a href="">is dog</a>!'
        >>> escape_text(text, escape_links=False)
        'Hello this &lt;a href=&quot;&quot;&gt;is dog</a>!'

        >>> text = 'Hello this <a href="http://some.site">is dog</a>!'
        >>> escape_text(text)
        'Hello this <a href="http://some.site">is dog</a>!'

        >>> text = 'Hello this <a href="http://some.site">is dog</a>!'
        >>> escape_text(text, escape_links=False)
        'Hello this <a href="http://some.site">is dog</a>!'
        >>> escape_text(text, escape_links=True)
        'Hello this &lt;a href=&quot;http://some.site&quot;&gt;is dog&lt;/a&gt;!'
    """

    if isinstance(value, HTML):
        return str(value)

    if value is None:
        text = ""
    elif isinstance(value, int | float):
        text = str(value)
    elif isinstance(value, LazyString):
        text = str(value)
    elif isinstance(value, str):
        text = value
    else:
        raise TypeError(f"Unsupported type {type(value)}")
    return escape_permissive(text, escape_links=escape_links)


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
        x = ht.lower().find("<script")
        if x == -1:
            break
        y = ht.lower().find("</script")
        if y == -1:
            break
        ht = ht[0:x] + ht[y + 9 :]

    return ht


def strip_tags(ht: EscapableEntity) -> str:
    """Strip all HTML tags from a text.

    This function does not handle all the possible edge cases. Beware.

    Args:
        ht: A text with possible html in it.

    Examples:

        >>> strip_tags('<b>Important Message</b>')
        'Important Message'

        >>> strip_tags('<a hr<!-- hallo hallo -->ef="">hello&nbsp;world</ <!-- blah -->  a>')
        'hello world'

        Even split HTML entities are recognized.

        >>> strip_tags("<b>foobar</b>&nb<a href="">s</a>p;blah")
        'foobar blah'

        >>> strip_tags("<scr<!-- foo -->ipt>alert();</scr<!-- foo -->ipt> blah")
        'alert(); blah'

        Edge cases.

        >>> strip_tags("<p<b<>re>foobar</</b>b> blah")
        're>foobarb> blah'

        Even HTML objects get stripped.

        >>> strip_tags(HTML.without_escaping('<a href="https://example.com">click here</a>'))
        'click here'

        Everything we don't know about won't get stripped.

        >>> strip_tags(object())  # type: ignore[arg-type]  # doctest: +ELLIPSIS
        '<object object at ...>'

    Returns:
        A string without working HTML tags.

    """
    if not isinstance(ht, str | HTML | LazyString):
        return str(ht)

    string = str(ht)
    while True:
        prev = string
        string = string.replace("&nbsp;", " ")
        string = _COMMENT_RE.sub("", string)
        string = _TAG_RE.sub("", string)
        if string == prev:
            return string


def strip_tags_for_tooltip(ht: EscapableEntity) -> str:
    string = str(ht)
    # Some painters render table and cell tags that would be stripped away in the next step and
    # result in the content of tables being joined together to a single word.
    # We replace the tags here with spaces to prevent that.
    #
    # For the moment we keep it simple and only fix the special case we stumbled upon.
    # In the future it might be better to find a more generic approach
    # that solves the problem for different tag combinations.
    string = string.replace("</th><td>", " ")
    return strip_tags(string)

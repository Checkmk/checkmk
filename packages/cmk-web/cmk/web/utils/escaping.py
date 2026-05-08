#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from functools import lru_cache
from html import escape as _html_escape

from cmk.web.utils.html import HTML
from cmk.web.utils.speaklater import LazyString
from cmk.web.utils.urls import is_allowed_url

# .
#   .--Escaper-------------------------------------------------------------.
#   |                 _____                                                |
#   |                | ____|___  ___ __ _ _ __   ____  ___ _ __            |
#   |                |  _| / __|/ __/ _` | '_ \ / _ \/ _ \ '__|            |
#   |                | |___\__ \ (_| (_| | |_) |  __/  __/ |               |
#   |                |_____|___/\___\__,_| .__/ \___|\___|_|               |
#   |                                    |_|                               |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'

EscapableEntity = int | HTML | str | LazyString | None

ALLOWED_TAGS = r"h1|h2|b|tt|i|u|hr|br(?: /)?|nobr(?: /)?|pre|sup|p|li|ul|ol"
_UNESCAPER_TEXT = re.compile(rf"&lt;(/?)({ALLOWED_TAGS})&gt;")
_CLOSING_A = re.compile(r"&lt;/a&gt;")
_A_HREF = re.compile(
    r"&lt;a href=(?:(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;))(?: target=(?:(?:&quot;|&#x27;)(.*?)(?:&quot;|&#x27;)))?&gt;"
)

_COMMENT_RE = re.compile("(<!--.*?-->)")
_TAG_RE = re.compile(r"(<[^>]+?>)")


def escape(value: str) -> str:
    """Escape text for HTML (e.g. ``< -> &lt;``)"""
    return _html_escape(value, quote=True)


def _unescape_link(escaped_str: str) -> str:
    """Helper for escape_permissive to unescape links.

    All ``</a>`` tags are unescaped, even the ones with no opening.

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
    """Escape HTML text, keeping safe structural tags.

    We only strip some tags and allow some simple tags such as <h1>, <b> or <i>
    to be part of the string. (See: ALLOWED_TAGS) This is useful for
    messages where we want to keep formatting options.

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
    if isinstance(value, str | LazyString):
        return escape(str(value))
    if isinstance(value, HTML):
        return str(value)  # HTML code which must not be escaped
    if value is None:
        return ""
    return str(value)


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
    elif isinstance(value, str):
        text = value
    else:
        text = str(value)
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
    while True:
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


def replace_anchor_tags_with_urls(html_str: str) -> str:
    """Replace URL icon buttons with their href URLs in place.

    This is the reverse operation of cmk/gui/view_utils._render_icon_button.
    Only replaces anchor tags marked with the 'cmk-url-icon-link' class.

    Example:
        >>> replace_anchor_tags_with_urls('<a href="https://example.com" class="cmk-url-icon-link" target="_blank">...</a>')
        'https://example.com'

        >>> replace_anchor_tags_with_urls('Text <a href="https://example.com" class="cmk-url-icon-link">icon</a> more text')
        'Text https://example.com more text'

        >>> replace_anchor_tags_with_urls('No links here')
        'No links here'
    """

    def replace_anchor_with_url(match: re.Match[str]) -> str:
        anchor_tag = match.group(0)
        if "class=" not in anchor_tag or "cmk-url-icon-link" not in anchor_tag:
            return anchor_tag

        href_match = re.search(r'href=["\']([^"\']+)["\']', anchor_tag)
        return href_match.group(1) if href_match else anchor_tag

    return re.sub(
        r"<a\b[^>]*>.*?</a>", replace_anchor_with_url, html_str, flags=re.IGNORECASE | re.DOTALL
    )


def replace_br_with_newlines(html_str: str) -> str:
    """Replace HTML line breaks with newline characters.

    Replaces <br>, <br/>, <br />, etc. with newline characters to preserve
    line breaks when exporting to text formats (CSV, PDF, etc.).

    Example:
        >>> replace_br_with_newlines('Line 1<br>Line 2')
        'Line 1\\nLine 2'

        >>> replace_br_with_newlines('Line 1<br />Line 2<BR/>Line 3')
        'Line 1\\nLine 2\\nLine 3'

        >>> replace_br_with_newlines('No line breaks')
        'No line breaks'
    """
    return re.sub(r"<br\s*/?>", "\n", html_str, flags=re.IGNORECASE)


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

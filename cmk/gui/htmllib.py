#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# TODO:
#
# Notes for future rewrite:
#
# - Find all call sites which do something like "int(html.request.var(...))"
#   and replace it with html.request.get_integer_input_mandatory(...)
#
# - Make clear which functions return values and which write out values
#   render_*, add_*, write_* (e.g. icon() -> outputs directly,
#                                  render_icon() -> returns icon
#
# - Order of arguments:
#   e.g. icon(help, icon) -> change and make help otional?
#
# - Fix names of message() show_error() show_warning()
#
# - change naming of escaping.escape_attribute() to html.render()
#
# - General rules:
# 1. values of type str that are passed as arguments or
#    return values or are stored in datastructures must not contain
#    non-Ascii characters! UTF-8 encoding must just be used in
#    the last few CPU cycles before outputting. Conversion from
#    input to str or unicode must happen as early as possible,
#    directly when reading from file or URL.
#
# - indentify internal helper methods and prefix them with "_"
#
# - Split HTML handling (page generating) code and generic request
#   handling (vars, cookies, ...) up into separate classes to make
#   the different tasks clearer. For ABCHTMLGenerator() or similar.
#
# - Unify CSS classes attribute to "class_"
import functools
import sys
import time
import os
import ast
import re
import json
import json.encoder  # type: ignore[import]
import abc
import pprint
from contextlib import contextmanager
from typing import (  # pylint: disable=unused-import
    Union, Text, Optional, List, Dict, Tuple, Any, Iterator, cast, Mapping, Set, TYPE_CHECKING,
    TypeVar,
)

import six

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error
else:
    from pathlib2 import Path  # pylint: disable=import-error

Value = TypeVar('Value')


# TODO: Cleanup this dirty hack. Import of htmllib must not magically modify the behaviour of
# the json module. Better would be to create a JSON wrapper in cmk.utils.json which uses a
# custom subclass of the JSONEncoder.
#
# Monkey patch in order to make the HTML class below json-serializable without changing the default json calls.
def _default(self, obj):
    # type: (json.JSONEncoder, object) -> Text
    # ignore attr-defined: See hack below
    return getattr(obj.__class__, "to_json", _default.default)(obj)  # type: ignore[attr-defined]


# TODO: suppress mypy warnings for this monkey patch right now. See also:
# https://github.com/python/mypy/issues/2087
# Save unmodified default:
_default.default = json.JSONEncoder().default  # type: ignore[attr-defined]
# replacement:
json.JSONEncoder.default = _default  # type: ignore[assignment]

# And here we go for another dirty JSON hack. We often use he JSON we produce for adding it to HTML
# tags and the JSON produced by json.dumps() can not directly be added to <script> tags in a save way.
# TODO: This is something which should be realized by using a custom JSONEncoder. The slash encoding
# is not necessary when the resulting string is not added to HTML content, but there is no problem
# to apply it to all encoded strings.


def _patch_json(json_module):
    # We make this a function which is called on import-time because mypy fell into an endless-loop
    # due to changes outside this scope.
    orig_func = json_module.encoder.encode_basestring_ascii

    @functools.wraps(orig_func)
    def _escaping_wrapper(s):
        return orig_func(s).replace('/', '\\/')

    json_module.encoder.encode_basestring_ascii = _escaping_wrapper


_patch_json(json)

import cmk.utils.version as cmk_version
import cmk.utils.paths
from cmk.utils.encoding import ensure_unicode
from cmk.utils.exceptions import MKGeneralException

from cmk.gui.exceptions import MKUserError
import cmk.gui.escaping as escaping
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.log as log
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import OutputFunnel
from cmk.gui.utils.transaction_manager import TransactionManager
from cmk.gui.utils.timeout_manager import TimeoutManager
from cmk.gui.utils.url_encoder import URLEncoder
from cmk.gui.i18n import _
from cmk.gui.http import Response

if TYPE_CHECKING:
    from cmk.gui.http import Request  # pylint: disable=unused-import
    from cmk.gui.type_defs import VisualContext, HTTPVariables  # pylint: disable=unused-import
    from cmk.gui.valuespec import ValueSpec  # pylint: disable=unused-import
    from cmk.gui.utils.output_funnel import OutputFunnelInput  # pylint: disable=unused-import

# TODO: Cleanup this mess.
CSSSpec = Union[None, str, List[str], List[Union[str, None]], str]
HTMLTagName = str
HTMLTagValue = Union[None, str, Text]
HTMLContent = Union[None, int, HTML, str, Text]
HTMLTagAttributeValue = Union[None, CSSSpec, HTMLTagValue, List[Union[str, Text]]]
HTMLTagAttributes = Dict[str, HTMLTagAttributeValue]
HTMLMessageInput = Union[HTML, Text]
Choices = List[Tuple[Union[None, str, Text], Text]]
DefaultChoice = Union[str, Text]
FoldingIndent = Union[str, None, bool]

#.
#   .--HTML Generator------------------------------------------------------.
#   |                      _   _ _____ __  __ _                            |
#   |                     | | | |_   _|  \/  | |                           |
#   |                     | |_| | | | | |\/| | |                           |
#   |                     |  _  | | | | |  | | |___                        |
#   |                     |_| |_| |_| |_|  |_|_____|                       |
#   |                                                                      |
#   |             ____                           _                         |
#   |            / ___| ___ _ __   ___ _ __ __ _| |_ ___  _ __             |
#   |           | |  _ / _ \ '_ \ / _ \ '__/ _` | __/ _ \| '__|            |
#   |           | |_| |  __/ | | |  __/ | | (_| | || (_) | |               |
#   |            \____|\___|_| |_|\___|_|  \__,_|\__\___/|_|               |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Generator which provides top level HTML writing functionality.      |
#   '----------------------------------------------------------------------'


class ABCHTMLGenerator(six.with_metaclass(abc.ABCMeta, object)):
    """ Usage Notes:

          - Tags can be opened using the open_[tag]() call where [tag] is one of the possible tag names.
            All attributes can be passed as function arguments, such as open_div(class_="example").
            However, python specific key words need to be escaped using a trailing underscore.
            One can also provide a dictionary as attributes: open_div(**{"class": "example"}).

          - All tags can be closed again using the close_[tag]() syntax.

          - For tags which shall only contain plain text (i.e. no tags other than highlighting tags)
            you can a the direct call using the tag name only as function name,
            self.div("Text content", **attrs). Tags featuring this functionality are listed in
            the "featured shortcuts" list.

          - Some tags require mandatory arguments. Those are defined explicitly below.
            For example an a tag needs the href attribute everytime.

          - If you want to provide plain HTML to a tag, please use the tag_content function or
            facillitate the HTML class.

        HOWTO HTML Attributes:

          - Python specific attributes have to be escaped using a trailing underscore

          - All attributes can be python objects. However, some attributes can also be lists of attrs:

                'class' attributes will be concatenated using one whitespace
                'style' attributes will be concatenated using the semicolon and one whitespace
                Behaviorial attributes such as 'onclick', 'onmouseover' will bec concatenated using
                a semicolon and one whitespace.

          - All attributes will be escaped, i.e. the characters '&', '<', '>', '"' will be replaced by
            non HtML relevant signs '&amp;', '&lt;', '&gt;' and '&quot;'. """

    #
    # Rendering
    #

    def _render_attributes(self, **attrs):
        # type: (**HTMLTagAttributeValue) -> Iterator[Text]
        css = self._get_normalized_css_classes(attrs)
        if css:
            attrs["class"] = css

        # options such as 'selected' and 'checked' dont have a value in html tags
        options = []

        # Links require href to be first attribute
        href = attrs.pop('href', None)
        if href:
            yield ' href=\"%s\"' % href

        # render all attributes
        for key_unescaped, v in attrs.items():
            if v is None:
                continue

            key = escaping.escape_attribute(key_unescaped.rstrip('_'))

            if v == '':
                options.append(key)
                continue

            if not isinstance(v, list):
                v = escaping.escape_attribute(v)
            else:
                if key == "class":
                    sep = ' '
                elif key == "style" or key.startswith('on'):
                    sep = '; '
                else:
                    sep = '_'

                joined_value = sep.join(
                    [a for a in (escaping.escape_attribute(vi) for vi in v) if a])

                if sep.startswith(';'):
                    joined_value = re.sub(';+', ';', joined_value)

                v = joined_value

            yield ' %s=\"%s\"' % (key, v)

        for k in options:
            yield " %s=\'\'" % k

    def _get_normalized_css_classes(self, attrs):
        # type: (HTMLTagAttributes) -> List[str]
        # make class attribute foolproof
        css = []  # type: List[str]
        for k in ["class_", "css", "cssclass", "class"]:
            if k in attrs:
                cls_spec = cast(CSSSpec, attrs.pop(k))
                if isinstance(cls_spec, list):
                    css.extend([c for c in cls_spec if c is not None])
                elif cls_spec is not None:
                    css.append(cls_spec)
        return css

    # applies attribute encoding to prevent code injections.
    def _render_start_tag(self, tag_name, close_tag=False, **attrs):
        # type: (HTMLTagName, bool, **HTMLTagAttributeValue) -> HTML
        """ You have to replace attributes which are also python elements such as
            'class', 'id', 'for' or 'type' using a trailing underscore (e.g. 'class_' or 'id_'). """
        return HTML("<%s%s%s>" %
                    (tag_name, '' if not attrs else ''.join(self._render_attributes(**attrs)),
                     '' if not close_tag else ' /'))

    def _render_end_tag(self, tag_name):
        # type: (HTMLTagName) -> HTML
        return HTML("</%s>" % (tag_name))

    def _render_element(self, tag_name, tag_content, **attrs):
        # type: (HTMLTagName, HTMLContent, **HTMLTagAttributeValue) -> HTML
        open_tag = self._render_start_tag(tag_name, close_tag=False, **attrs)

        if not tag_content:
            tag_content = ""
        elif not isinstance(tag_content, HTML):
            tag_content = escaping.escape_text(tag_content)

        return HTML("%s%s</%s>" % (open_tag, tag_content, tag_name))

    #
    # Showing / rendering
    #

    def render_text(self, text):
        # type: (HTMLContent) -> HTML
        return HTML(escaping.escape_text(text))

    def write_text(self, text):
        # type: (HTMLContent) -> None
        """ Write text. Highlighting tags such as h2|b|tt|i|br|pre|a|sup|p|li|ul|ol are not escaped. """
        self.write(self.render_text(text))

    def write_html(self, content):
        # type: (HTML) -> None
        """ Write HTML code directly, without escaping. """
        self.write(content)

    @abc.abstractmethod
    def write(self, text):
        # type: (OutputFunnelInput) -> None
        raise NotImplementedError()

    #
    # HTML element methods
    # If an argument is mandatory, it is used as default and it will overwrite an
    # implicit argument (e.g. id_ will overwrite attrs["id"]).
    #

    #
    # basic elements
    #

    def meta(self, httpequiv=None, **attrs):
        # type: (Optional[str], **HTMLTagAttributeValue) -> None
        if httpequiv:
            attrs['http-equiv'] = httpequiv
        self.write_html(self._render_start_tag('meta', close_tag=True, **attrs))

    def base(self, target):
        # type: (str) -> None
        self.write_html(self._render_start_tag('base', close_tag=True, target=target))

    def open_a(self, href, **attrs):
        # type: (Optional[str], **HTMLTagAttributeValue) -> None
        if href is not None:
            attrs['href'] = href
        self.write_html(self._render_start_tag('a', close_tag=False, **attrs))

    def render_a(self, content, href, **attrs):
        # type: (HTMLContent, Union[None, str, Text], **HTMLTagAttributeValue) -> HTML
        if href is not None:
            attrs['href'] = href
        return self._render_element('a', content, **attrs)

    def a(self, content, href, **attrs):
        # type: (HTMLContent, str, **HTMLTagAttributeValue) -> None
        self.write_html(self.render_a(content, href, **attrs))

    def stylesheet(self, href):
        # type: (str) -> None
        self.write_html(
            self._render_start_tag('link',
                                   rel="stylesheet",
                                   type_="text/css",
                                   href=href,
                                   close_tag=True))

    #
    # Scripting
    #

    def render_javascript(self, code):
        # type: (str) -> HTML
        return HTML("<script type=\"text/javascript\">\n%s\n</script>\n" % code)

    def javascript(self, code):
        # type: (str) -> None
        self.write_html(self.render_javascript(code))

    def javascript_file(self, src):
        # type: (str) -> None
        """ <script type="text/javascript" src="%(name)"/>\n """
        self.write_html(self._render_element('script', '', type_="text/javascript", src=src))

    def render_img(self, src, **attrs):
        # type: (str, **HTMLTagAttributeValue) -> HTML
        attrs['src'] = src
        return self._render_start_tag('img', close_tag=True, **attrs)

    def img(self, src, **attrs):
        # type: (str, **HTMLTagAttributeValue) -> None
        self.write_html(self.render_img(src, **attrs))

    def open_button(self, type_, **attrs):
        # type: (str, **HTMLTagAttributeValue) -> None
        attrs['type'] = type_
        self.write_html(self._render_start_tag('button', close_tag=True, **attrs))

    def play_sound(self, url):
        # type: (str) -> None
        self.write_html(self._render_start_tag('audio autoplay', src_=url))

    #
    # form elements
    #

    def render_label(self, content, for_, **attrs):
        # type: (HTMLContent, str, **HTMLTagAttributeValue) -> HTML
        attrs['for'] = for_
        return self._render_element('label', content, **attrs)

    def label(self, content, for_, **attrs):
        # type: (HTMLContent, str, **HTMLTagAttributeValue) -> None
        self.write_html(self.render_label(content, for_, **attrs))

    def render_input(self, name, type_, **attrs):
        # type: (Optional[str], str, **HTMLTagAttributeValue) -> HTML
        attrs['type_'] = type_
        attrs['name'] = name
        return self._render_start_tag('input', close_tag=True, **attrs)

    def input(self, name, type_, **attrs):
        # type: (Optional[str], str, **HTMLTagAttributeValue) -> None
        self.write_html(self.render_input(name, type_, **attrs))

    #
    # table and list elements
    #

    def li(self, content, **attrs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        """ Only for text content. You can't put HTML structure here. """
        self.write_html(self._render_element('li', content, **attrs))

    #
    # structural text elements
    #

    def render_heading(self, content):
        # type: (HTMLContent) -> HTML
        return self._render_element('h2', content)

    def heading(self, content):
        # type: (HTMLContent) -> None
        self.write_html(self.render_heading(content))

    def render_br(self):
        # type: () -> HTML
        return HTML("<br/>")

    def br(self):
        # type: () -> None
        self.write_html(self.render_br())

    def render_hr(self, **attrs):
        # type: (**HTMLTagAttributeValue) -> HTML
        return self._render_start_tag('hr', close_tag=True, **attrs)

    def hr(self, **attrs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self.render_hr(**attrs))

    def rule(self):
        # type: () -> None
        self.hr()

    def render_nbsp(self):
        # type: () -> HTML
        return HTML("&nbsp;")

    def nbsp(self):
        # type: () -> None
        self.write_html(self.render_nbsp())

    #
    # Simple HTML object rendering without specific functionality
    #

    def pre(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("pre", content, **kwargs))

    def h2(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("h2", content, **kwargs))

    def h3(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("h3", content, **kwargs))

    def h1(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("h1", content, **kwargs))

    def h4(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("h4", content, **kwargs))

    def style(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("style", content, **kwargs))

    def span(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("span", content, **kwargs))

    def sub(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("sub", content, **kwargs))

    def title(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("title", content, **kwargs))

    def tt(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("tt", content, **kwargs))

    def tr(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("tr", content, **kwargs))

    def th(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("th", content, **kwargs))

    def td(self, content, colspan=None, **kwargs):
        # type: (HTMLContent, Optional[int], **HTMLTagAttributeValue) -> None
        self.write_html(
            self._render_element("td",
                                 content,
                                 colspan=str(colspan) if colspan is not None else None,
                                 **kwargs))

    def option(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("option", content, **kwargs))

    def canvas(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("canvas", content, **kwargs))

    def strong(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("strong", content, **kwargs))

    def b(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("b", content, **kwargs))

    def center(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("center", content, **kwargs))

    def i(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("i", content, **kwargs))

    def p(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("p", content, **kwargs))

    def u(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("u", content, **kwargs))

    def iframe(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("iframe", content, **kwargs))

    def x(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("x", content, **kwargs))

    def div(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> None
        self.write_html(self._render_element("div", content, **kwargs))

    def open_pre(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("pre", close_tag=False, **kwargs))

    def close_pre(self):
        # type: () -> None
        self.write_html(self._render_end_tag("pre"))

    def render_pre(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("pre", content, **kwargs)

    def open_h2(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("h2", close_tag=False, **kwargs))

    def close_h2(self):
        # type: () -> None
        self.write_html(self._render_end_tag("h2"))

    def render_h2(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("h2", content, **kwargs)

    def open_h3(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("h3", close_tag=False, **kwargs))

    def close_h3(self):
        # type: () -> None
        self.write_html(self._render_end_tag("h3"))

    def render_h3(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("h3", content, **kwargs)

    def open_h1(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("h1", close_tag=False, **kwargs))

    def close_h1(self):
        # type: () -> None
        self.write_html(self._render_end_tag("h1"))

    def render_h1(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("h1", content, **kwargs)

    def open_h4(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("h4", close_tag=False, **kwargs))

    def close_h4(self):
        # type: () -> None
        self.write_html(self._render_end_tag("h4"))

    def render_h4(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("h4", content, **kwargs)

    def open_header(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("header", close_tag=False, **kwargs))

    def close_header(self):
        # type: () -> None
        self.write_html(self._render_end_tag("header"))

    def render_header(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("header", content, **kwargs)

    def open_tag(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("tag", close_tag=False, **kwargs))

    def close_tag(self):
        # type: () -> None
        self.write_html(self._render_end_tag("tag"))

    def render_tag(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("tag", content, **kwargs)

    def open_table(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("table", close_tag=False, **kwargs))

    def close_table(self):
        # type: () -> None
        self.write_html(self._render_end_tag("table"))

    def render_table(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("table", content, **kwargs)

    def open_select(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("select", close_tag=False, **kwargs))

    def close_select(self):
        # type: () -> None
        self.write_html(self._render_end_tag("select"))

    def render_select(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("select", content, **kwargs)

    def open_row(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("row", close_tag=False, **kwargs))

    def close_row(self):
        # type: () -> None
        self.write_html(self._render_end_tag("row"))

    def render_row(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("row", content, **kwargs)

    def open_style(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("style", close_tag=False, **kwargs))

    def close_style(self):
        # type: () -> None
        self.write_html(self._render_end_tag("style"))

    def render_style(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("style", content, **kwargs)

    def open_span(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("span", close_tag=False, **kwargs))

    def close_span(self):
        # type: () -> None
        self.write_html(self._render_end_tag("span"))

    def render_span(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("span", content, **kwargs)

    def open_sub(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("sub", close_tag=False, **kwargs))

    def close_sub(self):
        # type: () -> None
        self.write_html(self._render_end_tag("sub"))

    def render_sub(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("sub", content, **kwargs)

    def open_script(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("script", close_tag=False, **kwargs))

    def close_script(self):
        # type: () -> None
        self.write_html(self._render_end_tag("script"))

    def render_script(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("script", content, **kwargs)

    def open_tt(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("tt", close_tag=False, **kwargs))

    def close_tt(self):
        # type: () -> None
        self.write_html(self._render_end_tag("tt"))

    def render_tt(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("tt", content, **kwargs)

    def open_tr(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("tr", close_tag=False, **kwargs))

    def close_tr(self):
        # type: () -> None
        self.write_html(self._render_end_tag("tr"))

    def render_tr(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("tr", content, **kwargs)

    def open_tbody(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("tbody", close_tag=False, **kwargs))

    def close_tbody(self):
        # type: () -> None
        self.write_html(self._render_end_tag("tbody"))

    def render_tbody(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("tbody", content, **kwargs)

    def open_li(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("li", close_tag=False, **kwargs))

    def close_li(self):
        # type: () -> None
        self.write_html(self._render_end_tag("li"))

    def render_li(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("li", content, **kwargs)

    def open_html(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("html", close_tag=False, **kwargs))

    def close_html(self):
        # type: () -> None
        self.write_html(self._render_end_tag("html"))

    def render_html(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("html", content, **kwargs)

    def open_th(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("th", close_tag=False, **kwargs))

    def close_th(self):
        # type: () -> None
        self.write_html(self._render_end_tag("th"))

    def render_th(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("th", content, **kwargs)

    def open_sup(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("sup", close_tag=False, **kwargs))

    def close_sup(self):
        # type: () -> None
        self.write_html(self._render_end_tag("sup"))

    def render_sup(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("sup", content, **kwargs)

    def open_input(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("input", close_tag=False, **kwargs))

    def close_input(self):
        # type: () -> None
        self.write_html(self._render_end_tag("input"))

    def open_td(self, colspan=None, **kwargs):
        # type: (Optional[int], **HTMLTagAttributeValue) -> None
        self.write_html(
            self._render_start_tag("td",
                                   close_tag=False,
                                   colspan=str(colspan) if colspan is not None else None,
                                   **kwargs))

    def close_td(self):
        # type: () -> None
        self.write_html(self._render_end_tag("td"))

    def render_td(self, content, colspan=None, **kwargs):
        # type: (HTMLContent, Optional[int], **HTMLTagAttributeValue) -> HTML
        return self._render_element("td",
                                    content,
                                    colspan=str(colspan) if colspan is not None else None,
                                    **kwargs)

    def open_thead(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("thead", close_tag=False, **kwargs))

    def close_thead(self):
        # type: () -> None
        self.write_html(self._render_end_tag("thead"))

    def render_thead(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("thead", content, **kwargs)

    def open_body(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("body", close_tag=False, **kwargs))

    def close_body(self):
        # type: () -> None
        self.write_html(self._render_end_tag("body"))

    def render_body(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("body", content, **kwargs)

    def open_head(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("head", close_tag=False, **kwargs))

    def close_head(self):
        # type: () -> None
        self.write_html(self._render_end_tag("head"))

    def render_head(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("head", content, **kwargs)

    def open_fieldset(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("fieldset", close_tag=False, **kwargs))

    def close_fieldset(self):
        # type: () -> None
        self.write_html(self._render_end_tag("fieldset"))

    def render_fieldset(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("fieldset", content, **kwargs)

    def open_option(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("option", close_tag=False, **kwargs))

    def close_option(self):
        # type: () -> None
        self.write_html(self._render_end_tag("option"))

    def render_option(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("option", content, **kwargs)

    def open_form(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("form", close_tag=False, **kwargs))

    def close_form(self):
        # type: () -> None
        self.write_html(self._render_end_tag("form"))

    def render_form(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("form", content, **kwargs)

    def open_tags(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("tags", close_tag=False, **kwargs))

    def close_tags(self):
        # type: () -> None
        self.write_html(self._render_end_tag("tags"))

    def render_tags(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("tags", content, **kwargs)

    def open_canvas(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("canvas", close_tag=False, **kwargs))

    def close_canvas(self):
        # type: () -> None
        self.write_html(self._render_end_tag("canvas"))

    def render_canvas(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("canvas", content, **kwargs)

    def open_nobr(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("nobr", close_tag=False, **kwargs))

    def close_nobr(self):
        # type: () -> None
        self.write_html(self._render_end_tag("nobr"))

    def render_nobr(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("nobr", content, **kwargs)

    def open_br(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("br", close_tag=False, **kwargs))

    def close_br(self):
        # type: () -> None
        self.write_html(self._render_end_tag("br"))

    def open_strong(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("strong", close_tag=False, **kwargs))

    def close_strong(self):
        # type: () -> None
        self.write_html(self._render_end_tag("strong"))

    def render_strong(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("strong", content, **kwargs)

    def close_a(self):
        # type: () -> None
        self.write_html(self._render_end_tag("a"))

    def open_b(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("b", close_tag=False, **kwargs))

    def close_b(self):
        # type: () -> None
        self.write_html(self._render_end_tag("b"))

    def render_b(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("b", content, **kwargs)

    def open_center(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("center", close_tag=False, **kwargs))

    def close_center(self):
        # type: () -> None
        self.write_html(self._render_end_tag("center"))

    def render_center(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("center", content, **kwargs)

    def open_footer(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("footer", close_tag=False, **kwargs))

    def close_footer(self):
        # type: () -> None
        self.write_html(self._render_end_tag("footer"))

    def render_footer(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("footer", content, **kwargs)

    def open_i(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("i", close_tag=False, **kwargs))

    def close_i(self):
        # type: () -> None
        self.write_html(self._render_end_tag("i"))

    def render_i(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("i", content, **kwargs)

    def close_button(self):
        # type: () -> None
        self.write_html(self._render_end_tag("button"))

    def open_title(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("title", close_tag=False, **kwargs))

    def close_title(self):
        # type: () -> None
        self.write_html(self._render_end_tag("title"))

    def render_title(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("title", content, **kwargs)

    def open_p(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("p", close_tag=False, **kwargs))

    def close_p(self):
        # type: () -> None
        self.write_html(self._render_end_tag("p"))

    def render_p(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("p", content, **kwargs)

    def open_u(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("u", close_tag=False, **kwargs))

    def close_u(self):
        # type: () -> None
        self.write_html(self._render_end_tag("u"))

    def render_u(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("u", content, **kwargs)

    def open_iframe(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("iframe", close_tag=False, **kwargs))

    def close_iframe(self):
        # type: () -> None
        self.write_html(self._render_end_tag("iframe"))

    def render_iframe(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("iframe", content, **kwargs)

    def open_x(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("x", close_tag=False, **kwargs))

    def close_x(self):
        # type: () -> None
        self.write_html(self._render_end_tag("x"))

    def render_x(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("x", content, **kwargs)

    def open_div(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("div", close_tag=False, **kwargs))

    def close_div(self):
        # type: () -> None
        self.write_html(self._render_end_tag("div"))

    def render_div(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("div", content, **kwargs)

    def open_ul(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("ul", close_tag=False, **kwargs))

    def close_ul(self):
        # type: () -> None
        self.write_html(self._render_end_tag("ul"))

    def render_ul(self, content, **kwargs):
        # type: (HTMLContent, **HTMLTagAttributeValue) -> HTML
        return self._render_element("ul", content, **kwargs)


#.
#   .--html----------------------------------------------------------------.
#   |                        _     _             _                         |
#   |                       | |__ | |_ _ __ ___ | |                        |
#   |                       | '_ \| __| '_ ` _ \| |                        |
#   |                       | | | | |_| | | | | | |                        |
#   |                       |_| |_|\__|_| |_| |_|_|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Caution! The class needs to be derived from Outputfunnel first!      |
#   '----------------------------------------------------------------------'

OUTPUT_FORMAT_MIME_TYPES = {
    "json": "application/json",
    "jsonp": "application/javascript",
    "csv": "text/csv",
    "csv_export": "text/csv",
    "python": "text/plain",
    "text": "text/plain",
    "html": "text/html",
    "xml": "text/xml",
    "pdf": "application/pdf",
}


class html(ABCHTMLGenerator):
    def __init__(self, request):
        # type: (Request) -> None
        super(html, self).__init__()

        self._logger = log.logger.getChild("html")

        # rendering state
        self._header_sent = False
        self._context_buttons_open = False

        # style options
        self._body_classes = ['main']
        self._default_javascripts = ["main"]

        # behaviour options
        self.render_headfoot = True
        self.enable_debug = False
        self.screenshotmode = False
        self.have_help = False
        # TODO: Clean this foldable specific state member up
        self.folding_indent = None  # type: FoldingIndent

        # browser options
        self.output_format = "html"
        self.browser_reload = 0.0
        self.browser_redirect = ''
        self.link_target = None  # type: Optional[str]

        # Browser options
        self.user_errors = {}  # type: Dict[Optional[str], Text]
        self.focus_object = None  # type: Union[None, Tuple[Optional[str], str], str]
        self.status_icons = {}  # type: Dict[str, Union[Tuple[Text, str], Text]]
        self.final_javascript_code = ""
        self.page_context = {}  # type: VisualContext

        # Settings
        self.mobile = False
        self._theme = "facelift"

        # Forms
        self.form_name = None  # type: Optional[str]
        self.form_vars = []  # type: List[str]

        # Time measurement
        self.times = {}  # type: Dict[str, float]
        self.start_time = time.time()
        self.last_measurement = self.start_time

        # Register helpers
        self.encoder = URLEncoder()
        self.timeout_manager = TimeoutManager()
        self.transaction_manager = TransactionManager(request)
        self.response = Response()
        self.output_funnel = OutputFunnel(self.response)
        self.request = request

        # TODO: Cleanup this side effect (then remove disable_request_timeout() e.g. from update_config.py)
        self.enable_request_timeout()

        self.response.headers["Content-type"] = "text/html; charset=UTF-8"

        self.init_mobile()

        self.myfile = self._requested_file_name()

        # Disable caching for all our pages as they are mostly dynamically generated,
        # user related and are required to be up-to-date on every refresh
        self.response.headers["Cache-Control"] = "no-cache"

        try:
            output_format = self.request.get_ascii_input_mandatory("output_format", "html")
            self.set_output_format(output_format.lower())
        except (MKUserError, MKGeneralException):
            pass  # Silently ignore unsupported formats

    def init_modes(self):
        # type: () -> None
        """Initializes the operation mode of the html() object. This is called
        after the Check_MK GUI configuration has been loaded, so it is safe
        to rely on the config."""
        self._verify_not_using_threaded_mpm()

        self._init_screenshot_mode()
        self._init_debug_mode()
        self._init_webapi_cors_header()
        self.init_theme()

    def _init_webapi_cors_header(self):
        # type: () -> None
        # Would be better to put this to page individual code, but we currently have
        # no mechanism for a page to set do this before the authentication is made.
        if self.myfile == "webapi":
            self.response.headers["Access-Control-Allow-Origin"] = "*"

    def init_theme(self):
        # type: () -> None
        self.set_theme(config.ui_theme)

    def set_theme(self, theme_id):
        # type: (str) -> None
        if not theme_id:
            theme_id = config.ui_theme

        if theme_id not in dict(config.theme_choices()):
            theme_id = "facelift"

        self._theme = theme_id

    def get_theme(self):
        # type: () -> str
        return self._theme

    def theme_url(self, rel_url):
        # type: (str) -> str
        return "themes/%s/%s" % (self._theme, rel_url)

    def _verify_not_using_threaded_mpm(self):
        # type: () -> None
        if self.request.is_multithread:
            raise MKGeneralException(
                _("You are trying to Check_MK together with a threaded Apache multiprocessing module (MPM). "
                  "Check_MK is only working with the prefork module. Please change the MPM module to make "
                  "Check_MK work."))

    def _init_debug_mode(self):
        # type: () -> None
        # Debug flag may be set via URL to override the configuration
        if self.request.var("debug"):
            config.debug = True
        self.enable_debug = config.debug

    # Enabling the screenshot mode omits the fancy background and
    # makes it white instead.
    def _init_screenshot_mode(self):
        # type: () -> None
        if self.request.var("screenshotmode", "1" if config.screenshotmode else ""):
            self.screenshotmode = True

    def _requested_file_name(self):
        # type: () -> str
        parts = self.request.requested_file.rstrip("/").split("/")

        if len(parts) == 3 and parts[-1] == "check_mk":
            # Load index page when accessing /[site]/check_mk
            myfile = "index"

        elif parts[-1].endswith(".py"):
            # Regular pages end with .py - Stript it away to get the page name
            myfile = parts[-1][:-3]
            if myfile == "":
                myfile = "index"

        else:
            myfile = "index"

        # Redirect to mobile GUI if we are a mobile device and the index is requested
        if myfile == "index" and self.mobile:
            myfile = "mobile"

        return myfile

    def init_mobile(self):
        # type: () -> None
        if self.request.has_var("mobile"):
            # TODO: Make private
            self.mobile = bool(self.request.var("mobile"))
            # Persist the explicitly set state in a cookie to have it maintained through further requests
            self.response.set_http_cookie("mobile", str(int(self.mobile)))

        elif self.request.has_cookie("mobile"):
            self.mobile = self.request.cookie("mobile", "0") == "1"

        else:
            self.mobile = self._is_mobile_client(self.request.user_agent.string)

    def _is_mobile_client(self, user_agent):
        # type: (str) -> bool
        # These regexes are taken from the public domain code of Matt Sullivan
        # http://sullerton.com/2011/03/django-mobile-browser-detection-middleware/
        reg_b = re.compile(
            r"android.+mobile|avantgo|bada\\/|blackberry|bb10|blazer|compal|elaine|fennec|hiptop|iemobile|ip(hone|od)|iris|kindle|lge |maemo|midp|mmp|opera m(ob|in)i|palm( os)?|phone|p(ixi|re)\\/|plucker|pocket|psp|symbian|treo|up\\.(browser|link)|vodafone|wap|windows (ce|phone)|xda|xiino",  # noqa: E501
            re.I | re.M)
        reg_v = re.compile(
            r"1207|6310|6590|3gso|4thp|50[1-6]i|770s|802s|a wa|abac|ac(er|oo|s\\-)|ai(ko|rn)|al(av|ca|co)|amoi|an(ex|ny|yw)|aptu|ar(ch|go)|as(te|us)|attw|au(di|\\-m|r |s )|avan|be(ck|ll|nq)|bi(lb|rd)|bl(ac|az)|br(e|v)w|bumb|bw\\-(n|u)|c55\\/|capi|ccwa|cdm\\-|cell|chtm|cldc|cmd\\-|co(mp|nd)|craw|da(it|ll|ng)|dbte|dc\\-s|devi|dica|dmob|do(c|p)o|ds(12|\\-d)|el(49|ai)|em(l2|ul)|er(ic|k0)|esl8|ez([4-7]0|os|wa|ze)|fetc|fly(\\-|_)|g1 u|g560|gene|gf\\-5|g\\-mo|go(\\.w|od)|gr(ad|un)|haie|hcit|hd\\-(m|p|t)|hei\\-|hi(pt|ta)|hp( i|ip)|hs\\-c|ht(c(\\-| |_|a|g|p|s|t)|tp)|hu(aw|tc)|i\\-(20|go|ma)|i230|iac( |\\-|\\/)|ibro|idea|ig01|ikom|im1k|inno|ipaq|iris|ja(t|v)a|jbro|jemu|jigs|kddi|keji|kgt( |\\/)|klon|kpt |kwc\\-|kyo(c|k)|le(no|xi)|lg( g|\\/(k|l|u)|50|54|e\\-|e\\/|\\-[a-w])|libw|lynx|m1\\-w|m3ga|m50\\/|ma(te|ui|xo)|mc(01|21|ca)|m\\-cr|me(di|rc|ri)|mi(o8|oa|ts)|mmef|mo(01|02|bi|de|do|t(\\-| |o|v)|zz)|mt(50|p1|v )|mwbp|mywa|n10[0-2]|n20[2-3]|n30(0|2)|n50(0|2|5)|n7(0(0|1)|10)|ne((c|m)\\-|on|tf|wf|wg|wt)|nok(6|i)|nzph|o2im|op(ti|wv)|oran|owg1|p800|pan(a|d|t)|pdxg|pg(13|\\-([1-8]|c))|phil|pire|pl(ay|uc)|pn\\-2|po(ck|rt|se)|prox|psio|pt\\-g|qa\\-a|qc(07|12|21|32|60|\\-[2-7]|i\\-)|qtek|r380|r600|raks|rim9|ro(ve|zo)|s55\\/|sa(ge|ma|mm|ms|ny|va)|sc(01|h\\-|oo|p\\-)|sdk\\/|se(c(\\-|0|1)|47|mc|nd|ri)|sgh\\-|shar|sie(\\-|m)|sk\\-0|sl(45|id)|sm(al|ar|b3|it|t5)|so(ft|ny)|sp(01|h\\-|v\\-|v )|sy(01|mb)|t2(18|50)|t6(00|10|18)|ta(gt|lk)|tcl\\-|tdg\\-|tel(i|m)|tim\\-|t\\-mo|to(pl|sh)|ts(70|m\\-|m3|m5)|tx\\-9|up(\\.b|g1|si)|utst|v400|v750|veri|vi(rg|te)|vk(40|5[0-3]|\\-v)|vm40|voda|vulc|vx(52|53|60|61|70|80|81|83|85|98)|w3c(\\-| )|webc|whit|wi(g |nc|nw)|wmlb|wonu|x700|xda(\\-|2|g)|yas\\-|your|zeto|zte\\-",  # noqa: E501
            re.I | re.M)

        return reg_b.search(user_agent) is not None or reg_v.search(user_agent[0:4]) is not None

    #
    # HTTP variable processing
    #

    @contextmanager
    def stashed_vars(self):
        # type: () -> Iterator[None]
        saved_vars = dict(self.request.itervars())
        try:
            yield
        finally:
            self.request.del_vars()
            for varname, value in saved_vars.items():
                self.request.set_var(varname, value)

    def del_var_from_env(self, varname):
        # type: (str) -> None
        # HACKY WORKAROUND, REMOVE WHEN NO LONGER NEEDED
        # We need to get rid of query-string entries which can contain secret information.
        # As this is the only location where these are stored on the WSGI environment this
        # should be enough.
        # See also cmk.gui.globals:RequestContext
        # Filter the variables even if there are multiple copies of them (this is allowed).
        decoded_qs = [
            (key, value) for key, value in self.request.args.items(multi=True) if key != varname
        ]
        self.request.environ['QUERY_STRING'] = six.moves.urllib.parse.urlencode(decoded_qs)
        # We remove the form entry. As this entity is never copied it will be modified within
        # it's cache.
        dict.pop(self.request.form, varname, None)
        # We remove the __dict__ entries to allow @cached_property to reload them from
        # the environment. The rest of the request object stays the same.
        self.request.__dict__.pop('args', None)
        self.request.__dict__.pop('values', None)

    def get_item_input(self, varname, collection):
        # type: (str, Mapping[str, Value]) -> Tuple[Value, str]
        """Helper to get an item from the given collection
        Raises a MKUserError() in case the requested item is not available."""
        item = self.request.get_ascii_input(varname)
        if item not in collection:
            raise MKUserError(varname, _("The requested item %s does not exist") % item)
        assert item is not None
        return collection[item], item

    # TODO: Invalid default URL is not validated. Should we do it?
    # TODO: This is only protecting against some not allowed URLs but does not
    #       really verify that this is some kind of URL.
    def get_url_input(self, varname, deflt=None):
        # type: (str, Optional[str]) -> str
        """Helper function to retrieve a URL from HTTP parameters

        This is mostly used to the "back url" which can then be used to create
        a link to the previous page. For this kind of functionality it is
        necessary to restrict the URLs to prevent different attacks on users.

        In case the parameter is not given or is not valid the deflt URL will
        be used. In case no deflt URL is given a MKUserError() is raised.
        """
        if not self.request.has_var(varname):
            if deflt is not None:
                return deflt
            raise MKUserError(varname, _("The parameter \"%s\" is missing.") % varname)

        url = self.request.var(varname)
        assert url is not None

        if not utils.is_allowed_url(url):
            if deflt:
                return deflt
            raise MKUserError(varname, _("The parameter \"%s\" is not a valid URL.") % varname)

        return url

    def get_request(self, exclude_vars=None):
        # type: (Optional[List[str]]) -> Dict[Text, Any]
        """Returns a dictionary containing all parameters the user handed over to this request.

        The concept is that the user can either provide the data in a single "request" variable,
        which contains the request data encoded as JSON, or provide multiple GET/POST vars which
        are then used as top level entries in the request object.
        """

        if exclude_vars is None:
            exclude_vars = []

        if self.request.var("request_format") == "python":
            try:
                python_request = self.request.var("request", "{}")
                assert python_request is not None
                request = ast.literal_eval(python_request)
            except (SyntaxError, ValueError) as e:
                raise MKUserError(
                    "request",
                    _("Failed to parse Python request: '%s': %s") % (python_request, e))
        else:
            try:
                json_request = self.request.var("request", "{}")
                assert json_request is not None
                request = json.loads(json_request)
                request["request_format"] = "json"
            except ValueError as e:  # Python3: json.JSONDecodeError
                raise MKUserError("request",
                                  _("Failed to parse JSON request: '%s': %s") % (json_request, e))

        for key, val in self.request.itervars():
            if key not in ["request", "output_format"] + exclude_vars:
                request[key] = ensure_unicode(val) if isinstance(val, bytes) else val

        return request

    #
    # Transaction IDs
    #

    # TODO: Cleanup all call sites to self.transaction_manager.*
    def transaction_valid(self):
        # type: () -> bool
        return self.transaction_manager.transaction_valid()

    # TODO: Cleanup all call sites to self.transaction_manager.*
    def is_transaction(self):
        # type: () -> bool
        return self.transaction_manager.is_transaction()

    # TODO: Cleanup all call sites to self.transaction_manager.*
    def check_transaction(self):
        # type: () -> bool
        return self.transaction_manager.check_transaction()

    #
    # Encoding
    #

    # TODO: Cleanup all call sites to self.encoder.*
    def urlencode_vars(self, vars_):
        # type: (List[Tuple[str, Union[None, int, str, Text]]]) -> str
        return self.encoder.urlencode_vars(vars_)

    # TODO: Cleanup all call sites to self.encoder.*
    def urlencode(self, value):
        # type: (Union[None, str, Text]) -> str
        return self.encoder.urlencode(value)

    #
    # output funnel
    #

    def write(self, text):
        # type: (OutputFunnelInput) -> None
        self.output_funnel.write(text)

    def write_binary(self, data):
        # type: (bytes) -> None
        self.output_funnel.write_binary(data)

    @contextmanager
    def plugged(self):
        # type: () -> Iterator[None]
        with self.output_funnel.plugged():
            yield

    def drain(self):
        # type: () -> Text
        return self.output_funnel.drain()

    #
    # Timeout handling
    #

    def enable_request_timeout(self):
        # type: () -> None
        self.timeout_manager.enable_timeout(self.request.request_timeout)

    def disable_request_timeout(self):
        # type: () -> None
        self.timeout_manager.disable_timeout()

    #
    # Content Type
    #

    def set_output_format(self, f):
        # type: (str) -> None
        if f not in OUTPUT_FORMAT_MIME_TYPES:
            raise MKGeneralException(_("Unsupported context type '%s'") % f)

        self.output_format = f
        self.response.set_content_type(OUTPUT_FORMAT_MIME_TYPES[f])

    def is_api_call(self):
        # type: () -> bool
        return self.output_format != "html"

    #
    # Other things
    #

    def measure_time(self, name):
        # type: (str) -> None
        self.times.setdefault(name, 0.0)
        now = time.time()
        elapsed = now - self.last_measurement
        self.times[name] += elapsed
        self.last_measurement = now

    def is_mobile(self):
        # type: () -> bool
        return self.mobile

    def set_page_context(self, c):
        # type: (VisualContext) -> None
        self.page_context = c

    def set_link_target(self, framename):
        # type: (str) -> None
        self.link_target = framename

    def set_focus(self, varname):
        # type: (str) -> None
        self.focus_object = (self.form_name, varname)

    def set_focus_by_id(self, dom_id):
        # type: (str) -> None
        self.focus_object = dom_id

    def set_render_headfoot(self, render):
        # type: (bool) -> None
        self.render_headfoot = render

    def set_browser_reload(self, secs):
        # type: (float) -> None
        self.browser_reload = secs

    def set_browser_redirect(self, secs, url):
        # type: (float, str) -> None
        self.browser_reload = secs
        self.browser_redirect = url

    def clear_default_javascript(self):
        # type: () -> None
        del self._default_javascripts[:]

    def add_default_javascript(self, name):
        # type: (str) -> None
        if name not in self._default_javascripts:
            self._default_javascripts.append(name)

    def immediate_browser_redirect(self, secs, url):
        # type: (float, str) -> None
        self.javascript("cmk.utils.set_reload(%s, '%s');" % (secs, url))

    def add_body_css_class(self, cls):
        # type: (str) -> None
        self._body_classes.append(cls)

    def add_status_icon(self, img, tooltip, url=None):
        # type: (str, Text, Optional[str]) -> None
        if url:
            self.status_icons[img] = tooltip, url
        else:
            self.status_icons[img] = tooltip

    def final_javascript(self, code):
        # type: (str) -> None
        self.final_javascript_code += code + "\n"

    def reload_sidebar(self):
        # type: () -> None
        if not self.request.has_var("_ajaxid"):
            self.write_html(self.render_reload_sidebar())

    def render_reload_sidebar(self):
        # type: () -> HTML
        return self.render_javascript("cmk.utils.reload_sidebar()")

    def finalize(self):
        # type: () -> None
        """Finish the HTTP request processing before handing over to the application server"""
        self.transaction_manager.store_new()
        self.disable_request_timeout()

    #
    # Messages
    #

    def show_message(self, msg):
        # type: (HTMLMessageInput) -> None
        self.write(self._render_message(msg, 'message'))

    def show_error(self, msg):
        # type: (HTMLMessageInput) -> None
        self.write(self._render_message(msg, 'error'))

    def show_warning(self, msg):
        # type: (HTMLMessageInput) -> None
        self.write(self._render_message(msg, 'warning'))

    def render_message(self, msg):
        # type: (HTMLMessageInput) -> HTML
        return self._render_message(msg, 'message')

    def render_error(self, msg):
        # type: (HTMLMessageInput) -> HTML
        return self._render_message(msg, 'error')

    def render_warning(self, msg):
        # type: (HTMLMessageInput) -> HTML
        return self._render_message(msg, 'warning')

    # obj might be either a string (str or unicode) or an exception object
    def _render_message(self, msg, what='message'):
        # type: (HTMLMessageInput, str) -> HTML
        if what == 'message':
            cls = 'success'
            prefix = _('MESSAGE')
        elif what == 'warning':
            cls = 'warning'
            prefix = _('WARNING')
        else:
            cls = 'error'
            prefix = _('ERROR')

        code = HTML()

        if self.output_format == "html":
            code += self.render_div(self.render_text(msg), class_=cls)
            if self.mobile:
                code += self.render_center(code)
        else:
            code += self.render_text('%s: %s\n' % (prefix, escaping.strip_tags(msg)))

        return code

    def show_localization_hint(self):
        # type: () -> None
        url = "wato.py?mode=edit_configvar&varname=user_localizations"
        self.show_message(
            self.render_sup("*") + _("These texts may be localized depending on the users' "
                                     "language. You can configure the localizations %s.") %
            self.render_a("in the global settings", href=url))

    def del_language_cookie(self):
        # type: () -> None
        self.response.delete_cookie("language")

    def set_language_cookie(self, lang):
        # type: (Optional[str]) -> None
        cookie_lang = self.request.cookie("language")
        if cookie_lang == lang:
            return
        if lang is None:
            self.del_language_cookie()
        else:
            self.response.set_http_cookie("language", lang)

    def help(self, text):
        # type: (Union[None, HTML, Text]) -> None
        """Embed help box, whose visibility is controlled by a global button in the page.

        You may add macros like this to the help texts to create links to the user
        manual: [cms_piggyback|Piggyback chapter].
        """
        self.write_html(self.render_help(text))

    def render_help(self, text):
        # type: (Union[None, HTML, Text]) -> HTML
        if isinstance(text, HTML):
            text = "%s" % text

        if not text:
            return HTML("")

        stripped = text.strip()
        if not stripped:
            return HTML("")

        help_text = self._resolve_help_text_macros(stripped)

        self.enable_help_toggle()
        style = "display:%s;" % ("block" if config.user.show_help else "none")
        return self.render_div(HTML(help_text), class_="help", style=style)

    def _resolve_help_text_macros(self, text):
        # type: (Text) -> Text
        if config.user.language == "de":
            cmk_base_url = "https://checkmk.de"
        else:
            cmk_base_url = "https://checkmk.com"
        return re.sub(r"\[([a-z0-9_-]+)(#[a-z0-9_-]+|)\|([^\]]+)\]",
                      "<a href=\"%s/\\1.html\\2\" target=\"_blank\">\\3</a>" % cmk_base_url, text)

    def enable_help_toggle(self):
        # type: () -> None
        self.have_help = True

    #
    # Debugging, diagnose and logging
    #

    def debug(self, *x):
        # type: (*Any) -> None
        for element in x:
            try:
                formatted = pprint.pformat(element)
            except UnicodeDecodeError:
                formatted = repr(element)
            self.write(self.render_pre(formatted))

    #
    # URL building
    #

    def makeuri(self, addvars, remove_prefix=None, filename=None, delvars=None):
        # type: (HTTPVariables, Optional[str], Optional[str], Optional[List[str]]) -> str
        new_vars = [nv[0] for nv in addvars]
        vars_ = [(v, val)
                 for v, val in self.request.itervars()
                 if v[0] != "_" and v not in new_vars and (not delvars or v not in delvars)
                ]  # type: HTTPVariables
        if remove_prefix is not None:
            vars_ = [i for i in vars_ if not i[0].startswith(remove_prefix)]
        vars_ = vars_ + addvars
        if filename is None:
            filename = self.urlencode(self.myfile) + ".py"
        if vars_:
            return filename + "?" + self.urlencode_vars(vars_)
        return filename

    def makeuri_contextless(self, vars_, filename=None):
        # type: (HTTPVariables, Optional[str]) -> str
        if not filename:
            assert self.myfile is not None
            filename = self.myfile + ".py"
        if vars_:
            return filename + "?" + self.urlencode_vars(vars_)
        return filename

    def makeactionuri(self, addvars, filename=None, delvars=None):
        # type: (HTTPVariables, Optional[str], Optional[List[str]]) -> str
        return self.makeuri(addvars + [("_transid", self.transaction_manager.get())],
                            filename=filename,
                            delvars=delvars)

    def makeactionuri_contextless(self, addvars, filename=None):
        # type: (HTTPVariables, Optional[str]) -> str
        return self.makeuri_contextless(addvars + [("_transid", self.transaction_manager.get())],
                                        filename=filename)

    #
    # HTML heading and footer rendering
    #

    def default_html_headers(self):
        # type: () -> None
        self.meta(httpequiv="Content-Type", content="text/html; charset=utf-8")
        self.write_html(
            self._render_start_tag('link',
                                   rel="shortcut icon",
                                   href="themes/%s/images/favicon.ico" % self._theme,
                                   type_="image/ico",
                                   close_tag=True))

    def _head(self, title, javascripts=None):
        # type: (Text, Optional[List[str]]) -> None
        javascripts = javascripts if javascripts else []

        self.open_head()

        self.default_html_headers()
        self.title(title)

        # If the variable _link_target is set, then all links in this page
        # should be targetted to the HTML frame named by _link_target. This
        # is e.g. useful in the dash-board
        if self.link_target:
            self.base(target=self.link_target)

        fname = self._css_filename_for_browser("themes/%s/theme" % self._theme)
        if fname is not None:
            self.stylesheet(fname)

        self._add_custom_style_sheet()

        # Load all scripts
        for js in self._default_javascripts + javascripts:
            filename_for_browser = self.javascript_filename_for_browser(js)
            if filename_for_browser:
                self.javascript_file(filename_for_browser)

        if self.browser_reload != 0.0:
            if self.browser_redirect != '':
                self.javascript('cmk.utils.set_reload(%s, \'%s\')' %
                                (self.browser_reload, self.browser_redirect))
            else:
                self.javascript('cmk.utils.set_reload(%s)' % (self.browser_reload))

        self.close_head()

    def _add_custom_style_sheet(self):
        # type: () -> None
        for css in self._plugin_stylesheets():
            self.write('<link rel="stylesheet" type="text/css" href="css/%s">\n' % css)

        if config.custom_style_sheet:
            self.write('<link rel="stylesheet" type="text/css" href="%s">\n' %
                       config.custom_style_sheet)

        if self._theme == "classic" and cmk_version.is_managed_edition():
            import cmk.gui.cme.gui_colors as gui_colors  # pylint: disable=no-name-in-module
            gui_colors.GUIColors().render_html()

    def _plugin_stylesheets(self):
        # type: () -> Set[str]
        plugin_stylesheets = set([])
        for directory in [
                Path(cmk.utils.paths.web_dir, "htdocs", "css"),
                cmk.utils.paths.local_web_dir / "htdocs" / "css",
        ]:
            if directory.exists():
                for entry in directory.iterdir():
                    if entry.suffix == ".css":
                        plugin_stylesheets.add(entry.name)
        return plugin_stylesheets

    # Make the browser load specified javascript files. We have some special handling here:
    # a) files which can not be found shal not be loaded
    # b) in OMD environments, add the Check_MK version to the version (prevents update problems)
    # c) load the minified javascript when not in debug mode
    def javascript_filename_for_browser(self, jsname):
        # type: (str) -> Optional[str]
        filename_for_browser = None
        rel_path = "/share/check_mk/web/htdocs/js"
        if self.enable_debug:
            min_parts = ["", "_min"]
        else:
            min_parts = ["_min", ""]

        for min_part in min_parts:
            path_pattern = cmk.utils.paths.omd_root + "%s" + rel_path + "/" + jsname + min_part + ".js"
            if os.path.exists(path_pattern % "") or os.path.exists(path_pattern % "/local"):
                filename_for_browser = 'js/%s%s-%s.js' % (jsname, min_part, cmk_version.__version__)
                break

        return filename_for_browser

    def _css_filename_for_browser(self, css):
        # type: (str) -> Optional[str]
        rel_path = "/share/check_mk/web/htdocs/" + css + ".css"
        if os.path.exists(cmk.utils.paths.omd_root + rel_path) or \
            os.path.exists(cmk.utils.paths.omd_root + "/local" + rel_path):
            return '%s-%s.css' % (css, cmk_version.__version__)
        return None

    def html_head(self, title, javascripts=None, force=False):
        # type: (Text, Optional[List[str]], bool) -> None
        force_new_document = force  # for backward stability and better readability

        if force_new_document:
            self._header_sent = False

        if not self._header_sent:
            self.write_html(HTML('<!DOCTYPE HTML>\n'))
            self.open_html()
            self._head(title, javascripts)
            self._header_sent = True

    def header(self,
               title=u'',
               javascripts=None,
               force=False,
               show_body_start=True,
               show_top_heading=True):
        # type: (Text, Optional[List[str]], bool, bool, bool) -> None
        if self.output_format == "html":
            if not self._header_sent:
                if show_body_start:
                    self.body_start(title, javascripts=javascripts, force=force)

                self._header_sent = True

                if self.render_headfoot and show_top_heading:
                    self.top_heading(title)

    def body_start(self, title=u'', javascripts=None, force=False):
        # type: (Text, Optional[List[str]], bool) -> None
        self.html_head(title, javascripts, force)
        self.open_body(class_=self._get_body_css_classes())

    def _get_body_css_classes(self):
        # type: () -> List[str]
        if self.screenshotmode:
            return self._body_classes + ["screenshotmode"]
        return self._body_classes

    def html_foot(self):
        # type: () -> None
        self.close_html()

    def top_heading(self, title):
        # type: (Text) -> None
        if not isinstance(config.user, config.LoggedInNobody):
            login_text = "<b>%s</b> (%s" % (config.user.id, "+".join(config.user.role_ids))
            if self.enable_debug:
                if config.user.language:
                    login_text += "/%s" % config.user.language
            login_text += ')'
        else:
            login_text = _("not logged in")
        self.top_heading_left(title)

        self.write('<td style="min-width:240px" class=right><span id=headinfo></span>%s &nbsp; ' %
                   login_text)
        if config.pagetitle_date_format:
            self.write(' &nbsp; <b id=headerdate format="%s"></b>' % config.pagetitle_date_format)
        self.write(' <b id=headertime></b>')
        self.top_heading_right()

    def top_heading_left(self, title):
        # type: (Text) -> None
        self.open_table(class_="header")
        self.open_tr()
        self.open_td(width="*", class_="heading")
        # HTML() is needed here to prevent a double escape when we do  self._escape_attribute
        # here and self.a() escapes the content (with permissive escaping) again. We don't want
        # to handle "title" permissive.
        html_title = HTML(escaping.escape_attribute(title))
        self.a(html_title,
               href="#",
               onfocus="if (this.blur) this.blur();",
               onclick="this.innerHTML=\'%s\'; document.location.reload();" % _("Reloading..."))
        self.close_td()

    def top_heading_right(self):
        # type: () -> None
        cssclass = "active" if config.user.show_help else "passive"

        self.icon_button(None,
                         _("Toggle context help texts"),
                         "help",
                         id_="helpbutton",
                         onclick="cmk.help.toggle()",
                         style="display:none",
                         cssclass=cssclass)
        self.open_a(href="https://checkmk.com", class_="head_logo", target="_blank")
        self.img(src="themes/%s/images/logo_cmk_small.png" % self._theme)
        self.close_a()
        self.close_td()
        self.close_tr()
        self.close_table()
        self.hr(class_="header")

        if self.enable_debug:
            self._dump_get_vars()

    def footer(self, show_footer=True, show_body_end=True):
        # type: (bool, bool) -> None
        if self.output_format == "html":
            if show_footer:
                self.bottom_footer()

            if show_body_end:
                self.body_end()

    def bottom_footer(self):
        # type: () -> None
        if self._header_sent:
            self.bottom_focuscode()
            if self.render_headfoot:
                self.open_table(class_="footer")
                self.open_tr()

                self.open_td(class_="left")
                self._write_status_icons()
                self.close_td()

                self.td('', class_="middle")

                self.open_td(class_="right")
                content = _("refresh: %s secs") % self.render_div("%0.2f" % self.browser_reload,
                                                                  id_="foot_refresh_time")
                style = "display:inline-block;" if self.browser_reload else "display:none;"
                self.div(HTML(content), id_="foot_refresh", style=style)
                self.close_td()

                self.close_tr()
                self.close_table()

    def bottom_focuscode(self):
        # type: () -> None
        if self.focus_object:
            if isinstance(self.focus_object, tuple):
                formname, varname = self.focus_object
                assert formname is not None
                obj_ident = formname + "." + varname
            else:
                obj_ident = "getElementById(\"%s\")" % self.focus_object

            js_code = "<!--\n" \
                      "var focus_obj = document.%s;\n" \
                      "if (focus_obj) {\n" \
                      "    focus_obj.focus();\n" \
                      "    if (focus_obj.select)\n" \
                      "        focus_obj.select();\n" \
                      "}\n" \
                      "// -->\n" % obj_ident
            self.javascript(js_code)

    def focus_here(self):
        # type: () -> None
        self.a("", href="#focus_me", id_="focus_me")
        self.set_focus_by_id("focus_me")

    def body_end(self):
        # type: () -> None
        if self.have_help:
            self.javascript("cmk.help.enable();")
        if self.final_javascript_code:
            self.javascript(self.final_javascript_code)
        self.javascript("cmk.visibility_detection.initialize();")
        self.close_body()
        self.close_html()

    #
    # HTML form rendering
    #

    def begin_form(self, name, action=None, method="GET", onsubmit=None, add_transid=True):
        # type: (str, str, str, Optional[str], bool) -> None
        self.form_vars = []
        if action is None:
            assert self.myfile is not None
            action = self.myfile + ".py"
        self.current_form = name
        self.open_form(id_="form_%s" % name,
                       name=name,
                       class_=name,
                       action=action,
                       method=method,
                       onsubmit=onsubmit,
                       enctype="multipart/form-data" if method.lower() == "post" else None)
        self.hidden_field("filled_in", name, add_var=True)
        if add_transid:
            self.hidden_field("_transid", str(self.transaction_manager.get()))
        self.form_name = name

    def end_form(self):
        # type: () -> None
        self.close_form()
        self.form_name = None

    def in_form(self):
        # type: () -> bool
        return self.form_name is not None

    def prevent_password_auto_completion(self):
        # type: () -> None
        # These fields are not really used by the form. They are used to prevent the browsers
        # from filling the default password and previous input fields in the form
        # with password which are eventually saved in the browsers password store.
        self.input(name=None, type_="text", style="display:none;")
        self.input(name=None, type_="password", style="display:none;")

    # Needed if input elements are put into forms without the helper
    # functions of us. TODO: Should really be removed and cleaned up!
    def add_form_var(self, varname):
        # type: (str) -> None
        self.form_vars.append(varname)

    # Beware: call this method just before end_form(). It will
    # add all current non-underscored HTML variables as hiddedn
    # field to the form - *if* they are not used in any input
    # field. (this is the reason why you must not add any further
    # input fields after this method has been called).
    def hidden_fields(self, varlist=None, add_action_vars=False):
        # type: (List[str], bool) -> None
        if varlist is not None:
            for var in varlist:
                self.hidden_field(var, self.request.var(var, ""))
        else:  # add *all* get variables, that are not set by any input!
            for var, _val in self.request.itervars():
                if var not in self.form_vars and \
                    (var[0] != "_" or add_action_vars):  # and var != "filled_in":
                    self.hidden_field(var, self.request.get_unicode_input(var))

    def hidden_field(self, var, value, id_=None, add_var=False, class_=None):
        # type: (str, HTMLTagValue, str, bool, CSSSpec) -> None
        self.write_html(
            self.render_hidden_field(var=var, value=value, id_=id_, add_var=add_var, class_=class_))

    def render_hidden_field(self, var, value, id_=None, add_var=False, class_=None):
        # type: (str, HTMLTagValue, str, bool, CSSSpec) -> HTML
        if value is None:
            return HTML("")
        if add_var:
            self.add_form_var(var)
        return self.render_input(
            name=var,
            type_="hidden",
            id_=id_,
            value=value,
            class_=class_,
            autocomplete="off",
        )

    #
    # Form submission and variable handling
    #

    def do_actions(self):
        # type: () -> bool
        return self.request.var("_do_actions") not in ["", None, _("No")]

    # Check if the given form is currently filled in (i.e. we display
    # the form a second time while showing value typed in at the first
    # time and complaining about invalid user input)
    def form_submitted(self, form_name=None):
        # type: (Optional[str]) -> bool
        if form_name is None:
            return self.request.has_var("filled_in")
        return self.request.var("filled_in") == form_name

    # Get value of checkbox. Return True, False or None. None means
    # that no form has been submitted. The problem here is the distintion
    # between False and None. The browser does not set the variables for
    # Checkboxes that are not checked :-(
    def get_checkbox(self, varname):
        # type: (str) -> Optional[bool]
        if self.request.has_var(varname):
            return bool(self.request.var(varname))
        if self.form_submitted(self.form_name):
            return False  # Form filled in but variable missing -> Checkbox not checked
        return None

    #
    # Button elements
    #

    def button(self, varname, title, cssclass=None, style=None, help_=None):
        # type: (str, Text, Optional[str], Optional[str], Optional[Text]) -> None
        self.write_html(self.render_button(varname, title, cssclass, style, help_=help_))

    def render_button(self, varname, title, cssclass=None, style=None, help_=None):
        # type: (str, Text, Optional[str], Optional[str], Optional[Text]) -> HTML
        self.add_form_var(varname)
        return self.render_input(name=varname,
                                 type_="submit",
                                 id_=varname,
                                 class_=["button", cssclass if cssclass else None],
                                 value=title,
                                 title=help_,
                                 style=style)

    def buttonlink(self,
                   href,
                   text,
                   add_transid=False,
                   obj_id=None,
                   style=None,
                   title=None,
                   disabled=None,
                   class_=None):
        # type: (str, Text, bool, Optional[str], Optional[str], Optional[Text], Optional[str], CSSSpec) -> None
        if add_transid:
            href += "&_transid=%s" % self.transaction_manager.get()

        if not obj_id:
            obj_id = utils.gen_id()

        # Same API as other elements: class_ can be a list or string/None
        css_classes = ["button", "buttonlink"]  # type: List[Union[str, None]]
        if class_:
            if not isinstance(class_, list):
                css_classes.append(class_)
            else:
                css_classes.extend(class_)

        self.input(name=obj_id,
                   type_="button",
                   id_=obj_id,
                   class_=css_classes,
                   value=text,
                   style=style,
                   title=title,
                   disabled=disabled,
                   onclick="location.href=\'%s\'" % href)

    # TODO: Refactor the arguments. It is only used in views/wato
    def toggle_button(self,
                      id_,
                      isopen,
                      icon,
                      title,
                      hidden=False,
                      disabled=False,
                      onclick=None,
                      is_context_button=True):
        # type: (str, bool, str, Text, bool, bool, Optional[str], bool) -> None
        if is_context_button:
            self.begin_context_buttons()  # TODO: Check all calls. If done before, remove this!

        if not onclick and not disabled:
            onclick = "cmk.views.toggle_form(this.parentNode, '%s');" % id_

        if disabled:
            state = "off" if disabled else "on"
            cssclass = ""
            title = ""
        else:
            state = "on"
            if isopen:
                cssclass = "down"
            else:
                cssclass = "up"

        self.open_div(
            id_="%s_%s" % (id_, state),
            class_=["togglebutton", state, icon, cssclass],
            title=title,
            style='display:none' if hidden else None,
        )
        self.open_a("javascript:void(0)", onclick=onclick)
        self.icon(title=None, icon=icon)
        self.close_a()
        self.close_div()

    def empty_icon_button(self):
        # type: () -> None
        self.write(self.render_icon("trans", cssclass="iconbutton trans"))

    def disabled_icon_button(self, icon):
        # type: (str) -> None
        self.write(self.render_icon(icon, cssclass="iconbutton"))

    # TODO: Cleanup to use standard attributes etc.
    def jsbutton(self,
                 varname,
                 text,
                 onclick,
                 style='',
                 cssclass=None,
                 title="",
                 disabled=False,
                 class_=None):
        # type: (str, Text, str, str, Optional[str], Text, bool, CSSSpec) -> None
        if not isinstance(class_, list):
            class_ = [class_]
        # TODO: Investigate why mypy complains about the latest argument
        classes = ["button", cssclass] + cast(List[Optional[str]], class_)

        if disabled:
            class_.append("disabled")
            disabled_arg = ""  # type: Optional[str]
        else:
            disabled_arg = None

        # autocomplete="off": Is needed for firefox not to set "disabled="disabled" during page reload
        # when it has been set on a page via javascript before. Needed for WATO activate changes page.
        self.input(name=varname,
                   type_="button",
                   id_=varname,
                   class_=classes,
                   autocomplete="off",
                   onclick=onclick,
                   style=style,
                   disabled=disabled_arg,
                   value=text,
                   title=title)

    #
    # Other input elements
    #

    def user_error(self, e):
        # type: (MKUserError) -> None
        assert isinstance(e, MKUserError), "ERROR: This exception is not a user error!"
        self.open_div(class_="error")
        self.write("%s" % e.message)
        self.close_div()
        self.add_user_error(e.varname, e)

    # user errors are used by input elements to show invalid input
    def add_user_error(self, varname, msg_or_exc):
        # type: (Optional[str], Union[Text, str, Exception]) -> None
        if isinstance(msg_or_exc, Exception):
            message = u"%s" % msg_or_exc  # type: Text
        else:
            message = ensure_unicode(msg_or_exc)

        # TODO: Find the multiple varname call sites and clean this up
        if isinstance(varname, list):
            for v in varname:
                self.add_user_error(v, message)
        else:
            self.user_errors[varname] = message

    def has_user_errors(self):
        # type: () -> bool
        return len(self.user_errors) > 0

    def show_user_errors(self):
        # type: () -> None
        if self.has_user_errors():
            self.open_div(class_="error")
            self.write('<br>'.join(self.user_errors.values()))
            self.close_div()

    def text_input(
        self,
        varname,  # type: str
        default_value=u"",  # type: Text
        cssclass="text",  # type: str
        size=None,  # type: Union[None, str, int]
        label=None,  # type: Optional[Text]
        id_=None,  # type: str
        submit=None,  # type: Optional[str]
        try_max_width=False,  # type: bool
        read_only=False,  # type: bool
        autocomplete=None,  # type: Optional[str]
        style=None,  # type: Optional[str]
        omit_css_width=False,  # type: bool
        type_=None,  # type: Optional[str]
        onkeyup=None,  # type: Optional[Text]
        onblur=None,  # type: Optional[str]
        placeholder=None,  # type: Optional[Text]
        data_world=None,  # type: Optional[str]
        data_max_labels=None  # type: Optional[int]
    ):
        # type: (...) -> None

        # Model
        error = self.user_errors.get(varname)
        value = self.request.get_unicode_input(varname, default_value)
        if not value:
            value = ""
        if error:
            self.set_focus(varname)
        self.form_vars.append(varname)

        # View
        style_size = None  # type: Optional[str]
        field_size = None  # type: Optional[str]
        if try_max_width:
            style_size = "width: calc(100% - 10px); "
            if size is not None:
                assert isinstance(size, int)
                cols = size
            else:
                cols = 16
            style_size += "min-width: %d.8ex; " % cols

        elif size is not None:
            if size == "max":
                style_size = "width: 100%;"
            else:
                assert isinstance(size, int)
                field_size = "%d" % (size + 1)
                if not omit_css_width and (style is None or
                                           "width:" not in style) and not self.mobile:
                    style_size = "width: %d.8ex;" % size

        attributes = {
            "class": cssclass,
            "id": ("ti_%s" % varname) if (submit or label) and not id_ else id_,
            "style": [style_size] + ([] if style is None else [style]),
            "size": field_size,
            "autocomplete": autocomplete,
            "readonly": "true" if read_only else None,
            "value": value,
            "onblur": onblur,
            "onkeyup": onkeyup,
            "onkeydown": ('cmk.forms.textinput_enter_submit(event, %s);' %
                          json.dumps(submit)) if submit else None,
            "placeholder": placeholder,
            "data-world": data_world,
            "data-max-labels": None if data_max_labels is None else str(data_max_labels),
        }  # type: HTMLTagAttributes

        if error:
            self.open_x(class_="inputerror")

        if label:
            assert id_ is not None
            self.label(label, for_=id_)

        input_type = "text" if type_ is None else type_
        assert isinstance(input_type, str)
        self.write_html(self.render_input(varname, type_=input_type, **attributes))

        if error:
            self.close_x()

    def status_label(self, content, status, title, **attrs):
        # type: (HTMLContent, str, Text, **HTMLTagAttributeValue) -> None
        """Shows a colored badge with text (used on WATO activation page for the site status)"""
        self.status_label_button(content, status, title, onclick=None, **attrs)

    def status_label_button(self, content, status, title, onclick, **attrs):
        # type: (HTMLContent, str, Text, Optional[str], **HTMLTagAttributeValue) -> None
        """Shows a colored button with text (used in site and customer status snapins)"""
        button_cls = "button" if onclick else None
        self.div(content,
                 title=title,
                 class_=["status_label", button_cls, status],
                 onclick=onclick,
                 **attrs)

    def toggle_switch(self, enabled, help_txt, class_=None, href="javascript:void(0)", **attrs):
        # type: (bool, Text, CSSSpec, str, **HTMLTagAttributeValue) -> None
        # Same API as other elements: class_ can be a list or string/None
        if not isinstance(class_, list):
            class_ = [class_]

        class_ += [
            "toggle_switch",
            "on" if enabled else "off",
        ]
        onclick = attrs.pop("onclick", None)

        self.open_div(class_=class_, **attrs)
        self.a(
            content=_("on") if enabled else _("off"),
            href=href,
            title=help_txt,
            onclick=onclick,
        )
        self.close_div()

    def password_input(self,
                       varname,
                       default_value="",
                       cssclass="text",
                       size=None,
                       label=None,
                       id_=None,
                       submit=None,
                       try_max_width=False,
                       read_only=False,
                       autocomplete=None):
        # type: (str, Text, str, Union[None, str, int], Optional[Text], str, Optional[str], bool, bool, Optional[str]) -> None
        self.text_input(varname,
                        default_value,
                        cssclass=cssclass,
                        size=size,
                        label=label,
                        id_=id_,
                        submit=submit,
                        type_="password",
                        try_max_width=try_max_width,
                        read_only=read_only,
                        autocomplete=autocomplete)

    def text_area(self, varname, deflt="", rows=4, cols=30, try_max_width=False, **attrs):
        # type: (str, Union[str, Text], int, int, bool, **HTMLTagAttributeValue) -> None

        value = self.request.get_unicode_input(varname, deflt)
        error = self.user_errors.get(varname)

        self.form_vars.append(varname)
        if error:
            self.set_focus(varname)

        style = "width: %d.8ex;" % cols
        if try_max_width:
            style += "width: calc(100%% - 10px); min-width: %d.8ex;" % cols
        attrs["style"] = style
        attrs["rows"] = str(rows)
        attrs["cols"] = str(cols)
        attrs["name"] = varname

        # Fix handling of leading newlines (https://www.w3.org/TR/html5/syntax.html#element-restrictions)
        #
        # """
        # A single newline may be placed immediately after the start tag of pre
        # and textarea elements. This does not affect the processing of the
        # element. The otherwise optional newline must be included if the
        # element’s contents themselves start with a newline (because otherwise
        # the leading newline in the contents would be treated like the
        # optional newline, and ignored).
        # """
        if value and value.startswith("\n"):
            value = "\n" + value

        if error:
            self.open_x(class_="inputerror")
        self.write_html(self._render_element("textarea", value, **attrs))
        if error:
            self.close_x()

    # Choices is a list pairs of (key, title). They keys of the choices
    # and the default value must be of type None, str or unicode.
    def dropdown(
        self,
        varname,  # type: str
        choices,  # type: Choices
        deflt='',  # type: DefaultChoice
        ordered=False,  # type: bool
        label=None,  # type: Optional[Text]
        class_=None,  # type: CSSSpec
        size=1,  # type: int
        read_only=False,  # type: bool
        **attrs  # type: HTMLTagAttributeValue
    ):
        # type: (...) -> None
        current = self.request.get_unicode_input(varname, deflt)
        error = self.user_errors.get(varname)
        if varname:
            self.form_vars.append(varname)

        chs = list(choices)
        if ordered:
            # Sort according to display texts, not keys
            chs.sort(key=lambda a: a[1].lower())

        if error:
            self.open_x(class_="inputerror")

        if read_only:
            attrs["disabled"] = "disabled"
            self.hidden_field(varname, current, add_var=False)

        if label:
            self.label(label, for_=varname)

        # Do not enable select2 for select fields that allow multiple
        # selections like the dual list choice valuespec
        if "multiple" not in attrs:
            css_classes = ["select2-enable"]  # type: List[Optional[str]]
        else:
            css_classes = []

        if isinstance(class_, list):
            css_classes.extend(class_)
        else:
            css_classes.append(class_)

        self.open_select(name=varname,
                         id_=varname,
                         label=label,
                         class_=css_classes,
                         size=str(size),
                         **attrs)
        for value, text in chs:
            # if both the default in choices and current was '' then selected depended on the order in choices
            selected = (value == current) or (not value and not current)
            self.option(text, value=value if value else "", selected="" if selected else None)
        self.close_select()
        if error:
            self.close_x()

    def icon_dropdown(self, varname, choices, deflt=""):
        # type: (str, List[Tuple[str, Text, str]], str) -> None
        current = self.request.var(varname, deflt)
        if varname:
            self.form_vars.append(varname)

        self.open_select(class_="icon", name=varname, id_=varname, size="1")
        for value, text, icon in choices:
            # if both the default in choices and current was '' then selected depended on the order in choices
            selected = (value == current) or (not value and not current)
            self.option(text,
                        value=value if value else "",
                        selected='' if selected else None,
                        style="background-image:url(themes/%s/images/icon_%s.png);" %
                        (self._theme, icon))
        self.close_select()

    def upload_file(self, varname):
        # type: (str) -> None
        error = self.user_errors.get(varname)
        if error:
            self.open_x(class_="inputerror")
        self.input(name=varname, type_="file")
        if error:
            self.close_x()
        self.form_vars.append(varname)

    # The confirm dialog is normally not a dialog which need to be protected
    # by a transid itselfs. It is only a intermediate step to the real action
    # But there are use cases where the confirm dialog is used during rendering
    # a normal page, for example when deleting a dashlet from a dashboard. In
    # such cases, the transid must be added by the confirm dialog.
    # add_header: A title can be given to make the confirm method render the HTML
    #             header when showing the confirm message.
    def confirm(self, msg, method="POST", action=None, add_transid=False, add_header=None):
        # type: (Union[Text, HTML], str, Optional[str], bool, Optional[str]) -> Optional[bool]
        if self.request.var("_do_actions") == _("No"):
            # User has pressed "No", now invalidate the unused transid
            self.check_transaction()
            return None  # None --> "No"

        if not self.request.has_var("_do_confirm"):
            if add_header:
                self.header(add_header)

            if self.mobile:
                self.open_center()
            self.open_div(class_="really")
            self.write_text(msg)
            # FIXME: When this confirms another form, use the form name from self.request.itervars()
            self.begin_form("confirm", method=method, action=action, add_transid=add_transid)
            self.hidden_fields(add_action_vars=True)
            self.button("_do_confirm", _("Yes!"), "really")
            self.button("_do_actions", _("No"), "")
            self.end_form()
            self.close_div()
            if self.mobile:
                self.close_center()

            return False  # False --> "Dialog shown, no answer yet"
        else:
            # Now check the transaction
            return True if self.check_transaction(
            ) else None  # True: "Yes", None --> Browser reload of "yes" page

    #
    # Radio groups
    #

    def begin_radio_group(self, horizontal=False):
        # type: (bool) -> None
        if self.mobile:
            attrs = {'data-type': "horizontal" if horizontal else None, 'data-role': "controlgroup"}
            self.write(self._render_start_tag("fieldset", close_tag=False, **attrs))

    def end_radio_group(self):
        # type: () -> None
        if self.mobile:
            self.write(self._render_end_tag("fieldset"))

    def radiobutton(self, varname, value, checked, label):
        # type: (str, str, bool, Optional[Text]) -> None
        self.form_vars.append(varname)

        if self.request.has_var(varname):
            checked = self.request.var(varname) == value

        id_ = "rb_%s_%s" % (varname, value) if label else None
        self.open_span(class_="radiobutton_group")
        self.input(name=varname,
                   type_="radio",
                   value=value,
                   checked='' if checked else None,
                   id_=id_)
        if label and id_:
            self.label(label, for_=id_)
        self.close_span()

    #
    # Checkbox groups
    #

    def begin_checkbox_group(self, horizonal=False):
        # type: (bool) -> None
        self.begin_radio_group(horizonal)

    def end_checkbox_group(self):
        # type: () -> None
        self.end_radio_group()

    def checkbox(self, varname, deflt=False, label='', id_=None, **add_attr):
        # type: (str, bool, HTMLContent, Optional[str], **HTMLTagAttributeValue) -> None
        self.write(self.render_checkbox(varname, deflt, label, id_, **add_attr))

    def render_checkbox(self, varname, deflt=False, label='', id_=None, **add_attr):
        # type: (str, bool, HTMLContent, Optional[str], **HTMLTagAttributeValue) -> HTML
        # Problem with checkboxes: The browser will add the variable
        # only to the URL if the box is checked. So in order to detect
        # whether we should add the default value, we need to detect
        # if the form is printed for the first time. This is the
        # case if "filled_in" is not set.
        value = self.get_checkbox(varname)
        if value is None:  # form not yet filled in
            value = deflt

        error = self.user_errors.get(varname)
        if id_ is None:
            id_ = "cb_%s" % varname

        add_attr["id"] = id_
        add_attr["CHECKED"] = '' if value else None

        code = self.render_input(name=varname, type_="checkbox", **add_attr) + self.render_label(
            label, for_=id_)
        code = self.render_span(code, class_="checkbox")

        if error:
            code = self.render_x(code, class_="inputerror")

        self.form_vars.append(varname)
        return code

    #
    # Foldable context
    #

    def begin_foldable_container(self,
                                 treename,
                                 id_,
                                 isopen,
                                 title,
                                 indent=True,
                                 first=False,
                                 icon=None,
                                 fetch_url=None,
                                 title_url=None,
                                 title_target=None):
        # type: (str, str, bool, HTMLContent, FoldingIndent, bool, Optional[str], Optional[str], Optional[str], Optional[str]) -> bool
        self.folding_indent = indent

        isopen = self.foldable_container_is_open(treename, id_, isopen)

        onclick = "cmk.foldable_container.toggle(%s, %s, %s)"\
                    % (json.dumps(treename), json.dumps(id_), json.dumps(fetch_url if fetch_url else ''))

        img_id = "treeimg.%s.%s" % (treename, id_)
        container_id = "tree.%s.%s" % (treename, id_)

        if indent == "nform":
            self.open_thead()
            self.open_tr(class_="heading")
            self.open_td(id_="nform.%s.%s" % (treename, id_), onclick=onclick, colspan=2)
            if icon:
                self.img(id_=img_id,
                         class_=["treeangle", "title"],
                         src="themes/%s/images/icon_%s.png" % (self._theme, icon))
            else:
                self.img(id_=img_id,
                         class_=["treeangle", "nform", "open" if isopen else "closed"],
                         src="themes/%s/images/tree_closed.png" % (self._theme),
                         align="absbottom")
            self.write_text(title)
            self.close_td()
            self.close_tr()
            self.close_thead()
            self.open_tbody(id_=container_id, class_=["open" if isopen else "closed"])
        else:
            self.open_div(class_="foldable")

            if not icon:
                self.img(id_=img_id,
                         class_=["treeangle", "open" if isopen else "closed"],
                         src="themes/%s/images/tree_closed.png" % (self._theme),
                         align="absbottom",
                         onclick=onclick)
            if isinstance(title, HTML):  # custom HTML code
                if icon:
                    self.img(class_=["treeangle", "title"],
                             src="themes/%s/images/icon_%s.png" % (self._theme, icon),
                             onclick=onclick)
                self.write_text(title)
                if indent != "form":
                    self.br()
            else:
                self.open_b(class_=["treeangle", "title"], onclick=None if title_url else onclick)
                if icon:
                    self.img(class_=["treeangle", "title"],
                             src="themes/%s/images/icon_%s.png" % (self._theme, icon))
                if title_url:
                    self.a(title, href=title_url, target=title_target)
                else:
                    self.write_text(title)
                self.close_b()
                self.br()

            indent_style = "padding-left: %dpx; " % (indent is True and 15 or 0)
            if indent == "form":
                self.close_td()
                self.close_tr()
                self.close_table()
                indent_style += "margin: 0; "
            self.open_ul(id_=container_id,
                         class_=["treeangle", "open" if isopen else "closed"],
                         style=indent_style)

        # give caller information about current toggling state (needed for nform)
        return isopen

    def end_foldable_container(self):
        # type: () -> None
        if self.folding_indent != "nform":
            self.close_ul()
            self.close_div()

    def foldable_container_is_open(self, treename, id_, isopen):
        # type: (str, str, bool) -> bool
        # try to get persisted state of tree
        tree_state = config.user.get_tree_states(treename)

        if id_ in tree_state:
            isopen = tree_state[id_] == "on"
        return isopen

    #
    # Context Buttons
    #

    def begin_context_buttons(self):
        # type: () -> None
        if not self._context_buttons_open:
            self.context_button_hidden = False
            self.open_div(class_="contextlinks")
            self._context_buttons_open = True

    def end_context_buttons(self):
        # type: () -> None
        if self._context_buttons_open:
            if self.context_button_hidden:
                self.open_div(title=_("Show all buttons"),
                              id="toggle",
                              class_=["contextlink", "short"])
                self.a("...", onclick='cmk.utils.unhide_context_buttons(this);', href='#')
                self.close_div()
            self.div("", class_="end")
            self.close_div()
        self._context_buttons_open = False

    def context_button(self,
                       title,
                       url,
                       icon=None,
                       hot=False,
                       id_=None,
                       bestof=None,
                       hover_title=None,
                       class_=None):
        # type: (Text, str, Optional[str], bool, Optional[str], Optional[int], Optional[Text], CSSSpec) -> None
        self._context_button(title,
                             url,
                             icon=icon,
                             hot=hot,
                             id_=id_,
                             bestof=bestof,
                             hover_title=hover_title,
                             class_=class_)

    def _context_button(self,
                        title,
                        url,
                        icon=None,
                        hot=False,
                        id_=None,
                        bestof=None,
                        hover_title=None,
                        class_=None):
        # type: (Text, str, Optional[str], bool, Optional[str], Optional[int], Optional[Text], CSSSpec) -> None
        title = escaping.escape_attribute(title)
        display = "block"
        if bestof:
            counts = config.user.button_counts
            weights = list(counts.items())
            weights.sort(key=lambda x: x[1])
            best = dict(weights[-bestof:])  # pylint: disable=invalid-unary-operand-type
            if id_ not in best:
                display = "none"
                self.context_button_hidden = True

        if not self._context_buttons_open:
            self.begin_context_buttons()

        css_classes = ["contextlink"]  # type: List[Optional[str]]
        if hot:
            css_classes.append("hot")
        if class_:
            if isinstance(class_, list):
                css_classes.extend(class_)
            else:
                css_classes.append(class_)

        self.open_div(class_=css_classes, id_=id_, style="display:%s;" % display)

        self.open_a(href=url,
                    title=hover_title,
                    onclick="cmk.utils.count_context_button(this);" if bestof else None)

        if icon:
            self.icon('', icon, cssclass="inline", middle=False)

        self.span(title)

        self.close_a()

        self.close_div()

    #
    # Floating Options
    #

    def begin_floating_options(self, div_id, is_open):
        # type: (str, bool) -> None
        self.open_div(id_=div_id,
                      class_=["view_form"],
                      style="display: none" if not is_open else None)
        self.open_table(class_=["filterform"], cellpadding="0", cellspacing="0", border="0")
        self.open_tr()
        self.open_td()

    def end_floating_options(self, reset_url=None):
        # type: (Optional[str]) -> None
        self.close_td()
        self.close_tr()
        self.open_tr()
        self.open_td()
        self.button("apply", _("Apply"), "submit")
        if reset_url:
            self.buttonlink(reset_url, _("Reset to defaults"))

        self.close_td()
        self.close_tr()
        self.close_table()
        self.close_div()

    def render_floating_option(self, name, height, varprefix, valuespec, value):
        # type: (str, str, str, ValueSpec, Any) -> None
        self.open_div(class_=["floatfilter", height, name])
        self.div(valuespec.title(), class_=["legend"])
        self.open_div(class_=["content"])
        valuespec.render_input(varprefix + name, value)
        self.close_div()
        self.close_div()

    #
    # HTML icon rendering
    #

    # FIXME: Change order of input arguments in one: icon and render_icon!!
    def icon(self, title, icon, middle=True, id_=None, cssclass=None, class_=None):
        # type: (Optional[Text], str, bool, Optional[str], Optional[str], CSSSpec) -> None
        self.write_html(
            self.render_icon(icon_name=icon,
                             title=title,
                             middle=middle,
                             id_=id_,
                             cssclass=cssclass,
                             class_=class_))

    def empty_icon(self):
        # type: () -> None
        self.write_html(self.render_icon("trans"))

    def render_icon(self, icon_name, title=None, middle=True, id_=None, cssclass=None, class_=None):
        # type: (str, Optional[Text], bool, Optional[str], Optional[str], CSSSpec) -> HTML
        classes = ["icon", cssclass]
        if isinstance(class_, list):
            classes.extend(class_)
        else:
            classes.append(class_)

        return self._render_start_tag(
            'img',
            close_tag=True,
            title=title,
            id_=id_,
            class_=classes,
            align='absmiddle' if middle else None,
            src=(icon_name if "/" in icon_name else self._detect_icon_path(icon_name)),
        )

    def _detect_icon_path(self, icon_name):
        # type: (str) -> str
        """Detect from which place an icon shall be used and return it's path relative to
 htdocs/

        Priority:
        1. In case a theme is active: themes/images/icon_[name].png in site local hierarchy
        2. In case a theme is active: themes/images/icon_[name].png in standard hierarchy
        3. images/icons/[name].png in site local hierarchy
        4. images/icons/[name].png in standard hierarchy
        """

        rel_path = "share/check_mk/web/htdocs/themes/%s/images/icon_%s.png" % (self._theme,
                                                                               icon_name)
        if os.path.exists(cmk.utils.paths.omd_root + "/" +
                          rel_path) or os.path.exists(cmk.utils.paths.omd_root + "/local/" +
                                                      rel_path):
            return "themes/%s/images/icon_%s.png" % (self._theme, icon_name)

        # TODO: This fallback is odd. Find use cases and clean this up
        return "images/icons/%s.png" % icon_name

    def render_icon_button(self,
                           url,
                           title,
                           icon,
                           id_=None,
                           onclick=None,
                           style=None,
                           target=None,
                           cssclass=None,
                           class_=None):
        # type: (Union[None, str, Text], Text, str, Optional[str], Optional[HTMLTagAttributeValue], Optional[str], Optional[str], Optional[str], CSSSpec) -> HTML

        # Same API as other elements: class_ can be a list or string/None
        classes = [cssclass]
        if isinstance(class_, list):
            classes.extend(class_)
        else:
            classes.append(class_)

        href = url if not onclick else "javascript:void(0)"
        assert href is not None

        return self.render_a(
            content=HTML(self.render_icon(icon, cssclass="iconbutton")),
            href=href,
            title=title,
            id_=id_,
            class_=classes,
            style=style,
            target=target if target else '',
            onfocus="if (this.blur) this.blur();",
            onclick=onclick,
        )

    def icon_button(self,
                    url,
                    title,
                    icon,
                    id_=None,
                    onclick=None,
                    style=None,
                    target=None,
                    cssclass=None,
                    class_=None):
        # type: (Optional[str], Text, str, Optional[str], Optional[HTMLTagAttributeValue], Optional[str], Optional[str], Optional[str], CSSSpec) -> None
        self.write_html(
            self.render_icon_button(url, title, icon, id_, onclick, style, target, cssclass,
                                    class_))

    def popup_trigger(self,
                      content,
                      ident,
                      what=None,
                      data=None,
                      url_vars=None,
                      style=None,
                      menu_content=None,
                      cssclass=None,
                      onclose=None,
                      resizable=False,
                      content_body=None):
        # type: (HTML, str, Optional[str], Any, Optional[HTTPVariables], Optional[str], Optional[str], Optional[str], Optional[str], bool, Optional[str]) -> None
        self.write_html(
            self.render_popup_trigger(content, ident, what, data, url_vars, style, menu_content,
                                      cssclass, onclose, resizable, content_body))

    def render_popup_trigger(self,
                             content,
                             ident,
                             what=None,
                             data=None,
                             url_vars=None,
                             style=None,
                             menu_content=None,
                             cssclass=None,
                             onclose=None,
                             resizable=False,
                             content_body=None):
        # type: (HTML, str, Optional[str], Any, Optional[HTTPVariables], Optional[str], Optional[str], Optional[str], Optional[str], bool, Optional[str]) -> HTML
        onclick = 'cmk.popup_menu.toggle_popup(event, this, %s, %s, %s, %s, %s, %s, %s, %s);' % \
                    (json.dumps(ident),
                     json.dumps(what if what else None),
                     json.dumps(data if data else None),
                     json.dumps(self.urlencode_vars(url_vars) if url_vars else None),
                     json.dumps(menu_content if menu_content else None),
                     json.dumps(onclose.replace("'", "\\'") if onclose else None),
                     json.dumps(resizable),
                     content_body if content_body else json.dumps(None))

        atag = self.render_a(
            content,
            class_="popup_trigger",
            href="javascript:void(0);",
            # Needed to prevent wrong linking when views are parts of dashlets
            target="_self",
            onclick=onclick,
        )

        return self.render_div(atag,
                               class_=["popup_trigger", cssclass],
                               id_="popup_trigger_%s" % ident,
                               style=style)

    def element_dragger_url(self, dragging_tag, base_url):
        # type: (str, str) -> None
        self.write_html(
            self.render_element_dragger(
                dragging_tag,
                drop_handler=
                "function(index){return cmk.element_dragging.url_drop_handler(%s, index);})" %
                json.dumps(base_url)))

    def element_dragger_js(self, dragging_tag, drop_handler, handler_args):
        # type: (str, str, Dict[str, Any]) -> None
        self.write_html(
            self.render_element_dragger(
                dragging_tag,
                drop_handler="function(new_index){return %s(%s, new_index);})" %
                (drop_handler, json.dumps(handler_args))))

    # Currently only tested with tables. But with some small changes it may work with other
    # structures too.
    def render_element_dragger(self, dragging_tag, drop_handler):
        # type: (str,  str) -> HTML
        return self.render_a(self.render_icon("drag", _("Move this entry")),
                             href="javascript:void(0)",
                             class_=["element_dragger"],
                             onmousedown="cmk.element_dragging.start(event, this, %s, %s" %
                             (json.dumps(dragging_tag.upper()), drop_handler))

    #
    # HTML - All the common and more complex HTML rendering methods
    #

    def _dump_get_vars(self):
        # type: () -> None
        self.begin_foldable_container("html", "debug_vars", True,
                                      _("GET/POST variables of this page"))
        self.debug_vars(hide_with_mouse=False)
        self.end_foldable_container()

    def debug_vars(self, prefix=None, hide_with_mouse=True, vars_=None):
        # type: (Optional[str], bool, Optional[Dict[str, str]]) -> None
        it = self.request.itervars() if vars_ is None else vars_.items()
        hover = "this.style.display=\'none\';"
        self.open_table(class_=["debug_vars"], onmouseover=hover if hide_with_mouse else None)
        self.tr(self.render_th(_("POST / GET Variables"), colspan="2"))
        for name, value in sorted(it):
            if name in ["_password", "password"]:
                value = "***"
            if not prefix or name.startswith(prefix):
                self.tr(self.render_td(name, class_="left") + self.render_td(value, class_="right"))
        self.close_table()

    # TODO: Rename the status_icons because they are not only showing states. There are also actions.
    # Something like footer icons or similar seems to be better
    def _write_status_icons(self):
        # type: () -> None
        self.icon_button(self.makeuri([]),
                         _("URL to this frame"),
                         "frameurl",
                         target="_top",
                         cssclass="inline")
        self.icon_button("index.py?" + self.urlencode_vars([("start_url", self.makeuri([]))]),
                         _("URL to this page including sidebar"),
                         "pageurl",
                         target="_top",
                         cssclass="inline")

        # TODO: Move this away from here. Make a context button. The view should handle this
        if self.myfile == "view" and self.request.var('mode') != 'availability' and config.user.may(
                "general.csv_export"):
            self.icon_button(self.makeuri([("output_format", "csv_export")]),
                             _("Export as CSV"),
                             "download_csv",
                             target="_top",
                             cssclass="inline")

        # TODO: This needs to be realized as plugin mechanism
        if self.myfile == "view":
            mode_name = "availability" if self.request.var("mode") == "availability" else "view"

            encoded_vars = {}
            for k, v in self.page_context.items():
                if v is None:
                    v = ''
                elif isinstance(v, six.text_type):
                    v = six.ensure_str(v)
                encoded_vars[k] = v

            self.popup_trigger(
                self.render_icon("menu", _("Add this view to..."), cssclass="iconbutton inline"),
                'add_visual',
                'add_visual',
                data=[mode_name, encoded_vars, {
                    'name': self.request.var('view_name')
                }],
                url_vars=[("add_type", mode_name)])

        # TODO: This should be handled by pagetypes.py
        elif self.myfile == "graph_collection":

            self.popup_trigger(self.render_icon("menu",
                                                _("Add this graph collection to..."),
                                                cssclass="iconbutton inline"),
                               'add_visual',
                               'add_visual',
                               data=["graph_collection", {}, {
                                   'name': self.request.var('name')
                               }],
                               url_vars=[("add_type", "graph_collection")])

        for img, tooltip in self.status_icons.items():
            if isinstance(tooltip, tuple):
                tooltip, url = tooltip
                self.icon_button(url, tooltip, img, cssclass="inline")
            else:
                self.icon(tooltip, img, cssclass="inline")

        if self.times:
            self.measure_time('body')
            self.open_div(class_=["execution_times"])
            entries = sorted(self.times.items())
            for name, duration in entries:
                self.div("%s: %.1fms" % (name, duration * 1000))
            self.close_div()

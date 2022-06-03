#!/usr/bin/env python3
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
import os
import ast
import re
import json
import json.encoder  # type: ignore[import]
import abc
import pprint
from contextlib import contextmanager
from typing import (
    Union,
    Optional,
    List,
    Dict,
    Tuple,
    Any,
    Iterator,
    cast,
    Mapping,
    Set,
    Sequence,
    TYPE_CHECKING,
    TypeVar,
)
from pathlib import Path
import urllib.parse

from six import ensure_str

from cmk.gui.globals import session

Value = TypeVar('Value')


# TODO: Cleanup this dirty hack. Import of htmllib must not magically modify the behaviour of
# the json module. Better would be to create a JSON wrapper in cmk.utils.json which uses a
# custom subclass of the JSONEncoder.
#
# Monkey patch in order to make the HTML class below json-serializable without changing the default json calls.
def _default(self: json.JSONEncoder, obj: object) -> str:
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
from cmk.utils.exceptions import MKGeneralException

from cmk.gui.exceptions import MKUserError
import cmk.gui.escaping as escaping
import cmk.gui.utils as utils
import cmk.gui.config as config
import cmk.gui.log as log
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import OutputFunnel
from cmk.gui.utils.popups import PopupMethod
from cmk.gui.utils.transaction_manager import TransactionManager
from cmk.gui.utils.timeout_manager import TimeoutManager
from cmk.gui.utils.url_encoder import URLEncoder
from cmk.gui.utils.urls import (
    makeactionuri,
    makeactionuri_contextless,
    requested_file_name,
)
from cmk.gui.i18n import _
from cmk.gui.http import Response
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbRenderer
from cmk.gui.page_state import PageState, PageStateRenderer
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuRenderer,
    PageMenuPopupsRenderer,
    enable_page_menu_entry,
)
from cmk.gui.type_defs import (
    CSSSpec,
    Icon,
    Choices,
    ChoiceGroup,
    ChoiceText,
    GroupedChoices,
)

if TYPE_CHECKING:
    from cmk.gui.http import Request
    from cmk.gui.type_defs import VisualContext, HTTPVariables
    from cmk.gui.valuespec import ValueSpec
    from cmk.gui.utils.output_funnel import OutputFunnelInput

HTMLTagName = str
HTMLTagValue = Optional[str]
HTMLContent = Union[None, int, HTML, str]
HTMLTagAttributeValue = Union[None, CSSSpec, HTMLTagValue, List[str]]
HTMLTagAttributes = Dict[str, HTMLTagAttributeValue]
HTMLMessageInput = Union[HTML, str]
DefaultChoice = str

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


class ABCHTMLGenerator(metaclass=abc.ABCMeta):
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

    def _render_attributes(self, **attrs: HTMLTagAttributeValue) -> Iterator[str]:
        css = self._get_normalized_css_classes(attrs)
        if css:
            attrs["class"] = css

        # options such as 'selected' and 'checked' dont have a value in html tags
        options = []

        # Links require href to be first attribute
        href = attrs.pop('href', None)
        if href:
            attributes = list(attrs.items())
            attributes.insert(0, ("href", href))
        else:
            attributes = list(attrs.items())

        # render all attributes
        for key_unescaped, v in attributes:
            if v is None:
                continue

            key = escaping.escape_attribute(key_unescaped.rstrip('_'))

            if key.startswith('data_'):
                key = key.replace('_', '-', 1)  # HTML data attribute: 'data-name'

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

    def _get_normalized_css_classes(self, attrs: HTMLTagAttributes) -> List[str]:
        # make class attribute foolproof
        css: List[str] = []
        for k in ["class_", "css", "cssclass", "class"]:
            if k in attrs:
                cls_spec = cast(CSSSpec, attrs.pop(k))
                css += self.normalize_css_spec(cls_spec)
        return css

    def normalize_css_spec(self, css_classes: CSSSpec) -> List[str]:
        if isinstance(css_classes, list):
            return [c for c in css_classes if c is not None]

        if css_classes is not None:
            return [css_classes]

        return []

    # applies attribute encoding to prevent code injections.
    def _render_start_tag(self,
                          tag_name: HTMLTagName,
                          close_tag: bool = False,
                          **attrs: HTMLTagAttributeValue) -> HTML:
        """ You have to replace attributes which are also python elements such as
            'class', 'id', 'for' or 'type' using a trailing underscore (e.g. 'class_' or 'id_'). """
        return HTML("<%s%s%s>" %
                    (tag_name, '' if not attrs else ''.join(self._render_attributes(**attrs)),
                     '' if not close_tag else ' /'))

    def _render_end_tag(self, tag_name: HTMLTagName) -> HTML:
        return HTML("</%s>" % (tag_name))

    def _render_element(self, tag_name: HTMLTagName, tag_content: HTMLContent,
                        **attrs: HTMLTagAttributeValue) -> HTML:
        open_tag = self._render_start_tag(tag_name, close_tag=False, **attrs)

        if not tag_content:
            tag_content = ""
        elif not isinstance(tag_content, HTML):
            tag_content = escaping.escape_text(tag_content)

        return HTML("%s%s</%s>" % (open_tag, tag_content, tag_name))

    #
    # Showing / rendering
    #

    def render_text(self, text: HTMLContent) -> HTML:
        return HTML(escaping.escape_text(text))

    def write_text(self, text: HTMLContent) -> None:
        """ Write text. Highlighting tags such as h2|b|tt|i|br|pre|a|sup|p|li|ul|ol are not escaped. """
        self.write(self.render_text(text))

    def write_html(self, content: HTML) -> None:
        """ Write HTML code directly, without escaping. """
        self.write(content)

    @abc.abstractmethod
    def write(self, text: 'OutputFunnelInput') -> None:
        raise NotImplementedError()

    #
    # HTML element methods
    # If an argument is mandatory, it is used as default and it will overwrite an
    # implicit argument (e.g. id_ will overwrite attrs["id"]).
    #

    #
    # basic elements
    #

    def meta(self, httpequiv: Optional[str] = None, **attrs: HTMLTagAttributeValue) -> None:
        if httpequiv:
            attrs['http-equiv'] = httpequiv
        self.write_html(self._render_start_tag('meta', close_tag=True, **attrs))

    def base(self, target: str) -> None:
        self.write_html(self._render_start_tag('base', close_tag=True, target=target))

    def open_a(self, href: Optional[str], **attrs: HTMLTagAttributeValue) -> None:
        if href is not None:
            attrs['href'] = href
        self.write_html(self._render_start_tag('a', close_tag=False, **attrs))

    def render_a(self, content: HTMLContent, href: Union[None, str, str],
                 **attrs: HTMLTagAttributeValue) -> HTML:
        if href is not None:
            attrs['href'] = href
        return self._render_element('a', content, **attrs)

    def a(self, content: HTMLContent, href: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_a(content, href, **attrs))

    def stylesheet(self, href: str) -> None:
        self.write_html(
            self._render_start_tag('link',
                                   rel="stylesheet",
                                   type_="text/css",
                                   href=href,
                                   close_tag=True))

    #
    # Scripting
    #

    def render_javascript(self, code: str) -> HTML:
        return HTML("<script type=\"text/javascript\">\n%s\n</script>\n" % code)

    def javascript(self, code: str) -> None:
        self.write_html(self.render_javascript(code))

    def javascript_file(self, src: str) -> None:
        """ <script type="text/javascript" src="%(name)"/>\n """
        self.write_html(self._render_element('script', '', type_="text/javascript", src=src))

    def render_img(self, src: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs['src'] = src
        return self._render_start_tag('img', close_tag=True, **attrs)

    def img(self, src: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_img(src, **attrs))

    def open_button(self, type_: str, **attrs: HTMLTagAttributeValue) -> None:
        attrs['type'] = type_
        self.write_html(self._render_start_tag('button', close_tag=True, **attrs))

    def play_sound(self, url: str) -> None:
        self.write_html(self._render_start_tag('audio autoplay', src_=url))

    #
    # form elements
    #

    def render_label(self, content: HTMLContent, for_: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs['for'] = for_
        return self._render_element('label', content, **attrs)

    def label(self, content: HTMLContent, for_: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_label(content, for_, **attrs))

    def render_input(self, name: Optional[str], type_: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs['type_'] = type_
        attrs['name'] = name
        return self._render_start_tag('input', close_tag=True, **attrs)

    def input(self, name: Optional[str], type_: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_input(name, type_, **attrs))

    #
    # table and list elements
    #

    def li(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> None:
        """ Only for text content. You can't put HTML structure here. """
        self.write_html(self._render_element('li', content, **attrs))

    #
    # structural text elements
    #

    def render_heading(self, content: HTMLContent) -> HTML:
        return self._render_element('h2', content)

    def heading(self, content: HTMLContent) -> None:
        self.write_html(self.render_heading(content))

    def render_br(self) -> HTML:
        return HTML("<br/>")

    def br(self) -> None:
        self.write_html(self.render_br())

    def render_hr(self, **attrs: HTMLTagAttributeValue) -> HTML:
        return self._render_start_tag('hr', close_tag=True, **attrs)

    def hr(self, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_hr(**attrs))

    def rule(self) -> None:
        self.hr()

    def render_nbsp(self) -> HTML:
        return HTML("&nbsp;")

    def nbsp(self) -> None:
        self.write_html(self.render_nbsp())

    #
    # Simple HTML object rendering without specific functionality
    #

    def pre(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("pre", content, **kwargs))

    def h2(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("h2", content, **kwargs))

    def h3(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("h3", content, **kwargs))

    def h1(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("h1", content, **kwargs))

    def h4(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("h4", content, **kwargs))

    def style(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("style", content, **kwargs))

    def span(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("span", content, **kwargs))

    def sub(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("sub", content, **kwargs))

    def title(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("title", content, **kwargs))

    def tt(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("tt", content, **kwargs))

    def tr(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("tr", content, **kwargs))

    def th(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("th", content, **kwargs))

    def td(self,
           content: HTMLContent,
           colspan: Optional[int] = None,
           **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(
            self._render_element("td",
                                 content,
                                 colspan=str(colspan) if colspan is not None else None,
                                 **kwargs))

    def option(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("option", content, **kwargs))

    def canvas(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("canvas", content, **kwargs))

    def strong(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("strong", content, **kwargs))

    def b(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("b", content, **kwargs))

    def center(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("center", content, **kwargs))

    def i(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("i", content, **kwargs))

    def p(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("p", content, **kwargs))

    def u(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("u", content, **kwargs))

    def iframe(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("iframe", content, **kwargs))

    def x(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("x", content, **kwargs))

    def div(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_element("div", content, **kwargs))

    def open_pre(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("pre", close_tag=False, **kwargs))

    def close_pre(self) -> None:
        self.write_html(self._render_end_tag("pre"))

    def render_pre(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("pre", content, **kwargs)

    def open_h2(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("h2", close_tag=False, **kwargs))

    def close_h2(self) -> None:
        self.write_html(self._render_end_tag("h2"))

    def render_h2(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("h2", content, **kwargs)

    def open_h3(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("h3", close_tag=False, **kwargs))

    def close_h3(self) -> None:
        self.write_html(self._render_end_tag("h3"))

    def render_h3(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("h3", content, **kwargs)

    def open_h1(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("h1", close_tag=False, **kwargs))

    def close_h1(self) -> None:
        self.write_html(self._render_end_tag("h1"))

    def render_h1(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("h1", content, **kwargs)

    def open_h4(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("h4", close_tag=False, **kwargs))

    def close_h4(self) -> None:
        self.write_html(self._render_end_tag("h4"))

    def render_h4(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("h4", content, **kwargs)

    def open_header(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("header", close_tag=False, **kwargs))

    def close_header(self) -> None:
        self.write_html(self._render_end_tag("header"))

    def render_header(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("header", content, **kwargs)

    def open_tag(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("tag", close_tag=False, **kwargs))

    def close_tag(self) -> None:
        self.write_html(self._render_end_tag("tag"))

    def render_tag(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("tag", content, **kwargs)

    def open_table(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("table", close_tag=False, **kwargs))

    def close_table(self) -> None:
        self.write_html(self._render_end_tag("table"))

    def render_table(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("table", content, **kwargs)

    def open_select(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("select", close_tag=False, **kwargs))

    def close_select(self) -> None:
        self.write_html(self._render_end_tag("select"))

    def render_select(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("select", content, **kwargs)

    def open_row(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("row", close_tag=False, **kwargs))

    def close_row(self) -> None:
        self.write_html(self._render_end_tag("row"))

    def render_row(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("row", content, **kwargs)

    def open_style(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("style", close_tag=False, **kwargs))

    def close_style(self) -> None:
        self.write_html(self._render_end_tag("style"))

    def render_style(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("style", content, **kwargs)

    def open_span(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("span", close_tag=False, **kwargs))

    def close_span(self) -> None:
        self.write_html(self._render_end_tag("span"))

    def render_span(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("span", content, **kwargs)

    def open_sub(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("sub", close_tag=False, **kwargs))

    def close_sub(self) -> None:
        self.write_html(self._render_end_tag("sub"))

    def render_sub(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("sub", content, **kwargs)

    def open_script(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("script", close_tag=False, **kwargs))

    def close_script(self) -> None:
        self.write_html(self._render_end_tag("script"))

    def render_script(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("script", content, **kwargs)

    def open_tt(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("tt", close_tag=False, **kwargs))

    def close_tt(self) -> None:
        self.write_html(self._render_end_tag("tt"))

    def render_tt(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("tt", content, **kwargs)

    def open_tr(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("tr", close_tag=False, **kwargs))

    def close_tr(self) -> None:
        self.write_html(self._render_end_tag("tr"))

    def render_tr(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("tr", content, **kwargs)

    def open_tbody(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("tbody", close_tag=False, **kwargs))

    def close_tbody(self) -> None:
        self.write_html(self._render_end_tag("tbody"))

    def render_tbody(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("tbody", content, **kwargs)

    def open_li(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("li", close_tag=False, **kwargs))

    def close_li(self) -> None:
        self.write_html(self._render_end_tag("li"))

    def render_li(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("li", content, **kwargs)

    def open_html(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("html", close_tag=False, **kwargs))

    def close_html(self) -> None:
        self.write_html(self._render_end_tag("html"))

    def render_html(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("html", content, **kwargs)

    def open_th(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("th", close_tag=False, **kwargs))

    def close_th(self) -> None:
        self.write_html(self._render_end_tag("th"))

    def render_th(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("th", content, **kwargs)

    def open_sup(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("sup", close_tag=False, **kwargs))

    def close_sup(self) -> None:
        self.write_html(self._render_end_tag("sup"))

    def render_sup(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("sup", content, **kwargs)

    def open_input(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("input", close_tag=False, **kwargs))

    def close_input(self) -> None:
        self.write_html(self._render_end_tag("input"))

    def open_td(self, colspan: Optional[int] = None, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(
            self._render_start_tag("td",
                                   close_tag=False,
                                   colspan=str(colspan) if colspan is not None else None,
                                   **kwargs))

    def close_td(self) -> None:
        self.write_html(self._render_end_tag("td"))

    def render_td(self,
                  content: HTMLContent,
                  colspan: Optional[int] = None,
                  **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("td",
                                    content,
                                    colspan=str(colspan) if colspan is not None else None,
                                    **kwargs)

    def open_thead(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("thead", close_tag=False, **kwargs))

    def close_thead(self) -> None:
        self.write_html(self._render_end_tag("thead"))

    def render_thead(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("thead", content, **kwargs)

    def open_body(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("body", close_tag=False, **kwargs))

    def close_body(self) -> None:
        self.write_html(self._render_end_tag("body"))

    def render_body(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("body", content, **kwargs)

    def open_head(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("head", close_tag=False, **kwargs))

    def close_head(self) -> None:
        self.write_html(self._render_end_tag("head"))

    def render_head(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("head", content, **kwargs)

    def open_fieldset(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("fieldset", close_tag=False, **kwargs))

    def close_fieldset(self) -> None:
        self.write_html(self._render_end_tag("fieldset"))

    def render_fieldset(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("fieldset", content, **kwargs)

    def open_optgroup(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(self._render_start_tag("optgroup", close_tag=False, **kwargs))

    def close_optgroup(self):
        # type: () -> None
        self.write_html(self._render_end_tag("optgroup"))

    def open_option(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("option", close_tag=False, **kwargs))

    def close_option(self) -> None:
        self.write_html(self._render_end_tag("option"))

    def render_option(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("option", content, **kwargs)

    def open_form(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("form", close_tag=False, **kwargs))

    def close_form(self) -> None:
        self.write_html(self._render_end_tag("form"))

    def render_form(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("form", content, **kwargs)

    def open_tags(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("tags", close_tag=False, **kwargs))

    def close_tags(self) -> None:
        self.write_html(self._render_end_tag("tags"))

    def render_tags(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("tags", content, **kwargs)

    def open_canvas(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("canvas", close_tag=False, **kwargs))

    def close_canvas(self) -> None:
        self.write_html(self._render_end_tag("canvas"))

    def render_canvas(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("canvas", content, **kwargs)

    def open_nobr(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("nobr", close_tag=False, **kwargs))

    def close_nobr(self) -> None:
        self.write_html(self._render_end_tag("nobr"))

    def render_nobr(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("nobr", content, **kwargs)

    def open_br(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("br", close_tag=False, **kwargs))

    def close_br(self) -> None:
        self.write_html(self._render_end_tag("br"))

    def open_strong(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("strong", close_tag=False, **kwargs))

    def close_strong(self) -> None:
        self.write_html(self._render_end_tag("strong"))

    def render_strong(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("strong", content, **kwargs)

    def close_a(self) -> None:
        self.write_html(self._render_end_tag("a"))

    def open_b(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("b", close_tag=False, **kwargs))

    def close_b(self) -> None:
        self.write_html(self._render_end_tag("b"))

    def render_b(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("b", content, **kwargs)

    def open_center(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("center", close_tag=False, **kwargs))

    def close_center(self) -> None:
        self.write_html(self._render_end_tag("center"))

    def render_center(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("center", content, **kwargs)

    def open_footer(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("footer", close_tag=False, **kwargs))

    def close_footer(self) -> None:
        self.write_html(self._render_end_tag("footer"))

    def render_footer(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("footer", content, **kwargs)

    def open_i(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("i", close_tag=False, **kwargs))

    def close_i(self) -> None:
        self.write_html(self._render_end_tag("i"))

    def render_i(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("i", content, **kwargs)

    def close_button(self) -> None:
        self.write_html(self._render_end_tag("button"))

    def open_title(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("title", close_tag=False, **kwargs))

    def close_title(self) -> None:
        self.write_html(self._render_end_tag("title"))

    def render_title(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("title", content, **kwargs)

    def open_p(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("p", close_tag=False, **kwargs))

    def close_p(self) -> None:
        self.write_html(self._render_end_tag("p"))

    def render_p(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("p", content, **kwargs)

    def open_u(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("u", close_tag=False, **kwargs))

    def close_u(self) -> None:
        self.write_html(self._render_end_tag("u"))

    def render_u(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("u", content, **kwargs)

    def open_iframe(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("iframe", close_tag=False, **kwargs))

    def close_iframe(self) -> None:
        self.write_html(self._render_end_tag("iframe"))

    def render_iframe(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("iframe", content, **kwargs)

    def open_x(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("x", close_tag=False, **kwargs))

    def close_x(self) -> None:
        self.write_html(self._render_end_tag("x"))

    def render_x(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("x", content, **kwargs)

    def open_div(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("div", close_tag=False, **kwargs))

    def close_div(self) -> None:
        self.write_html(self._render_end_tag("div"))

    def render_div(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return self._render_element("div", content, **kwargs)

    def open_ul(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(self._render_start_tag("ul", close_tag=False, **kwargs))

    def close_ul(self) -> None:
        self.write_html(self._render_end_tag("ul"))

    def render_ul(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
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
    "json_export": "application/json",
    "jsonp": "application/javascript",
    "csv": "text/csv",
    "csv_export": "text/csv",
    "python": "text/plain",
    "text": "text/plain",
    "html": "text/html",
    "xml": "text/xml",
    "pdf": "application/pdf",
    "x-tgz": "application/x-tgz",
}


class html(ABCHTMLGenerator):
    def __init__(self, request: 'Request') -> None:
        super(html, self).__init__()

        self._logger = log.logger.getChild("html")

        # rendering state
        self._header_sent = False

        # style options
        self._body_classes = ['main']
        self._default_javascripts = ["main"]

        # behaviour options
        self.render_headfoot = True
        self.enable_debug = False
        self.screenshotmode = False
        self.have_help = False

        # browser options
        self.output_format = "html"
        self.browser_reload = 0.0
        self.browser_redirect = ''
        self.link_target: Optional[str] = None

        # Browser options
        self.user_errors: Dict[Optional[str], str] = {}
        self.final_javascript_code = ""
        self.page_context: 'VisualContext' = {}

        # Settings
        self.mobile = False
        self._theme = "facelift"

        # Forms
        self.form_name: Optional[str] = None
        self.form_vars: List[str] = []

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

        self.myfile = requested_file_name(self.request)

        # Disable caching for all our pages as they are mostly dynamically generated,
        # user related and are required to be up-to-date on every refresh
        self.response.headers["Cache-Control"] = "no-cache"

        try:
            output_format = self.request.get_ascii_input_mandatory("output_format", "html")
            self.set_output_format(output_format.lower())
        except (MKUserError, MKGeneralException):
            pass  # Silently ignore unsupported formats

    def init_modes(self) -> None:
        """Initializes the operation mode of the html() object. This is called
        after the Check_MK GUI configuration has been loaded, so it is safe
        to rely on the config."""
        self._verify_not_using_threaded_mpm()

        self._init_screenshot_mode()
        self._init_debug_mode()
        self._init_webapi_cors_header()
        self.init_theme()

    def _init_webapi_cors_header(self) -> None:
        # Would be better to put this to page individual code, but we currently have
        # no mechanism for a page to set do this before the authentication is made.
        if self.myfile == "webapi":
            self.response.headers["Access-Control-Allow-Origin"] = "*"

    def init_theme(self) -> None:
        self.set_theme(config.ui_theme)

    def set_theme(self, theme_id: str) -> None:
        if not theme_id:
            theme_id = config.ui_theme

        if theme_id not in dict(config.theme_choices()):
            theme_id = "facelift"

        self._theme = theme_id

    def get_theme(self) -> str:
        return self._theme

    def icon_themes(self) -> List[str]:
        """Returns the themes where icons of a theme can be found in increasing order of importance.
        By default the facelift theme provides all icons. If a theme wants to use different icons it
        only needs to add those icons under the same name. See detect_icon_path for a detailed list
        of paths.
        """
        return ["facelift"] if self._theme == "facelift" else ["facelift", self._theme]

    def theme_url(self, rel_url: str) -> str:
        return "themes/%s/%s" % (self._theme, rel_url)

    def _verify_not_using_threaded_mpm(self) -> None:
        if self.request.is_multithread:
            raise MKGeneralException(
                _("You are trying to Checkmk together with a threaded Apache multiprocessing module (MPM). "
                  "Check_MK is only working with the prefork module. Please change the MPM module to make "
                  "Check_MK work."))

    def _init_debug_mode(self) -> None:
        # Debug flag may be set via URL to override the configuration
        if self.request.var("debug"):
            config.debug = True
        self.enable_debug = config.debug

    # Enabling the screenshot mode omits the fancy background and
    # makes it white instead.
    def _init_screenshot_mode(self) -> None:
        if self.request.var("screenshotmode", "1" if config.screenshotmode else ""):
            self.screenshotmode = True

    def init_mobile(self) -> None:
        if self.request.has_var("mobile"):
            # TODO: Make private
            self.mobile = bool(self.request.var("mobile"))
            # Persist the explicitly set state in a cookie to have it maintained through further requests
            self.response.set_http_cookie("mobile",
                                          str(int(self.mobile)),
                                          secure=self.request.is_secure)

        elif self.request.has_cookie("mobile"):
            self.mobile = self.request.cookie("mobile", "0") == "1"

        else:
            self.mobile = self._is_mobile_client(self.request.user_agent.string)

    def _is_mobile_client(self, user_agent: str) -> bool:
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
    def stashed_vars(self) -> Iterator[None]:
        saved_vars = dict(self.request.itervars())
        try:
            yield
        finally:
            self.request.del_vars()
            for varname, value in saved_vars.items():
                self.request.set_var(varname, value)

    def del_var_from_env(self, varname: str) -> None:
        # HACKY WORKAROUND, REMOVE WHEN NO LONGER NEEDED
        # We need to get rid of query-string entries which can contain secret information.
        # As this is the only location where these are stored on the WSGI environment this
        # should be enough.
        # See also cmk.gui.globals:RequestContext
        # Filter the variables even if there are multiple copies of them (this is allowed).
        decoded_qs = [
            (key, value) for key, value in self.request.args.items(multi=True) if key != varname
        ]
        self.request.query_string = urllib.parse.urlencode(decoded_qs).encode("utf-8")
        self.request.environ['QUERY_STRING'] = self.request
        # We remove the form entry. As this entity is never copied it will be modified within
        # it's cache.
        try:
            dict.pop(self.request.form, varname)
        except KeyError:
            pass
        # We remove the __dict__ entries to allow @cached_property to reload them from
        # the environment. The rest of the request object stays the same.
        self.request.__dict__.pop('args', None)
        self.request.__dict__.pop('values', None)

    def get_item_input(self, varname: str, collection: Mapping[str, Value]) -> Tuple[Value, str]:
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
    def get_url_input(self, varname: str, deflt: Optional[str] = None) -> str:
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

    def get_request(self, exclude_vars: Optional[List[str]] = None) -> Dict[str, Any]:
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
                request[key] = ensure_str(val) if isinstance(val, bytes) else val

        return request

    #
    # Transaction IDs
    #

    # TODO: Cleanup all call sites to self.transaction_manager.*
    def transaction_valid(self) -> bool:
        return self.transaction_manager.transaction_valid()

    # TODO: Cleanup all call sites to self.transaction_manager.*
    def is_transaction(self) -> bool:
        return self.transaction_manager.is_transaction()

    # TODO: Cleanup all call sites to self.transaction_manager.*
    def check_transaction(self) -> bool:
        return self.transaction_manager.check_transaction()

    #
    # Encoding
    #

    # TODO: Cleanup all call sites to self.encoder.*
    def urlencode_vars(self, vars_: List[Tuple[str, Union[None, int, str]]]) -> str:
        return self.encoder.urlencode_vars(vars_)

    # TODO: Cleanup all call sites to self.encoder.*
    def urlencode(self, value: Optional[str]) -> str:
        return self.encoder.urlencode(value)

    #
    # output funnel
    #

    def write(self, text: 'OutputFunnelInput') -> None:
        self.output_funnel.write(text)

    def write_binary(self, data: bytes) -> None:
        self.output_funnel.write_binary(data)

    @contextmanager
    def plugged(self) -> Iterator[None]:
        with self.output_funnel.plugged():
            yield

    def drain(self) -> str:
        return self.output_funnel.drain()

    #
    # Timeout handling
    #

    def enable_request_timeout(self) -> None:
        self.timeout_manager.enable_timeout(self.request.request_timeout)

    def disable_request_timeout(self) -> None:
        self.timeout_manager.disable_timeout()

    #
    # Content Type
    #

    def set_output_format(self, f: str) -> None:
        if f not in OUTPUT_FORMAT_MIME_TYPES:
            raise MKGeneralException(_("Unsupported context type '%s'") % f)

        self.output_format = f
        self.response.set_content_type(OUTPUT_FORMAT_MIME_TYPES[f])

    def is_api_call(self) -> bool:
        return self.output_format != "html"

    #
    # Other things
    #

    def is_mobile(self) -> bool:
        return self.mobile

    def set_page_context(self, c: 'VisualContext') -> None:
        self.page_context = c

    def set_link_target(self, framename: str) -> None:
        self.link_target = framename

    def set_focus(self, varname: str) -> None:
        self.final_javascript("cmk.utils.set_focus_by_name(%s, %s)" %
                              (json.dumps(self.form_name), json.dumps(varname)))

    def set_focus_by_id(self, dom_id: str) -> None:
        self.final_javascript("cmk.utils.set_focus_by_id(%s)" % (json.dumps(dom_id)))

    def set_render_headfoot(self, render: bool) -> None:
        self.render_headfoot = render

    def set_browser_reload(self, secs: float) -> None:
        self.browser_reload = secs

    def set_browser_redirect(self, secs: float, url: str) -> None:
        self.browser_reload = secs
        self.browser_redirect = url

    def clear_default_javascript(self) -> None:
        del self._default_javascripts[:]

    def add_default_javascript(self, name: str) -> None:
        if name not in self._default_javascripts:
            self._default_javascripts.append(name)

    def immediate_browser_redirect(self, secs: float, url: str) -> None:
        self.javascript("cmk.utils.set_reload(%s, '%s');" % (secs, url))

    def add_body_css_class(self, cls: str) -> None:
        self._body_classes.append(cls)

    def final_javascript(self, code: str) -> None:
        self.final_javascript_code += code + "\n"

    def reload_whole_page(self, url: Optional[str] = None) -> None:
        if not self.request.has_var("_ajaxid"):
            return self.final_javascript("cmk.utils.reload_whole_page(%s)" % json.dumps(url))

    def finalize(self) -> None:
        """Finish the HTTP request processing before handing over to the application server"""
        self.disable_request_timeout()

    #
    # Messages
    #

    def show_message(self, msg: HTMLMessageInput) -> None:
        self.write(self._render_message(msg, 'message'))

    def show_error(self, msg: HTMLMessageInput) -> None:
        self.write(self._render_message(msg, 'error'))

    def show_warning(self, msg: HTMLMessageInput) -> None:
        self.write(self._render_message(msg, 'warning'))

    def render_message(self, msg: HTMLMessageInput) -> HTML:
        return self._render_message(msg, 'message')

    def render_error(self, msg: HTMLMessageInput) -> HTML:
        return self._render_message(msg, 'error')

    def render_warning(self, msg: HTMLMessageInput) -> HTML:
        return self._render_message(msg, 'warning')

    # obj might be either a string (str or unicode) or an exception object
    def _render_message(self, msg: HTMLMessageInput, what: str = 'message') -> HTML:
        if what == 'message':
            cls = 'success'
            prefix = _('MESSAGE')
        elif what == 'warning':
            cls = 'warning'
            prefix = _('WARNING')
        else:
            cls = 'error'
            prefix = _('ERROR')

        if self.output_format == "html":
            code = self.render_div(self.render_text(msg), class_=cls)
            if self.mobile:
                return self.render_center(code)
            return code
        return self.render_text('%s: %s\n' % (prefix, escaping.strip_tags(msg)))

    def show_localization_hint(self) -> None:
        url = "wato.py?mode=edit_configvar&varname=user_localizations"
        self.show_message(
            self.render_sup("*") + _("These texts may be localized depending on the users' "
                                     "language. You can configure the localizations %s.") %
            self.render_a("in the global settings", href=url))

    def del_language_cookie(self) -> None:
        self.response.delete_cookie("language")

    def set_language_cookie(self, lang: Optional[str]) -> None:
        cookie_lang = self.request.cookie("language")
        if cookie_lang == lang:
            return
        if lang is None:
            self.del_language_cookie()
        else:
            self.response.set_http_cookie("language", lang)

    def help(self, text: Union[None, HTML, str], escape_text: bool = True) -> None:
        """Embed help box, whose visibility is controlled by a global button in the page.

        You may add macros like this to the help texts to create links to the user
        manual: [piggyback|Piggyback chapter].
        """
        self.write_html(self.render_help(text, escape_text=escape_text))

    def render_help(self, text: Union[None, HTML, str], escape_text: bool = True) -> HTML:
        if isinstance(text, str) and escape_text:
            text = escaping.escape_text(text)
        elif isinstance(text, HTML):
            text = "%s" % text

        if not text:
            return HTML("")

        stripped = text.strip()
        if not stripped:
            return HTML("")

        help_text = self.resolve_help_text_macros(stripped)

        self.enable_help_toggle()
        style = "display:%s;" % ("block" if config.user.show_help else "none")
        return self.render_div(HTML(help_text), class_="help", style=style)

    def resolve_help_text_macros(self, text: str) -> str:
        return re.sub(
            r"\[([a-z0-9_-]+)(#[a-z0-9_-]+|)\|([^\]]+)\]",
            "<a href=\"%s/\\1.html\\2\" target=\"_blank\">\\3</a>" %
            config.user.get_docs_base_url(), text)

    def enable_help_toggle(self) -> None:
        self.have_help = True

    #
    # Debugging, diagnose and logging
    #

    def debug(self, *x: Any) -> None:
        for element in x:
            try:
                formatted = pprint.pformat(element)
            except UnicodeDecodeError:
                formatted = repr(element)
            self.write(self.render_pre(formatted))

    #
    # URL building
    #

    def makeactionuri(self,
                      addvars: 'HTTPVariables',
                      filename: Optional[str] = None,
                      delvars: Optional[Sequence[str]] = None) -> str:
        return makeactionuri(
            self.request,
            self.transaction_manager,
            addvars,
            filename=filename,
            delvars=delvars,
        )

    def makeactionuri_contextless(self,
                                  addvars: 'HTTPVariables',
                                  filename: Optional[str] = None) -> str:
        return makeactionuri_contextless(
            self.request,
            self.transaction_manager,
            addvars,
            filename=filename,
        )

    #
    # HTML heading and footer rendering
    #

    def default_html_headers(self) -> None:
        self.meta(httpequiv="Content-Type", content="text/html; charset=utf-8")
        self.write_html(
            self._render_start_tag('link',
                                   rel="shortcut icon",
                                   href="themes/%s/images/favicon.ico" % self._theme,
                                   type_="image/ico",
                                   close_tag=True))

    def _head(self, title: str, javascripts: Optional[List[str]] = None) -> None:
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

        self._set_js_csrf_token()

        if self.browser_reload != 0.0:
            if self.browser_redirect != '':
                self.javascript('cmk.utils.set_reload(%s, \'%s\')' %
                                (self.browser_reload, self.browser_redirect))
            else:
                self.javascript('cmk.utils.set_reload(%s)' % (self.browser_reload))

        self.close_head()

    def _set_js_csrf_token(self) -> None:
        # session is LocalProxy, only on access it is None, so we cannot test on 'is None'
        if not hasattr(session, "session_info"):
            return
        self.javascript("var global_csrf_token = %s;" %
                        (json.dumps(session.session_info.csrf_token)))

    def _add_custom_style_sheet(self) -> None:
        for css in self._plugin_stylesheets():
            self.write('<link rel="stylesheet" type="text/css" href="css/%s">\n' % css)

        if config.custom_style_sheet:
            self.write('<link rel="stylesheet" type="text/css" href="%s">\n' %
                       config.custom_style_sheet)

    def _plugin_stylesheets(self) -> Set[str]:
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
    # b) in OMD environments, add the Checkmk version to the version (prevents update problems)
    # c) load the minified javascript when not in debug mode
    def javascript_filename_for_browser(self, jsname: str) -> Optional[str]:
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

    def _css_filename_for_browser(self, css: str) -> Optional[str]:
        rel_path = "/share/check_mk/web/htdocs/" + css + ".css"
        if os.path.exists(cmk.utils.paths.omd_root + rel_path) or \
            os.path.exists(cmk.utils.paths.omd_root + "/local" + rel_path):
            return '%s-%s.css' % (css, cmk_version.__version__)
        return None

    def html_head(self,
                  title: str,
                  javascripts: Optional[List[str]] = None,
                  force: bool = False) -> None:
        force_new_document = force  # for backward stability and better readability

        if force_new_document:
            self._header_sent = False

        if not self._header_sent:
            self.write_html(HTML('<!DOCTYPE HTML>\n'))
            self.open_html()
            self._head(title, javascripts)
            self._header_sent = True

    def header(self,
               title: str,
               breadcrumb: Breadcrumb,
               page_menu: Optional[PageMenu] = None,
               page_state: Optional[PageState] = None,
               javascripts: Optional[List[str]] = None,
               force: bool = False,
               show_body_start: bool = True,
               show_top_heading: bool = True) -> None:
        if self.output_format == "html":
            if not self._header_sent:
                if show_body_start:
                    self.body_start(title, javascripts=javascripts, force=force)

                self._header_sent = True

                breadcrumb = breadcrumb or Breadcrumb()

                if self.render_headfoot and show_top_heading:
                    self.top_heading(
                        title,
                        breadcrumb=breadcrumb,
                        page_menu=page_menu or PageMenu(breadcrumb=breadcrumb),
                        page_state=page_state,
                    )
            self.begin_page_content()

    def body_start(self,
                   title: str = u'',
                   javascripts: Optional[List[str]] = None,
                   force: bool = False) -> None:
        self.html_head(title, javascripts, force)
        self.open_body(class_=self._get_body_css_classes(), data_theme=self.get_theme())

    def _get_body_css_classes(self) -> List[str]:
        classes = self._body_classes[:]
        if self.screenshotmode:
            classes += ["screenshotmode"]
        return classes

    def html_foot(self) -> None:
        self.close_html()

    def top_heading(self,
                    title: str,
                    breadcrumb: Breadcrumb,
                    page_menu: Optional[PageMenu] = None,
                    page_state: Optional[PageState] = None) -> None:
        self.open_div(id_="top_heading")
        self.open_div(class_="titlebar")

        # HTML() is needed here to prevent a double escape when we do  self._escape_attribute
        # here and self.a() escapes the content (with permissive escaping) again. We don't want
        # to handle "title" permissive.
        html_title = HTML(escaping.escape_attribute(title))
        self.a(html_title,
               class_="title",
               href="#",
               onfocus="if (this.blur) this.blur();",
               onclick="this.innerHTML=\'%s\'; document.location.reload();" % _("Reloading..."))

        if breadcrumb:
            BreadcrumbRenderer().show(breadcrumb)

        if page_state is None:
            page_state = self._make_default_page_state()

        if page_state:
            PageStateRenderer().show(page_state)

        self.close_div()  # titlebar

        if page_menu:
            PageMenuRenderer().show(
                page_menu,
                hide_suggestions=not config.user.get_tree_state("suggestions", "all", True),
            )

        self.close_div()  # top_heading

        if page_menu:
            PageMenuPopupsRenderer().show(page_menu)

        if self.enable_debug:
            self._dump_get_vars()

    def _make_default_page_state(self) -> Optional[PageState]:
        """Create a general page state for all pages without specific one"""
        if not self.browser_reload:
            return None

        return PageState(
            text=self.render_span("%d" % self.browser_reload),
            icon_name="trans",
            css_classes=["default"],
            url="javascript:document.location.reload()",
            tooltip_text=_("Automatic page reload in %d seconds." % self.browser_reload) + "\n" +
            _("Click for instant reload."),
        )

    def begin_page_content(self):
        content_id = "main_page_content"
        self.open_div(id_=content_id)
        self.final_javascript("cmk.utils.content_scrollbar(%s)" % json.dumps(content_id))

    def end_page_content(self):
        self.close_div()

    def footer(self, show_body_end: bool = True) -> None:
        if self.output_format == "html":
            self.end_page_content()

            if show_body_end:
                self.body_end()

    def focus_here(self) -> None:
        self.a("", href="#focus_me", id_="focus_me")
        self.set_focus_by_id("focus_me")

    def body_end(self) -> None:
        if self.have_help:
            enable_page_menu_entry("inline_help")
        if self.final_javascript_code:
            self.javascript(self.final_javascript_code)
        self.javascript("cmk.visibility_detection.initialize();")
        self.close_body()
        self.close_html()

    #
    # HTML form rendering
    #

    def begin_form(self,
                   name: str,
                   action: Optional[str] = None,
                   method: str = "GET",
                   onsubmit: Optional[str] = None,
                   add_transid: bool = True) -> None:
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
        if hasattr(session, "session_info"):
            self.hidden_field("csrf_token", session.session_info.csrf_token)
        self.hidden_field("filled_in", name, add_var=True)
        if add_transid:
            self.hidden_field(
                "_transid",
                str(self.transaction_manager.get()),
                add_var=True,
            )
        self.form_name = name

    def end_form(self) -> None:
        self.close_form()
        self.form_name = None

    def add_confirm_on_submit(self, form_name: str, msg: str) -> None:
        """Adds a confirm dialog to a form that is shown before executing a form submission"""
        self.javascript("cmk.forms.add_confirm_on_submit(%s, %s)" %
                        (json.dumps("form_%s" % form_name), json.dumps(escaping.escape_text(msg))))

    def in_form(self) -> bool:
        return self.form_name is not None

    def prevent_password_auto_completion(self) -> None:
        # These fields are not really used by the form. They are used to prevent the browsers
        # from filling the default password and previous input fields in the form
        # with password which are eventually saved in the browsers password store.
        self.input(name=None, type_="text", style="display:none;")
        self.input(name=None, type_="password", style="display:none;")

    # Needed if input elements are put into forms without the helper
    # functions of us. TODO: Should really be removed and cleaned up!
    def add_form_var(self, varname: str) -> None:
        self.form_vars.append(varname)

    # Beware: call this method just before end_form(). It will
    # add all current non-underscored HTML variables as hiddedn
    # field to the form - *if* they are not used in any input
    # field. (this is the reason why you must not add any further
    # input fields after this method has been called).
    def hidden_fields(self,
                      varlist: Optional[List[str]] = None,
                      add_action_vars: bool = False) -> None:
        if varlist is not None:
            for var in varlist:
                self.hidden_field(var, self.request.var(var, ""))
        else:  # add *all* get variables, that are not set by any input!
            for var, _val in self.request.itervars():
                if var not in self.form_vars and \
                    (var[0] != "_" or add_action_vars):  # and var != "filled_in":
                    self.hidden_field(var, self.request.get_unicode_input(var))

    def hidden_field(self,
                     var: str,
                     value: HTMLTagValue,
                     id_: Optional[str] = None,
                     add_var: bool = False,
                     class_: CSSSpec = None) -> None:
        self.write_html(
            self.render_hidden_field(var=var, value=value, id_=id_, add_var=add_var, class_=class_))

    def render_hidden_field(self,
                            var: str,
                            value: HTMLTagValue,
                            id_: Optional[str] = None,
                            add_var: bool = False,
                            class_: CSSSpec = None) -> HTML:
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

    def do_actions(self) -> bool:
        return self.request.var("_do_actions") not in ["", None, _("No")]

    # Check if the given form is currently filled in (i.e. we display
    # the form a second time while showing value typed in at the first
    # time and complaining about invalid user input)
    def form_submitted(self, form_name: Optional[str] = None) -> bool:
        if form_name is None:
            return self.request.has_var("filled_in")
        return self.request.var("filled_in") == form_name

    # Get value of checkbox. Return True, False or None. None means
    # that no form has been submitted. The problem here is the distintion
    # between False and None. The browser does not set the variables for
    # Checkboxes that are not checked :-(
    def get_checkbox(self, varname: str) -> Optional[bool]:
        if self.request.has_var(varname):
            return bool(self.request.var(varname))
        if self.form_submitted(self.form_name):
            return False  # Form filled in but variable missing -> Checkbox not checked
        return None

    #
    # Button elements
    #

    def button(self,
               varname: str,
               title: str,
               cssclass: Optional[str] = None,
               style: Optional[str] = None,
               help_: Optional[str] = None,
               form: Optional[str] = None,
               formnovalidate: bool = False) -> None:
        self.write_html(
            self.render_button(varname,
                               title,
                               cssclass,
                               style,
                               help_=help_,
                               form=form,
                               formnovalidate=formnovalidate))

    def render_button(self,
                      varname: str,
                      title: str,
                      cssclass: Optional[str] = None,
                      style: Optional[str] = None,
                      help_: Optional[str] = None,
                      form: Optional[str] = None,
                      formnovalidate: bool = False) -> HTML:
        self.add_form_var(varname)
        return self.render_input(name=varname,
                                 type_="submit",
                                 id_=varname,
                                 class_=["button", cssclass if cssclass else None],
                                 value=title,
                                 title=help_,
                                 style=style,
                                 form=form,
                                 formnovalidate='' if formnovalidate else None)

    def buttonlink(self,
                   href: str,
                   text: str,
                   add_transid: bool = False,
                   obj_id: Optional[str] = None,
                   style: Optional[str] = None,
                   title: Optional[str] = None,
                   disabled: Optional[str] = None,
                   class_: CSSSpec = None) -> None:
        if add_transid:
            href += "&_transid=%s" % self.transaction_manager.get()

        if not obj_id:
            obj_id = utils.gen_id()

        # Same API as other elements: class_ can be a list or string/None
        css_classes: List[Optional[str]] = ["button", "buttonlink"]
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
                   onclick="location.href=%s" % json.dumps(href))

    def empty_icon_button(self) -> None:
        self.write(self.render_icon("trans", cssclass="iconbutton trans"))

    def disabled_icon_button(self, icon: str) -> None:
        self.write(self.render_icon(icon, cssclass="iconbutton"))

    # TODO: Cleanup to use standard attributes etc.
    def jsbutton(self,
                 varname: str,
                 text: str,
                 onclick: str,
                 style: str = '',
                 cssclass: Optional[str] = None,
                 title: str = "",
                 disabled: bool = False,
                 class_: CSSSpec = None) -> None:
        if not isinstance(class_, list):
            class_ = [class_]
        # TODO: Investigate why mypy complains about the latest argument
        classes = ["button", cssclass] + cast(List[Optional[str]], class_)

        if disabled:
            class_.append("disabled")
            disabled_arg: Optional[str] = ""
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

    def user_error(self, e: MKUserError) -> None:
        assert isinstance(e, MKUserError), "ERROR: This exception is not a user error!"
        self.open_div(class_="error")
        self.write_text(str(e))
        self.close_div()
        self.add_user_error(e.varname, e)

    # user errors are used by input elements to show invalid input
    def add_user_error(self, varname: Optional[str], msg_or_exc: Union[str, Exception]) -> None:
        if isinstance(msg_or_exc, Exception):
            message: str = u"%s" % msg_or_exc
        else:
            message = ensure_str(msg_or_exc)

        # TODO: Find the multiple varname call sites and clean this up
        if isinstance(varname, list):
            for v in varname:
                self.add_user_error(v, message)
        else:
            self.user_errors[varname] = message

    def has_user_errors(self) -> bool:
        return len(self.user_errors) > 0

    def show_user_errors(self) -> None:
        if self.has_user_errors():
            self.open_div(class_="error")
            self.write(self.render_br().join(
                self.render_text(s) for s in self.user_errors.values()))
            self.close_div()

    def text_input(self,
                   varname: str,
                   default_value: str = u"",
                   cssclass: str = "text",
                   size: Union[None, str, int] = None,
                   label: Optional[str] = None,
                   id_: Optional[str] = None,
                   submit: Optional[str] = None,
                   try_max_width: bool = False,
                   read_only: bool = False,
                   autocomplete: Optional[str] = None,
                   style: Optional[str] = None,
                   omit_css_width: bool = False,
                   type_: Optional[str] = None,
                   onkeyup: Optional[str] = None,
                   onblur: Optional[str] = None,
                   placeholder: Optional[str] = None,
                   data_world: Optional[str] = None,
                   data_max_labels: Optional[int] = None,
                   required: bool = False,
                   title: Optional[str] = None) -> None:

        # Model
        error = self.user_errors.get(varname)
        value = self.request.get_unicode_input(varname, default_value)
        if not value:
            value = ""
        if error:
            self.set_focus(varname)
        self.form_vars.append(varname)

        # View
        # TODO: Move styling away from py code
        style_size: Optional[str] = None
        field_size: Optional[str] = None
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

        attributes: HTMLTagAttributes = {
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
            "required": "" if required else None,
            "title": title,
        }

        if error:
            self.open_x(class_="inputerror")

        if label:
            assert id_ is not None
            self.label(label, for_=id_, class_="required" if required else None)

        input_type = "text" if type_ is None else type_
        assert isinstance(input_type, str)
        self.write_html(self.render_input(varname, type_=input_type, **attributes))

        if error:
            self.close_x()

    def status_label(self, content: HTMLContent, status: str, title: str,
                     **attrs: HTMLTagAttributeValue) -> None:
        """Shows a colored badge with text (used on WATO activation page for the site status)"""
        self.status_label_button(content, status, title, onclick=None, **attrs)

    def status_label_button(self, content: HTMLContent, status: str, title: str,
                            onclick: Optional[str], **attrs: HTMLTagAttributeValue) -> None:
        """Shows a colored button with text (used in site and customer status snapins)"""
        button_cls = "button" if onclick else None
        self.div(content,
                 title=title,
                 class_=["status_label", button_cls, status],
                 onclick=onclick,
                 **attrs)

    def toggle_switch(self,
                      enabled: bool,
                      help_txt: str,
                      class_: CSSSpec = None,
                      href: str = "javascript:void(0)",
                      **attrs: HTMLTagAttributeValue) -> None:
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
                       varname: str,
                       default_value: str = "",
                       cssclass: str = "text",
                       size: Union[None, str, int] = None,
                       label: Optional[str] = None,
                       id_: Optional[str] = None,
                       submit: Optional[str] = None,
                       try_max_width: bool = False,
                       read_only: bool = False,
                       autocomplete: Optional[str] = None,
                       placeholder: Optional[str] = None) -> None:
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
                        autocomplete=autocomplete,
                        placeholder=placeholder)

    def text_area(self,
                  varname: str,
                  deflt: str = "",
                  rows: int = 4,
                  cols: int = 30,
                  try_max_width: bool = False,
                  **attrs: HTMLTagAttributeValue) -> None:

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
    def dropdown(self,
                 varname: str,
                 choices: Union[Choices, GroupedChoices],
                 locked_choice: Optional[ChoiceText] = None,
                 deflt: DefaultChoice = '',
                 ordered: bool = False,
                 label: Optional[str] = None,
                 class_: CSSSpec = None,
                 size: int = 1,
                 read_only: bool = False,
                 **attrs: HTMLTagAttributeValue) -> None:
        current = self.request.get_unicode_input(varname, deflt)
        error = self.user_errors.get(varname)
        if varname:
            self.form_vars.append(varname)

        # Normalize all choices to grouped choice structure
        grouped: GroupedChoices = []
        ungrouped_group = ChoiceGroup(title="", choices=[])
        grouped.append(ungrouped_group)
        for e in choices:
            if not isinstance(e, ChoiceGroup):
                ungrouped_group.choices.append(e)
            else:
                grouped.append(e)

        if error:
            self.open_x(class_="inputerror")

        if read_only:
            attrs["disabled"] = "disabled"
            self.hidden_field(varname, current, add_var=False)

        if label:
            self.label(label, for_=varname)

        # Do not enable select2 for select fields that allow multiple
        # selections like the dual list choice valuespec
        css_classes: List[Optional[str]] = ["select2-enable"]
        if "multiple" in attrs or (isinstance(class_, list) and "ajax-vals" in class_):
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

        for group in grouped:
            if group.title:
                self.open_optgroup(label=group.title)

            for value, text in (group.choices if not ordered else sorted(
                    group.choices, key=lambda a: a[1].lower())):
                # if both the default in choices and current was '' then selected depended on the order in choices
                selected = (value == current) or (not value and not current)
                self.option(
                    text,
                    value=value if value else "",
                    selected="" if selected else None,
                )

            if locked_choice:
                self.option(locked_choice, value="", disabled="")

            if group.title:
                self.close_optgroup()

        self.close_select()
        if error:
            self.close_x()

    def icon_dropdown(self,
                      varname: str,
                      choices: List[Tuple[str, str, str]],
                      deflt: str = "") -> None:
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

    def upload_file(self, varname: str) -> None:
        error = self.user_errors.get(varname)
        if error:
            self.open_x(class_="inputerror")
        self.input(name=varname, type_="file")
        if error:
            self.close_x()
        self.form_vars.append(varname)

    #
    # Radio groups
    #

    def begin_radio_group(self, horizontal: bool = False) -> None:
        if self.mobile:
            attrs = {'data-type': "horizontal" if horizontal else None, 'data-role': "controlgroup"}
            self.write(self._render_start_tag("fieldset", close_tag=False, **attrs))

    def end_radio_group(self) -> None:
        if self.mobile:
            self.write(self._render_end_tag("fieldset"))

    def radiobutton(self, varname: str, value: str, checked: bool, label: Optional[str]) -> None:
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

    def begin_checkbox_group(self, horizonal: bool = False) -> None:
        self.begin_radio_group(horizonal)

    def end_checkbox_group(self) -> None:
        self.end_radio_group()

    def checkbox(self,
                 varname: str,
                 deflt: bool = False,
                 label: HTMLContent = '',
                 id_: Optional[str] = None,
                 **add_attr: HTMLTagAttributeValue) -> None:
        self.write(self.render_checkbox(varname, deflt, label, id_, **add_attr))

    def render_checkbox(self,
                        varname: str,
                        deflt: bool = False,
                        label: HTMLContent = '',
                        id_: Optional[str] = None,
                        **add_attr: HTMLTagAttributeValue) -> HTML:
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
                                 treename: str,
                                 id_: str,
                                 isopen: bool,
                                 title: HTMLContent,
                                 indent: Union[str, None, bool] = True,
                                 first: bool = False,
                                 icon: Optional[str] = None,
                                 fetch_url: Optional[str] = None,
                                 title_url: Optional[str] = None,
                                 title_target: Optional[str] = None,
                                 padding: int = 15) -> bool:
        isopen = config.user.get_tree_state(treename, id_, isopen)
        onclick = self.foldable_container_onclick(treename, id_, fetch_url)
        img_id = self.foldable_container_img_id(treename, id_)
        container_id = self.foldable_container_id(treename, id_)

        self.open_div(class_=["foldable", "open" if isopen else "closed"])

        if isinstance(title, HTML):  # custom HTML code
            self.write_text(title)

        else:
            self.open_b(class_=["treeangle", "title"], onclick=None if title_url else onclick)

            if title_url:
                self.a(title, href=title_url, target=title_target)
            else:
                self.write_text(title)
            self.close_b()

        if icon:
            self.img(
                id_=img_id,
                class_=[
                    "treeangle",
                    "title",
                    # Although foldable_sidebar is given via the argument icon it should not be
                    # displayed as big as an icon.
                    "icon" if icon != "foldable_sidebar" else None,
                    "open" if isopen else "closed",
                ],
                src=self.detect_icon_path(icon, prefix="icon_"),
                onclick=onclick)
        else:
            self.img(id_=img_id,
                     class_=["treeangle", "open" if isopen else "closed"],
                     src="themes/%s/images/tree_closed.svg" % (self._theme),
                     onclick=onclick)

        if indent != "form" or not isinstance(title, HTML):
            self.br()

        indent_style = "padding-left: %dpx; " % (padding if indent else 0)
        if indent == "form":
            self.close_td()
            self.close_tr()
            self.close_table()
            indent_style += "margin: 0; "
        self.open_ul(id_=container_id,
                     class_=["treeangle", "open" if isopen else "closed"],
                     style=indent_style)

        return isopen

    def end_foldable_container(self) -> None:
        self.close_ul()
        self.close_div()

    def foldable_container_onclick(self, treename: str, id_: str, fetch_url: Optional[str]) -> str:
        return "cmk.foldable_container.toggle(%s, %s, %s)" % (
            json.dumps(treename), json.dumps(id_), json.dumps(fetch_url if fetch_url else ''))

    def foldable_container_img_id(self, treename: str, id_: str) -> str:
        return "treeimg.%s.%s" % (treename, id_)

    def foldable_container_id(self, treename: str, id_: str) -> str:
        return "tree.%s.%s" % (treename, id_)

    #
    # Floating Options
    #

    def render_floating_option(self, name: str, height: str, varprefix: str, valuespec: 'ValueSpec',
                               value: Any) -> None:
        self.open_div(class_=["floatfilter", height, name])
        self.div(valuespec.title(), class_=["legend"])
        self.open_div(class_=["content"])
        valuespec.render_input(varprefix + name, value)
        self.close_div()
        self.close_div()

    #
    # HTML icon rendering
    #

    def icon(self,
             icon: Icon,
             title: Optional[str] = None,
             id_: Optional[str] = None,
             cssclass: Optional[str] = None,
             class_: CSSSpec = None) -> None:
        self.write_html(
            self.render_icon(icon=icon, title=title, id_=id_, cssclass=cssclass, class_=class_))

    def empty_icon(self) -> None:
        self.write_html(self.render_icon("trans"))

    def render_icon(self,
                    icon: Icon,
                    title: Optional[str] = None,
                    id_: Optional[str] = None,
                    cssclass: Optional[str] = None,
                    class_: CSSSpec = None) -> HTML:
        classes = ["icon", cssclass]
        if isinstance(class_, list):
            classes.extend(class_)
        else:
            classes.append(class_)

        icon_name = icon["icon"] if isinstance(icon, dict) else icon
        src = icon_name if "/" in icon_name else self.detect_icon_path(icon_name, prefix="icon_")
        if src.endswith(".png"):
            classes.append("png")
        if src.endswith("/icon_missing.svg") and title:
            title += " (%s)" % _("icon not found")

        icon_element = self._render_start_tag(
            'img',
            close_tag=True,
            title=title,
            id_=id_,
            class_=classes,
            src=src,
        )

        if isinstance(icon, dict) and icon["emblem"] is not None:
            return self.render_emblem(icon["emblem"], title, id_, icon_element)

        return icon_element

    def render_emblem(
        self,
        emblem: str,
        title: Optional[str],
        id_: Optional[str],
        icon_element: Optional[HTML] = None,
    ) -> HTML:
        """ Render emblem to corresponding icon (icon_element in function call)
        or render emblem itself as icon image, used e.g. in view options."""

        emblem_path = self.detect_icon_path(emblem, prefix="emblem_")
        if not icon_element:
            return self._render_start_tag(
                'img',
                close_tag=True,
                title=title,
                id_=id_,
                class_="icon",
                src=emblem_path,
            )

        return self.render_span(
            icon_element + self.render_img(emblem_path, class_="emblem"),
            class_="emblem",
        )

    def detect_icon_path(self, icon_name: str, prefix: str) -> str:
        """Detect from which place an icon shall be used and return it's path relative to htdocs/

        Priority:
        1. In case the modern-dark theme is active: <theme> = modern-dark -> priorities 3-6
        2. In case the modern-dark theme is active: <theme> = facelift -> priorities 3-6
        3. In case a theme is active: themes/<theme>/images/icon_[name].svg in site local hierarchy
        4. In case a theme is active: themes/<theme>/images/icon_[name].svg in standard hierarchy
        5. In case a theme is active: themes/<theme>/images/icon_[name].png in site local hierarchy
        6. In case a theme is active: themes/<theme>/images/icon_[name].png in standard hierarchy
        7. images/icons/[name].png in site local hierarchy
        8. images/icons/[name].png in standard hierarchy
        """
        path = "share/check_mk/web/htdocs"
        for theme in self.icon_themes():
            icon = prefix + icon_name
            theme_path = path + "/themes/%s/images/%s" % (theme, icon)
            for base_dir in [
                    cmk.utils.paths.omd_root + "/local/",
                    cmk.utils.paths.omd_root + "/",
            ]:
                for file_type in ["svg", "png"]:
                    if os.path.exists(base_dir + theme_path + "." + file_type):
                        return "themes/%s/images/%s.%s" % (self._theme, icon, file_type)
                    if os.path.exists(base_dir + path + "/images/icons/%s.%s" %
                                      (icon_name, file_type)):
                        return "images/icons/%s.%s" % (icon_name, file_type)

        return "themes/facelift/images/icon_missing.svg"

    def render_icon_button(self,
                           url: Union[None, str, str],
                           title: str,
                           icon: Icon,
                           id_: Optional[str] = None,
                           onclick: Optional[HTMLTagAttributeValue] = None,
                           style: Optional[str] = None,
                           target: Optional[str] = None,
                           cssclass: Optional[str] = None,
                           class_: CSSSpec = None) -> HTML:
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
                    url: Optional[str],
                    title: str,
                    icon: Icon,
                    id_: Optional[str] = None,
                    onclick: Optional[HTMLTagAttributeValue] = None,
                    style: Optional[str] = None,
                    target: Optional[str] = None,
                    cssclass: Optional[str] = None,
                    class_: CSSSpec = None) -> None:
        self.write_html(
            self.render_icon_button(url, title, icon, id_, onclick, style, target, cssclass,
                                    class_))

    def more_button(self,
                    id_: str,
                    dom_levels_up: int,
                    additional_js: str = "",
                    with_text: bool = False) -> None:
        if config.user.show_mode == "enforce_show_more":
            return

        self.open_a(href="javascript:void(0)",
                    id_="more_%s" % id_,
                    class_=["more", "has_text" if with_text else ""],
                    onfocus="if (this.blur) this.blur();",
                    onclick="cmk.utils.toggle_more(this, %s, %d);%s" %
                    (json.dumps(id_), dom_levels_up, additional_js))
        self.open_div(title=_("Show more") if not with_text else "", class_="show_more")
        if with_text:
            self.write_text(_("show more"))
        self.close_div()
        self.open_div(title=_("Show less") if not with_text else "", class_="show_less")
        if with_text:
            self.write_text(_("show less"))
        self.close_div()
        self.close_a()

    def popup_trigger(self,
                      content: HTML,
                      ident: str,
                      method: PopupMethod,
                      data: Any = None,
                      style: Optional[str] = None,
                      cssclass: CSSSpec = None,
                      onclose: Optional[str] = None,
                      onopen: Optional[str] = None,
                      resizable: bool = False,
                      popup_group: Optional[str] = None,
                      hover_switch_delay: Optional[int] = None) -> None:
        self.write_html(
            self.render_popup_trigger(content, ident, method, data, style, cssclass, onclose,
                                      onopen, resizable, popup_group, hover_switch_delay))

    def render_popup_trigger(self,
                             content: HTML,
                             ident: str,
                             method: PopupMethod,
                             data: Any = None,
                             style: Optional[str] = None,
                             cssclass: CSSSpec = None,
                             onclose: Optional[str] = None,
                             onopen: Optional[str] = None,
                             resizable: bool = False,
                             popup_group: Optional[str] = None,
                             hover_switch_delay: Optional[int] = None) -> HTML:

        onclick = 'cmk.popup_menu.toggle_popup(event, this, %s, %s, %s, %s, %s,  %s);' % \
                    (json.dumps(ident),
                     json.dumps(method.asdict()),
                     json.dumps(data if data else None),
                     json.dumps(onclose.replace("'", "\\'") if onclose else None),
                     json.dumps(onopen.replace("'", "\\'") if onopen else None),
                     json.dumps(resizable))

        if popup_group:
            onmouseenter: Optional[str] = (
                "cmk.popup_menu.switch_popup_menu_group(this, %s, %s)" %
                (json.dumps(popup_group), json.dumps(hover_switch_delay)))
            onmouseleave: Optional[str] = "cmk.popup_menu.stop_popup_menu_group_switch(this)"
        else:
            onmouseenter = None
            onmouseleave = None

        atag = self.render_a(
            content,
            class_="popup_trigger",
            href="javascript:void(0);",
            # Needed to prevent wrong linking when views are parts of dashlets
            target="_self",
            onclick=onclick,
            onmouseenter=onmouseenter,
            onmouseleave=onmouseleave,
        )

        classes: List[Optional[str]] = ["popup_trigger"]
        if isinstance(cssclass, list):
            classes.extend(cssclass)
        elif cssclass:
            classes.append(cssclass)

        return self.render_div(atag + method.content,
                               class_=classes,
                               id_="popup_trigger_%s" % ident,
                               style=style)

    def element_dragger_url(self, dragging_tag: str, base_url: str) -> None:
        self.write_html(
            self.render_element_dragger(
                dragging_tag,
                drop_handler=
                "function(index){return cmk.element_dragging.url_drop_handler(%s, index);})" %
                json.dumps(base_url)))

    def element_dragger_js(self, dragging_tag: str, drop_handler: str,
                           handler_args: Dict[str, Any]) -> None:
        self.write_html(
            self.render_element_dragger(
                dragging_tag,
                drop_handler="function(new_index){return %s(%s, new_index);})" %
                (drop_handler, json.dumps(handler_args))))

    # Currently only tested with tables. But with some small changes it may work with other
    # structures too.
    def render_element_dragger(self, dragging_tag: str, drop_handler: str) -> HTML:
        return self.render_a(self.render_icon("drag", _("Move this entry")),
                             href="javascript:void(0)",
                             class_=["element_dragger"],
                             onmousedown="cmk.element_dragging.start(event, this, %s, %s" %
                             (json.dumps(dragging_tag.upper()), drop_handler))

    #
    # HTML - All the common and more complex HTML rendering methods
    #

    def _dump_get_vars(self) -> None:
        self.begin_foldable_container("html", "debug_vars", True,
                                      _("GET/POST variables of this page"))
        self.debug_vars(hide_with_mouse=False)
        self.end_foldable_container()

    def debug_vars(self,
                   prefix: Optional[str] = None,
                   hide_with_mouse: bool = True,
                   vars_: Optional[Dict[str, str]] = None) -> None:
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

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# TODO:
#
# Notes for future rewrite:
#
# - Find all call sites which do something like "int(request.var(...))"
#   and replace it with request.get_integer_input_mandatory(...)
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
# - Unify CSS classes attribute to "class_"

from __future__ import annotations

import abc
from typing import Optional, Union

import cmk.gui.utils.escaping as escaping
from cmk.gui.utils.html import HTML

from .tag_rendering import (
    HTMLContent,
    HTMLTagAttributeValue,
    render_element,
    render_end_tag,
    render_start_tag,
)

# .
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


class ABCHTMLGenerator(abc.ABC):
    # The class should not be abstract.  We should pass it a "writer" object
    # instead of making the class abstract for this single method.
    #
    """Usage Notes:

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
        non HtML relevant signs '&amp;', '&lt;', '&gt;' and '&quot;'."""

    #
    # Showing / rendering
    #

    def write_text(self, text: HTMLContent) -> None:
        """Write text. Highlighting tags such as h2|b|tt|i|br|pre|a|sup|p|li|ul|ol are not escaped."""
        self.write_html(HTML(escaping.escape_text(text)))

    def write_html(self, content: HTML) -> None:
        """Write HTML code directly, without escaping."""
        self._write(content)

    @abc.abstractmethod
    def _write(self, text: HTMLContent) -> None:
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
            attrs["http-equiv"] = httpequiv
        self.write_html(render_start_tag("meta", close_tag=True, **attrs))

    def base(self, target: str) -> None:
        self.write_html(render_start_tag("base", close_tag=True, target=target))

    def open_a(self, href: Optional[str], **attrs: HTMLTagAttributeValue) -> None:
        if href is not None:
            attrs["href"] = href
        self.write_html(render_start_tag("a", close_tag=False, **attrs))

    def render_a(
        self, content: HTMLContent, href: Union[None, str, str], **attrs: HTMLTagAttributeValue
    ) -> HTML:
        if href is not None:
            attrs["href"] = href
        return render_element("a", content, **attrs)

    def a(self, content: HTMLContent, href: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_a(content, href, **attrs))

    def stylesheet(self, href: str) -> None:
        self.link(rel="stylesheet", href=href, type_="text/css")

    def link(self, *, rel: str, href: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("link", rel=rel, href=href, close_tag=True, **attrs))

    #
    # Scripting
    #

    def render_javascript(self, code: str) -> HTML:
        return HTML('<script type="text/javascript">\n%s\n</script>\n' % code)

    def javascript(self, code: str) -> None:
        self.write_html(self.render_javascript(code))

    def javascript_file(self, src: str) -> None:
        """<script type="text/javascript" src="%(name)"/>\n"""
        self.write_html(render_element("script", "", type_="text/javascript", src=src))

    def render_img(self, src: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs["src"] = src
        return render_start_tag("img", close_tag=True, **attrs)

    def img(self, src: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_img(src, **attrs))

    def open_button(self, type_: str, **attrs: HTMLTagAttributeValue) -> None:
        attrs["type"] = type_
        self.write_html(render_start_tag("button", close_tag=True, **attrs))

    def play_sound(self, url: str) -> None:
        self.write_html(render_start_tag("audio autoplay", src_=url))

    #
    # form elements
    #

    def render_label(self, content: HTMLContent, for_: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs["for"] = for_
        return render_element("label", content, **attrs)

    def label(self, content: HTMLContent, for_: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_label(content, for_, **attrs))

    def render_input(self, name: Optional[str], type_: str, **attrs: HTMLTagAttributeValue) -> HTML:
        if type_ == "submit":
            self.form_has_submit_button = True
        attrs["type_"] = type_
        attrs["name"] = name
        return render_start_tag("input", close_tag=True, **attrs)

    def input(self, name: Optional[str], type_: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(self.render_input(name, type_, **attrs))

    #
    # table and list elements
    #

    def li(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> None:
        """Only for text content. You can't put HTML structure here."""
        self.write_html(render_element("li", content, **attrs))

    #
    # structural text elements
    #

    def render_heading(self, content: HTMLContent) -> HTML:
        return render_element("h2", content)

    def heading(self, content: HTMLContent) -> None:
        self.write_html(self.render_heading(content))

    def render_br(self) -> HTML:
        return HTML("<br />")

    def br(self) -> None:
        self.write_html(self.render_br())

    def render_hr(self, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_start_tag("hr", close_tag=True, **attrs)

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
        self.write_html(render_element("pre", content, **kwargs))

    def h2(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("h2", content, **kwargs))

    def h3(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("h3", content, **kwargs))

    def h1(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("h1", content, **kwargs))

    def h4(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("h4", content, **kwargs))

    def style(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("style", content, **kwargs))

    def span(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("span", content, **kwargs))

    def sub(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("sub", content, **kwargs))

    def title(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("title", content, **kwargs))

    def tt(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("tt", content, **kwargs))

    def tr(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("tr", content, **kwargs))

    def th(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("th", content, **kwargs))

    def td(
        self, content: HTMLContent, colspan: Optional[int] = None, **kwargs: HTMLTagAttributeValue
    ) -> None:
        self.write_html(
            render_element(
                "td", content, colspan=str(colspan) if colspan is not None else None, **kwargs
            )
        )

    def option(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("option", content, **kwargs))

    def canvas(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("canvas", content, **kwargs))

    def strong(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("strong", content, **kwargs))

    def b(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("b", content, **kwargs))

    def center(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("center", content, **kwargs))

    def i(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("i", content, **kwargs))

    def p(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("p", content, **kwargs))

    def u(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("u", content, **kwargs))

    def iframe(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("iframe", content, **kwargs))

    def x(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("x", content, **kwargs))

    def div(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("div", content, **kwargs))

    def legend(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_element("legend", content, **kwargs))

    def open_pre(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("pre", close_tag=False, **kwargs))

    def close_pre(self) -> None:
        self.write_html(render_end_tag("pre"))

    def render_pre(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("pre", content, **kwargs)

    def open_h2(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("h2", close_tag=False, **kwargs))

    def close_h2(self) -> None:
        self.write_html(render_end_tag("h2"))

    def render_h2(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("h2", content, **kwargs)

    def open_h3(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("h3", close_tag=False, **kwargs))

    def close_h3(self) -> None:
        self.write_html(render_end_tag("h3"))

    def render_h3(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("h3", content, **kwargs)

    def open_h1(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("h1", close_tag=False, **kwargs))

    def close_h1(self) -> None:
        self.write_html(render_end_tag("h1"))

    def render_h1(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("h1", content, **kwargs)

    def open_h4(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("h4", close_tag=False, **kwargs))

    def close_h4(self) -> None:
        self.write_html(render_end_tag("h4"))

    def render_h4(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("h4", content, **kwargs)

    def open_header(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("header", close_tag=False, **kwargs))

    def close_header(self) -> None:
        self.write_html(render_end_tag("header"))

    def render_header(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("header", content, **kwargs)

    def open_tag(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tag", close_tag=False, **kwargs))

    def close_tag(self) -> None:
        self.write_html(render_end_tag("tag"))

    def render_tag(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tag", content, **kwargs)

    def open_table(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("table", close_tag=False, **kwargs))

    def close_table(self) -> None:
        self.write_html(render_end_tag("table"))

    def render_table(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("table", content, **kwargs)

    def open_select(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("select", close_tag=False, **kwargs))

    def close_select(self) -> None:
        self.write_html(render_end_tag("select"))

    def render_select(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("select", content, **kwargs)

    def open_row(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("row", close_tag=False, **kwargs))

    def close_row(self) -> None:
        self.write_html(render_end_tag("row"))

    def render_row(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("row", content, **kwargs)

    def open_style(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("style", close_tag=False, **kwargs))

    def close_style(self) -> None:
        self.write_html(render_end_tag("style"))

    def render_style(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("style", content, **kwargs)

    def open_span(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("span", close_tag=False, **kwargs))

    def close_span(self) -> None:
        self.write_html(render_end_tag("span"))

    def render_span(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("span", content, **kwargs)

    def open_sub(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("sub", close_tag=False, **kwargs))

    def close_sub(self) -> None:
        self.write_html(render_end_tag("sub"))

    def render_sub(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("sub", content, **kwargs)

    def open_script(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("script", close_tag=False, **kwargs))

    def close_script(self) -> None:
        self.write_html(render_end_tag("script"))

    def render_script(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("script", content, **kwargs)

    def open_tt(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tt", close_tag=False, **kwargs))

    def close_tt(self) -> None:
        self.write_html(render_end_tag("tt"))

    def render_tt(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tt", content, **kwargs)

    def open_tr(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tr", close_tag=False, **kwargs))

    def close_tr(self) -> None:
        self.write_html(render_end_tag("tr"))

    def render_tr(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tr", content, **kwargs)

    def open_tbody(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tbody", close_tag=False, **kwargs))

    def close_tbody(self) -> None:
        self.write_html(render_end_tag("tbody"))

    def render_tbody(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tbody", content, **kwargs)

    def open_li(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("li", close_tag=False, **kwargs))

    def close_li(self) -> None:
        self.write_html(render_end_tag("li"))

    def render_li(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("li", content, **kwargs)

    def open_html(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("html", close_tag=False, **kwargs))

    def close_html(self) -> None:
        self.write_html(render_end_tag("html"))

    def render_html(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("html", content, **kwargs)

    def open_th(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("th", close_tag=False, **kwargs))

    def close_th(self) -> None:
        self.write_html(render_end_tag("th"))

    def render_th(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("th", content, **kwargs)

    def open_sup(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("sup", close_tag=False, **kwargs))

    def close_sup(self) -> None:
        self.write_html(render_end_tag("sup"))

    def render_sup(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("sup", content, **kwargs)

    def open_input(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("input", close_tag=False, **kwargs))

    def close_input(self) -> None:
        self.write_html(render_end_tag("input"))

    def open_td(self, colspan: Optional[int] = None, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(
            render_start_tag(
                "td",
                close_tag=False,
                colspan=str(colspan) if colspan is not None else None,
                **kwargs,
            )
        )

    def close_td(self) -> None:
        self.write_html(render_end_tag("td"))

    def render_td(
        self, content: HTMLContent, colspan: Optional[int] = None, **kwargs: HTMLTagAttributeValue
    ) -> HTML:
        return render_element(
            "td", content, colspan=str(colspan) if colspan is not None else None, **kwargs
        )

    def open_thead(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("thead", close_tag=False, **kwargs))

    def close_thead(self) -> None:
        self.write_html(render_end_tag("thead"))

    def render_thead(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("thead", content, **kwargs)

    def open_body(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("body", close_tag=False, **kwargs))

    def close_body(self) -> None:
        self.write_html(render_end_tag("body"))

    def render_body(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("body", content, **kwargs)

    def open_head(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("head", close_tag=False, **kwargs))

    def close_head(self) -> None:
        self.write_html(render_end_tag("head"))

    def render_head(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("head", content, **kwargs)

    def open_fieldset(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("fieldset", close_tag=False, **kwargs))

    def close_fieldset(self) -> None:
        self.write_html(render_end_tag("fieldset"))

    def render_fieldset(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("fieldset", content, **kwargs)

    def open_optgroup(self, **kwargs):
        # type: (**HTMLTagAttributeValue) -> None
        self.write_html(render_start_tag("optgroup", close_tag=False, **kwargs))

    def close_optgroup(self):
        # type: () -> None
        self.write_html(render_end_tag("optgroup"))

    def open_option(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("option", close_tag=False, **kwargs))

    def close_option(self) -> None:
        self.write_html(render_end_tag("option"))

    def render_option(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("option", content, **kwargs)

    def open_form(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("form", close_tag=False, **kwargs))

    def close_form(self) -> None:
        self.write_html(render_end_tag("form"))

    def render_form(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("form", content, **kwargs)

    def open_tags(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tags", close_tag=False, **kwargs))

    def close_tags(self) -> None:
        self.write_html(render_end_tag("tags"))

    def render_tags(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tags", content, **kwargs)

    def open_canvas(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("canvas", close_tag=False, **kwargs))

    def close_canvas(self) -> None:
        self.write_html(render_end_tag("canvas"))

    def render_canvas(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("canvas", content, **kwargs)

    def open_nobr(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("nobr", close_tag=False, **kwargs))

    def close_nobr(self) -> None:
        self.write_html(render_end_tag("nobr"))

    def render_nobr(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("nobr", content, **kwargs)

    def open_br(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("br", close_tag=False, **kwargs))

    def close_br(self) -> None:
        self.write_html(render_end_tag("br"))

    def open_strong(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("strong", close_tag=False, **kwargs))

    def close_strong(self) -> None:
        self.write_html(render_end_tag("strong"))

    def render_strong(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("strong", content, **kwargs)

    def close_a(self) -> None:
        self.write_html(render_end_tag("a"))

    def open_b(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("b", close_tag=False, **kwargs))

    def close_b(self) -> None:
        self.write_html(render_end_tag("b"))

    def render_b(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("b", content, **kwargs)

    def open_center(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("center", close_tag=False, **kwargs))

    def close_center(self) -> None:
        self.write_html(render_end_tag("center"))

    def render_center(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("center", content, **kwargs)

    def open_footer(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("footer", close_tag=False, **kwargs))

    def close_footer(self) -> None:
        self.write_html(render_end_tag("footer"))

    def render_footer(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("footer", content, **kwargs)

    def open_i(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("i", close_tag=False, **kwargs))

    def close_i(self) -> None:
        self.write_html(render_end_tag("i"))

    def render_i(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("i", content, **kwargs)

    def close_button(self) -> None:
        self.write_html(render_end_tag("button"))

    def open_title(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("title", close_tag=False, **kwargs))

    def close_title(self) -> None:
        self.write_html(render_end_tag("title"))

    def render_title(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("title", content, **kwargs)

    def open_p(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("p", close_tag=False, **kwargs))

    def close_p(self) -> None:
        self.write_html(render_end_tag("p"))

    def render_p(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("p", content, **kwargs)

    def open_u(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("u", close_tag=False, **kwargs))

    def close_u(self) -> None:
        self.write_html(render_end_tag("u"))

    def render_u(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("u", content, **kwargs)

    def open_iframe(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("iframe", close_tag=False, **kwargs))

    def close_iframe(self) -> None:
        self.write_html(render_end_tag("iframe"))

    def render_iframe(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("iframe", content, **kwargs)

    def open_x(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("x", close_tag=False, **kwargs))

    def close_x(self) -> None:
        self.write_html(render_end_tag("x"))

    def render_x(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("x", content, **kwargs)

    def open_div(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("div", close_tag=False, **kwargs))

    def close_div(self) -> None:
        self.write_html(render_end_tag("div"))

    def render_div(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("div", content, **kwargs)

    def open_ul(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("ul", close_tag=False, **kwargs))

    def close_ul(self) -> None:
        self.write_html(render_end_tag("ul"))

    def render_ul(self, content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("ul", content, **kwargs)

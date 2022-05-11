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

from typing import final, Final, List, Optional, Union

from cmk.utils.exceptions import MKGeneralException

import cmk.gui.utils.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import OutputFunnel

from .tag_rendering import (
    HTMLContent,
    HTMLTagAttributeValue,
    render_element,
    render_end_tag,
    render_start_tag,
)


class HTMLWriter:
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

    def __init__(self, output_funnel: OutputFunnel, output_format: str, mobile: bool):
        self.output_funnel: Final = output_funnel
        self.output_format: Final = output_format
        self.mobile: Final = mobile
        self._final_javascript: List[str] = []

    def write_text(self, text: HTMLContent) -> None:
        """Write text. Highlighting tags such as h2|b|tt|i|br|pre|a|sup|p|li|ul|ol are not escaped."""
        self.write_html(HTML(escaping.escape_text(text)))

    def write_html(self, content: HTML) -> None:
        """Write HTML code directly, without escaping."""
        self.write(content)

    @final
    def write(self, text: HTMLContent) -> None:
        if not text:
            return

        if isinstance(text, (int, HTML)):
            text = str(text)

        if not isinstance(text, str):
            raise MKGeneralException(_("Type Error: html.write accepts str input objects only!"))

        self.output_funnel.write(text.encode("utf-8"))

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

    @staticmethod
    def render_a(
        content: HTMLContent, href: Union[None, str, str], **attrs: HTMLTagAttributeValue
    ) -> HTML:
        if href is not None:
            attrs["href"] = href
        return render_element("a", content, **attrs)

    def a(self, content: HTMLContent, href: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(HTMLWriter.render_a(content, href, **attrs))

    def stylesheet(self, href: str) -> None:
        self.link(rel="stylesheet", href=href, type_="text/css")

    def link(self, *, rel: str, href: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("link", rel=rel, href=href, close_tag=True, **attrs))

    @staticmethod
    def render_javascript(code: str) -> HTML:
        return HTML('<script type="text/javascript">\n%s\n</script>\n' % code)

    def final_javascript(self, code: str) -> None:
        self._final_javascript.append(code)

    def final_javascript_code(self) -> str:
        return "\n".join(self._final_javascript)

    def write_final_javascript(self) -> None:
        if not self._final_javascript:
            return
        self.javascript(self.final_javascript_code())

    def javascript(self, code: str) -> None:
        self.write_html(HTMLWriter.render_javascript(code))

    def javascript_file(self, src: str) -> None:
        """<script type="text/javascript" src="%(name)"/>\n"""
        self.write_html(render_element("script", "", type_="text/javascript", src=src))

    @staticmethod
    def render_img(src: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs["src"] = src
        return render_start_tag("img", close_tag=True, **attrs)

    def img(self, src: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(HTMLWriter.render_img(src, **attrs))

    def open_button(self, type_: str, **attrs: HTMLTagAttributeValue) -> None:
        attrs["type"] = type_
        self.write_html(render_start_tag("button", close_tag=True, **attrs))

    def play_sound(self, url: str) -> None:
        self.write_html(render_start_tag("audio autoplay", src_=url))

    @staticmethod
    def render_label(content: HTMLContent, for_: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs["for"] = for_
        return render_element("label", content, **attrs)

    def label(self, content: HTMLContent, for_: str, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(HTMLWriter.render_label(content, for_, **attrs))

    def li(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> None:
        """Only for text content. You can't put HTML structure here."""
        self.write_html(render_element("li", content, **attrs))

    @staticmethod
    def render_heading(content: HTMLContent) -> HTML:
        return render_element("h2", content)

    def heading(self, content: HTMLContent) -> None:
        self.write_html(HTMLWriter.render_heading(content))

    @staticmethod
    def render_br() -> HTML:
        return HTML("<br />")

    def br(self) -> None:
        self.write_html(HTMLWriter.render_br())

    @staticmethod
    def render_hr(**attrs: HTMLTagAttributeValue) -> HTML:
        return render_start_tag("hr", close_tag=True, **attrs)

    def hr(self, **attrs: HTMLTagAttributeValue) -> None:
        self.write_html(HTMLWriter.render_hr(**attrs))

    def rule(self) -> None:
        self.hr()

    @staticmethod
    def render_nbsp() -> HTML:
        return HTML("&nbsp;")

    def nbsp(self) -> None:
        self.write_html(HTMLWriter.render_nbsp())

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

    @staticmethod
    def render_pre(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("pre", content, **kwargs)

    def open_h2(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("h2", close_tag=False, **kwargs))

    def close_h2(self) -> None:
        self.write_html(render_end_tag("h2"))

    @staticmethod
    def render_h2(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("h2", content, **kwargs)

    def open_h3(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("h3", close_tag=False, **kwargs))

    def close_h3(self) -> None:
        self.write_html(render_end_tag("h3"))

    @staticmethod
    def render_h3(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("h3", content, **kwargs)

    def open_h1(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("h1", close_tag=False, **kwargs))

    def close_h1(self) -> None:
        self.write_html(render_end_tag("h1"))

    @staticmethod
    def render_h1(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("h1", content, **kwargs)

    def open_h4(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("h4", close_tag=False, **kwargs))

    def close_h4(self) -> None:
        self.write_html(render_end_tag("h4"))

    @staticmethod
    def render_h4(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("h4", content, **kwargs)

    def open_header(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("header", close_tag=False, **kwargs))

    def close_header(self) -> None:
        self.write_html(render_end_tag("header"))

    @staticmethod
    def render_header(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("header", content, **kwargs)

    def open_tag(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tag", close_tag=False, **kwargs))

    def close_tag(self) -> None:
        self.write_html(render_end_tag("tag"))

    @staticmethod
    def render_tag(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tag", content, **kwargs)

    def open_table(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("table", close_tag=False, **kwargs))

    def close_table(self) -> None:
        self.write_html(render_end_tag("table"))

    @staticmethod
    def render_table(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("table", content, **kwargs)

    def open_select(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("select", close_tag=False, **kwargs))

    def close_select(self) -> None:
        self.write_html(render_end_tag("select"))

    @staticmethod
    def render_select(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("select", content, **kwargs)

    def open_row(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("row", close_tag=False, **kwargs))

    def close_row(self) -> None:
        self.write_html(render_end_tag("row"))

    @staticmethod
    def render_row(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("row", content, **kwargs)

    def open_style(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("style", close_tag=False, **kwargs))

    def close_style(self) -> None:
        self.write_html(render_end_tag("style"))

    @staticmethod
    def render_style(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("style", content, **kwargs)

    def open_span(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("span", close_tag=False, **kwargs))

    def close_span(self) -> None:
        self.write_html(render_end_tag("span"))

    @staticmethod
    def render_span(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("span", content, **kwargs)

    def open_sub(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("sub", close_tag=False, **kwargs))

    def close_sub(self) -> None:
        self.write_html(render_end_tag("sub"))

    @staticmethod
    def render_sub(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("sub", content, **kwargs)

    def open_script(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("script", close_tag=False, **kwargs))

    def close_script(self) -> None:
        self.write_html(render_end_tag("script"))

    @staticmethod
    def render_script(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("script", content, **kwargs)

    def open_tt(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tt", close_tag=False, **kwargs))

    def close_tt(self) -> None:
        self.write_html(render_end_tag("tt"))

    @staticmethod
    def render_tt(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tt", content, **kwargs)

    def open_tr(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tr", close_tag=False, **kwargs))

    def close_tr(self) -> None:
        self.write_html(render_end_tag("tr"))

    @staticmethod
    def render_tr(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tr", content, **kwargs)

    def open_tbody(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tbody", close_tag=False, **kwargs))

    def close_tbody(self) -> None:
        self.write_html(render_end_tag("tbody"))

    @staticmethod
    def render_tbody(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tbody", content, **kwargs)

    def open_li(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("li", close_tag=False, **kwargs))

    def close_li(self) -> None:
        self.write_html(render_end_tag("li"))

    @staticmethod
    def render_li(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("li", content, **kwargs)

    def open_html(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("html", close_tag=False, **kwargs))

    def close_html(self) -> None:
        self.write_html(render_end_tag("html"))

    @staticmethod
    def render_html(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("html", content, **kwargs)

    def open_th(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("th", close_tag=False, **kwargs))

    def close_th(self) -> None:
        self.write_html(render_end_tag("th"))

    @staticmethod
    def render_th(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("th", content, **kwargs)

    def open_sup(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("sup", close_tag=False, **kwargs))

    def close_sup(self) -> None:
        self.write_html(render_end_tag("sup"))

    @staticmethod
    def render_sup(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
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

    @staticmethod
    def render_td(
        content: HTMLContent, colspan: Optional[int] = None, **kwargs: HTMLTagAttributeValue
    ) -> HTML:
        return render_element(
            "td", content, colspan=str(colspan) if colspan is not None else None, **kwargs
        )

    def open_thead(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("thead", close_tag=False, **kwargs))

    def close_thead(self) -> None:
        self.write_html(render_end_tag("thead"))

    @staticmethod
    def render_thead(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("thead", content, **kwargs)

    def open_body(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("body", close_tag=False, **kwargs))

    def close_body(self) -> None:
        self.write_html(render_end_tag("body"))

    @staticmethod
    def render_body(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("body", content, **kwargs)

    def open_head(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("head", close_tag=False, **kwargs))

    def close_head(self) -> None:
        self.write_html(render_end_tag("head"))

    @staticmethod
    def render_head(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("head", content, **kwargs)

    def open_fieldset(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("fieldset", close_tag=False, **kwargs))

    def close_fieldset(self) -> None:
        self.write_html(render_end_tag("fieldset"))

    @staticmethod
    def render_fieldset(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
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

    @staticmethod
    def render_option(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("option", content, **kwargs)

    def open_form(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("form", close_tag=False, **kwargs))

    def close_form(self) -> None:
        self.write_html(render_end_tag("form"))

    @staticmethod
    def render_form(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("form", content, **kwargs)

    def open_tags(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("tags", close_tag=False, **kwargs))

    def close_tags(self) -> None:
        self.write_html(render_end_tag("tags"))

    @staticmethod
    def render_tags(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("tags", content, **kwargs)

    def open_canvas(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("canvas", close_tag=False, **kwargs))

    def close_canvas(self) -> None:
        self.write_html(render_end_tag("canvas"))

    @staticmethod
    def render_canvas(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("canvas", content, **kwargs)

    def open_nobr(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("nobr", close_tag=False, **kwargs))

    def close_nobr(self) -> None:
        self.write_html(render_end_tag("nobr"))

    @staticmethod
    def render_nobr(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("nobr", content, **kwargs)

    def open_br(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("br", close_tag=False, **kwargs))

    def close_br(self) -> None:
        self.write_html(render_end_tag("br"))

    def open_strong(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("strong", close_tag=False, **kwargs))

    def close_strong(self) -> None:
        self.write_html(render_end_tag("strong"))

    @staticmethod
    def render_strong(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("strong", content, **kwargs)

    def close_a(self) -> None:
        self.write_html(render_end_tag("a"))

    def open_b(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("b", close_tag=False, **kwargs))

    def close_b(self) -> None:
        self.write_html(render_end_tag("b"))

    @staticmethod
    def render_b(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("b", content, **kwargs)

    def open_center(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("center", close_tag=False, **kwargs))

    def close_center(self) -> None:
        self.write_html(render_end_tag("center"))

    @staticmethod
    def render_center(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("center", content, **kwargs)

    def open_footer(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("footer", close_tag=False, **kwargs))

    def close_footer(self) -> None:
        self.write_html(render_end_tag("footer"))

    @staticmethod
    def render_footer(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("footer", content, **kwargs)

    def open_i(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("i", close_tag=False, **kwargs))

    def close_i(self) -> None:
        self.write_html(render_end_tag("i"))

    @staticmethod
    def render_i(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("i", content, **kwargs)

    def close_button(self) -> None:
        self.write_html(render_end_tag("button"))

    def open_title(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("title", close_tag=False, **kwargs))

    def close_title(self) -> None:
        self.write_html(render_end_tag("title"))

    @staticmethod
    def render_title(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("title", content, **kwargs)

    def open_p(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("p", close_tag=False, **kwargs))

    def close_p(self) -> None:
        self.write_html(render_end_tag("p"))

    @staticmethod
    def render_p(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("p", content, **kwargs)

    def open_u(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("u", close_tag=False, **kwargs))

    def close_u(self) -> None:
        self.write_html(render_end_tag("u"))

    @staticmethod
    def render_u(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("u", content, **kwargs)

    def open_iframe(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("iframe", close_tag=False, **kwargs))

    def close_iframe(self) -> None:
        self.write_html(render_end_tag("iframe"))

    @staticmethod
    def render_iframe(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("iframe", content, **kwargs)

    def open_x(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("x", close_tag=False, **kwargs))

    def close_x(self) -> None:
        self.write_html(render_end_tag("x"))

    @staticmethod
    def render_x(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("x", content, **kwargs)

    def open_div(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("div", close_tag=False, **kwargs))

    def close_div(self) -> None:
        self.write_html(render_end_tag("div"))

    @staticmethod
    def render_div(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("div", content, **kwargs)

    def open_ul(self, **kwargs: HTMLTagAttributeValue) -> None:
        self.write_html(render_start_tag("ul", close_tag=False, **kwargs))

    def close_ul(self) -> None:
        self.write_html(render_end_tag("ul"))

    @staticmethod
    def render_ul(content: HTMLContent, **kwargs: HTMLTagAttributeValue) -> HTML:
        return render_element("ul", content, **kwargs)

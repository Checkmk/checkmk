#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import json
from typing import Any, assert_never

from cmk.web.htmllib.tag_rendering import (
    HTMLContent,
    HTMLTagAttributeValue,
    render_element,
    render_end_tag,
    render_start_tag,
)
from cmk.web.utils.escaping import escape_text
from cmk.web.utils.html import HTML


def _dump_standard_compliant_json(data: object) -> str:
    # default json.dumps produces non standard compliant output: NaN, Infinity, -Infinity are not
    # part of the JSON spec. in case you still serialize such a value with pythons default
    # json.dumps you see very confusing parsing errors in the frontend.
    # this function will make sure that a backend error is thrown if one of the three values is
    # serialized, which makes it more obvious whats going wrong.
    return json.dumps(data, allow_nan=False)


class HtmlBuilder:
    """Buffer-based HTML builder."""

    def __init__(self) -> None:
        self._parts: list[str] = []

    # ------------------------------------------------------------------
    # Core write helpers
    # ------------------------------------------------------------------

    def write_html(self, content: HTML) -> HtmlBuilder:
        """Append pre-rendered HTML without escaping."""
        if content:
            self._parts.append(str(content))
        return self

    def write_text(self, text: HTMLContent) -> HtmlBuilder:
        """Append text with strict HTML escaping."""
        match text:
            case None:
                pass
            case int():
                self._parts.append(str(HTML.with_escaping(str(text))))
            case HTML():
                self._parts.append(str(text))
            case str():
                self._parts.append(str(HTML.with_escaping(text)))
            case _ as unreachable:
                assert_never(unreachable)
        return self

    def write_text_permissive(self, text: HTMLContent) -> HtmlBuilder:
        """Append text allowing safe markup tags (h1, b, i, br, …)."""
        self._parts.append(escape_text(text))
        return self

    def render(self) -> str:
        """Drain the buffer and return the accumulated HTML string."""
        result = "".join(self._parts)
        self._parts.clear()
        return result

    # ------------------------------------------------------------------
    # Generic open / close
    # ------------------------------------------------------------------

    def open(self, tag: str, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag(tag, close_tag=False, **attrs)))
        return self

    def close(self, tag: str) -> HtmlBuilder:
        self._parts.append(str(render_end_tag(tag)))
        return self

    # ------------------------------------------------------------------
    # <a>
    # ------------------------------------------------------------------

    def open_a(self, href: str | None = None, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        if href is not None:
            attrs["href"] = href
        self._parts.append(str(render_start_tag("a", close_tag=False, **attrs)))
        return self

    def close_a(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("a")))
        return self

    @staticmethod
    def render_a(content: HTMLContent, href: str | None, **attrs: HTMLTagAttributeValue) -> HTML:
        if href is not None:
            attrs["href"] = href
        return render_element("a", content, **attrs)

    def a(self, content: HTMLContent, href: str, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(HtmlBuilder.render_a(content, href, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <b>
    # ------------------------------------------------------------------

    def open_b(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("b", close_tag=False, **attrs)))
        return self

    def close_b(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("b")))
        return self

    @staticmethod
    def render_b(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("b", content, **attrs)

    def b(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(HtmlBuilder.render_b(content, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <br>
    # ------------------------------------------------------------------

    @staticmethod
    def render_br() -> HTML:
        return HTML.without_escaping("<br />")

    def br(self) -> HtmlBuilder:
        self._parts.append("<br />")
        return self

    # ------------------------------------------------------------------
    # <center>
    # ------------------------------------------------------------------

    def open_center(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("center", close_tag=False, **attrs)))
        return self

    def close_center(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("center")))
        return self

    @staticmethod
    def render_center(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("center", content, **attrs)

    # ------------------------------------------------------------------
    # <div>
    # ------------------------------------------------------------------

    def open_div(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("div", close_tag=False, **attrs)))
        return self

    def close_div(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("div")))
        return self

    @staticmethod
    def render_div(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("div", content, **attrs)

    def div(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("div", content, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <form>
    # ------------------------------------------------------------------

    @staticmethod
    def render_form(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("form", content, **attrs)

    # ------------------------------------------------------------------
    # <h1> / <h2> / <h3>
    # ------------------------------------------------------------------

    def open_h1(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("h1", close_tag=False, **attrs)))
        return self

    def close_h1(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("h1")))
        return self

    @staticmethod
    def render_h1(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("h1", content, **attrs)

    def h1(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("h1", content, **attrs)))
        return self

    def open_h2(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("h2", close_tag=False, **attrs)))
        return self

    def close_h2(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("h2")))
        return self

    @staticmethod
    def render_h2(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("h2", content, **attrs)

    def h2(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("h2", content, **attrs)))
        return self

    def open_h3(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("h3", close_tag=False, **attrs)))
        return self

    def close_h3(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("h3")))
        return self

    @staticmethod
    def render_h3(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("h3", content, **attrs)

    def h3(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("h3", content, **attrs)))
        return self

    @staticmethod
    def render_heading(content: HTMLContent) -> HTML:
        return render_element("h2", content)

    def heading(self, content: HTMLContent) -> HtmlBuilder:
        self._parts.append(str(render_element("h2", content)))
        return self

    # ------------------------------------------------------------------
    # <hr>
    # ------------------------------------------------------------------

    @staticmethod
    def render_hr(**attrs: HTMLTagAttributeValue) -> HTML:
        return render_start_tag("hr", close_tag=True, **attrs)

    def hr(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("hr", close_tag=True, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <i>
    # ------------------------------------------------------------------

    @staticmethod
    def render_i(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("i", content, **attrs)

    def i(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("i", content, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <iframe>
    # ------------------------------------------------------------------

    @staticmethod
    def render_iframe(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("iframe", content, **attrs)

    # ------------------------------------------------------------------
    # <img>
    # ------------------------------------------------------------------

    @staticmethod
    def render_img(src: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs["src"] = src
        return render_start_tag("img", close_tag=True, **attrs)

    def img(self, src: str, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(HtmlBuilder.render_img(src, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <label>
    # ------------------------------------------------------------------

    @staticmethod
    def render_label(content: HTMLContent, for_: str, **attrs: HTMLTagAttributeValue) -> HTML:
        attrs["for"] = for_
        return render_element("label", content, **attrs)

    # ------------------------------------------------------------------
    # <li>
    # ------------------------------------------------------------------

    def open_li(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("li", close_tag=False, **attrs)))
        return self

    def close_li(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("li")))
        return self

    @staticmethod
    def render_li(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("li", content, **attrs)

    def li(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        """Only for text content. You can't put HTML structure here."""
        self._parts.append(str(render_element("li", content, **attrs)))
        return self

    # ------------------------------------------------------------------
    # &nbsp;
    # ------------------------------------------------------------------

    @staticmethod
    def render_nbsp() -> HTML:
        return HTML.without_escaping("&nbsp;")

    def nbsp(self) -> HtmlBuilder:
        self._parts.append("&nbsp;")
        return self

    # ------------------------------------------------------------------
    # <nobr>
    # ------------------------------------------------------------------

    def open_nobr(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("nobr", close_tag=False, **attrs)))
        return self

    def close_nobr(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("nobr")))
        return self

    @staticmethod
    def render_nobr(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("nobr", content, **attrs)

    # ------------------------------------------------------------------
    # <p>
    # ------------------------------------------------------------------

    def open_p(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("p", close_tag=False, **attrs)))
        return self

    def close_p(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("p")))
        return self

    @staticmethod
    def render_p(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("p", content, **attrs)

    def p(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("p", content, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <pre>
    # ------------------------------------------------------------------

    def open_pre(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("pre", close_tag=False, **attrs)))
        return self

    def close_pre(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("pre")))
        return self

    @staticmethod
    def render_pre(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("pre", content, **attrs)

    def pre(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("pre", content, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <script>
    # ------------------------------------------------------------------

    @staticmethod
    def render_javascript(code: str, **attrs: HTMLTagAttributeValue) -> HTML:
        # We can not use the regular html.escape since it escapes with HTML entities, which
        # are not interpreted properly in script. Using the unicode escape sequences seems to
        # have the desired effect.
        # In case it turns out that it has unwanted side effects, we may finally have to get rid of
        # the inline scripts, which would be a great idea anyways, but is quite some effort.
        def escape_for_script(code: str) -> str:
            return code.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")

        return render_element("script", HTML.without_escaping(escape_for_script(code)), **attrs)

    # ------------------------------------------------------------------
    # <span>
    # ------------------------------------------------------------------

    def open_span(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("span", close_tag=False, **attrs)))
        return self

    def close_span(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("span")))
        return self

    @staticmethod
    def render_span(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("span", content, **attrs)

    def span(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("span", content, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <strong>
    # ------------------------------------------------------------------

    @staticmethod
    def render_strong(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("strong", content, **attrs)

    # ------------------------------------------------------------------
    # <sup>
    # ------------------------------------------------------------------

    @staticmethod
    def render_sup(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("sup", content, **attrs)

    # ------------------------------------------------------------------
    # <table> / <thead> / <tbody> / <tr> / <th> / <td>
    # ------------------------------------------------------------------

    def open_table(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("table", close_tag=False, **attrs)))
        return self

    def close_table(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("table")))
        return self

    @staticmethod
    def render_table(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("table", content, **attrs)

    def open_thead(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("thead", close_tag=False, **attrs)))
        return self

    def close_thead(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("thead")))
        return self

    def open_tbody(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("tbody", close_tag=False, **attrs)))
        return self

    def close_tbody(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("tbody")))
        return self

    def open_tr(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("tr", close_tag=False, **attrs)))
        return self

    def close_tr(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("tr")))
        return self

    @staticmethod
    def render_tr(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("tr", content, **attrs)

    def tr(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("tr", content, **attrs)))
        return self

    def open_th(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("th", close_tag=False, **attrs)))
        return self

    def close_th(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("th")))
        return self

    @staticmethod
    def render_th(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("th", content, **attrs)

    def th(self, content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_element("th", content, **attrs)))
        return self

    def open_td(self, colspan: int | None = None, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(
            str(
                render_start_tag(
                    "td",
                    close_tag=False,
                    colspan=str(colspan) if colspan is not None else None,
                    **attrs,
                )
            )
        )
        return self

    def close_td(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("td")))
        return self

    @staticmethod
    def render_td(
        content: HTMLContent, colspan: int | None = None, **attrs: HTMLTagAttributeValue
    ) -> HTML:
        return render_element(
            "td", content, colspan=str(colspan) if colspan is not None else None, **attrs
        )

    def td(
        self, content: HTMLContent, colspan: int | None = None, **attrs: HTMLTagAttributeValue
    ) -> HtmlBuilder:
        self._parts.append(str(HtmlBuilder.render_td(content, colspan, **attrs)))
        return self

    # ------------------------------------------------------------------
    # <title>
    # ------------------------------------------------------------------

    @staticmethod
    def render_title(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("title", content, **attrs)

    # ------------------------------------------------------------------
    # <tt>
    # ------------------------------------------------------------------

    @staticmethod
    def render_tt(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("tt", content, **attrs)

    # ------------------------------------------------------------------
    # <ul> / <ol>
    # ------------------------------------------------------------------

    def open_ul(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("ul", close_tag=False, **attrs)))
        return self

    def close_ul(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("ul")))
        return self

    @staticmethod
    def render_ul(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("ul", content, **attrs)

    def open_ol(self, **attrs: HTMLTagAttributeValue) -> HtmlBuilder:
        self._parts.append(str(render_start_tag("ol", close_tag=False, **attrs)))
        return self

    def close_ol(self) -> HtmlBuilder:
        self._parts.append(str(render_end_tag("ol")))
        return self

    # ------------------------------------------------------------------
    # Checkmk-specific custom elements
    # ------------------------------------------------------------------

    @staticmethod
    def render_tag(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("tag", content, **attrs)

    @staticmethod
    def render_tags(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("tags", content, **attrs)

    @staticmethod
    def render_x(content: HTMLContent, **attrs: HTMLTagAttributeValue) -> HTML:
        return render_element("x", content, **attrs)

    @staticmethod
    def render_vue_component(
        component_name: str, data: dict[str, Any], **attrs: HTMLTagAttributeValue
    ) -> HTML:
        return render_element(
            component_name,
            None,
            data=_dump_standard_compliant_json(data),
            **attrs,
        )

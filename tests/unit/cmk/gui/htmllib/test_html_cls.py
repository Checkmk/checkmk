#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback

from tests.testlib import compare_html

from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.context import html
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.user_errors import user_errors


def test_render_help_empty(request_context):
    assert html.have_help is False
    assert html.render_help(None) == HTML("")
    assert isinstance(html.render_help(None), HTML)
    assert html.have_help is False

    assert html.render_help("") == HTML("")
    assert isinstance(html.render_help(""), HTML)
    assert html.render_help("    ") == HTML("")
    assert isinstance(html.render_help("    "), HTML)


def test_render_help_html(request_context):
    assert html.have_help is False
    assert compare_html(
        html.render_help(HTML("<abc>")), HTML('<div style="display:none" class="help"><abc></div>')
    )
    # NOTE: This seems to be a mypy 0.780 bug.
    assert html.have_help is True  # type: ignore[comparison-overlap]


def test_render_help_text(request_context):
    assert compare_html(
        html.render_help("äbc"), HTML('<div style="display:none" class="help">äbc</div>')
    )


def test_render_help_visible(request_context, monkeypatch):
    monkeypatch.setattr(LoggedInUser, "show_help", property(lambda s: True))
    assert user.show_help is True
    assert compare_html(
        html.render_help("äbc"), HTML('<div style="display:block" class="help">äbc</div>')
    )


def test_add_manual_link(request_context):
    assert user.language is None
    assert compare_html(
        html.render_help("[intro_welcome|Welcome]"),
        HTML(
            '<div style="display:none" class="help"><a href="https://docs.checkmk.com/master/en/intro_welcome.html" target="_blank">Welcome</a></div>'
        ),
    )


def test_add_manual_link_localized(request_context, monkeypatch):
    monkeypatch.setattr(user, "language", lambda: "de")
    assert compare_html(
        html.render_help("[intro_welcome|Welcome]"),
        HTML(
            '<div style="display:none" class="help"><a href="https://docs.checkmk.com/master/de/intro_welcome.html" target="_blank">Welcome</a></div>'
        ),
    )


def test_add_manual_link_anchor(request_context, monkeypatch):
    monkeypatch.setattr(user, "language", lambda: "de")
    assert compare_html(
        html.render_help("[graphing#rrds|RRDs]"),
        HTML(
            '<div style="display:none" class="help"><a href="https://docs.checkmk.de/master/de/graphing.html#rrds" target="_blank">RRDs</a></div>'
        ),
    )


def test_user_error(request_context):
    with output_funnel.plugged():
        html.user_error(MKUserError(None, "asd <script>alert(1)</script> <br> <b>"))
        c = output_funnel.drain()
    assert c == '<div class="error">asd &lt;script&gt;alert(1)&lt;/script&gt; <br> <b></div>'


def test_show_user_errors(request_context):
    assert not user_errors
    user_errors.add(MKUserError(None, "asd <script>alert(1)</script> <br> <b>"))
    assert user_errors

    with output_funnel.plugged():
        html.show_user_errors()
        c = output_funnel.drain()
    assert c == '<div class="error">asd &lt;script&gt;alert(1)&lt;/script&gt; <br> <b></div>'


def test_HTMLWriter(request_context):
    with output_funnel.plugged():

        with output_funnel.plugged():
            html.open_div()
            text = output_funnel.drain()
            assert text.rstrip("\n").rstrip(" ") == "<div>"

        with output_funnel.plugged():
            # html.open_div().write("test").close_div()
            html.open_div()
            html.write_text("test")
            html.close_div()
            assert compare_html(output_funnel.drain(), "<div>test</div>")

        with output_funnel.plugged():
            # html.open_table().open_tr().td("1").td("2").close_tr().close_table()
            html.open_table()
            html.open_tr()
            html.td("1")
            html.td("2")
            html.close_tr()
            html.close_table()
            assert compare_html(
                output_funnel.drain(), "<table><tr><td>1</td><td>2</td></tr></table>"
            )

        with output_funnel.plugged():
            html.div("test", **{"</div>malicious_code<div>": "trends"})
            assert compare_html(
                output_funnel.drain(),
                "<div &lt;/div&gt;malicious_code&lt;div&gt;=trends>test</div>",
            )

        a = "\u2665"
        with output_funnel.plugged():
            assert html.render_a("test", href="www.test.case")
            html.render_a("test", href="www.test.case")
            html.render_a("test", href="www.test.case")
            html.render_a("test", href="www.test.case")
            try:
                assert html.render_a(
                    "test",
                    href=str("www.test.case"),
                    id_=str("something"),
                    class_=str("test_%s") % a,
                )
            except Exception as e:
                traceback.print_exc()
                print(e)


def test_multiclass_call(request_context):
    with output_funnel.plugged():
        html.div("", class_="1", css="3", cssclass="4", **{"class": "2"})
        written_text = "".join(output_funnel.drain())
    assert compare_html(written_text, '<div class="1 3 4 2"></div>')


def test_exception_handling(request_context):
    try:
        raise Exception("Test")
    except Exception as e:
        assert compare_html(html.render_div(str(e)), "<div>%s</div>" % e)


def test_text_input(request_context):
    with output_funnel.plugged():
        html.text_input("tralala")
        written_text = "".join(output_funnel.drain())
        assert compare_html(
            written_text, '<input style="" name="tralala" type="text" class="text" value=\'\' />'
        )

    with output_funnel.plugged():
        html.text_input("blabla", cssclass="blubb")
        written_text = "".join(output_funnel.drain())
        assert compare_html(
            written_text, '<input style="" name="tralala" type="text" class="blubb" value=\'\' />'
        )

    with output_funnel.plugged():
        html.text_input("blabla", autocomplete="yep")
        written_text = "".join(output_funnel.drain())
        assert compare_html(
            written_text,
            '<input style="" name="blabla" autocomplete="yep" type="text" class="text" value=\'\' />',
        )

    with output_funnel.plugged():
        html.text_input("blabla", placeholder="placido", data_world="welt", data_max_labels=42)
        written_text = "".join(output_funnel.drain())
        assert compare_html(
            written_text, '<input style="" name="tralala" type="text" class="text" value=\'\' />'
        )


def test_render_a(request_context):
    a = html.render_a("bla", href="blu", class_=["eee"], target="_blank")
    assert compare_html(a, '<a href="blu" target="_blank" class="eee">bla</a>')

    a = html.render_a(
        "b<script>alert(1)</script>la",
        href="b<script>alert(1)</script>lu",
        class_=["eee"],
        target="_blank",
    )
    assert compare_html(
        a,
        '<a href="b&lt;script&gt;alert(1)&lt;/script&gt;lu" target="_blank" '
        'class="eee">b&lt;script&gt;alert(1)&lt;/script&gt;la</a>',
    )

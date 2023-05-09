#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback

from cmk.gui.globals import html
from tools import compare_html  # type: ignore[import]


def test_ABCHTMLGenerator(register_builtin_html):
    with html.plugged():

        with html.plugged():
            html.open_div()
            text = html.drain()
            assert text.rstrip('\n').rstrip(' ') == "<div>"

        with html.plugged():
            #html.open_div().write("test").close_div()
            html.open_div()
            html.write("test")
            html.close_div()
            assert compare_html(html.drain(), "<div>test</div>")

        with html.plugged():
            #html.open_table().open_tr().td("1").td("2").close_tr().close_table()
            html.open_table()
            html.open_tr()
            html.td("1")
            html.td("2")
            html.close_tr()
            html.close_table()
            assert compare_html(html.drain(), "<table><tr><td>1</td><td>2</td></tr></table>")

        with html.plugged():
            html.div("test", **{"</div>malicious_code<div>": "trends"})
            assert compare_html(html.drain(),
                                "<div &lt;/div&gt;malicious_code&lt;div&gt;=trends>test</div>")

        a = u"\u2665"
        with html.plugged():
            assert html.render_a("test", href="www.test.case")
            html.render_a(u"test", href="www.test.case")
            html.render_a("test", href=u"www.test.case")
            html.render_a(u"test", href=u"www.test.case")
            try:
                assert html.render_a(u"test",
                                     href=str("www.test.case"),
                                     id_=str("something"),
                                     class_=str("test_%s") % a)
            except Exception as e:
                traceback.print_exc()
                print(e)


def test_multiclass_call(register_builtin_html):
    with html.plugged():
        html.div('', class_="1", css="3", cssclass="4", **{"class": "2"})
        written_text = "".join(html.drain())
    assert compare_html(written_text, "<div class=\"1 3 4 2\"></div>")


def test_exception_handling(register_builtin_html):
    try:
        raise Exception("Test")
    except Exception as e:
        assert compare_html(html.render_div(str(e)), "<div>%s</div>" % e)


def test_text_input(register_builtin_html):
    with html.plugged():
        html.text_input('tralala')
        written_text = "".join(html.drain())
        assert compare_html(
            written_text, '<input style="" name="tralala" type="text" class="text" value=\'\' />')

    with html.plugged():
        html.text_input('blabla', cssclass='blubb')
        written_text = "".join(html.drain())
        assert compare_html(
            written_text, '<input style="" name="tralala" type="text" class="blubb" value=\'\' />')

    with html.plugged():
        html.text_input('blabla', autocomplete='yep')
        written_text = "".join(html.drain())
        assert compare_html(
            written_text,
            '<input style="" name="blabla" autocomplete="yep" type="text" class="text" value=\'\' />'
        )

    with html.plugged():
        html.text_input('blabla', placeholder='placido', data_world='welt', data_max_labels=42)
        written_text = "".join(html.drain())
        assert compare_html(
            written_text, '<input style="" name="tralala" type="text" class="text" value=\'\' />')


def test_render_a(register_builtin_html):
    a = html.render_a("bla", href="blu", class_=["eee"], target="_blank")
    assert compare_html(a, '<a href="blu" target="_blank" class="eee">bla</a>')

    a = html.render_a("b<script>alert(1)</script>la",
                      href="b<script>alert(1)</script>lu",
                      class_=["eee"],
                      target="_blank")
    assert compare_html(
        a, '<a href="b&lt;script&gt;alert(1)&lt;/script&gt;lu" target="_blank" '
        'class="eee">b&lt;script&gt;alert(1)&lt;/script&gt;la</a>')

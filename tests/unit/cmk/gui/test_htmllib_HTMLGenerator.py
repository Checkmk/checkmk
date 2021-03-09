#!/usr/bin/env python
# -*- coding: utf-8 -*-

import traceback

from cmk.gui.globals import html
from tools import compare_html


def test_HTMLGenerator(register_builtin_html):
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
                                     href=unicode("www.test.case"),
                                     id_=unicode("something"),
                                     class_=unicode("test_%s") % a)
            except Exception as e:
                print traceback.print_exc()
                print e


def test_multiclass_call(register_builtin_html):
    with html.plugged():
        html.div('', class_="1", css="3", cssclass="4", **{"class": "2"})
        written_text = "".join(html.drain())
    assert compare_html(written_text, "<div class=\"1 3 4 2\"></div>")


def test_exception_handling(register_builtin_html):
    try:
        raise Exception("Test")
    except Exception as e:
        assert compare_html(html.render_div(e), "<div>%s</div>" % e)

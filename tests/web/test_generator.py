#!/usr/bin/python
# call using
# > py.test -s -k test_HTML_generator.py

# external imports
import re

# internal imports
from htmllib import HTML, HTMLGenerator
import tools


def test_HTMLGenerator():

    html = HTMLGenerator()
    html.plug()

    with html.plugged():
        html.open_div()
        text = html.drain()
        assert text.rstrip('\n').rstrip(' ') == "<div>"

    with html.plugged():
        #html.open_div().write("test").close_div()
        html.open_div()
        html.write("test")
        html.close_div()
        assert tools.compare_html(html.drain(), "<div>test</div>")

    with html.plugged():
        #html.open_table().open_tr().td("1").td("2").close_tr().close_table()
        html.open_table()
        html.open_tr()
        html.td("1")
        html.td("2")
        html.close_tr()
        html.close_table()
        assert tools.compare_html(html.drain(), "<table><tr><td>1</td><td>2</td></tr></table>")


def test_exception_handling():
    html = HTMLGenerator()
    html.plug()
    try:
        raise Exception("Test")
    except Exception, e:
        assert tools.compare_html(html.render_div(e), "<div>%s</div>" % e)

#!/usr/bin/python
# call using
# > py.test -s -k test_HTML_generator.py

# enable imports from web directory
from testlib import cmk_path
import sys
sys.path.insert(0, "%s/web/htdocs" % cmk_path())

# external imports
import re

# internal imports
from htmllib import HTML, HTMLGenerator




def test_HTMLGenerator():

    html = HTMLGenerator()
    html.plug()

    html.open_div()
    assert html.drain() == "<div>"

    #html.open_div().write("test").close_div()
    html.open_div()
    html.write("test")
    html.close_div()
    assert html.drain() == "<div>test</div>"

    #html.open_table().open_tr().td("1").td("2").close_tr().close_table()
    html.open_table()
    html.open_tr()
    html.td("1")
    html.td("2")
    html.close_tr()
    html.close_table()
    assert html.drain() == "<table><tr><td>1</td><td>2</td></tr></table>"

def test_exception_handling():
    html = HTMLGenerator()
    html.plug()
    try:
        raise Exception("Test")
    except Exception, e:
        assert html.render_div(e) == "<div>%s</div>" % e

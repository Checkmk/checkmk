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

    html.a("Test", href = "javascript:void(0);",
            onclick = "testfunction(\"The whole wide world.\")")

    print html.drain()
    html.plug()

    submit = "Title"

    html.a("Test", href="#", onfocus="if (this.blur) this.blur();",
            onclick="this.innerHTML=\'%s\'; document.location.reload();" % submit)

    print html.drain()
    html.plug()

    html.a("Test", href = "javascript:void(0);",
            onmouseover="this.style.backgroundImage=\"url(\'images/contextlink%s_hi.png\')\";" % submit)

    print html.drain()
    html.plug()

    html.a("Test", href = "javascript:void(0);",
        onkeydown="function(e) { if (!e) e = window.event; textinput_enter_submit(e, \"%s\"); };" % submit)

    print html.drain()
    assert True

    text = "Toto &nbsp; <br>"
    assert html.render_text(text) == text

    text = "<u> Unterstrichen </u>"
    assert html.render_text(text) == text
    print html.render_text(text)


#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# enable imports from web directory
from testlib import cmk_path
import sys
sys.path.insert(0, "%s/web/htdocs" % cmk_path())

# external imports
import re

import i18n

# internal imports
from htmllib import html
from htmllib import HTMLGenerator, HTMLCheck_MK
from tools import compare_html , gentest, compare_and_empty
from classes import HTMLOrigTester, GeneratorTester, HTMLCheck_MKTester, DeprecatedRenderer







def test_select():

    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    label = ["label", "None"]
    value = ["value", "val"]
    varnames = ["name1", "varname"]
    choices = [[(1,"ch11"), (2,"ch12")], [(1,"ch21"), (2,"ch22")]]
    dfaults = ["", None,  "default"]
    onchange = [None, "javascript:void()"]
    attrs = {"title": "LOL", "style": "one love"}

    for n in varnames:
        for c in choices:
            for d in dfaults:
                for o in onchange:
                    old.add_var(n, n)
                    new.add_var(n, n)
                    old.user_errors = {n: "(not) a test error"}
                    new.user_errors = {n: "(not) a test error"}

                    old.select(n,c,d,o,attrs)
                    new.select(n,c,d,o,attrs)
                    compare_and_empty(old, new)

def test_icon_select():

    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    label = ["label", "None"]
    value = ["value", "val"]
    varnames = ["name1", "varname"]
    choices = [[(1,"ch11", "ico1"), (2,"ch12", "ico2")], [(1,"ch21", "ico1"), (2,"ch22", "ico2")]]
    dfaults = ["", None,  "default"]
    onchange = [None, "javascript:void()"]
    attrs = {"title": "LOL", "style": "one love"}

    for n in varnames:
        for c in choices:
            for d in dfaults:
                old.add_var(n, n)
                new.add_var(n, n)

                old.icon_select(n,c,d)
                new.icon_select(n,c,d)
                compare_and_empty(old, new)


def test_radiobuttons():

    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()


    mobile = [True, False]
    horizontal = [True, False]

    checked = [True, False]
    label = ["label", "None"]
    value = ["value", "val"]
    varnames = ["name1", "varname"]

    for m in mobile:
        for l in label:
            for c in checked:
                for h in horizontal:
                    old.mobile = m
                    new.mobile = m
                    old.begin_radio_group(horizontal=h)
                    new.begin_radio_group(horizontal=h)
                    for v, n in zip(value, varnames):
                        old.radiobutton( n, v, c, l)
                        new.radiobutton( n, v, c, l)
                    old.end_radio_group()
                    new.end_radio_group()
                    compare_and_empty(old, new)


def test_text_area():

    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()

    varname = ["varname", "var"]
    dflt_val = [None, "test"]
    rows = 4
    cols = 30
    attrs = [ {"style": "height:40px;", "name": "test"}, {"style": "height:40px;", "class": "test"} ]
    try_max_width = [True, False]

    for v in varname:
        for d in dflt_val:
             for a in attrs:
                for t in try_max_width:
                     print v,d,a,t
                     gentest(old, new, lambda x: x.text_area(v,d,rows, cols, a,t))



def test_text_input():

    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()

    varname = ["varname", "var"]
    dflt_val = [None, "test"]
    cssclass = ["text"]
    label = [None, "label", 2]
    id_ = [None, "id1"]
    attrs = [ {"style": "height:40px;", "name": "test"}, {"style": "height:40px;", "class": "test"} ]
    submit = [None, "submit"]
    args = [{"size": "max"}, {"size": 4, "autocomplete" : "oh yeah!"}]

    for v in varname:
        for d in dflt_val:
            for c in cssclass:
                for l in label:
                    for i in id_:
                        for s in submit:
                            for a in attrs:
                                for arg in args:
                                    print v,d,c,l,i,s,a,arg
                                    old.add_var(v, v)
                                    new.add_var(v, v)
                                    old.user_errors = {v: "(not) a test error"}
                                    new.user_errors = {v: "(not) a test error"}
                                    gentest(old, new, lambda x: x.text_input(v,d,c,l,i,s,a,**arg))

def test_generator():

    old = HTMLOrigTester()
    new = GeneratorTester()
    old.plug()
    new.plug()

    gentest(old, new, lambda x: x.heading("Test"))

    gentest(old, new, lambda x: x.rule())

    gentest(old, new, lambda x: x.p("Test"))

    gentest(old, new, lambda x: x.javascript("Test"))

    gentest(old, new, lambda x: x.javascript("set_reload(0, \'address\')"))

    gentest(old, new, lambda x: x.javascript_file("Test"))

    gentest(old, new, lambda x: x.play_sound("Test"))

    old.write('<link rel="stylesheet" type="text/css" href="%s" />\n' % "testname")
    new.stylesheet("testname")
    compare_and_empty(old, new)


def test_renderers_instance():

    new = HTMLCheck_MKTester()

    assert isinstance(new.render_icon("icon"), HTML)
    assert isinstance(new.render_icon_button("www.url.de", "help", "icon"), HTML)
    assert isinstance(new.render_popup_trigger("content", "ident"), HTML)
    assert isinstance(new.render_hidden_field("var", "val"), HTML)
    assert not new.render_hidden_field("var", None) or isinstance(new.render_hidden_field("var", None), HTML)
    assert isinstance(new.render_checkbox("var"), HTML)


def context_button_test(obj, title, url, icon=None, hot=False, id_=None, bestof=None, hover_title=None, fkey=None, id_in_best=False):
    obj.begin_context_buttons()
    obj.context_button(title, url, icon=icon, hot=hot, id=id_, bestof=bestof, hover_title=hover_title, fkey=fkey)
    if id_in_best:
        obj.context_button_hidden = True
    obj.end_context_buttons()


# TODO: refactoring tests still needed?
#def test_context_buttons():
#
#    old = HTMLOrigTester()
#    new = HTMLCheck_MKTester()
#    old.plug()
#    new.plug()
#
#    gentest(old, new, lambda x: context_button_test(x, "testtitle", "www.test.me"))
#    gentest(old, new, lambda x: context_button_test(x, "testtitle", "www.test.me", icon="ico"))
#    gentest(old, new, lambda x: context_button_test(x, "testtitle", "www.test.me", icon="ico", hot=True))
#    gentest(old, new, lambda x: context_button_test(x, "testtitle", "www.test.me", icon="ico", hot=True, id_="id"))
#    gentest(old, new, lambda x: context_button_test(x, "testtitle", "www.test.me", icon="ico", hot=True, id_="id", hover_title="HoverMeBaby!"))
#    gentest(old, new, lambda x: context_button_test(x, "testtitle", "www.test.me", icon="ico", hot=True, id_="id", hover_title="HoverMeBaby!", fkey=112))
#    gentest(old, new, lambda x: context_button_test(x, "testtitle", "www.test.me", icon="ico", hot=True, id_="id", hover_title="HoverMeBaby!", fkey=112, bestof = True))
#    gentest(old, new, lambda x: context_button_test(x, "testtitle", "www.test.me", icon="ico", hot=True, id_="id", hover_title="HoverMeBaby!", fkey=112, bestof = True, id_in_best=True))










def test_check_mk():

    old = HTMLOrigTester()
    new = HTMLCheck_MKTester()
    old.plug()
    new.plug()

    # form elements

    # gentest(old, new, lambda x: x.begin_form("Test", method="GET"))
    # gentest(old, new, lambda x: x.begin_form("Test", method="POST"))
    # gentest(old, new, lambda x: x.begin_form("Test", action="TestAction", onsubmit="Do Something"))
    # gentest(old, new, lambda x: x.begin_form("Test", add_transid=False))


    assert compare_html(\
        old.render_icon("TestIcon", help="Icon Title", middle=True, id="TestID", cssclass="test"),\
        new.render_icon("TestIcon", help="Icon Title", middle=True, id="TestID", cssclass="test"))


    assert compare_html(\
        old.render_icon_button("www.test.de", "Test Title", "TestIcon", id="TestID",
                  onclick="Do domething", style="Test Style", target="Test Target",
                  cssclass="test", ty="button"),\
        new.render_icon_button("www.test.de", "Test Title", "TestIcon", id="TestID",
                  onclick="Do domething", style="Test Style", target="Test Target",
                  cssclass="test", ty="button"))

    gentest(old, new, lambda x: x.icon("Test Title", "TestIcon"))

    gentest(old, new, lambda x: x.empty_icon())

    gentest(old, new, lambda x: x.icon_button("www.test.de", "Test Title", "TestIcon", id="TestID",
                  onclick="Do domething", style="Test Style", target="Test Target",
                  cssclass="test", ty="button"))

    gentest(old, new, lambda x: x.popup_trigger("CONTENT", 0, what="it", data=None, url_vars=None,
                             style=None, menu_content=None, cssclass=None, onclose=None))
    gentest(old, new, lambda x: x.popup_trigger("CONTENT", 0, what="it", data="data", url_vars=[("lol", "true")],
                             style=None, menu_content=None, cssclass=None, onclose=None))
    gentest(old, new, lambda x: x.popup_trigger("CONTENT", 0, what="it", data=None, url_vars=[("lol", "true")],
                             style="height:50px;", menu_content=None, cssclass=None, onclose=None))
    gentest(old, new, lambda x: x.popup_trigger("CONTENT", 0, what="it", data=None, url_vars=[("lol", "true")],
                             style="height:50px;", menu_content="test_content", cssclass=None, onclose=None))
    gentest(old, new, lambda x: x.popup_trigger("CONTENT", 0, what="it", data=None, url_vars=[("lol", "true")],
                             style="height:50px;", menu_content="test_content", cssclass="class", onclose=None))
    gentest(old, new, lambda x: x.popup_trigger("CONTENT", 0, what="it", data=None, url_vars=[("lol", "true")],
                             style="height:50px;", menu_content="test_content", cssclass="class", onclose="close();"))

    # headers

    gentest(old, new, lambda x: x.default_html_headers())

    gentest(old, new, lambda x: x.top_heading("Test"))

    gentest(old, new, lambda x: x.top_heading_left("Test"))

    gentest(old, new, lambda x: x.top_heading_right())


    javascripts = ['hallo_welt.js']
    stylesheets = ['pages', 'teststylesheet']


    gentest(old, new, attributes=['header_sent'], fun = lambda x:
                        x.html_head("Test", javascripts=javascripts,
                                            stylesheets=stylesheets, force=False))

    gentest(old, new, attributes=['header_sent'], fun = lambda x:
                        x.html_head("Test", javascripts=javascripts,
                                            stylesheets=stylesheets, force=True))

    gentest(old, new, attributes=['header_sent'], fun = lambda x:
                        x.header("Test", javascripts=javascripts,
                                         stylesheets=stylesheets, force=False))

    gentest(old, new, attributes=['header_sent'], fun = lambda x:
                        x.header("Test", javascripts=javascripts,
                                         stylesheets=stylesheets, force=True))


    # body

    gentest(old, new, attributes=['header_sent'], fun = lambda x:
                        x.body_start("Test", javascripts=javascripts,
                                         stylesheets=stylesheets, force=False))

    gentest(old, new, attributes=['header_sent'], fun = lambda x:
                        x.body_start("Test", javascripts=javascripts,
                                         stylesheets=stylesheets, force=True))


    gentest(old, new, lambda x: x.html_foot())




class _OutputFunnel(object):
    def __init__(self):
        print "OutputFunnel"
    def write(self, text):
        print text


class _HTMLGenerator(_OutputFunnel):
#class HTMLGenerator(OutputFunnel):
    def __init__(self):
        print "HTMLGenerator"
        super(_HTMLGenerator, self).__init__()
#    def write(self, text):
#        raise NotImplementedError()
    def generate(self, text):
        self.write(text)


class _HTMLCheck_MK(_HTMLGenerator):
    def __init__(self):
        print "HTMLCheck_MK"
        super(_HTMLCheck_MK, self).__init__()
        self.header_sent = False


class _DeprecatedRenderer(object):
    def __init__(self):
        print "DeprecatedRenderer"
        super(_DeprecatedRenderer, self).__init__()
        self.header_sent = False


class _DeprecationWrapper(_HTMLCheck_MK):
    def __init__(self):
        print "DeprecationWrapper"
        super(_DeprecationWrapper, self).__init__()


#class _html(_DeprecationWrapper, _OutputFunnel):
class _html(_DeprecationWrapper):
    def __init__(self):
        print "html"
        super(_html, self).__init__()
#        OutputFunnel.__init__(self)
#        DeprecationWrapper.__init__(self)
        self.generate("HALLO WELT!")


def test_class_hierarchy():

    print "\n\n"
    old = html()
    old.plug()
    try:
        print old.header_sent
    finally:
        old.write("hallo Welt!")


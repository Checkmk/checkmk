#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py


import pytest

# Override the global site fixture. Not wanted for git tests!
@pytest.fixture
def site(request):
    pass

# Mark all tests in this file to be executed in the git context
pytestmark = pytest.mark.html_gentest

# external imports
import re
import copy


# internal imports
from htmllib import html
from htmllib import HTMLGenerator
from tools import compare_html, gentest, compare_and_empty, get_attributes, compare_attributes
from classes import HTMLOrigTester, Refactored_htmlTester, DeprecatedRenderer
import html_tests
from html_tests import build_orig_test, build_cmk_test, save_html_test, load_html_test, HtmlTest, set_html_state, get_cartesian_product


def run_tests(function_name, tests=None):
    if tests is None:
        tests = build_test(function_name)
    #for test in tests:
    #    assert test.run(), "%s" % test
    assert save_html_test(function_name, tests)


def build_test(function_name):
    tests = []
    state_in = {}
    add_vars = {}
    args = {}
    if function_name == "select":
        varnames = ["name1"]
        arguments = {"varname" : ["name1"],
                     "choices" : [[(1,"ch11"), (2,"ch12")], [(1,"ch21"), (2,"ch22")]],
                     "deflt"   : ["", None,  "default"],
                     "onchange": [None, "javascript:void()"],
                     "attrs"   : [{}, {"title": "LOL", "style": "one love"}],}
        for args in get_cartesian_product(arguments):
            state_in = {"user_errors"  : {args["varname"]: "(not) a test error"}}
            add_vars = {args["varname"]: args["varname"]}
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "icon_select":
        varnames = ["name1"]
        arguments = {"varname" : ["name1", "varname"],
                     "choices" : [[(1,"ch11", "icon1"), (2,"ch12", "icon1")], [(1,"ch21","icon2"), (2,"ch22","icon2")]],
                     "deflt"   : ["", None,  "default"],}
        for args in get_cartesian_product(arguments):
            add_vars = {args["varname"]: args["varname"]}
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "radiobuttons":
        arguments     = {"checked": [True, False],
                         "label": ["label", None], }
        values = ["value", "val"]
        varnames = ["name1", "varname"]

        for mobile in ["True", "False"]:
            for horizontal in [True, False]:
                for args in get_cartesian_product(arguments):
                    state_in = {"mobile" : mobile}
                    args["varnames"] = varnames
                    args["values"]   = values
                    args["horizontal"] = horizontal
                    tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "text_area":
        arguments = {"varname": ["varname"],\
                     "deflt": [None, "test"],\
                     "rows" : [4],\
                     "cols" : [30],\
                     "attrs": [ {"style": "height:40px;", "name": "test"}, {"style": "height:40px;", "class": "test"} ],\
                     "try_max_width": [True, False]}
        for args in get_cartesian_product(arguments):
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "text_input":
        arguments = {"varname": ["gruenes_kaninchen"],
                     "default_value": ['', None, "test"],
                     "css_class": ["text"],
                     "label": [None, "label", 2],
                     "id_": [None, "id1"],
                     "submit": [None, "submit"],
                     "attrs": [{}, {"style": "height:40px;", "name": "test"}, {"style": "height:40px;", "class": "test"} ],
                    }
        additional_args = [{}, {"style": "nice", "size": 10, "autocomplete": True}]
        for add_args in additional_args:
            for args in get_cartesian_product(arguments):
                args.update(add_args)
                add_vars = {args["varname"]: args["varname"]}
                state_in = {"user_errors": {args["varname"]: "(not) a test error"}}
                tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))
                tests.append(build_orig_test(function_name, args))

    elif function_name == "empty_icon":
        tests = [build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars)]

    elif function_name in ["render_icon", "icon"]:
        args = {"icon_name":"TestIcon", "help":"Icon Title", "middle":True, "id":"TestID", "cssclass":"test"}
        if function_name == "icon":
            args["icon"] = args.pop("icon_name")
        tests = [build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars)]

    elif function_name in ["render_icon_button", "icon_button"]:
        args = {"url":"www.test.de", "icon":"TestIcon", "help":"Icon Title", "id":"TestID", "cssclass":"test",\
                "onclick":"do_something(void);", "target":"test target", "style": "size=98%", "ty":"button"}
        tests = [build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars)]

    elif function_name == "popup_trigger":
        arguments = {"content":["CONTENT"],
                     "ident":[0],
                     "what":["it"],
                     "data":[None],
                     "url_vars":[None, [("lol", "true")]],
                     "style":[None, "height:50px;"],
                     "menu_content":[None, "test_content", "Menu '<div> TEST </div>"],
                     "cssclass":[None, "testclass"],
                     "onclose":[None,"wait_then_do_close(void);"]}
        for args in get_cartesian_product(arguments):
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "default_html_headers":
        tests = [build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars)]
    elif function_name in ["top_heading", "top_heading_left"]:
        args["title"] = "TEST"
        tests = [build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars)]
    elif function_name == "top_heading_right":
        tests = [build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars)]
    elif function_name in ["html_head", "header"]:
        args = {"title": "Test",
                "javascripts": ['hallo_welt.js'],
                "stylesheets": ['pages', 'teststylesheet']}
        for header_sent in [True, False]:
            state_in = {"header_sent": header_sent}
            for force in [True, False]:
                args["force"] = force
                tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "play_sound":
        args = {"url": "www.test.de"}
        tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))
    elif function_name == "stylesheet":
        href = "www.test.de"
        tests.append(HtmlTest().create(function_name, '<link rel="stylesheet" type="text/css" href="%s" />\n' % href, {"href": href}))
    elif function_name == "javascript_file":
        src = "js/test.js"
        tests.append(HtmlTest().create(function_name, '<script type="text/javascript" src="%s"/></script>\n' % src, {"src": src}))
    elif function_name == "javascript":
        code = '<tag> foo </tag> <bar class_="class \"><hello onclick = "malicious_code(void);"/>\" this is a test </bar>'
        tests.append(HtmlTest().create(function_name, "<script type=\"text/javascript\">\n%s\n</script>\n" % code, {"code": code}))
    elif function_name == "context_button_test":
        arguments = {"title": ["testtitle"], "url": ["www.test.me"],
                     "icon": [None, "ico"],
                     "hot" : [False, True],
                     "id_" : [None, "id1"],
                     "hover_title": [None, "HoverMeBaby!"],
                     "fkey": [None, 112],
                     "bestof": [None, True, False],
                     "id_in_best" : [True, False], }
        for args in get_cartesian_product(arguments):
            tests.append(build_cmk_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "begin_form":
        arguments = {"name"     : ["Test"],
                     "action"   : [None, "TestAction"],
                     "method"   : ["GET", "POST"],
                     "onsubmit" : [None, "do_sth(void);"],
                     "add_transid": [True, False],}
        for args in get_cartesian_product(arguments):
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "body_start":
        arguments = {"title": ["Test"],
                     "javascripts": [None, ["js1", "js2"]],
                     "stylesheets": [None, ["sts1", "sts2"]],
                     "force": [True, False] }
        for header_sent in [True, False]:
            state_in = {"header_sent": header_sent}
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "html_foot":
        tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))


    elif function_name == "hidden_field":
        arguments = {"var": ["var"], "value": ["value", None], "id":[None,"id"], "add_var": [True, False]}
        for args in get_cartesian_product(arguments):
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "button":
        arguments = {"varname": ["var"],
                     "title": ["title", ''],
                     "cssclass": ['', "test class"],
                     "style": [None, "height:10pt;"]}
        for args in get_cartesian_product(arguments):
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "buttonlink":
        arguments = {"href": ["www.buttonlink.de"],
                     "text": ["text"],
                     "add_transid": [True, False],
                     "obj_id": ['', "objid"],
                     "style": [None, "height:10pt;"],
                     "title": ["title", None],
                     "disabled": [None, "disabled"],}
        for args in get_cartesian_product(arguments):
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    elif function_name == "checkbox":
        arguments = {"varname" : ["_vname"],
                     "deflt"   : [True, False],
                     "cssclass": ["test"],
                     "onclick" : ["javascript:void();"],
                     "label"   : ["label_text", ''],
                     "id"      : [None, "id"],
                     "add_attr": [None, ["title=\"Title\" tags=\"TAG\""]]}

        for args in get_cartesian_product(arguments):
            add_vars = {args["varname"]: args["varname"]}
            state_in = {}
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

            add_vars = {args["varname"]: ''}
            state_in = {}
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

            add_vars = {}
            state_in = {"user_errors": {args["varname"]: "(not) a test error"}}
            tests.append(build_orig_test(function_name, args, state_in=state_in, add_vars=add_vars))

    else:
        raise Exception("Testcase \'%s\' unknown!" % function_name)

    return tests


def test_checkbox():
    #html_tests.generate_tests()
    html_tests.load_gentest_file("checkbox", "new")


def test_select():
    run_tests("select")


def test_icon_select():
    run_tests("icon_select")


def test_radiobuttons():
    run_tests("radiobuttons")


def test_text_area():
    run_tests("text_area")


def test_text_input():
    run_tests("text_input")


def test_icons():
    for function_name in ["empty_icon", "render_icon", "icon", "render_icon_button", "icon_button"]:
        run_tests(function_name)


def test_popup_trigger():
    run_tests("popup_trigger")


def test_header():
    for function_name in ["default_html_headers", "top_heading", "top_heading_left", "top_heading_right", "html_head", "header"]:
        run_tests(function_name)


def test_scripts():

    for function_name in ["javascript", "javascript_file", "play_sound", "stylesheet"]:
        run_tests(function_name)


def test_context_buttons():
    run_tests("context_button_test")


def test_body_foot():
    for function_name in ["body_start", "html_foot"]:
        run_tests(function_name)


def test_hidden_field():
    run_tests("hidden_field")


def test_buttons():
    run_tests("button")
    run_tests("buttonlink")






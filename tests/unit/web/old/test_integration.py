#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py

# internal imports
from classes import HTMLTester
from html_tests import load_html_test

from cmk.gui.htmllib import HTML

def run_tests(function_name, tests=None):
    tests = load_html_test(function_name)
    for test in tests:
        assert test.run(), "%s" % test


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


def test_header(monkeypatch):
    import cmk.gui.config as config
    monkeypatch.setattr(config, "custom_style_sheet", None, raising=False)

    for function_name in ["default_html_headers", "top_heading", "top_heading_left", "top_heading_right", "html_head", "header"]:
        run_tests(function_name)


def test_scripts():

    for function_name in ["javascript", "javascript_file", "play_sound", "stylesheet"]:
        run_tests(function_name)


def test_renderers_instance():

    new = HTMLTester()

    assert isinstance(new.render_icon("icon"), HTML)
    assert isinstance(new.render_icon_button("www.url.de", "help", "icon"), HTML)
    assert isinstance(new.render_popup_trigger("content", "ident"), HTML)
    assert isinstance(new.render_hidden_field("var", "val"), HTML)
    assert not new.render_hidden_field("var", None) or isinstance(new.render_hidden_field("var", None), HTML)
    assert isinstance(new.render_checkbox("var"), HTML)


def test_context_buttons():
    run_tests("context_button_test")


def test_body_foot(monkeypatch):
    import cmk.gui.config as config
    monkeypatch.setattr(config, "custom_style_sheet", None, raising=False)

    for function_name in ["body_start", "html_foot"]:
        run_tests(function_name)

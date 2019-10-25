# encoding: utf-8
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML


def test_render_help_empty(register_builtin_html):
    assert html.have_help is False
    assert html.render_help(None) == ""
    assert html.have_help is False

    assert html.render_help("") == ""
    assert html.render_help("    ") == ""


def test_render_help_html(register_builtin_html):
    assert html.have_help is False
    assert html.render_help(
        HTML("<abc>")) == HTML("<div style=\"display: none;\" class=\"help\"><abc></div>")
    assert html.have_help is True


def test_render_help_text(register_builtin_html):
    assert html.render_help(u"äbc") == HTML(
        u"<div style=\"display: none;\" class=\"help\">äbc</div>")


def test_render_help_visible(register_builtin_html):
    assert html.help_visible is False
    html.help_visible = True
    assert html.render_help(u"äbc") == HTML(
        u"<div style=\"display: block;\" class=\"help\">äbc</div>")

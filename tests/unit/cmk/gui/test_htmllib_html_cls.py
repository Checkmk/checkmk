#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
import cmk.gui.config as config
from cmk.gui.exceptions import MKUserError
from tools import compare_html  # type: ignore[import]


def test_render_help_empty(register_builtin_html):
    assert html.have_help is False
    assert html.render_help(None) == HTML("")
    assert isinstance(html.render_help(None), HTML)
    assert html.have_help is False

    assert html.render_help("") == HTML("")
    assert isinstance(html.render_help(""), HTML)
    assert html.render_help("    ") == HTML("")
    assert isinstance(html.render_help("    "), HTML)


def test_render_help_html(register_builtin_html):
    assert html.have_help is False
    assert compare_html(html.render_help(HTML("<abc>")),
                        HTML("<div style=\"display:none\" class=\"help\"><abc></div>"))
    # NOTE: This seems to be a mypy 0.780 bug.
    assert html.have_help is True  # type: ignore[comparison-overlap]


def test_render_help_text(register_builtin_html):
    assert compare_html(html.render_help(u"äbc"),
                        HTML(u"<div style=\"display:none\" class=\"help\">äbc</div>"))
    assert compare_html(
        html.render_help("<tt>permissive?</tt>"),
        HTML(u"<div style=\"display:none\" class=\"help\"><tt>permissive?</tt></div>"))
    assert compare_html(
        html.render_help("<script>alert(1)</script>"),
        HTML(
            u"<div style=\"display:none\" class=\"help\">&gt;script&lt;alert(1)&gt;/script&lt;</div>"
        ))


def test_render_help_visible(module_wide_request_context, register_builtin_html, monkeypatch):
    monkeypatch.setattr(config.LoggedInUser, "show_help", property(lambda s: True))
    assert config.user.show_help is True
    assert compare_html(html.render_help(u"äbc"),
                        HTML(u"<div style=\"display:block\" class=\"help\">äbc</div>"))


def test_add_manual_link(register_builtin_html):
    assert config.user.language is None
    assert compare_html(
        html.render_help(u"[introduction_docker|docker]"),
        HTML(
            u"<div style=\"display:none\" class=\"help\"><a href=\"https://docs.checkmk.com/2.0.0/en/introduction_docker.html\" target=\"_blank\">docker</a></div>"
        ))


def test_add_manual_link_localized(module_wide_request_context, monkeypatch):
    monkeypatch.setattr(config.user, "language", lambda: "de")
    assert compare_html(
        html.render_help(u"[introduction_docker|docker]"),
        HTML(
            u"<div style=\"display:none\" class=\"help\"><a href=\"https://docs.checkmk.com/2.0.0/de/introduction_docker.html\" target=\"_blank\">docker</a></div>"
        ))


def test_add_manual_link_anchor(module_wide_request_context, monkeypatch):
    monkeypatch.setattr(config.user, "language", lambda: "de")
    assert compare_html(
        html.render_help(u"[graphing#rrds|RRDs]"),
        HTML(
            u"<div style=\"display:none\" class=\"help\"><a href=\"https://docs.checkmk.de/2.0.0/de/graphing.html#rrds\" target=\"_blank\">RRDs</a></div>"
        ))


def test_user_error(register_builtin_html):
    with html.plugged():
        html.user_error(MKUserError(None, "asd <script>alert(1)</script> <br> <b>"))
        c = html.drain()
    assert c == "<div class=\"error\">asd &lt;script&gt;alert(1)&lt;/script&gt; <br> <b></div>"


def test_add_user_error(register_builtin_html):
    assert not html.has_user_errors()
    html.add_user_error(None, "asd <script>alert(1)</script> <br> <b>")
    assert html.has_user_errors()

    with html.plugged():
        html.show_user_errors()
        c = html.drain()
    assert c == "<div class=\"error\">asd &lt;script&gt;alert(1)&lt;/script&gt; <br> <b></div>"

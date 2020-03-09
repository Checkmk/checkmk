#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import html
from cmk.gui.htmllib import HTML
import cmk.gui.config as config
from tools import compare_html


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
    assert html.have_help is True


def test_render_help_text(register_builtin_html):
    assert compare_html(html.render_help(u"äbc"),
                        HTML(u"<div style=\"display:none\" class=\"help\">äbc</div>"))


def test_render_help_visible(module_wide_request_context, register_builtin_html, monkeypatch):
    monkeypatch.setattr(config.LoggedInUser, "show_help", property(lambda s: True))
    assert config.user.show_help is True
    assert compare_html(html.render_help(u"äbc"),
                        HTML(u"<div style=\"display:block\" class=\"help\">äbc</div>"))


def test_add_manual_link(register_builtin_html):
    assert config.user.language is None
    assert compare_html(
        html.render_help(u"[cms_introduction_docker|docker]"),
        HTML(
            u"<div style=\"display:none\" class=\"help\"><a href=\"https://checkmk.com/cms_introduction_docker.html\" target=\"_blank\">docker</a></div>"
        ))


def test_add_manual_link_localized(module_wide_request_context, monkeypatch):
    monkeypatch.setattr(config.user, "language", lambda: "de")
    assert compare_html(
        html.render_help(u"[cms_introduction_docker|docker]"),
        HTML(
            u"<div style=\"display:none\" class=\"help\"><a href=\"https://checkmk.de/cms_introduction_docker.html\" target=\"_blank\">docker</a></div>"
        ))


def test_add_manual_link_anchor(module_wide_request_context, monkeypatch):
    monkeypatch.setattr(config.user, "language", lambda: "de")
    assert compare_html(
        html.render_help(u"[cms_graphing#rrds|RRDs]"),
        HTML(
            u"<div style=\"display:none\" class=\"help\"><a href=\"https://checkmk.de/cms_graphing.html#rrds\" target=\"_blank\">RRDs</a></div>"
        ))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.htmllib.tag_rendering import (
    normalize_css_spec,
    render_element,
    render_end_tag,
    render_start_tag,
)
from cmk.gui.utils.html import HTML


def test_render_start_tag_no_attributes() -> None:
    tag = render_start_tag("div")
    assert isinstance(tag, HTML)
    assert str(tag) == "<div>"


def test_render_start_tag_simple_attributes() -> None:
    tag = render_start_tag("div", id="xyz", name="aaa")
    assert str(tag) == '<div id="xyz" name="aaa">'


def test_render_start_tag_convert_data_attributes() -> None:
    tag = render_start_tag("div", data_abc="xyz")
    assert str(tag) == '<div data-abc="xyz">'


def test_render_start_tag_skip_none_values() -> None:
    tag = render_start_tag("div", name=None)
    assert str(tag) == "<div>"


def test_render_start_tag_keep_empty_values() -> None:
    tag = render_start_tag("div", name="")
    assert str(tag) == "<div name=''>"


@pytest.mark.parametrize("value", [["1", "2"], "1 2", ["1", None, "2"]])
@pytest.mark.parametrize("key", ["class_", "css", "cssclass", "class"])
def test_render_start_tag_class_variants(key, value) -> None:
    tag = render_start_tag("div", **{key: value})
    assert str(tag) == '<div class="1 2">'


def test_render_start_tag_style_separator() -> None:
    tag = render_start_tag("a", style=["width: 10px", "height:10px"])
    assert str(tag) == '<a style="width: 10px; height:10px">'


def test_render_start_tag_on_separator() -> None:
    tag = render_start_tag("a", onclick=["func1()", "func2()"])
    assert str(tag) == '<a onclick="func1(); func2()">'


def test_render_start_tag_on_separator_skip_empty_element() -> None:
    tag = render_start_tag("a", onclick=["func1()", "", "func2()"])
    assert str(tag) == '<a onclick="func1(); func2()">'


def test_render_start_tag_a_first_attr_href() -> None:
    tag = render_start_tag("a", class_="xyz", href="bla", target="_blank")
    assert str(tag) == '<a href="bla" target="_blank" class="xyz">'


def test_render_start_tag_escape_key() -> None:
    tag = render_start_tag("a", close_tag=False, **{"b<script>alert(1)</script>la": "1"})
    assert str(tag) == '<a b&lt;script&gt;alert(1)&lt;/script&gt;la="1">'


def test_render_start_tag_escape_value() -> None:
    tag = render_start_tag("a", href="b<script>alert(1)</script>la")
    assert str(tag) == '<a href="b&lt;script&gt;alert(1)&lt;/script&gt;la">'


def test_render_start_tag_escape_list_of_values() -> None:
    tag = render_start_tag("a", style=["ding", "b<script>alert(1)</script>la"])
    assert str(tag) == '<a style="ding; b&lt;script&gt;alert(1)&lt;/script&gt;la">'


def test_render_end_tag() -> None:
    tag = render_end_tag("a")
    assert isinstance(tag, HTML)
    assert str(tag) == "</a>"


def test_render_element_simple() -> None:
    tag = render_element("a", "content", href="ding")
    assert isinstance(tag, HTML)
    assert str(tag) == '<a href="ding">content</a>'


def test_render_element_none_content() -> None:
    tag = render_element("a", None, href="ding")
    assert isinstance(tag, HTML)
    assert str(tag) == '<a href="ding"></a>'


def test_render_element_escape_content() -> None:
    tag = render_element("a", "b<script>alert(1)</script>la", href="ding")
    assert isinstance(tag, HTML)
    assert str(tag) == '<a href="ding">b&lt;script&gt;alert(1)&lt;/script&gt;la</a>'


def test_render_element_do_not_escape_html() -> None:
    tag = render_element("a", HTML("b<script>alert(1)</script>la"), href="ding")
    assert isinstance(tag, HTML)
    assert str(tag) == '<a href="ding">b<script>alert(1)</script>la</a>'


@pytest.mark.parametrize("value", [["1"], "1", ["1", None]])
def test_normalize_css_spec_skip_nones(value) -> None:
    assert normalize_css_spec(value) == ["1"]

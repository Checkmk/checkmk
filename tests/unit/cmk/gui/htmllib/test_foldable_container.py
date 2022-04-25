#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from tests.testlib import compare_html

from cmk.gui.htmllib.foldable_container import (
    foldable_container,
    foldable_container_id,
    foldable_container_img_id,
    foldable_container_onclick,
)
from cmk.gui.utils.output_funnel import output_funnel


def test_foldable_container(request_context) -> None:
    with output_funnel.plugged():
        with foldable_container(treename="name", id_="id", isopen=False, title="Title") as is_open:
            assert is_open is False
        code = output_funnel.drain()
        assert compare_html(
            code,
            """<div class="foldable closed"><div
onclick="cmk.foldable_container.toggle(&quot;name&quot;, &quot;id&quot;, &quot;&quot;)"
class="foldable_header"><b class="treeangle title">Title</b><img id="treeimg.name.id"
src="themes/facelift/images/tree_closed.svg" class="treeangle closed" /></div><ul
id="tree.name.id" style="padding-left: 15px; " class="treeangle closed"></ul></div>""",
        )


def test_foldable_container_id() -> None:
    assert foldable_container_id("name", "id") == "tree.name.id"


def test_foldable_container_img_id() -> None:
    assert foldable_container_img_id("name", "id") == "treeimg.name.id"


def test_foldable_container_onclick_without_url() -> None:
    assert (
        foldable_container_onclick("name", "id", None)
        == 'cmk.foldable_container.toggle("name", "id", "", true)'
    )


def test_foldable_container_onclick_no_save() -> None:
    assert (
        foldable_container_onclick("name", "id", None, False)
        == 'cmk.foldable_container.toggle("name", "id", "", false)'
    )


def test_foldable_container_onclick_with_url() -> None:
    assert (
        foldable_container_onclick("name", "id", "http://bla")
        == 'cmk.foldable_container.toggle("name", "id", "http:\\/\\/bla", true)'
    )

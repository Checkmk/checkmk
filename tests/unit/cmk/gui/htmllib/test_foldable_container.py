#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from bs4 import BeautifulSoup, Tag
from pytest_mock import MockerFixture

from cmk.gui.htmllib.foldable_container import (
    foldable_container,
    foldable_container_id,
    foldable_container_img_id,
    foldable_container_onclick,
)
from cmk.gui.utils.output_funnel import output_funnel
from tests.unit.cmk.gui.compare_html import compare_html


@pytest.mark.usefixtures("request_context")
def test_foldable_container(mocker: MockerFixture) -> None:
    mocker.patch(
        "cmk.gui.theme._theme_type.Theme.detect_icon_path",
        return_value="some_random_icon_path.svg",
    )
    with output_funnel.plugged():
        with foldable_container(treename="name", id_="id", isopen=False, title="Title") as is_open:
            assert is_open is False
        code = output_funnel.drain()
        assert compare_html(
            code,
            """
            <div class="foldable closed">
            <div class="foldable_header" data-cmk_on_click="foldable_container_toggle" data-cmk_on_click_arguments="{&quot;treename&quot;: &quot;name&quot;, &quot;id&quot;: &quot;id&quot;, &quot;fetch_url&quot;: &quot;&quot;, &quot;save_state&quot;: &quot;true&quot;}">
            <img id="treeimg.name.id" src="some_random_icon_path.svg" class="treeangle closed" />
            <b class="treeangle title">Title</b>
            </div>
            <ul id="tree.name.id" style="padding-left: 15px; " class="treeangle closed"></ul>
            </div>

            """,
        )


TOGGLE_ARGUMENTS = {"treename": "name", "id": "id", "fetch_url": "", "save_state": "true"}


def _render(title_url: str | None = None) -> BeautifulSoup:
    with output_funnel.plugged():
        with foldable_container(
            treename="name", id_="id", isopen=True, title="Title", title_url=title_url
        ):
            pass
        return BeautifulSoup(output_funnel.drain(), "lxml")


def _click_handling(tag: Tag | None) -> tuple[object, object, object]:
    assert tag is not None
    arguments = tag.get("data-cmk_on_click_arguments")
    return (
        tag.get("onclick"),
        tag.get("data-cmk_on_click"),
        None if arguments is None else json.loads(str(arguments)),
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_foldable_container_header_toggles_by_click_action() -> None:
    soup = _render()

    assert _click_handling(soup.select_one("div.foldable_header")) == (
        None,
        "foldable_container_toggle",
        TOGGLE_ARGUMENTS,
    )


@pytest.mark.usefixtures("request_context", "patch_theme")
def test_foldable_container_with_title_url_toggles_on_the_icon_only() -> None:
    soup = _render(title_url="view.py")

    assert (
        _click_handling(soup.select_one("div.foldable_header")),
        _click_handling(soup.select_one("img.treeangle")),
    ) == ((None, None, None), (None, "foldable_container_toggle", TOGGLE_ARGUMENTS))


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
        == 'cmk.foldable_container.toggle("name", "id", "http://bla", true)'
    )

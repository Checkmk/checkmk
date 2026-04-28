#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from cmk.gui.http import Request
from cmk.gui.page_menu import (
    _with_navigation,
    _without_navigation,
    make_external_link,
    make_form_submit_link,
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuTopic,
)
from cmk.gui.type_defs import DynamicIconName


def test_make_simple_link() -> None:
    item = make_simple_link("views.py")
    assert item.link.url == "views.py"
    assert item.link.target is None
    assert item.link.onclick is None


def test_make_external_link() -> None:
    item = make_external_link("https://checkmk.com/")
    assert item.link.url == "https://checkmk.com/"
    assert item.link.target == "_blank"
    assert item.link.onclick is None


def test_make_javascript_link() -> None:
    item = make_javascript_link("bla.blub()")
    assert item.link.url is None
    assert item.link.target is None
    assert item.link.onclick == "bla.blub();cmk.page_menu.close_active_dropdown();"


def test_make_form_submit_link() -> None:
    item = make_form_submit_link("frm", "btn")
    assert item.link.url is None
    assert item.link.target is None
    assert (
        item.link.onclick
        == 'cmk.page_menu.form_submit("frm", "btn");cmk.page_menu.close_active_dropdown();'
    )


@pytest.mark.usefixtures("request_context")
def test_simple_page_menu() -> None:
    pm = PageMenu(
        [
            PageMenuDropdown(
                name="hallo",
                title="HALLO",
                topics=[
                    PageMenuTopic(
                        title="Title",
                        entries=[
                            PageMenuEntry(
                                name="abc",
                                title="Mach das",
                                description="Ich beschreibe",
                                icon_name=DynamicIconName("icon"),
                                item=make_external_link("https://checkmk.com/"),
                            ),
                        ],
                    )
                ],
            ),
        ]
    )

    assert len(pm.dropdowns) == 3  # help, display-options-Dropdowns are added automatically
    assert len(list(pm.shortcuts)) == 0
    assert len(list(pm.suggestions)) == 0
    assert pm.has_suggestions is False

    dropdown = pm.dropdowns[0]
    assert dropdown.name == "hallo"
    assert dropdown.title == "HALLO"
    assert len(dropdown.topics) == 1
    assert dropdown.any_show_more_entries is False
    assert dropdown.is_empty is False

    for topic in dropdown.topics:
        assert topic.title == "Title"
        assert len(topic.entries) == 1

        for entry in topic.entries:
            assert entry.name == "abc"
            assert entry.title == "Mach das"
            assert entry.description == "Ich beschreibe"
            assert entry.icon_name == "icon"
            assert isinstance(entry.item, PageMenuLink)
            assert entry.item.link.url == "https://checkmk.com/"
            assert entry.item.link.target == "_blank"
            assert entry.item.link.onclick is None

    display_dropdown = pm.dropdowns[1]
    assert display_dropdown.name == "display"

    help_dropdown = pm.dropdowns[2]
    assert help_dropdown.name == "help"
    assert help_dropdown.topics[0].entries[0].name == "inline_help"


def _make_request(
    query_string: str = "", path_info: str = "/NO_SITE/check_mk/dashboard.py"
) -> Request:
    return Request(create_environ(path=path_info, query_string=query_string))


@pytest.mark.parametrize(
    "query_string,expected_url",
    [
        pytest.param(
            "",
            "index.py?start_url=dashboard.py&kiosk=true",
            id="plain inner path wrapped into index",
        ),
        pytest.param(
            "name=foo&site=bar",
            "index.py?start_url=dashboard.py%3Fname%3Dfoo%26site%3Dbar&kiosk=true",
            id="inner vars survive url encoded",
        ),
        pytest.param(
            "kiosk=true&name=foo",
            "index.py?start_url=dashboard.py%3Fname%3Dfoo&kiosk=true",
            id="inner kiosk stripped outer is source of truth",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_with_navigation(query_string: str, expected_url: str) -> None:
    link = _with_navigation(_make_request(query_string=query_string))
    assert link.url == expected_url
    assert link.target == "_top"


@pytest.mark.parametrize(
    "query_string,expected_url",
    [
        pytest.param("", "index.py?start_url=dashboard.py", id="plain inner path"),
        pytest.param(
            "kiosk=true&name=foo&_password=secret&_transid=42",
            "index.py?start_url=dashboard.py%3Fname%3Dfoo",
            id="kiosk and underscore sensitive vars stripped",
        ),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_without_navigation(query_string: str, expected_url: str) -> None:
    link = _without_navigation(_make_request(query_string=query_string))
    assert link.url == expected_url
    assert link.target == "_top"

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from cmk.gui.htmllib.generator import ClickAction
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request
from cmk.gui.page_menu import (
    _with_navigation,
    _without_navigation,
    DropdownEntryRenderer,
    inpage_search_form,
    make_click_action_link,
    make_external_link,
    make_form_submit_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuLink,
    PageMenuTopic,
    ShortcutRenderer,
    SuggestedEntryRenderer,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.web.utils.confirm_links import make_confirm_link
from cmk.web.utils.icons import DynamicIconName, IconNames, StaticIcon


def test_make_simple_link() -> None:
    item = make_simple_link("views.py")
    assert item.link.url == "views.py"
    assert item.link.target is None
    assert item.link.click_action is None


def test_make_external_link() -> None:
    item = make_external_link("https://checkmk.com/")
    assert item.link.url == "https://checkmk.com/"
    assert item.link.target == "_blank"
    assert item.link.click_action is None


def test_make_click_action_link() -> None:
    click_action = ClickAction(action="reload_page")
    item = make_click_action_link(click_action)
    assert item.link.url is None
    assert item.link.click_action == click_action


def test_make_click_action_link_with_url() -> None:
    click_action = ClickAction(action="waiting_flash_message", arguments={"message": "Wait"})
    item = make_click_action_link(click_action, url="wato.py?_action=verify")
    assert item.link.url == "wato.py?_action=verify"
    assert item.link.click_action == click_action


def test_make_form_submit_link() -> None:
    item = make_form_submit_link("frm", "btn")
    assert item.link.url is None
    assert item.link.target is None
    assert item.link.click_action == ClickAction(
        action="page_menu_form_submit", arguments={"form_name": "frm", "button_name": "btn"}
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
            assert entry.item.link.click_action is None

    display_dropdown = pm.dropdowns[1]
    assert display_dropdown.name == "display"

    help_dropdown = pm.dropdowns[2]
    assert help_dropdown.name == "help"
    assert help_dropdown.topics[0].entries[0].name == "inline_help"


@pytest.mark.usefixtures("request_context")
def test_page_menu_renders_actions_as_action_links() -> None:
    action = PageMenuEntry(
        name="save",
        title="Save",
        icon_name=StaticIcon(IconNames.save),
        item=make_form_submit_link("frm", "btn"),
    )
    link = PageMenuEntry(
        name="views",
        title="Views",
        icon_name=StaticIcon(IconNames.trans),
        item=make_simple_link("views.py"),
    )

    with output_funnel.plugged():
        for entry in (action, link):
            SuggestedEntryRenderer().show(entry)
            ShortcutRenderer().show(entry)
            DropdownEntryRenderer().show(entry)
        written = output_funnel.drain()

    assert "javascript:" not in written
    assert written.count('data-cmk_on_click="page_menu_form_submit"') == 3
    assert written.count('<a href="#"') == 3
    assert written.count('href="views.py"') == 3


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


@pytest.mark.parametrize(
    "malicious_reset_url",
    [
        pytest.param("javascript:alert(1)", id="javascript scheme"),
        pytest.param("https://evil.example/", id="cross-origin absolute url"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_inpage_search_form_rejects_unsafe_reset_url(malicious_reset_url: str) -> None:
    request.set_var("reset_url", malicious_reset_url)
    with html.output_funnel.plugged():
        inpage_search_form()
        output = html.output_funnel.drain()

    assert malicious_reset_url not in output


@pytest.mark.usefixtures("request_context")
def test_inpage_search_form_keeps_safe_reset_url() -> None:
    request.set_var("reset_url", "dashboard.py")
    with html.output_funnel.plugged():
        inpage_search_form()
        output = html.output_funnel.drain()

    assert 'value="dashboard.py"' in output


def test_make_simple_link_with_confirm_link() -> None:
    link = make_confirm_link(i18n=lambda s: s, url="wato.py?a=1", title="Reset")

    assert make_simple_link(link) == make_click_action_link(ClickAction.confirm(link))

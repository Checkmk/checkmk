#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pytest

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.sidebar._snapin import _helpers
from cmk.gui.sidebar._snapin._helpers import (
    bulletlink,
    footnotelinks,
    heading,
    iconlink,
    is_menu_item_supported_visual,
    link,
    make_main_menu,
    render_link,
    show_main_menu,
    snapin_site_choice,
    VisualItem,
    VisualMenuItem,
    VisualMenuItemType,
    write_snapin_exception,
)
from cmk.gui.sites import SiteStatus
from cmk.gui.type_defs import DynamicIconName, IconNames, StaticIcon, Visual
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing.main_menu import LoadingTransition as SharedLoadingTransition
from cmk.shared_typing.main_menu import NavItemTopic, NavItemTopicEntry, TopicItemMode


@pytest.fixture(name="rendering_user", autouse=True)
def fixture_rendering_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "confdir", Path(""))
        m.setattr(user, "may", lambda x: True)
        yield


def _entry(
    id_: str,
    title: str,
    *,
    url: str | None = "view.py?view_name=x",
    mode: TopicItemMode | None = None,
    entries: Sequence[NavItemTopicEntry] | None = None,
    is_show_more: bool | None = None,
) -> NavItemTopicEntry:
    return NavItemTopicEntry(
        id=id_,
        title=title,
        sort_index=0,
        url=url,
        mode=mode,
        entries=entries,
        is_show_more=is_show_more,
    )


def _topic(id_: str, entries: Sequence[NavItemTopicEntry]) -> NavItemTopic:
    return NavItemTopic(id=id_, title="Topic %s" % id_, sort_index=0, entries=entries)


@pytest.mark.parametrize(
    "type_name,supported",
    [
        pytest.param("views", True, id="views"),
        pytest.param("dashboards", True, id="dashboards"),
        pytest.param("reports", True, id="reports"),
        pytest.param("pages", True, id="pages"),
        pytest.param("custom_graph", True, id="custom_graph"),
        pytest.param("graph_collection", True, id="graph_collection"),
        pytest.param("forecast_graph", True, id="forecast_graph"),
        pytest.param("bookmark_list", False, id="unsupported_pagetype"),
        pytest.param("", False, id="empty"),
    ],
)
def test_is_menu_item_supported_visual(type_name: str, supported: bool) -> None:
    assert is_menu_item_supported_visual(type_name) is supported


@pytest.mark.parametrize(
    "url,expected_href",
    [
        pytest.param("view.py?view_name=allhosts", "/NO_SITE/check_mk/view.py?view_name=allhosts"),
        pytest.param("/absolute/link.py", "/absolute/link.py", id="absolute_path_kept"),
        pytest.param("http://host/url/link.py", "http://host/url/link.py", id="http_kept"),
        pytest.param("https://host/url/link.py", "https://host/url/link.py", id="https_kept"),
        pytest.param("javascript:void(0)", "javascript:void(0)", id="javascript_kept"),
    ],
)
def test_render_link_only_absolutizes_relative_urls(url: str, expected_href: str) -> None:
    assert 'href="%s"' % expected_href in str(render_link("Text", url))


def test_render_link_passes_through_optional_attributes() -> None:
    rendered = str(
        render_link("Text", "view.py", target="main", onclick="do_it()", title="Tooltip")
    )

    assert 'target="main"' in rendered
    assert 'onclick="do_it()"' in rendered
    assert 'title="Tooltip"' in rendered
    assert 'class="link"' in rendered


def test_render_link_omits_empty_optional_attributes() -> None:
    rendered = str(render_link("Text", "view.py"))

    assert "onclick=" not in rendered
    assert "title=" not in rendered


def test_link_writes_the_rendered_anchor() -> None:
    with output_funnel.plugged():
        link("Text", "view.py")
        rendered = output_funnel.drain()

    assert rendered == str(render_link("Text", "view.py"))


def test_bulletlink_wraps_the_link_in_a_list_item() -> None:
    with output_funnel.plugged():
        bulletlink("Text", "view.py")
        rendered = output_funnel.drain()

    assert rendered.startswith('<li class="sidebar">')
    assert rendered.endswith("</li>")
    assert "view.py" in rendered


def test_bulletlink_renders_nothing_without_an_url() -> None:
    """Menu entries may carry no URL (e.g. pure grouping entries); those must be skipped
    instead of rendering a dangling bullet."""
    with output_funnel.plugged():
        bulletlink("Text", None)
        assert output_funnel.drain() == ""


def test_iconlink_renders_nothing_without_an_url() -> None:
    with output_funnel.plugged():
        iconlink("Text", None, StaticIcon(IconNames.host))
        assert output_funnel.drain() == ""


@pytest.mark.usefixtures("patch_theme")
def test_iconlink_renders_a_static_icon() -> None:
    with output_funnel.plugged():
        iconlink("Text", "view.py", StaticIcon(IconNames.host))
        rendered = output_funnel.drain()

    assert 'class="iconlink link"' in rendered
    assert "cmk-static-icon" in rendered
    assert "Text" in rendered
    assert rendered.endswith("<br />")


@pytest.mark.usefixtures("patch_theme")
def test_iconlink_renders_a_dynamic_icon() -> None:
    with output_funnel.plugged():
        iconlink("Text", "view.py", DynamicIconName("bookmark_list"))
        rendered = output_funnel.drain()

    assert 'class="iconlink link"' in rendered
    assert "cmk-static-icon" not in rendered
    assert "Text" in rendered


def test_heading_renders_a_h3() -> None:
    with output_funnel.plugged():
        heading("Some heading")
        assert output_funnel.drain() == "<h3>Some heading</h3>"


def test_footnotelinks_wraps_all_links_in_one_container() -> None:
    with output_funnel.plugged():
        footnotelinks([("Edit", "edit_views.py"), ("Export", "export_views.py")])
        rendered = output_funnel.drain()

    assert rendered.startswith('<div class="footnotelink">')
    assert rendered.endswith("</div>")
    assert rendered.count("<a") == 2


def test_footnotelinks_without_links_renders_the_empty_container() -> None:
    with output_funnel.plugged():
        footnotelinks([])
        assert output_funnel.drain() == '<div class="footnotelink"></div>'


def test_write_snapin_exception_hides_the_traceback() -> None:
    """The message is shown to the user, the traceback only to whoever inspects the DOM."""
    with output_funnel.plugged():
        write_snapin_exception(ValueError("Something went wrong"))
        rendered = output_funnel.drain()

    assert 'class="snapinexception"' in rendered
    assert "Something went wrong" in rendered
    assert 'style="display:none;"' in rendered


ONLINE_SITES = {
    SiteId("heute"): SiteStatus({"state": "online"}),
    SiteId("beta"): SiteStatus({"state": "online"}),
}


def _site_choice(
    monkeypatch: pytest.MonkeyPatch,
    *,
    states: dict[SiteId, SiteStatus],
    choices: list[tuple[SiteId, str]],
    stored: dict[str, str],
) -> tuple[list[SiteId] | None, str]:
    with monkeypatch.context() as m:
        m.setattr(_helpers, "states", lambda: states)
        m.setattr(user, "load_file", lambda *args, **kwargs: stored)
        with output_funnel.plugged():
            only_sites = snapin_site_choice("performance", choices)
            return only_sites, output_funnel.drain()


def test_snapin_site_choice_returns_none_for_a_single_site(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With only one reachable site there is nothing to choose, so no dropdown is rendered
    and the snap-in stays unrestricted."""
    only_sites, rendered = _site_choice(
        monkeypatch,
        states={SiteId("heute"): SiteStatus({"state": "online"})},
        choices=[(SiteId("heute"), "Heute")],
        stored={},
    )

    assert only_sites is None
    assert rendered == ""


def test_snapin_site_choice_skips_sites_without_a_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured but unknown site must not be offered - and must not push the number of
    choices over the threshold that makes the dropdown appear."""
    only_sites, rendered = _site_choice(
        monkeypatch,
        states={SiteId("heute"): SiteStatus({"state": "online"})},
        choices=[(SiteId("heute"), "Heute"), (SiteId("gone"), "Gone")],
        stored={},
    )

    assert only_sites is None
    assert rendered == ""


def test_snapin_site_choice_renders_a_dropdown_for_several_sites(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    only_sites, rendered = _site_choice(
        monkeypatch,
        states=ONLINE_SITES,
        choices=[(SiteId("heute"), "Heute"), (SiteId("beta"), "Beta")],
        stored={},
    )

    assert only_sites is None
    assert "All sites" in rendered
    assert "Heute" in rendered
    assert "Beta" in rendered
    assert "cmk.sidebar.set_snapin_site" in rendered


def test_snapin_site_choice_restricts_to_the_stored_site(monkeypatch: pytest.MonkeyPatch) -> None:
    only_sites, _rendered = _site_choice(
        monkeypatch,
        states=ONLINE_SITES,
        choices=[(SiteId("heute"), "Heute"), (SiteId("beta"), "Beta")],
        stored={"performance": "beta"},
    )

    assert only_sites == ["beta"]


def test_show_main_menu_skips_topics_without_entries() -> None:
    with output_funnel.plugged():
        show_main_menu("views", [_topic("empty", [])])
        assert output_funnel.drain() == ""


@pytest.mark.usefixtures("patch_theme")
def test_show_main_menu_renders_one_foldable_container_per_topic() -> None:
    with output_funnel.plugged():
        show_main_menu("views", [_topic("a", [_entry("v1", "View 1")]), _topic("b", [])])
        rendered = output_funnel.drain()

    assert "Topic a" in rendered
    assert "Topic b" not in rendered
    assert "View 1" in rendered
    assert "cmk.sidebar.wato_views_clicked" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_main_menu_prefixes_entries_of_grouping_items() -> None:
    with output_funnel.plugged():
        show_main_menu(
            "views",
            [
                _topic(
                    "a",
                    [
                        _entry(
                            "group",
                            "Group",
                            url=None,
                            mode=TopicItemMode.indented,
                            entries=[_entry("v1", "View 1")],
                        )
                    ],
                )
            ],
        )
        rendered = output_funnel.drain()

    assert "Group | View 1" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_main_menu_with_item_icons_marks_show_more_entries() -> None:
    with output_funnel.plugged():
        show_main_menu(
            "views",
            [_topic("a", [_entry("v1", "View 1", is_show_more=True)])],
            show_item_icons=True,
        )
        rendered = output_funnel.drain()

    assert "show_more_mode" in rendered
    assert 'class="iconlink link"' in rendered


def _visual(**overrides: object) -> Visual:
    spec: dict[str, Any] = {
        "owner": UserId.builtin(),
        "name": "some_visual",
        "context": {},
        "single_infos": [],
        "add_context_to_title": False,
        "title": "Some visual",
        "description": "",
        "topic": "overview",
        "sort_index": 10,
        "is_show_more": False,
        "icon": None,
        "hidden": False,
        "hidebutton": False,
        "public": True,
        "packaged": False,
        "link_from": {},
        "main_menu_search_terms": [],
    }
    spec.update(overrides)
    return spec  # type: ignore[return-value]


def _single_entry(visuals: list[VisualMenuItem]) -> NavItemTopicEntry:
    topics = make_main_menu(visuals, UserPermissions({}, {}, {}, []))
    entries = [entry for topic in topics for entry in topic.entries]
    assert len(entries) == 1
    return entries[0]


@pytest.mark.parametrize(
    "visual_type_name,name,expected_url",
    [
        pytest.param("views", "allhosts", "view.py?view_name=allhosts", id="views"),
        pytest.param(
            "dashboards", "main", "dashboard.py?name=main&owner=", id="dashboards_carry_the_owner"
        ),
        pytest.param("reports", "monthly", "report.py?name=monthly", id="reports"),
        pytest.param("pages", "wato", "wato.py", id="pages_get_a_py_suffix"),
        pytest.param("pages", "wato.py", "wato.py", id="pages_keep_an_existing_py_suffix"),
        pytest.param(
            "custom_graph",
            "cpu",
            "custom_graph.py?name=cpu&owner=",
            id="custom_graph_carries_the_owner",
        ),
        pytest.param(
            "graph_collection", "cpu", "graph_collection.py?name=cpu", id="graph_collection"
        ),
        pytest.param("forecast_graph", "cpu", "forecast_graph.py?name=cpu", id="forecast_graph"),
    ],
)
def test_make_main_menu_builds_the_url_per_visual_type(
    visual_type_name: VisualMenuItemType, name: str, expected_url: str
) -> None:
    entry = _single_entry([VisualMenuItem(visual_type_name, VisualItem(name, _visual()))])

    assert entry.url == expected_url


@pytest.mark.parametrize(
    "visual_type_name,expected_url",
    [
        pytest.param("dashboards", "dashboard.py?name=cpu&owner=harri", id="dashboards"),
        pytest.param("custom_graph", "custom_graph.py?name=cpu&owner=harri", id="custom_graph"),
    ],
)
def test_make_main_menu_builds_the_url_of_a_visual_owned_by_a_user(
    visual_type_name: VisualMenuItemType, expected_url: str
) -> None:
    entry = _single_entry(
        [VisualMenuItem(visual_type_name, VisualItem("cpu", _visual(owner=UserId("harri"))))]
    )

    assert entry.url == expected_url


def test_make_main_menu_rejects_an_unknown_visual_type() -> None:
    """``_visual_url`` is exhaustive over ``VisualMenuItemType``; a type that slipped past
    ``is_menu_item_supported_visual`` must fail loudly rather than build a bogus URL."""
    with pytest.raises(AssertionError):
        make_main_menu(
            [VisualMenuItem("bookmark_list", VisualItem("x", _visual()))],  # type: ignore[arg-type]
            UserPermissions({}, {}, {}, []),
        )


@pytest.mark.parametrize(
    "visual_type_name,expected_transition",
    [
        pytest.param("dashboards", SharedLoadingTransition.dashboard, id="dashboards"),
        pytest.param("custom_graph", SharedLoadingTransition.dashboard, id="custom_graph"),
        pytest.param("views", SharedLoadingTransition.table, id="views"),
        pytest.param("reports", SharedLoadingTransition.table, id="reports"),
        pytest.param("pages", None, id="pages_have_no_transition"),
        pytest.param("graph_collection", None, id="graph_collection_has_no_transition"),
    ],
)
def test_make_main_menu_sets_the_loading_transition(
    visual_type_name: VisualMenuItemType, expected_transition: SharedLoadingTransition | None
) -> None:
    entry = _single_entry([VisualMenuItem(visual_type_name, VisualItem("x", _visual()))])

    assert entry.loading_transition == expected_transition


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({"hidden": True}, id="hidden"),
        pytest.param({"mobile": True}, id="mobile_only"),
    ],
)
def test_make_main_menu_skips_visuals_not_meant_for_the_menu(overrides: dict[str, object]) -> None:
    topics = make_main_menu(
        [VisualMenuItem("views", VisualItem("x", _visual(**overrides)))],
        UserPermissions({}, {}, {}, []),
    )

    assert [entry for topic in topics for entry in topic.entries] == []


def test_make_main_menu_falls_back_to_the_other_topic() -> None:
    """A visual referring to a topic that no longer exists must still show up somewhere
    instead of disappearing from the menu."""
    topics = make_main_menu(
        [VisualMenuItem("views", VisualItem("x", _visual(topic="no_such_topic")))],
        UserPermissions({}, {}, {}, []),
    )

    assert [topic.id for topic in topics] == ["other"]


def test_make_main_menu_sorts_entries_by_sort_index_then_title() -> None:
    topics = make_main_menu(
        [
            VisualMenuItem("views", VisualItem("c", _visual(sort_index=1, title="C"))),
            VisualMenuItem("views", VisualItem("a", _visual(sort_index=2, title="A"))),
            VisualMenuItem("views", VisualItem("b", _visual(sort_index=1, title="B"))),
        ],
        UserPermissions({}, {}, {}, []),
    )

    assert [entry.id for topic in topics for entry in topic.entries] == ["b", "c", "a"]

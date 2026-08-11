#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the snap-ins that list visuals: views and dashboards."""

# mypy: disable-error-code="explicit-any"

import dataclasses
from collections.abc import Iterator
from typing import Any

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.sidebar._snapin._dashboards import Dashboards
from cmk.gui.sidebar._snapin._views import (
    ajax_export_views,
    default_view_menu_topics,
    view_menu_items,
    Views,
)
from cmk.gui.type_defs import Visual
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions

USER_PERMISSIONS = UserPermissions({}, {}, {}, [])


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


def _visual(name: str, title: str, *, topic: str = "overview") -> Visual:
    spec: dict[str, Any] = {
        "owner": UserId.builtin(),
        "name": name,
        "context": {},
        "single_infos": [],
        "add_context_to_title": False,
        "title": title,
        "description": "",
        "topic": topic,
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
    return spec  # type: ignore[return-value]


def _page_context(config: Config) -> PageContext:
    return PageContext(config=config, request=request)


def test_views_metadata() -> None:
    assert Views.type_name() == "views"
    assert Views.title() == "Views"
    assert Views.description() == "Links to global views and dashboards"


def test_dashboards_metadata() -> None:
    assert Dashboards.type_name() == "dashboards"
    assert Dashboards.title() == "Dashboards"
    assert Dashboards.description() == "Links to all dashboards"


def test_view_menu_items_collects_views_and_dashboards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.sidebar._snapin._views.get_permitted_views",
            lambda: {"allhosts": _visual("allhosts", "All hosts")},
        )
        m.setattr(
            "cmk.gui.sidebar._snapin._views.get_permitted_dashboards",
            lambda: {"main": _visual("main", "Main dashboard")},
        )
        items = view_menu_items(USER_PERMISSIONS)

    by_type = {item.type: item for item in items if item.item.name in ("allhosts", "main")}
    assert by_type["views"].item.name == "allhosts"
    assert by_type["dashboards"].item.name == "main"


def test_view_menu_items_includes_the_hardcoded_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """The topology and the all-hosts page are not visuals but must still show up in the
    Monitor menu, so they are wrapped into a visual-like structure."""
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_views", dict)
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_dashboards", dict)
        items = view_menu_items(USER_PERMISSIONS)

    assert "pages" in {item.type for item in items}


def test_view_menu_items_skips_the_hardcoded_pages_without_the_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: False)
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_views", dict)
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_dashboards", dict)
        items = view_menu_items(USER_PERMISSIONS)

    assert "pages" not in {item.type for item in items}


def test_default_view_menu_topics_are_built_from_the_menu_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.sidebar._snapin._views.get_permitted_views",
            lambda: {"allhosts": _visual("allhosts", "All hosts")},
        )
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_dashboards", dict)
        topics = default_view_menu_topics(USER_PERMISSIONS)

    assert "allhosts" in {entry.id for topic in topics for entry in topic.entries}


@pytest.mark.usefixtures("patch_theme")
def test_views_snapin_offers_the_edit_link(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.sidebar._snapin._views.get_permitted_views",
            lambda: {"allhosts": _visual("allhosts", "All hosts")},
        )
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_dashboards", dict)
        with output_funnel.plugged():
            Views().show(load_config)
            rendered = output_funnel.drain()

    assert "All hosts" in rendered
    assert "edit_views.py" in rendered
    assert "export_views.py" not in rendered


@pytest.mark.usefixtures("patch_theme")
def test_views_snapin_offers_the_export_link_only_in_debug_mode(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_views", dict)
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_dashboards", dict)
        with output_funnel.plugged():
            Views().show(dataclasses.replace(load_config, debug=True))
            rendered = output_funnel.drain()

    assert "export_views.py" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_views_snapin_hides_the_footnote_links_without_the_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "general.edit_views")
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_views", dict)
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_dashboards", dict)
        with output_funnel.plugged():
            Views().show(load_config)
            rendered = output_funnel.drain()

    assert "edit_views.py" not in rendered


def test_export_views_publishes_every_permitted_view(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The export is a debugging aid meant to be pasted into a site config, so the owner is
    stripped and everything is made public."""
    views = {"allhosts": _visual("allhosts", "All hosts")}
    views["allhosts"]["owner"] = UserId("harry")
    views["allhosts"]["public"] = False
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar._snapin._views.get_permitted_views", lambda: views)
        ajax_export_views(_page_context(load_config))

    assert views["allhosts"]["owner"] == UserId.builtin()
    assert views["allhosts"]["public"] is True
    assert b"allhosts" in response.get_data()


def test_dashboard_menu_items_are_grouped_into_topics(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.sidebar._snapin._dashboards.get_permitted_dashboards",
            lambda: {"main": _visual("main", "Main dashboard")},
        )
        topics = Dashboards()._get_dashboard_menu_items(USER_PERMISSIONS)

    assert "main" in {entry.id for topic in topics for entry in topic.entries}


@pytest.mark.usefixtures("patch_theme")
def test_dashboards_snapin_offers_the_edit_link(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.sidebar._snapin._dashboards.get_permitted_dashboards",
            lambda: {"main": _visual("main", "Main dashboard")},
        )
        with output_funnel.plugged():
            Dashboards().show(load_config)
            rendered = output_funnel.drain()

    assert "Main dashboard" in rendered
    assert "edit_dashboards.py" in rendered
    assert "export_dashboards.py" not in rendered


@pytest.mark.usefixtures("patch_theme")
def test_dashboards_snapin_offers_the_export_link_only_in_debug_mode(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar._snapin._dashboards.get_permitted_dashboards", dict)
        with output_funnel.plugged():
            Dashboards().show(dataclasses.replace(load_config, debug=True))
            rendered = output_funnel.drain()

    assert "export_dashboards.py" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_dashboards_snapin_hides_the_footnote_links_without_the_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "general.edit_dashboards")
        m.setattr("cmk.gui.sidebar._snapin._dashboards.get_permitted_dashboards", dict)
        with output_funnel.plugged():
            Dashboards().show(load_config)
            rendered = output_funnel.drain()

    assert "edit_dashboards.py" not in rendered

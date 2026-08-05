#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Iterator
from typing import Any, cast, override

import pytest

from cmk.gui.config import Config
from cmk.gui.dashboard.type_defs import SnapinDashletConfig
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.sidebar._snapin._base import SidebarSnapin
from cmk.gui.sidebar._snapin_dashlet import SnapinDashlet, SnapinWidgetIFramePage
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions

USER_PERMISSIONS = UserPermissions({}, {}, {}, [])


class StyledSnapin(SidebarSnapin):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "styled"

    @classmethod
    @override
    def title(cls) -> str:
        return "Styled"

    @classmethod
    @override
    def description(cls) -> str:
        return ""

    @override
    def styles(self) -> str | None:
        return ".styled { color: red; }"

    @override
    def show(self, config: Config) -> None:
        html.write_text_permissive("snapin body")


class PlainSnapin(StyledSnapin):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "plain"

    @override
    def styles(self) -> str | None:
        return None


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


def _dashlet_spec(snapin: str) -> SnapinDashletConfig:
    spec: dict[str, Any] = {"type": "snapin", "snapin": snapin}
    return cast(SnapinDashletConfig, spec)


def _page_context(config: Config) -> PageContext:
    return PageContext(config=config, request=request._get_current_object())


def test_dashlet_metadata() -> None:
    assert SnapinDashlet.type_name() == "snapin"
    assert SnapinDashlet.title() == "Sidebar element"
    assert SnapinDashlet.sort_index() == 55


def test_dashlet_starts_at_a_sidebar_shaped_size() -> None:
    """A snap-in is designed for the narrow sidebar, so the widget starts taller than wide."""
    constraints = SnapinDashlet.relative_layout_constraints()

    assert constraints.initial_size.height > 0
    assert constraints.initial_size.width > 0


def test_dashlet_title_is_the_title_of_the_embedded_snapin(load_config: Config) -> None:
    dashlet = SnapinDashlet(_dashlet_spec("tactical_overview"))

    assert dashlet.default_display_title() == "Overview"


def test_dashlet_title_of_an_unknown_snapin(load_config: Config) -> None:
    dashlet = SnapinDashlet(_dashlet_spec("no_such_snapin"))

    with pytest.raises(KeyError):
        dashlet.default_display_title()


def test_snapin_instance_of_a_known_snapin() -> None:
    instance = SnapinWidgetIFramePage._get_snapin_instance("tactical_overview", USER_PERMISSIONS)

    assert instance.type_name() == "tactical_overview"


def test_snapin_instance_of_an_unknown_snapin() -> None:
    """The widget name comes from the dashboard configuration, which may still reference a
    snap-in that was removed - that has to be a user error, not a crash."""
    with pytest.raises(MKUserError, match="does not exist"):
        SnapinWidgetIFramePage._get_snapin_instance("no_such_snapin", USER_PERMISSIONS)


def test_scrollbar_wraps_its_body() -> None:
    with output_funnel.plugged():
        with SnapinWidgetIFramePage._scrollbar():
            html.write_text_permissive("body")
        rendered = output_funnel.drain()

    assert rendered == '<div id="check_mk_sidebar">body</div>'


def test_scrollbar_is_closed_even_when_the_body_raises() -> None:
    with output_funnel.plugged():
        with pytest.raises(ValueError), SnapinWidgetIFramePage._scrollbar():
            raise ValueError("boom")
        rendered = output_funnel.drain()

    assert rendered == '<div id="check_mk_sidebar"></div>'


def test_snapin_container_carries_the_show_more_state(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "get_show_more_setting", lambda more_id: True)
        with output_funnel.plugged():
            with SnapinWidgetIFramePage._snapin_container("tactical_overview"):
                pass
            more = output_funnel.drain()

        m.setattr(user, "get_show_more_setting", lambda more_id: False)
        with output_funnel.plugged():
            with SnapinWidgetIFramePage._snapin_container("tactical_overview"):
                pass
            less = output_funnel.drain()

    assert 'id="snapin_container_tactical_overview"' in more
    assert "snapin more" in more
    assert "snapin less" in less


def test_show_snapin_injects_the_snapin_styles(load_config: Config) -> None:
    with output_funnel.plugged():
        SnapinWidgetIFramePage._show_snapin(StyledSnapin(), load_config)
        rendered = output_funnel.drain()

    assert 'id="snapin_styled"' in rendered
    assert ".styled { color: red; }" in rendered
    assert "snapin body" in rendered


def test_show_snapin_without_styles_renders_no_style_tag(load_config: Config) -> None:
    with output_funnel.plugged():
        SnapinWidgetIFramePage._show_snapin(PlainSnapin(), load_config)
        rendered = output_funnel.drain()

    assert "<style" not in rendered
    assert "snapin body" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_page_renders_a_standalone_document_around_the_snapin(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The widget is loaded into an iframe, so it needs its own head and body - and must not
    trigger the sidebar's browser reload."""
    request.set_var("name", "time")
    with monkeypatch.context() as m:
        m.setattr(user, "get_show_more_setting", lambda more_id: False)
        with output_funnel.plugged():
            SnapinWidgetIFramePage().page(_page_context(load_config))
            rendered = output_funnel.drain()

    assert "<body" in rendered
    assert 'id="check_mk_sidebar"' in rendered
    assert 'id="side_content"' in rendered
    assert 'id="snapin_container_time"' in rendered


def test_page_rejects_a_request_without_a_name(load_config: Config) -> None:
    with pytest.raises(MKUserError):
        SnapinWidgetIFramePage().page(_page_context(load_config))

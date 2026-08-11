#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import dataclasses
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, override

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import SiteId
from cmk.gui import sidebar, sites
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.permissions import permission_registry
from cmk.gui.sidebar import (
    SidebarRenderer,
    SidebarSnapin,
    SnapinVisibility,
    UserSidebarSnapin,
)
from cmk.gui.theme.current_theme import theme
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions

USER_PERMISSIONS = UserPermissions({}, {}, {}, [])


class NoisySnapin(SidebarSnapin):
    """A snap-in that fails while rendering."""

    @classmethod
    @override
    def type_name(cls) -> str:
        return "noisy"

    @classmethod
    @override
    def title(cls) -> str:
        return "A very long snap-in title that does not fit into the sidebar"

    @classmethod
    @override
    def description(cls) -> str:
        return "Noisy"

    @override
    def styles(self) -> str | None:
        return ".noisy { color: red; }"

    @override
    def show(self, config: Config) -> None:
        raise ValueError("snapin exploded")


class QuietSnapin(SidebarSnapin):
    @classmethod
    @override
    def type_name(cls) -> str:
        return "quiet"

    @classmethod
    @override
    def title(cls) -> str:
        return "Quiet"

    @classmethod
    @override
    def description(cls) -> str:
        return "Quiet"

    @classmethod
    @override
    def has_show_more_items(cls) -> bool:
        return True

    @override
    def show(self, config: Config) -> None:
        html.write_text_permissive("quiet body")


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "confdir", Path(""))
        m.setattr(user, "may", lambda x: True)
        yield


@pytest.fixture(name="extra_snapins")
def fixture_extra_snapins() -> Iterator[None]:
    """Registers the local test snap-ins and removes them again, including permissions."""
    for snapin in (NoisySnapin, QuietSnapin):
        sidebar.snapin_registry.register(snapin)
    try:
        yield
    finally:
        for snapin in (NoisySnapin, QuietSnapin):
            sidebar.snapin_registry.unregister(snapin.type_name())
            permission_registry.unregister(snapin.permission_name())


def _page_context(config: Config) -> PageContext:
    return PageContext(config=config, request=request)


def _only_test_snapins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Limits the snap-in universe to the local test snap-ins.

    Rendering every registered snap-in would reach for livestatus, which says nothing about
    the code under test here."""
    monkeypatch.setattr(
        "cmk.gui.sidebar.all_snapins",
        lambda user_permissions: {"quiet": QuietSnapin, "noisy": NoisySnapin},
    )


def _user_snapin(
    snapin: type[SidebarSnapin], visibility: SnapinVisibility = SnapinVisibility.OPEN
) -> UserSidebarSnapin:
    return UserSidebarSnapin(snapin, visibility)


def test_user_sidebar_snapin_inequality() -> None:
    assert _user_snapin(QuietSnapin) != _user_snapin(NoisySnapin)
    assert _user_snapin(QuietSnapin) != "not a snapin"
    assert _user_snapin(QuietSnapin) != _user_snapin(QuietSnapin, SnapinVisibility.CLOSED)
    assert _user_snapin(QuietSnapin) == _user_snapin(QuietSnapin)


def test_legacy_dict_snapins_become_classes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pre-1.5 plug-ins declared snap-ins as dictionaries; they are wrapped into classes so
    the rest of the sidebar only has to deal with one shape."""
    rendered: list[str] = []
    with monkeypatch.context() as m:
        m.setattr(
            sidebar,
            "sidebar_snapins",
            {
                "legacy": {
                    "title": "Legacy",
                    "description": "An old snap-in",
                    "render": lambda: rendered.append("rendered"),
                    "allowed": ["admin"],
                    "refresh": True,
                    "restart": True,
                    "styles": ".legacy {}",
                }
            },
        )
        sidebar.transform_old_dict_based_snapins()
        try:
            snapin = sidebar.snapin_registry["legacy"]

            assert snapin.type_name() == "legacy"
            assert snapin.title() == "Legacy"
            assert snapin.description() == "An old snap-in"
            assert snapin.allowed_roles() == ["admin"]
            assert snapin.refresh_regularly() is True
            assert snapin.refresh_on_restart() is True
            assert snapin().styles() == ".legacy {}"

            snapin().show(Config())
            assert rendered == ["rendered"]
        finally:
            sidebar.snapin_registry.unregister("legacy")
            permission_registry.unregister("sidesnap.legacy")


def test_legacy_dict_snapins_default_the_optional_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            sidebar,
            "sidebar_snapins",
            {"legacy": {"title": "Legacy", "render": lambda: None, "allowed": ["admin"]}},
        )
        sidebar.transform_old_dict_based_snapins()
        try:
            snapin = sidebar.snapin_registry["legacy"]

            assert snapin.description() == ""
            assert snapin.refresh_regularly() is False
            assert snapin.refresh_on_restart() is False
            assert snapin().styles() is None
        finally:
            sidebar.snapin_registry.unregister("legacy")
            permission_registry.unregister("sidesnap.legacy")


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_render_snapin_shortens_a_long_title(load_config: Config) -> None:
    """The snap-in head is only a few characters wide, so a long title has to be cut rather
    than pushing the close button out of the sidebar."""
    with output_funnel.plugged():
        SidebarRenderer().render_snapin(load_config, _user_snapin(QuietSnapin))
        rendered = output_funnel.drain()

    with output_funnel.plugged():
        SidebarRenderer().render_snapin(load_config, _user_snapin(NoisySnapin))
        long_title = output_funnel.drain()

    assert "Quiet" in rendered
    assert "..." in long_title


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_render_snapin_reports_a_failing_snapin_inline(load_config: Config) -> None:
    """One broken snap-in must not take the whole sidebar with it."""
    with output_funnel.plugged():
        SidebarRenderer().render_snapin(load_config, _user_snapin(NoisySnapin))
        rendered = output_funnel.drain()

    assert "snapinexception" in rendered
    assert "snapin exploded" in rendered


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_render_snapin_injects_the_snapin_styles(load_config: Config) -> None:
    with output_funnel.plugged():
        SidebarRenderer().render_snapin(load_config, _user_snapin(NoisySnapin))
        rendered = output_funnel.drain()

    assert ".noisy { color: red; }" in rendered


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_render_snapin_hides_the_body_of_a_closed_snapin(load_config: Config) -> None:
    with output_funnel.plugged():
        SidebarRenderer().render_snapin(
            load_config, _user_snapin(QuietSnapin, SnapinVisibility.CLOSED)
        )
        rendered = output_funnel.drain()

    assert 'style="display:none"' in rendered
    assert 'class="closesnapin hidden"' in rendered


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_render_snapin_always_opens_a_snapin_the_user_may_not_configure(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """Without the configure permission there is no way to reopen a snap-in, so a closed one
    would be invisible forever."""
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "general.configure_sidebar")
        with output_funnel.plugged():
            SidebarRenderer().render_snapin(
                load_config, _user_snapin(QuietSnapin, SnapinVisibility.CLOSED)
            )
            rendered = output_funnel.drain()

    assert 'style="display:none"' not in rendered
    assert "closesnapin" not in rendered
    assert "snapin_start_drag" not in rendered


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_render_snapin_offers_dragging_and_closing_to_configuring_users(
    load_config: Config,
) -> None:
    with output_funnel.plugged():
        SidebarRenderer().render_snapin(load_config, _user_snapin(QuietSnapin))
        rendered = output_funnel.drain()

    assert "cmk.sidebar.snapin_start_drag(event)" in rendered
    assert "cmk.sidebar.remove_sidebar_snapin" in rendered
    assert "cmk.sidebar.toggle_sidebar_snapin" in rendered


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_render_snapin_offers_the_more_button_for_show_more_snapins(
    load_config: Config,
) -> None:
    with output_funnel.plugged():
        SidebarRenderer().render_snapin(load_config, _user_snapin(QuietSnapin))
        with_more = output_funnel.drain()

    with output_funnel.plugged():
        SidebarRenderer().render_snapin(load_config, _user_snapin(NoisySnapin))
        without_more = output_funnel.drain()

    assert "moresnapin" in with_more
    assert "moresnapin" not in without_more


@pytest.mark.usefixtures("extra_snapins")
def test_snapin_styles_are_only_rendered_when_there_are_any() -> None:
    with output_funnel.plugged():
        SidebarRenderer()._render_snapin_styles(QuietSnapin())
        assert output_funnel.drain() == ""

    with output_funnel.plugged():
        SidebarRenderer()._render_snapin_styles(NoisySnapin())
        assert "<style>" in output_funnel.drain()


@pytest.mark.usefixtures("extra_snapins")
def test_vue_snapin_config_carries_the_refresh_behaviour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "get_show_more_setting", lambda more_id: True)
        config = SidebarRenderer()._migrate_to_vue_sidbar_snapin_config(_user_snapin(QuietSnapin))

    assert config.name == "quiet"
    assert config.title == "Quiet"
    assert config.has_show_more_items is True
    assert config.show_more_active is True
    assert config.open is True


@pytest.mark.usefixtures("extra_snapins")
def test_vue_snapin_config_of_a_closed_snapin() -> None:
    config = SidebarRenderer()._migrate_to_vue_sidbar_snapin_config(
        _user_snapin(QuietSnapin, SnapinVisibility.CLOSED)
    )

    assert config.open is False


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_show_snapins_sorts_the_snapins_by_refresh_behaviour(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The sidebar polls the regularly refreshed snap-ins, re-renders the restart-dependent
    ones only after a core restart, and never touches the static ones."""

    class RegularSnapin(QuietSnapin):
        @classmethod
        @override
        def type_name(cls) -> str:
            return "regular"

        @classmethod
        @override
        def refresh_regularly(cls) -> bool:
            return True

    class RestartSnapin(QuietSnapin):
        @classmethod
        @override
        def type_name(cls) -> str:
            return "restart"

        @classmethod
        @override
        def refresh_on_restart(cls) -> bool:
            return True

    user_config = sidebar.UserSidebarConfig(user, load_config.sidebar, USER_PERMISSIONS)
    del user_config.snapins[:]
    user_config.snapins.extend(
        [
            _user_snapin(RegularSnapin),
            _user_snapin(RestartSnapin),
            _user_snapin(QuietSnapin),
        ]
    )

    with output_funnel.plugged():
        refresh, restart, static = SidebarRenderer()._show_snapins(load_config, user_config)
        output_funnel.drain()

    assert [name for name, _url in refresh] == ["regular", "restart"]
    assert restart == ["restart"]
    assert static == ["quiet"]


@pytest.mark.usefixtures("patch_theme")
def test_add_snapin_button_links_to_the_add_page() -> None:
    with output_funnel.plugged():
        SidebarRenderer()._show_add_snapin_button()
        rendered = output_funnel.drain()

    assert 'id="add_snapin"' in rendered
    assert "sidebar_add_snapin.py" in rendered


def test_icon_path_is_none_without_a_custom_logo(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(theme, "has_custom_logo", lambda name: False)
        assert sidebar._get_icon_path() is None


def test_icon_path_of_a_custom_logo(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(theme, "has_custom_logo", lambda name: True)
        m.setattr(theme, "detect_icon_path", lambda icon_name, prefix: "images/navbar_logo.svg")
        assert sidebar._get_icon_path() == "images/navbar_logo.svg"


@pytest.mark.usefixtures("extra_snapins")
def test_used_snapins_lists_the_configured_snapins(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": [("quiet", "open")]},
        )
        assert sidebar._used_snapins(Config(), USER_PERMISSIONS) == ["quiet"]


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_ajax_snapin_renders_the_requested_snapin(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("name", "quiet")
    with monkeypatch.context() as m:
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": [("quiet", "open")]},
        )
        sidebar.ajax_snapin(_page_context(load_config))

    assert "quiet body" in json.loads(response.get_data())[0]


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_ajax_snapin_renders_several_snapins_by_name(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("names", "quiet,not_configured")
    with monkeypatch.context() as m:
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": [("quiet", "open")]},
        )
        sidebar.ajax_snapin(_page_context(load_config))

    assert len(json.loads(response.get_data())) == 1


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_ajax_snapin_reports_a_failing_snapin_without_failing_the_request(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("name", "noisy")
    with monkeypatch.context() as m:
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": [("noisy", "open")]},
        )
        sidebar.ajax_snapin(_page_context(load_config))

    assert "snapinexception" in json.loads(response.get_data())[0]


@pytest.mark.usefixtures("patch_theme")
def test_ajax_snapin_skips_a_restart_snapin_without_a_restart(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """A snap-in that only refreshes on restart is polled like the others; without a restart
    it answers with an empty body so the client keeps its current content."""
    request.set_var("name", "hostgroups")
    request.set_var("since", "1000")
    with monkeypatch.context() as m:
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": [("hostgroups", "open")]},
        )
        m.setattr(sites, "states", dict)
        sidebar.ajax_snapin(_page_context(load_config))

    assert json.loads(response.get_data()) == [""]


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_open_close_rejects_an_invalid_state(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("name", "quiet")
    request.set_var("state", "sideways")
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.check_csrf_token", lambda: None)
        with pytest.raises(MKUserError, match="Invalid state"):
            sidebar.AjaxOpenCloseSnapin().page(_page_context(load_config))


def test_open_close_needs_the_configure_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.check_csrf_token", lambda: None)
        m.setattr(user, "may", lambda x: x != "general.configure_sidebar")
        m_save = _NeverCalled()
        m.setattr(sidebar.UserSidebarConfig, "save", m_save)

        assert sidebar.AjaxOpenCloseSnapin().page(_page_context(load_config)) is None


def test_open_close_without_a_snapin_name(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.check_csrf_token", lambda: None)

        assert sidebar.AjaxOpenCloseSnapin().page(_page_context(load_config)) is None


@pytest.mark.usefixtures("extra_snapins")
def test_open_close_of_a_snapin_that_is_not_configured(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("name", "quiet")
    request.set_var("state", "closed")
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.check_csrf_token", lambda: None)
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": []},
        )

        assert sidebar.AjaxOpenCloseSnapin().page(_page_context(load_config)) is None


def test_move_snapin_without_a_name(monkeypatch: pytest.MonkeyPatch, load_config: Config) -> None:
    with monkeypatch.context() as m:
        m.setattr(sidebar.UserSidebarConfig, "_load", _NeverCalled())

        sidebar.move_snapin(_page_context(load_config))


def test_add_snapin_needs_the_configure_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.check_csrf_token", lambda: None)
        m.setattr(user, "may", lambda x: x != "general.configure_sidebar")
        with pytest.raises(MKGeneralException, match="not allowed"):
            sidebar.AjaxAddSnapin().page(_page_context(load_config))


def test_add_snapin_rejects_an_unknown_snapin(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("name", "no_such_snapin")
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.check_csrf_token", lambda: None)
        with pytest.raises(MKUserError, match="Invalid sidebar element"):
            sidebar.AjaxAddSnapin().page(_page_context(load_config))


@pytest.mark.usefixtures("extra_snapins")
def test_add_snapin_rejects_an_already_enabled_snapin(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("name", "quiet")
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.check_csrf_token", lambda: None)
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": [("quiet", "open")]},
        )
        with pytest.raises(MKUserError, match="already enabled"):
            sidebar.AjaxAddSnapin().page(_page_context(load_config))


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_add_snapin_returns_the_rendered_snapin(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    request.set_var("name", "quiet")
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar.check_csrf_token", lambda: None)
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": []},
        )
        m.setattr(sidebar.UserSidebarConfig, "save", lambda self: None)
        result = sidebar.AjaxAddSnapin().page(_page_context(load_config))

    assert isinstance(result, dict)
    assert result["name"] == "quiet"
    assert "quiet body" in str(result["content"])


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_available_snapins_exclude_the_configured_ones(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        _only_test_snapins(m)
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": [("quiet", "open")]},
        )
        available = sidebar.AjaxGetAvialableSnapins().page(_page_context(load_config))

    assert isinstance(available, list)
    names = [entry["name"] for entry in available]
    assert "quiet" not in names
    assert "noisy" in names


@pytest.mark.usefixtures("patch_theme", "extra_snapins")
def test_available_snapins_preview_a_failing_snapin(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The add dialog renders every element as a preview; one that raises must show its
    error in place instead of emptying the whole dialog."""
    with monkeypatch.context() as m:
        _only_test_snapins(m)
        m.setattr(
            sidebar.UserSidebarConfig,
            "_user_config",
            lambda self: {"fold": False, "snapins": []},
        )
        available = sidebar.AjaxGetAvialableSnapins().page(_page_context(load_config))

    assert isinstance(available, list)
    noisy = next(entry for entry in available if entry["name"] == "noisy")
    assert "snapinexception" in str(noisy["content"])


@pytest.mark.usefixtures("extra_snapins")
def test_set_snapin_site_rejects_an_unknown_snapin(load_config: Config) -> None:
    request.set_var("ident", "no_such_snapin")

    with pytest.raises(MKUserError, match="Invalid ident"):
        sidebar.ajax_set_snapin_site(_page_context(load_config))


@pytest.mark.usefixtures("extra_snapins")
def test_set_snapin_site_rejects_an_unknown_site(load_config: Config) -> None:
    """The site is written into the user's profile and later used as a livestatus filter, so
    it has to be one of the configured sites."""
    request.set_var("ident", "quiet")
    request.set_var("site", "no_such_site")

    with pytest.raises(MKUserError, match="Invalid site"):
        sidebar.ajax_set_snapin_site(_page_context(load_config))


@pytest.mark.usefixtures("extra_snapins")
def test_set_snapin_site_stores_all_sites(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    saved: dict[str, Any] = {}
    request.set_var("ident", "quiet")
    request.set_var("site", "")
    with monkeypatch.context() as m:
        m.setattr(user, "load_file", lambda *args, **kwargs: {})
        m.setattr(user, "save_file", lambda name, content: saved.update({name: content}))
        sidebar.ajax_set_snapin_site(_page_context(load_config))

    assert saved == {"sidebar_sites": {"quiet": ""}}


@pytest.mark.usefixtures("extra_snapins")
def test_set_snapin_site_stores_a_configured_site(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    saved: dict[str, Any] = {}
    request.set_var("ident", "quiet")
    request.set_var("site", "NO_SITE")
    with monkeypatch.context() as m:
        m.setattr(
            "cmk.gui.sidebar.get_configured_site_choices",
            lambda: [(SiteId("NO_SITE"), "Local site")],
        )
        m.setattr(user, "load_file", lambda *args, **kwargs: {})
        m.setattr(user, "save_file", lambda name, content: saved.update({name: content}))
        sidebar.ajax_set_snapin_site(_page_context(load_config))

    assert saved == {"sidebar_sites": {"quiet": "NO_SITE"}}


@pytest.mark.usefixtures("patch_theme")
def test_add_snapin_page_needs_the_configure_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "general.configure_sidebar")
        with pytest.raises(MKGeneralException, match="not allowed"):
            sidebar.page_add_snapin(_page_context(load_config))


class _NeverCalled:
    def __call__(self, *args: object, **kwargs: object) -> None:
        raise AssertionError("must not be called")


def test_renderer_writes_the_content_between_navigation_and_close(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """Chrome-bearing pages render their body into the same document as the sidebar, so the
    content has to land inside the opened content area."""
    calls: list[str] = []
    with monkeypatch.context() as m:
        m.setattr(
            SidebarRenderer,
            "render_main_navigation_with_open_content_area",
            lambda self, title, nav: calls.append("open"),
        )
        m.setattr(
            SidebarRenderer,
            "render_main_navigation_close",
            lambda self: calls.append("close"),
        )
        with output_funnel.plugged():
            SidebarRenderer().show(
                config=load_config,
                user_permissions=USER_PERMISSIONS,
                title=None,
                content=html.render_div("body"),
                sidebar_config=load_config.sidebar,
                screenshot_mode=False,
                sidebar_notify_interval=None,
                start_url="index.py",
                show_scrollbar=False,
                sidebar_update_interval=30.0,
                kiosk=False,
            )
            rendered = output_funnel.drain()

    assert calls == ["open", "close"]
    assert "<div>body</div>" in rendered


def test_renderer_without_content(monkeypatch: pytest.MonkeyPatch, load_config: Config) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            SidebarRenderer,
            "render_main_navigation_with_open_content_area",
            lambda self, title, nav: None,
        )
        m.setattr(SidebarRenderer, "render_main_navigation_close", lambda self: None)
        with output_funnel.plugged():
            SidebarRenderer().show(
                config=load_config,
                user_permissions=USER_PERMISSIONS,
                title=None,
                content=None,
                sidebar_config=load_config.sidebar,
                screenshot_mode=False,
                sidebar_notify_interval=None,
                start_url="index.py",
                show_scrollbar=False,
                sidebar_update_interval=30.0,
                kiosk=False,
            )
            assert output_funnel.drain() == ""


@pytest.mark.usefixtures("patch_theme")
def test_body_start_marks_screenshot_mode(load_config: Config) -> None:
    with output_funnel.plugged():
        SidebarRenderer()._show_body_start(
            screenshot_mode=True, sidebar_notify_interval=None, kiosk=False
        )
        rendered = output_funnel.drain()

    assert "screenshotmode" in rendered
    assert "side" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_body_start_of_a_kiosk_page_has_no_sidebar_shell(load_config: Config) -> None:
    """Kiosk pages (widget iframes) host no sidebar, so they must not get its body styling."""
    with output_funnel.plugged():
        SidebarRenderer()._show_body_start(
            screenshot_mode=False, sidebar_notify_interval=None, kiosk=True
        )
        rendered = output_funnel.drain()

    assert 'class="side"' not in rendered


@pytest.mark.usefixtures("patch_theme")
def test_sidebar_is_replaced_by_a_placeholder_without_the_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The navigation container is always present so the layout does not shift; it just
    stays empty for users who may not see the sidebar."""
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "general.see_sidebar")
        with output_funnel.plugged():
            SidebarRenderer()._show_sidebar(
                load_config,
                USER_PERMISSIONS,
                load_config.sidebar,
                "index.py",
                show_scrollbar=False,
                sidebar_update_interval=30.0,
            )
            rendered = output_funnel.drain()

    assert rendered == '<div id="check_mk_navigation"></div>'


def test_page_side_uses_the_configured_sidebar(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    seen: dict[str, Any] = {}

    def _show(self: SidebarRenderer, **kwargs: Any) -> None:
        seen.update(kwargs)

    with monkeypatch.context() as m:
        m.setattr(SidebarRenderer, "show", _show)
        sidebar.page_side(_page_context(dataclasses.replace(load_config, screenshotmode=True)))

    assert seen["kiosk"] is False
    assert seen["content"] is None
    assert seen["screenshot_mode"] is True

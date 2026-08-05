#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Iterator
from typing import cast

import pytest

from livestatus import SiteConfiguration, SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui import sites, user_sites
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.sidebar._snapin._site_status import SiteStatus as SiteStatusSnapin
from cmk.gui.sites import SiteStatus
from cmk.gui.utils.output_funnel import output_funnel


class RecordingSiteConfig:
    """Captures the per-user site enable/disable calls instead of writing the profile."""

    def __init__(self) -> None:
        self.enabled: list[SiteId] = []
        self.disabled: list[SiteId] = []
        self.saved = 0

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(user, "enable_site", self.enabled.append)
        monkeypatch.setattr(user, "disable_site", self.disabled.append)
        monkeypatch.setattr(user, "save_site_config", self._save)

    def _save(self) -> None:
        self.saved += 1


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        m.setattr(sites, "update_site_states_from_dead_sites", lambda: None)
        yield


def _config_with_sites(config: Config, aliases: dict[str, str]) -> Config:
    return dataclasses.replace(
        config,
        sites=SiteConfigurations(
            {
                SiteId(site_id): cast(SiteConfiguration, {"alias": alias})
                for site_id, alias in aliases.items()
            }
        ),
    )


def _show(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
    *,
    aliases: dict[str, str],
    states: dict[SiteId, SiteStatus],
) -> str:
    with monkeypatch.context() as m:
        m.setattr(sites, "states", lambda: states)
        m.setattr(
            user_sites,
            "sorted_sites",
            lambda site_configs: [(SiteId(s), a) for s, a in aliases.items()],
        )
        with output_funnel.plugged():
            SiteStatusSnapin().show(_config_with_sites(config, aliases))
            return output_funnel.drain()


def test_snapin_metadata() -> None:
    assert SiteStatusSnapin.type_name() == "sitestatus"
    assert SiteStatusSnapin.title() == "Site status"
    assert SiteStatusSnapin.refresh_regularly() is True


def test_guests_may_not_switch_site_connections() -> None:
    assert SiteStatusSnapin.allowed_roles() == ["user", "admin"]


def test_page_handlers_expose_both_switch_endpoints() -> None:
    assert sorted(SiteStatusSnapin().page_handlers()) == ["set_all_sites", "switch_site"]


@pytest.mark.usefixtures("patch_theme")
def test_show_marks_a_site_without_a_state_as_missing(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """A configured site the livestatus layer never answered for must be visible as broken
    rather than silently offered as switchable."""
    rendered = _show(monkeypatch, load_config, aliases={"gone": "Gone site"}, states={})

    assert "missing" in rendered
    assert "Site is missing" in rendered
    assert "switch_site.py" not in rendered
    assert "Gone site" not in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_offers_to_enable_a_disabled_site(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    rendered = _show(
        monkeypatch,
        load_config,
        aliases={"beta": "Beta site"},
        states={SiteId("beta"): SiteStatus(state="disabled")},
    )

    assert "Beta site" in rendered
    assert "Enable this site" in rendered
    assert "_site_switch=beta%3Aon" in rendered
    assert "view.py?view_name=sitehosts" not in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_links_an_online_site_to_its_hosts(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    rendered = _show(
        monkeypatch,
        load_config,
        aliases={"heute": "Heute site"},
        states={SiteId("heute"): SiteStatus(state="online")},
    )

    assert "Disable this site" in rendered
    assert "_site_switch=heute%3Aoff" in rendered
    assert "view.py?view_name=sitehosts&site=heute" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_offers_the_bulk_switches(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    rendered = _show(
        monkeypatch,
        load_config,
        aliases={"heute": "Heute site"},
        states={SiteId("heute"): SiteStatus(state="online")},
    )

    assert "Enable all" in rendered
    assert "Disable all" in rendered
    assert "set_all_sites.py?_new_state=online" in rendered
    assert "set_all_sites.py?_new_state=disabled" in rendered


def _page_context(config: Config) -> PageContext:
    return PageContext(config=config, request=request._get_current_object())


def test_switch_site_needs_the_snapin_permission(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The endpoint is reachable for anyone with a session, so it has to re-check the
    permission itself instead of relying on the snap-in being visible."""
    recorded = RecordingSiteConfig()
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar._snapin._site_status.check_csrf_token", lambda: None)
        m.setattr(user, "may", lambda x: x != "sidesnap.sitestatus")
        recorded.install(m)
        request.set_var("_site_switch", "heute:off")

        SiteStatusSnapin()._ajax_switch_site(_page_context(load_config))

    assert recorded.disabled == []
    assert recorded.saved == 0


@pytest.mark.parametrize(
    "switch_var,expected_enabled,expected_disabled",
    [
        pytest.param("heute:off", [], ["heute"], id="disable_one"),
        pytest.param("heute:on", ["heute"], [], id="enable_one"),
        pytest.param("heute:on,beta:off", ["heute"], ["beta"], id="both_at_once"),
        pytest.param("gone:off", [], [], id="unknown_site_is_ignored"),
    ],
)
def test_switch_site_applies_the_requested_states(
    monkeypatch: pytest.MonkeyPatch,
    load_config: Config,
    switch_var: str,
    expected_enabled: list[str],
    expected_disabled: list[str],
) -> None:
    recorded = RecordingSiteConfig()
    config = _config_with_sites(load_config, {"heute": "Heute", "beta": "Beta"})
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar._snapin._site_status.check_csrf_token", lambda: None)
        recorded.install(m)
        request.set_var("_site_switch", switch_var)

        SiteStatusSnapin()._ajax_switch_site(_page_context(config))

    assert recorded.enabled == [SiteId(s) for s in expected_enabled]
    assert recorded.disabled == [SiteId(s) for s in expected_disabled]
    assert recorded.saved == 1


def test_switch_site_without_a_request_variable(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    recorded = RecordingSiteConfig()
    with monkeypatch.context() as m:
        m.setattr("cmk.gui.sidebar._snapin._site_status.check_csrf_token", lambda: None)
        recorded.install(m)

        SiteStatusSnapin()._ajax_switch_site(_page_context(load_config))

    assert recorded.saved == 0


@pytest.mark.parametrize(
    "new_state,expected_enabled,expected_disabled",
    [
        pytest.param("online", ["beta"], [], id="enable_all_only_touches_disabled_sites"),
        pytest.param("disabled", [], ["heute"], id="disable_all_only_touches_online_sites"),
        pytest.param("junk", [], [], id="unknown_state_changes_nothing"),
    ],
)
def test_set_all_sites_skips_sites_already_in_the_target_state(
    monkeypatch: pytest.MonkeyPatch,
    load_config: Config,
    new_state: str,
    expected_enabled: list[str],
    expected_disabled: list[str],
) -> None:
    """Sites in a transient state (down, unreach, ...) must be left alone - flipping them
    would overwrite the user's per-site configuration based on a temporary outage."""
    recorded = RecordingSiteConfig()
    aliases = {"heute": "Heute", "beta": "Beta", "old": "Old"}
    with monkeypatch.context() as m:
        recorded.install(m)
        m.setattr(
            sites,
            "states",
            lambda: {
                SiteId("heute"): SiteStatus(state="online"),
                SiteId("beta"): SiteStatus(state="disabled"),
                SiteId("old"): SiteStatus(state="down"),
            },
        )
        m.setattr(
            user_sites,
            "sorted_sites",
            lambda site_configs: [(SiteId(s), a) for s, a in aliases.items()],
        )
        request.set_var("_new_state", new_state)

        SiteStatusSnapin()._ajax_set_all_sites(
            _page_context(_config_with_sites(load_config, aliases))
        )

    assert recorded.enabled == [SiteId(s) for s in expected_enabled]
    assert recorded.disabled == [SiteId(s) for s in expected_disabled]
    assert recorded.saved == 1


def test_set_all_sites_ignores_sites_without_a_state(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    recorded = RecordingSiteConfig()
    aliases = {"gone": "Gone"}
    with monkeypatch.context() as m:
        recorded.install(m)
        m.setattr(sites, "states", dict)
        m.setattr(
            user_sites,
            "sorted_sites",
            lambda site_configs: [(SiteId(s), a) for s, a in aliases.items()],
        )
        request.set_var("_new_state", "online")

        SiteStatusSnapin()._ajax_set_all_sites(
            _page_context(_config_with_sites(load_config, aliases))
        )

    assert recorded.enabled == []
    assert recorded.disabled == []

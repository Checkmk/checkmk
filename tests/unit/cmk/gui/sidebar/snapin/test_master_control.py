#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Literal

import pytest

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.config import Config
from cmk.gui.logged_in import user
from cmk.gui.sidebar._snapin._master_control import MasterControlSnapin
from cmk.gui.sites import SiteStatus
from cmk.gui.utils.output_funnel import output_funnel
from cmk.livestatus_client import MKLivestatusQueryError

CMC_VERSION = "Check_MK 2.5.0"
NAGIOS_VERSION = "Nagios 4.4.6"

type SiteState = Literal[
    "online", "disabled", "down", "unreach", "dead", "waiting", "missing", "unknown"
]


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "confdir", Path(""))
        m.setattr(user, "may", lambda x: True)
        yield


class FakeLive:
    def __init__(self, rows: Sequence[Sequence[object]] | Exception) -> None:
        self._rows = rows
        self.prepend_site: list[bool] = []
        self.queries: list[str] = []

    def set_prepend_site(self, value: bool) -> None:
        self.prepend_site.append(value)

    def query(self, query: str) -> Sequence[Sequence[object]]:
        self.queries.append(query)
        if isinstance(self._rows, Exception):
            raise self._rows
        return self._rows


def _site_state(
    state: SiteState, *, exception: str | None = None, program_version: str = CMC_VERSION
) -> SiteStatus:
    site_status = SiteStatus(state=state, program_version=program_version)
    if exception is not None:
        site_status["exception"] = MKLivestatusQueryError(exception)
    return site_status


def _all_toggles_on() -> dict[SiteId, list]:
    return {SiteId("heute"): [1] * len(MasterControlSnapin()._core_toggles())}


def _show_site(
    monkeypatch: pytest.MonkeyPatch,
    *,
    site_state: SiteStatus | None,
    site_status_info: dict[SiteId, list] | None = None,
) -> str:
    with monkeypatch.context() as m:
        m.setattr(
            sites, "states", lambda: {} if site_state is None else {SiteId("heute"): site_state}
        )
        with output_funnel.plugged():
            MasterControlSnapin()._show_master_control_site(
                SiteId("heute"),
                _all_toggles_on() if site_status_info is None else site_status_info,
                MasterControlSnapin()._core_toggles(),
            )
            return output_funnel.drain()


def test_snapin_metadata() -> None:
    assert MasterControlSnapin.type_name() == "master_control"
    assert MasterControlSnapin.title() == "Master control"
    assert MasterControlSnapin.refresh_regularly() is True


def test_only_administrators_may_flip_the_master_switches() -> None:
    assert MasterControlSnapin.allowed_roles() == ["admin"]


def test_page_handlers_expose_the_switch_endpoint() -> None:
    assert list(MasterControlSnapin().page_handlers()) == ["switch_master_state"]


def test_core_toggles_cover_both_handler_flavours() -> None:
    """Event handlers and alert handlers share one livestatus column; the snap-in lists it
    twice and picks the right label per core, so both entries must stay present."""
    titles = [title for _colname, title in MasterControlSnapin()._core_toggles()]

    assert "Event handlers" in titles
    assert "Alert handlers" in titles
    assert [colname for colname, title in MasterControlSnapin()._core_toggles()].count(
        "enable_event_handlers"
    ) == 2


def test_show_site_without_a_known_state(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_site(monkeypatch, site_state=None)

    assert "Site state is unknown" in rendered
    assert "master_control" not in rendered


def test_show_site_that_is_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_site(monkeypatch, site_state=_site_state("dead"))

    assert "Site is dead" in rendered


def test_show_site_that_is_dead_reports_the_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_site(
        monkeypatch, site_state=_site_state("dead", exception="Connection refused")
    )

    assert "Connection refused" in rendered
    assert "Site is dead" not in rendered


def test_show_site_that_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_site(monkeypatch, site_state=_site_state("disabled"))

    assert "Site is disabled" in rendered


def test_show_site_in_unknown_state(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_site(monkeypatch, site_state=_site_state("unknown"))

    assert "Site state is unknown" in rendered


def test_show_site_in_unknown_state_reports_the_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered = _show_site(
        monkeypatch, site_state=_site_state("unknown", exception="Bad certificate")
    )

    assert "Bad certificate" in rendered


def test_show_site_without_status_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """The site answered the state query but not the status query - rendering toggles from
    missing data would show wrong switch positions."""
    rendered = _show_site(monkeypatch, site_state=_site_state("online"), site_status_info={})

    assert "Site state is unknown" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_site_hides_event_handlers_on_the_micro_core(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_site(monkeypatch, site_state=_site_state("online"))

    assert "Alert handlers" in rendered
    assert "Event handlers" not in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_site_hides_alert_handlers_on_nagios(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_site(
        monkeypatch,
        site_state=_site_state("online", program_version=NAGIOS_VERSION),
    )

    assert "Event handlers" in rendered
    assert "Alert handlers" not in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_site_links_each_toggle_to_the_opposite_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(sites, "states", lambda: {SiteId("heute"): _site_state("online")})
        with output_funnel.plugged():
            MasterControlSnapin()._show_master_control_site(
                SiteId("heute"),
                {SiteId("heute"): [1, 0, 1, 1, 1, 1, 1]},
                MasterControlSnapin()._core_toggles(),
            )
            rendered = output_funnel.drain()

    assert "state=0&amp;switch=enable_notifications" in rendered
    assert "state=1&amp;switch=execute_service_checks" in rendered
    assert "cmk.sidebar.update_vue_snapin_contents" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_reports_a_broken_site_without_hiding_the_others(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """One site raising while its switches are rendered must not take the whole snap-in
    down - the remaining sites still need their controls."""
    with monkeypatch.context() as m:
        m.setattr(sites, "live", lambda: FakeLive([["heute", *([1] * 7)]]))
        m.setattr(sites, "update_site_states_from_dead_sites", lambda: None)
        m.setattr(sites, "states", lambda: {SiteId("heute"): _site_state("online")})
        m.setattr(
            MasterControlSnapin,
            "_show_master_control_site",
            lambda *args: (_ for _ in ()).throw(ValueError("boom")),
        )
        with output_funnel.plugged():
            MasterControlSnapin().show(load_config)
            rendered = output_funnel.drain()

    assert "snapinexception" in rendered
    assert "boom" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_show_resets_prepend_site_on_the_shared_connection(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    live = FakeLive([["heute", *([1] * 7)]])
    with monkeypatch.context() as m:
        m.setattr(sites, "live", lambda: live)
        m.setattr(sites, "update_site_states_from_dead_sites", lambda: None)
        m.setattr(sites, "states", lambda: {SiteId("heute"): _site_state("online")})
        with output_funnel.plugged():
            MasterControlSnapin().show(load_config)
            output_funnel.drain()

    assert live.prepend_site == [True, False]

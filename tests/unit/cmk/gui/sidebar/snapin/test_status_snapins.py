#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the thin livestatus-backed status snap-ins: server time, Speed-O-Meter and
server performance."""

import json
import re
from collections.abc import Iterator, Sequence

import pytest

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.config import Config
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.pages import PageContext
from cmk.gui.sidebar._snapin._performance import Performance
from cmk.gui.sidebar._snapin._server_time import CurrentTime
from cmk.gui.sidebar._snapin._speedometer import Speedometer
from cmk.gui.utils.output_funnel import output_funnel

PERFORMANCE_COLUMNS = 16


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: True)
        yield


class FakeLive:
    def __init__(
        self,
        *,
        rows: Sequence[Sequence[float]] = (),
        summed_stats: Sequence[Sequence[float]] = (),
    ) -> None:
        self._rows = rows
        self._summed_stats = list(summed_stats)
        self.only_sites: list[list[SiteId] | None] = []
        self.queries: list[str] = []

    def set_only_sites(self, only_sites: list[SiteId] | None = None) -> None:
        self.only_sites.append(only_sites)

    def query(self, query: str) -> Sequence[Sequence[float]]:
        self.queries.append(query)
        return self._rows

    def query_summed_stats(self, query: str) -> Sequence[float]:
        self.queries.append(query)
        return self._summed_stats.pop(0)


def _page_context(config: Config) -> PageContext:
    return PageContext(config=config, request=request)


def test_server_time_metadata() -> None:
    assert CurrentTime.type_name() == "time"
    assert CurrentTime.title() == "Server time"
    assert CurrentTime.refresh_regularly() is True


def test_server_time_renders_hours_and_minutes(load_config: Config) -> None:
    with output_funnel.plugged():
        CurrentTime().show(load_config)
        rendered = output_funnel.drain()

    assert re.fullmatch(r'<div class="time">\d{2}:\d{2}</div>', rendered)


def test_speedometer_metadata() -> None:
    assert Speedometer.type_name() == "speedometer"
    assert Speedometer.allowed_roles() == ["admin"]
    assert list(Speedometer().page_handlers()) == ["sidebar_ajax_speedometer"]


@pytest.mark.usefixtures("patch_theme")
def test_speedometer_renders_a_canvas_over_the_dial(load_config: Config) -> None:
    with output_funnel.plugged():
        Speedometer().show(load_config)
        rendered = output_funnel.drain()

    assert 'id="speedometerbg"' in rendered
    assert "<canvas" in rendered
    assert "cmk.sidebar.speedometer_show_speed(0, 0, 0);" in rendered


def _ajax_speedometer(
    monkeypatch: pytest.MonkeyPatch,
    config: Config,
    *,
    live: FakeLive,
    last_perc: str = "50",
    scheduled_rate: str = "10",
    program_start: str = "1000",
) -> dict[str, object]:
    request.set_var("last_perc", last_perc)
    request.set_var("scheduled_rate", scheduled_rate)
    request.set_var("program_start", program_start)
    with monkeypatch.context() as m:
        m.setattr(sites, "live", lambda: live)
        Speedometer()._ajax_speedometer(_page_context(config))
    payload = json.loads(response.get_data())
    assert isinstance(payload, dict)
    return payload


def test_ajax_speedometer_reuses_the_known_scheduled_rate(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """Deriving the scheduled rate loops over every service, so it is only recomputed when
    a site restarted and the configuration may have changed."""
    live = FakeLive(summed_stats=[[5.0, 1000]])

    payload = _ajax_speedometer(monkeypatch, load_config, live=live)

    assert payload["scheduled_rate"] == 10.0
    assert payload["percentage"] == 50.0
    assert len(live.queries) == 1


def test_ajax_speedometer_recomputes_the_rate_after_a_restart(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    live = FakeLive(summed_stats=[[5.0, 2000], [600.0]])

    payload = _ajax_speedometer(monkeypatch, load_config, live=live)

    assert payload["scheduled_rate"] == 10.0
    assert payload["program_start"] == 2000
    assert len(live.queries) == 2


def test_ajax_speedometer_falls_back_when_there_are_no_metrics(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The snap-in is polled regularly; a site that cannot answer must produce a needle at
    zero with an explanation instead of an error page."""
    live = FakeLive(summed_stats=[[0.0, 1000]])

    payload = _ajax_speedometer(
        monkeypatch, load_config, live=live, scheduled_rate="0", program_start="1000"
    )

    assert payload["percentage"] == 0
    assert payload["scheduled_rate"] == 0.0
    assert payload["last_perc"] == 0.0
    assert "No metrics" in str(payload["title"])


def test_performance_metadata() -> None:
    assert Performance.type_name() == "performance"
    assert Performance.allowed_roles() == ["admin"]
    assert Performance.has_show_more_items() is True
    assert Performance.refresh_regularly() is True
    assert Performance.refresh_on_restart() is True


@pytest.mark.usefixtures("patch_theme")
def test_performance_sums_the_rates_of_all_sites(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    live = FakeLive(
        rows=[[1.0] * PERFORMANCE_COLUMNS, [2.0] * PERFORMANCE_COLUMNS],
    )
    with monkeypatch.context() as m:
        m.setattr(sites, "live", lambda: live)
        m.setattr("cmk.gui.sidebar._snapin._performance.snapin_site_choice", lambda *a: None)
        m.setattr("cmk.gui.sidebar._snapin._performance.site_config.enabled_sites", lambda s: {})
        with output_funnel.plugged():
            Performance().show(load_config)
            rendered = output_funnel.drain()

    assert "Service checks:" in rendered
    assert "3.00/s" in rendered
    assert "Com. buf. max/total" not in rendered


@pytest.mark.usefixtures("patch_theme")
def test_performance_shows_the_command_buffer_only_for_a_single_site(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    """The command buffer is a per-core number; summing it over several sites would be
    meaningless, so it is only shown when exactly one site is queried."""
    live = FakeLive(rows=[[7.0] * PERFORMANCE_COLUMNS])
    with monkeypatch.context() as m:
        m.setattr(sites, "live", lambda: live)
        m.setattr("cmk.gui.sidebar._snapin._performance.snapin_site_choice", lambda *a: None)
        m.setattr(
            "cmk.gui.sidebar._snapin._performance.site_config.enabled_sites",
            lambda s: {SiteId("heute"): {}},
        )
        with output_funnel.plugged():
            Performance().show(load_config)
            rendered = output_funnel.drain()

    assert "Com. buf. max/total" in rendered
    assert live.only_sites == [None, None, None]


@pytest.mark.usefixtures("patch_theme")
def test_performance_restricted_to_one_site_skips_the_command_buffer(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    live = FakeLive(rows=[[7.0] * PERFORMANCE_COLUMNS])
    with monkeypatch.context() as m:
        m.setattr(sites, "live", lambda: live)
        m.setattr(
            "cmk.gui.sidebar._snapin._performance.snapin_site_choice",
            lambda *a: [SiteId("heute")],
        )
        m.setattr(
            "cmk.gui.sidebar._snapin._performance.site_config.enabled_sites",
            lambda s: {SiteId("heute"): {}},
        )
        with output_funnel.plugged():
            Performance().show(load_config)
            rendered = output_funnel.drain()

    assert "Com. buf. max/total" not in rendered
    assert live.only_sites[0] == [SiteId("heute")]

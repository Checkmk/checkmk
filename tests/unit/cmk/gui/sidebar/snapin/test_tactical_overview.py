#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Literal

import pytest

import cmk.livestatus_client as livestatus
from cmk.ccc.site import SiteId
from cmk.gui import notifications, sites
from cmk.gui.logged_in import user
from cmk.gui.sidebar._snapin._tactical_overview import (
    get_context_url_variables,
    group_by_state,
    TacticalOverviewSnapin,
    total_url,
)
from cmk.gui.utils.output_funnel import output_funnel


@pytest.fixture(name="permissive_user", autouse=True)
def fixture_permissive_user(
    request_context: None, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    with monkeypatch.context() as m:
        m.setattr(user, "confdir", Path(""))
        m.setattr(user, "may", lambda x: True)
        yield


class FakeLive:
    """Records the livestatus interaction of the snap-in without talking to a core."""

    def __init__(self, summed_stats: Sequence[int] | Exception) -> None:
        self._summed_stats = summed_stats
        self.auth_domains: list[str] = []
        self.only_sites: list[list[SiteId] | None] = []
        self.queries: list[str | livestatus.Query] = []

    def set_auth_domain(self, domain: str) -> None:
        self.auth_domains.append(domain)

    def set_only_sites(self, only_sites: list[SiteId] | None = None) -> None:
        self.only_sites.append(only_sites)

    def query_summed_stats(self, query: str | livestatus.Query) -> Sequence[int]:
        self.queries.append(query)
        if isinstance(self._summed_stats, Exception):
            raise self._summed_stats
        return self._summed_stats


def test_get_context_url_variables_flattens_all_filters() -> None:
    assert sorted(
        get_context_url_variables({"host": {"host": "heute"}, "service": {"service": "CPU"}})
    ) == [("host", "heute"), ("service", "CPU")]


def test_get_context_url_variables_of_an_empty_context() -> None:
    assert get_context_url_variables({}) == []


def test_get_context_url_variables_lets_later_filters_win() -> None:
    """The variables of all filters are merged into one flat namespace, so a filter
    repeating a variable name overwrites the earlier value."""
    assert get_context_url_variables({"a": {"host": "first"}, "b": {"host": "second"}}) == [
        ("host", "second")
    ]


def test_group_by_state_appends_to_the_matching_bucket() -> None:
    assert group_by_state({"up": [], "down": []}, ("heute", "down")) == {
        "up": [],
        "down": ["heute"],
    }


def test_group_by_state_requires_a_prepared_bucket() -> None:
    with pytest.raises(KeyError):
        group_by_state({"up": []}, ("heute", "down"))


def test_default_parameters_cover_hosts_services_and_events() -> None:
    parameters = TacticalOverviewSnapin.parameters()

    assert [row.query[0] for row in parameters.rows] == ["hosts", "services", "events"]
    assert parameters.show_stale is True
    assert parameters.show_failed_notifications is True
    assert parameters.show_sites_not_connected is True


@pytest.mark.parametrize(
    "what,expected_total_view,expected_stale",
    [
        pytest.param("hosts", "allhosts", "stale_hosts", id="hosts"),
        pytest.param("services", "allservices", "uncheckedsvc", id="services"),
        pytest.param("events", "ec_events", None, id="events_have_no_stale_view"),
    ],
)
def test_row_views_per_table(
    what: Literal["hosts", "services", "events"],
    expected_total_view: str,
    expected_stale: str | None,
) -> None:
    views = TacticalOverviewSnapin()._row_views(what)

    assert dict(views.total)["view_name"] == expected_total_view
    if expected_stale is None:
        assert views.stale is None
    else:
        assert views.stale is not None
        assert dict(views.stale)["view_name"] == expected_stale


@pytest.mark.parametrize(
    "what",
    [
        pytest.param("hosts", id="hosts"),
        pytest.param("services", id="services"),
        pytest.param("events", id="events"),
    ],
)
def test_row_views_unhandled_is_narrower_than_handled(
    what: Literal["hosts", "services", "events"],
) -> None:
    """ "Unhandled" must always add at least one filter on top of "Problems", otherwise the
    two columns of the overview would show the same number."""
    views = TacticalOverviewSnapin()._row_views(what)

    assert len(views.unhandled) > len(views.handled)


def test_row_views_rejects_an_unknown_table() -> None:
    with pytest.raises(NotImplementedError):
        TacticalOverviewSnapin()._row_views("junk")  # type: ignore[arg-type]


def test_host_stats_query_counts_four_columns() -> None:
    query = TacticalOverviewSnapin()._get_host_stats_query(1.5, "Filter: host_name = heute\n")

    assert query.startswith("GET hosts\n")
    assert "Stats: host_staleness >= 1.5\n" in query
    assert query.endswith("Filter: host_name = heute\n")
    assert query.count("Stats: ") == 8


def test_service_stats_query_counts_four_columns() -> None:
    query = TacticalOverviewSnapin()._get_service_stats_query(2.0, "")

    assert query.startswith("GET services\n")
    assert "Stats: service_staleness >= 2.0\n" in query


def test_event_stats_query_suppresses_a_missing_event_console() -> None:
    """A site without the Event Console must not be marked dead just because the overview
    asked for event statistics."""
    query = TacticalOverviewSnapin()._get_event_stats_query("")

    assert isinstance(query, livestatus.Query)
    assert livestatus.MKLivestatusTableNotFoundError in query.suppress_exceptions
    assert livestatus.MKLivestatusBadGatewayError in query.suppress_exceptions


def test_event_stats_query_without_the_permission_to_see_all_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: False)
        query = TacticalOverviewSnapin()._get_event_stats_query("")

    assert "Filter: event_contact_groups != \n" in str(query)


def test_event_stats_query_with_the_permission_to_see_all_events() -> None:
    query = TacticalOverviewSnapin()._get_event_stats_query("")

    assert "event_contact_groups" not in str(query)


def test_execute_stats_query_returns_the_summed_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    live = FakeLive([5, 2, 1, 0])
    monkeypatch.setattr(sites, "live", lambda: live)

    assert TacticalOverviewSnapin()._execute_stats_query("GET hosts\n") == [5, 2, 1, 0]
    assert live.auth_domains == ["read", "read"]


def test_execute_stats_query_restores_the_auth_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    """The event statistics need the ``ec`` auth domain, but the connection is shared - it
    has to be handed back in its default state."""
    live = FakeLive([1, 2, 3])
    monkeypatch.setattr(sites, "live", lambda: live)

    TacticalOverviewSnapin()._execute_stats_query("GET eventconsoleevents\n", auth_domain="ec")

    assert live.auth_domains == ["ec", "read"]
    assert live.only_sites == [None]


def test_execute_stats_query_limits_to_the_given_sites(monkeypatch: pytest.MonkeyPatch) -> None:
    live = FakeLive([1])
    monkeypatch.setattr(sites, "live", lambda: live)

    TacticalOverviewSnapin()._execute_stats_query("GET hosts\n", only_sites=[SiteId("heute")])

    assert live.only_sites == [[SiteId("heute")], None]


def test_execute_stats_query_falls_back_when_the_table_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = FakeLive(livestatus.MKLivestatusNotFoundError("no such table"))
    monkeypatch.setattr(sites, "live", lambda: live)

    assert TacticalOverviewSnapin()._execute_stats_query("GET x\n", deflt=[0, 0, 0]) == [0, 0, 0]


def test_execute_stats_query_without_a_fallback_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = FakeLive(livestatus.MKLivestatusNotFoundError("no such table"))
    monkeypatch.setattr(sites, "live", lambda: live)

    assert TacticalOverviewSnapin()._execute_stats_query("GET x\n") is None


def _show_rows(
    monkeypatch: pytest.MonkeyPatch,
    stats: dict[str, Sequence[int] | None],
    *,
    mkeventd_enabled: bool = True,
) -> str:
    with monkeypatch.context() as m:
        m.setattr(
            TacticalOverviewSnapin,
            "_get_stats",
            lambda self, what, context, threshold: stats[what],
        )
        with output_funnel.plugged():
            TacticalOverviewSnapin()._show_rows(1.5, mkeventd_enabled)
            return output_funnel.drain()


def test_show_rows_reports_when_a_site_answered_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A single row without stats means the query failed everywhere - showing a partial
    table would silently understate the number of problems."""
    rendered = _show_rows(
        monkeypatch, {"hosts": [1, 0, 0, 0], "services": None, "events": [0, 0, 0]}
    )

    assert "No data from any site" in rendered
    assert "tacticaloverview" not in rendered


def test_show_rows_renders_a_column_per_table(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_rows(
        monkeypatch,
        {"hosts": [10, 3, 2, 0], "services": [100, 5, 4, 0], "events": [7, 2, 1]},
    )

    assert 'class="tacticaloverview"' in rendered
    assert "Hosts" in rendered
    assert "Services" in rendered
    assert "Events" in rendered
    assert "monitor_all_hosts.py" in rendered
    assert "view.py?view_name=allhosts" not in rendered


def test_total_url_links_an_unfiltered_hosts_row_to_the_new_all_hosts_page() -> None:
    url = total_url("hosts", {}, [], [("view_name", "allhosts")])

    assert url == "monitor_all_hosts.py"


def test_total_url_keeps_the_classic_view_for_a_filtered_hosts_row() -> None:
    """A filtered "hosts" row (e.g. a custom sidebar element) must keep linking to the
    classic view, because the new All hosts page does not understand the filter context."""
    context = {"host": {"host": "heute"}}
    url = total_url(
        "hosts", context, get_context_url_variables(context), [("view_name", "allhosts")]
    )

    assert url == "view.py?host=heute&view_name=allhosts"


def test_total_url_treats_an_empty_filter_value_as_unfiltered() -> None:
    """A context that carries a filter variable with an empty value (e.g. a filter form
    left blank) does not actually restrict anything - it must be treated the same as no
    filter at all."""
    context = {"host": {"host": ""}}
    url = total_url(
        "hosts", context, get_context_url_variables(context), [("view_name", "allhosts")]
    )

    assert url == "monitor_all_hosts.py"


def test_total_url_keeps_the_classic_view_for_non_host_rows() -> None:
    url = total_url("services", {}, [], [("view_name", "allservices")])

    assert url == "view.py?view_name=allservices"


def test_show_rows_hides_events_when_none_exist_and_the_ec_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered = _show_rows(
        monkeypatch,
        {"hosts": [10, 0, 0, 0], "services": [100, 0, 0, 0], "events": [0, 0, 0]},
        mkeventd_enabled=False,
    )

    assert "Events" not in rendered


def test_show_rows_keeps_events_when_the_ec_is_off_but_events_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered = _show_rows(
        monkeypatch,
        {"hosts": [10, 0, 0, 0], "services": [100, 0, 0, 0], "events": [3, 1, 1]},
        mkeventd_enabled=False,
    )

    assert "Events" in rendered


def test_show_rows_shows_the_stale_column_only_when_something_is_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    without_stale = _show_rows(
        monkeypatch,
        {"hosts": [10, 0, 0, 0], "services": [100, 0, 0, 0], "events": [0, 0, 0]},
    )
    with_stale = _show_rows(
        monkeypatch,
        {"hosts": [10, 0, 0, 4], "services": [100, 0, 0, 0], "events": [0, 0, 0]},
    )

    assert "Stale" not in without_stale
    assert "Stale" in with_stale
    assert "view.py?view_name=stale_hosts" in with_stale


def test_show_rows_marks_non_zero_problem_cells(monkeypatch: pytest.MonkeyPatch) -> None:
    rendered = _show_rows(
        monkeypatch,
        {"hosts": [10, 3, 2, 0], "services": [100, 0, 0, 0], "events": [0, 0, 0]},
    )

    assert "states prob" in rendered


def test_show_rows_skips_events_without_the_permission(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "mkeventd.see_in_tactical_overview")
        rendered = _show_rows(
            monkeypatch,
            {"hosts": [10, 0, 0, 0], "services": [100, 0, 0, 0], "events": [9, 9, 9]},
        )

    assert "Events" not in rendered


def test_show_failed_notifications_is_silent_without_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(notifications, "acknowledged_time", lambda: 0)
        m.setattr(notifications, "number_of_failed_notifications", lambda **k: 0)
        with output_funnel.plugged():
            TacticalOverviewSnapin()._show_failed_notifications()
            assert output_funnel.drain() == ""


@pytest.mark.usefixtures("patch_theme")
def test_show_failed_notifications_links_to_the_view_and_the_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(notifications, "acknowledged_time", lambda: 0)
        m.setattr(notifications, "number_of_failed_notifications", lambda **k: 3)
        with output_funnel.plugged():
            TacticalOverviewSnapin()._show_failed_notifications()
            rendered = output_funnel.drain()

    assert "3 failed notifications" in rendered
    assert "clear_failed_notifications.py" in rendered
    assert "view.py?view_name=failed_notifications" in rendered
    assert 'class="tacticalalert"' in rendered


def _grouped_states(
    disabled: list[SiteId], error: list[SiteId]
) -> dict[str, sites.GroupedSiteState]:
    return {
        "disabled": sites.GroupedSiteState(readable="disabled", site_ids=list(disabled)),
        "error": sites.GroupedSiteState(readable="down", site_ids=list(error)),
    }


def test_show_site_status_is_silent_when_all_sites_are_up(monkeypatch: pytest.MonkeyPatch) -> None:
    with monkeypatch.context() as m:
        m.setattr(sites, "get_grouped_site_states", lambda: _grouped_states([], []))
        with output_funnel.plugged():
            TacticalOverviewSnapin()._show_site_status()
            assert output_funnel.drain() == ""


@pytest.mark.usefixtures("patch_theme")
def test_show_site_status_distinguishes_disabled_from_broken(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(
            sites,
            "get_grouped_site_states",
            lambda: _grouped_states([SiteId("beta")], [SiteId("heute"), SiteId("old")]),
        )
        with output_funnel.plugged():
            TacticalOverviewSnapin()._show_site_status()
            rendered = output_funnel.drain()

    assert "1 site is disabled." in rendered
    assert "2 sites are down." in rendered
    assert 'class="tacticalinfo"' in rendered
    assert 'class="tacticalalert"' in rendered


@pytest.mark.usefixtures("patch_theme")
def test_status_box_links_to_the_site_setup_for_administrators() -> None:
    with output_funnel.plugged():
        TacticalOverviewSnapin()._create_status_box([SiteId("heute")], "tacticalalert", "down")
        rendered = output_funnel.drain()

    assert "wato.py?mode=sites" in rendered


@pytest.mark.usefixtures("patch_theme")
def test_status_box_is_plain_text_without_the_setup_permission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as m:
        m.setattr(user, "may", lambda x: x != "wato.sites")
        with output_funnel.plugged():
            TacticalOverviewSnapin()._create_status_box([SiteId("heute")], "tacticalalert", "down")
            rendered = output_funnel.drain()

    assert "wato.py" not in rendered
    assert "1 site is down." in rendered

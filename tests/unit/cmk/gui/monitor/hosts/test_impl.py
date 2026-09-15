#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence
from typing import Literal

import pytest

from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.monitor.hosts._folder import MonitorFolders, SetupFolders
from cmk.gui.monitor.hosts._impl import (
    _build_primary_sort,
    _build_query_filter,
    _count_relations,
    _LIVESTATUS_SORT_COLUMNS,
    _OPTIONAL_COLUMNS,
    _SORT_COLUMN_FIELDS,
    LiveStatusHostRepository,
    unavailable_sites,
)
from cmk.gui.monitor.hosts._models import (
    Host,
    HostFilter,
    HostOptionalField,
    HostSort,
    HostSortColumn,
    HostSortDirection,
    MAX_RESOLVED_RELATIONS,
)
from cmk.gui.monitor.hosts._site import MonitorSite, MonitorSites
from cmk.gui.sites import SiteStates, SiteStatus
from cmk.livestatus_client.testing import expect_single_query, MockLiveStatusConnection
from tests.testlib.gui.web_test_app import SetConfig

SiteState = Literal["online", "disabled", "down", "unreach", "dead", "waiting"]


@pytest.mark.parametrize(
    "sorters, expected",
    [
        pytest.param(
            [],
            "OrderBy: name asc",
            id="default fallback",
        ),
        pytest.param(
            [HostSort(HostSortColumn.STATE, HostSortDirection.DESC)],
            "OrderBy: state desc",
            id="descending order",
        ),
        pytest.param(
            [HostSort(HostSortColumn.NAME, HostSortDirection.ASC)],
            "OrderBy: name asc natural",
            id="natural sort",
        ),
        pytest.param(
            [HostSort(HostSortColumn.FOLDER, HostSortDirection.ASC)],
            "OrderBy: filename asc natural",
            id="folder/filename handling",
        ),
        pytest.param(
            [HostSort(HostSortColumn.SITE_ID, HostSortDirection.ASC)],
            "OrderBy: name asc",
            id="site_id falls back to the default primary sort, site isn't a real Livestatus column",
        ),
        pytest.param(
            [
                HostSort(HostSortColumn.SITE_ID, HostSortDirection.ASC),
                HostSort(HostSortColumn.NAME, HostSortDirection.DESC),
            ],
            "OrderBy: name asc",
            id="site_id as the first sorter still falls back, even with a real sorter behind it",
        ),
        pytest.param(
            [HostSort(HostSortColumn.NUM_RELATIONS, HostSortDirection.DESC)],
            "OrderBy: name asc",
            id="num_relations falls back too, the count is built from a custom variable",
        ),
        pytest.param(
            [
                HostSort(HostSortColumn.STATE, HostSortDirection.DESC),
                HostSort(HostSortColumn.NAME, HostSortDirection.ASC),
                HostSort(HostSortColumn.FOLDER, HostSortDirection.ASC),
            ],
            "OrderBy: state desc",
            id="only first sorter used",
        ),
    ],
)
def test_build_primary_sort(sorters: Sequence[HostSort], expected: str) -> None:
    assert _build_primary_sort(sorters) == expected


def test_every_optional_field_names_the_columns_it_needs() -> None:
    """A new HostOptionalField must say which livestatus columns it reads, or it reads none."""
    assert set(_OPTIONAL_COLUMNS) == set(HostOptionalField)


def test_every_sort_column_says_which_field_it_needs_read() -> None:
    """Sorting happens in Python, so a sort column must name its field, or `None` for always-read."""
    assert set(_SORT_COLUMN_FIELDS) == set(HostSortColumn)


def test_every_sort_column_says_how_livestatus_orders_by_it() -> None:
    """A column with no entry would default to its own name and be rejected by every site."""
    assert set(_LIVESTATUS_SORT_COLUMNS) == set(HostSortColumn)


_TITLES = {"web_dmz": "Web DMZ", "network": "Netzwerk"}


def _folders() -> MonitorFolders:
    """A `MonitorFolders` titling two folders, the way Setup's functions are wired in."""
    folders = MonitorFolders()
    folders.use_setup_source(
        SetupFolders(title_of=_TITLES.get, all_titles=lambda: _TITLES),
    )
    return folders


def _sites() -> MonitorSites:
    return MonitorSites(
        [
            MonitorSite(id=SiteId("heute")),
            MonitorSite(id=SiteId("remote_muc"), customer="Bäckerei (Müller) GmbH"),
        ]
    )


def test_build_query_filter_without_a_query_matches_everything() -> None:
    assert (
        _build_query_filter("", frozenset(HostOptionalField), _folders(), _sites()).render() == []
    )


def test_build_query_filter_searches_the_name_of_a_table_without_optional_columns() -> None:
    assert _build_query_filter("web", frozenset(), _folders(), _sites()).render() == [
        ("Filter", "name ~~ web")
    ]


def test_build_query_filter_searches_every_shown_text_field() -> None:
    """The folder is searched by its title, so the query reaches it as that folder's file."""
    assert _build_query_filter(
        "web",
        frozenset(
            {
                HostOptionalField.ALIAS,
                HostOptionalField.ADDRESS,
                HostOptionalField.FOLDER,
                HostOptionalField.LAST_CHECK,
            }
        ),
        _folders(),
        _sites(),
    ).render() == [
        ("Filter", "name ~~ web"),
        ("Filter", "alias ~~ web"),
        ("Filter", "address ~~ web"),
        ("Filter", "filename = /wato/web_dmz/hosts.mk"),
        ("Or", "4"),
    ]


def test_build_query_filter_leaves_out_the_folder_no_title_carries() -> None:
    assert _build_query_filter(
        "no such folder", frozenset({HostOptionalField.FOLDER}), _folders(), _sites()
    ).render() == [("Filter", "name ~~ no such folder")]


@pytest.mark.parametrize(
    "field, expected",
    [
        pytest.param(
            HostOptionalField.LABELS,
            [
                ("Filter", "label_names ~~ web"),
                ("Filter", "label_values ~~ web"),
                ("Or", "2"),
            ],
            id="labels match by name or by value",
        ),
        pytest.param(
            HostOptionalField.TAGS,
            [
                ("Filter", "tag_names ~~ web"),
                ("Filter", "tag_values ~~ web"),
                ("Or", "2"),
            ],
            id="tags match by name or by value",
        ),
        pytest.param(
            HostOptionalField.CONTACTS,
            [("Filter", "contacts ~~ web")],
            id="contacts",
        ),
        pytest.param(
            HostOptionalField.CONTACT_GROUPS,
            [("Filter", "contact_groups ~~ web")],
            id="contact groups",
        ),
    ],
)
def test_build_query_filter_searches_a_shown_list_column(
    field: HostOptionalField, expected: list[tuple[str, str]]
) -> None:
    assert _build_query_filter("web", frozenset({field}), _folders(), _sites()).render() == [
        ("Filter", "name ~~ web"),
        *expected,
        ("Or", "2"),
    ]


def test_build_query_filter_searches_the_site_of_every_host_it_monitors() -> None:
    assert _build_query_filter("heute", frozenset(), _folders(), _sites()).render() == [
        ("Filter", "name ~~ heute"),
        ("Filter", "labels = cmk/site heute"),
        ("Or", "2"),
    ]


def test_build_query_filter_searches_the_site_of_a_table_not_showing_the_column() -> None:
    assert _build_query_filter(
        "heute", frozenset({HostOptionalField.ALIAS}), _folders(), _sites()
    ).render() == [
        ("Filter", "name ~~ heute"),
        ("Filter", "alias ~~ heute"),
        ("Filter", "labels = cmk/site heute"),
        ("Or", "3"),
    ]


def test_build_query_filter_searches_the_site_ignoring_case() -> None:
    assert _build_query_filter("REMOTE", frozenset(), _folders(), _sites()).render() == [
        ("Filter", "name ~~ REMOTE"),
        ("Filter", "labels = cmk/site remote_muc"),
        ("Or", "2"),
    ]


def test_build_query_filter_leaves_out_the_site_no_id_carries() -> None:
    assert _build_query_filter("no such site", frozenset(), _folders(), _sites()).render() == [
        ("Filter", "name ~~ no such site")
    ]


def test_build_query_filter_takes_a_regex_metacharacter_in_the_site_query_literally() -> None:
    assert _build_query_filter("heute[", frozenset(), _folders(), _sites()).render() == [
        ("Filter", "name ~~ heute[")
    ]


def test_build_query_filter_searches_the_customer_of_every_host_its_sites_monitor() -> None:
    assert _build_query_filter("Müller", frozenset(), _folders(), _sites()).render() == [
        ("Filter", "name ~~ Müller"),
        ("Filter", "labels = cmk/site remote_muc"),
        ("Or", "2"),
    ]


def test_build_query_filter_leaves_out_the_site_of_a_customer_nothing_names() -> None:
    assert _build_query_filter("Bäckerei Meier", frozenset(), _folders(), _sites()).render() == [
        ("Filter", "name ~~ Bäckerei Meier")
    ]


def test_build_query_filter_takes_a_regex_metacharacter_in_the_customer_literally() -> None:
    assert _build_query_filter(
        "Bäckerei (Müller) GmbH", frozenset(), _folders(), _sites()
    ).render() == [
        ("Filter", "name ~~ Bäckerei (Müller) GmbH"),
        ("Filter", "labels = cmk/site remote_muc"),
        ("Or", "2"),
    ]


def test_build_query_filter_leaves_out_a_hidden_field() -> None:
    assert _build_query_filter(
        "web", frozenset({HostOptionalField.ALIAS}), _folders(), _sites()
    ).render() == [
        ("Filter", "name ~~ web"),
        ("Filter", "alias ~~ web"),
        ("Or", "2"),
    ]


def test_count_matched_keeps_a_stray_carriage_return_on_one_line() -> None:
    # Regression test: a "\r" embedded in a filter value must not turn into a Livestatus line
    # break when the hand-assembled Stats query is joined with "\n" - only a real "\n" may do
    # that. Livestatus itself treats "\r" as ordinary data, and so must this query.
    filters = HostFilter("Filter: name ~~ evil\rmore")
    with expect_single_query(
        "GET hosts\nStats: state >= 0\nFilter: name ~~ evil\rmore",
        match_type="strict",
        tables={"hosts": []},
    ) as live:
        repo = LiveStatusHostRepository(connection=live)
        repo.count_matched(query="", filters=filters, fields=frozenset())


@pytest.mark.parametrize(
    "staleness, threshold, expected_stale",
    [
        pytest.param(5.0, 3.5, True, id="staleness at or above the threshold is stale"),
        pytest.param(2.0, 3.5, False, id="staleness below the threshold is not stale"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_fetch_derives_stale_from_the_staleness_threshold(
    staleness: float, threshold: float, expected_stale: bool, set_config: SetConfig
) -> None:
    row = _host_row(staleness=staleness)
    with expect_single_query("GET hosts", tables={"hosts": [row]}) as live:
        repo = LiveStatusHostRepository(connection=live)
        with set_config(staleness_threshold=threshold):
            hosts = repo.fetch(
                limit=None,
                query="",
                sorters=[],
                filters=HostFilter(""),
                fields=frozenset(),
                visible_relations=None,
            )

    assert [host.stale for host in hosts] == [expected_stale]


@pytest.mark.parametrize(
    "active_checks_enabled, modified_attributes_list, expected",
    [
        pytest.param(0, ["active_checks_enabled"], True, id="a user switched them off"),
        pytest.param(0, [], False, id="never on, so nobody switched them off"),
        pytest.param(1, ["active_checks_enabled"], False, id="a user switched them back on"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_fetch_counts_only_a_modified_setting_as_manually_disabled(
    active_checks_enabled: int, modified_attributes_list: list[str], expected: bool
) -> None:
    row = _host_row(
        modified_attributes_list=modified_attributes_list,
        active_checks_enabled=active_checks_enabled,
    )
    with expect_single_query("GET hosts", tables={"hosts": [row]}) as live:
        hosts = LiveStatusHostRepository(connection=live).fetch(
            limit=None,
            query="",
            sorters=[],
            filters=HostFilter(""),
            fields=frozenset(),
            visible_relations=None,
        )

    assert [host.active_checks_disabled for host in hosts] == [expected]


_TWO_RELATIONS = (
    '[{"kind": "management", "direction": "child", "host": "a", "site": "central"},'
    ' {"kind": "management", "direction": "parent", "host": "b", "site": "remote"}]'
)
_BOTH_COUNTERPARTS = frozenset({("central", "a"), ("remote", "b")})


@pytest.mark.parametrize(
    "raw, visible, unavailable, expected",
    [
        pytest.param(None, _BOTH_COUNTERPARTS, frozenset(), 0, id="host without the macro"),
        pytest.param(
            '[{"kind": "management", "direction": "child", "host": "a", "site": "central"}]',
            _BOTH_COUNTERPARTS,
            frozenset(),
            1,
            id="one relation",
        ),
        pytest.param(_TWO_RELATIONS, _BOTH_COUNTERPARTS, frozenset(), 2, id="both ends counted"),
        pytest.param(
            '[{"kind": "peering", "direction": "symmetric", "host": "a", "site": "central"}]',
            _BOTH_COUNTERPARTS,
            frozenset(),
            0,
            id="a relation of a later version is not counted - no card would be rendered for it",
        ),
        pytest.param(
            _TWO_RELATIONS,
            frozenset({("central", "a")}),
            frozenset(),
            1,
            id="a counterpart the reader may not see is left out",
        ),
        pytest.param(
            '[{"kind": "management", "direction": "child", "host": "a", "site": "remote"}]',
            frozenset(),
            frozenset({"remote"}),
            1,
            id="a counterpart on an unavailable site is kept, like its card in the details",
        ),
        pytest.param(
            '[{"kind": "management", "direction": "child", "host": "a", "site": "central"}]',
            frozenset({("remote", "a")}),
            frozenset(),
            0,
            id="the same name on another site is not the counterpart",
        ),
    ],
)
def test_count_relations(
    raw: str | None,
    visible: frozenset[tuple[str, str]],
    unavailable: frozenset[str],
    expected: int,
) -> None:
    """The malformed cases are covered where the value is parsed, in test_host_relations.py."""
    assert _count_relations(raw, visible, unavailable) == expected


def test_has_any_relations_asks_the_core_for_one_host_carrying_the_macro() -> None:
    """A list column compares by "contains", which is what ``>=`` means here."""
    with expect_single_query(
        "GET hosts\nColumns: name\nFilter: custom_variable_names >= RELATIONS\nLimit: 1",
        match_type="strict",
        tables={"hosts": [{"name": "some-host", "custom_variable_names": ["RELATIONS"]}]},
    ) as live:
        assert LiveStatusHostRepository(connection=live).has_any_relations() is True


def test_has_any_relations_false_when_no_host_carries_the_macro() -> None:
    with expect_single_query("GET hosts", tables={"hosts": []}) as live:
        assert LiveStatusHostRepository(connection=live).has_any_relations() is False


_VISIBLE_RELATION_HOSTS_QUERY = [
    "GET hosts",
    "Columns: name",
    "Filter: custom_variable_names >= RELATIONS",
]

_RELATION_LISTING_QUERY = [
    "GET hosts",
    (
        "Columns: name state has_been_checked acknowledged scheduled_downtime_depth "
        "notifications_enabled comments modified_attributes_list active_checks_enabled "
        "accept_passive_checks in_notification_period in_service_period in_check_period "
        "is_flapping staleness custom_variables"
    ),
]


def _host_row(name: str = "some-host", **overrides: object) -> dict[str, object]:
    """A row carrying every column ``fetch`` reads unconditionally."""
    return {
        "name": name,
        "state": 0,
        "has_been_checked": 1,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "notifications_enabled": 1,
        "comments": [],
        "modified_attributes_list": [],
        "active_checks_enabled": 1,
        "accept_passive_checks": 1,
        "in_notification_period": 1,
        "in_service_period": 1,
        "in_check_period": 1,
        "is_flapping": 0,
        "staleness": 0.0,
        "custom_variables": {},
        **overrides,
    }


def _related_host_row(name: str, related_to: str | None) -> dict[str, object]:
    relations = (
        []
        if related_to is None
        else [{"kind": "management", "direction": "parent", "host": related_to, "site": "NO_SITE"}]
    )
    return _host_row(
        name,
        custom_variables={"RELATIONS": json.dumps(relations)} if relations else {},
        custom_variable_names=["RELATIONS"] if relations else [],
    )


def _overview_row(name: str, relations: Sequence[Mapping[str, str]]) -> dict[str, object]:
    """A row shaped for the single-host query behind ``get_overview``."""
    return {
        "name": name,
        "alias": name,
        "address": "127.0.0.1",
        "state": 0,
        "has_been_checked": 1,
        "num_services": 0,
        "num_services_ok": 0,
        "num_services_warn": 0,
        "num_services_crit": 0,
        "num_services_unknown": 0,
        "num_services_pending": 0,
        "acknowledged": 0,
        "scheduled_downtime_depth": 0,
        "notifications_enabled": 1,
        "comments": [],
        "modified_attributes_list": [],
        "active_checks_enabled": 1,
        "accept_passive_checks": 1,
        "in_notification_period": 1,
        "in_service_period": 1,
        "in_check_period": 1,
        "is_flapping": 0,
        "staleness": 0.0,
        "last_check": 0,
        "last_state_change": 0,
        "contact_groups": [],
        "tags": {},
        "labels": {},
        "label_sources": {},
        "filename": "",
        "custom_variables": {"RELATIONS": json.dumps(relations)} if relations else {},
        "custom_variable_names": ["RELATIONS"] if relations else [],
    }


def _fetch_relation_counts() -> Sequence[int | None]:
    repo = LiveStatusHostRepository(connection=sites.live())
    fields = frozenset({HostOptionalField.NUM_RELATIONS})
    visible_relations = repo.visible_relation_hosts(fields=fields, sorters=[])
    return [
        host.num_relations
        for host in repo.fetch(
            limit=None,
            query="",
            sorters=[],
            filters=HostFilter(""),
            fields=fields,
            visible_relations=visible_relations,
        )
    ]


def _expect_overview_query(mock_livestatus: MockLiveStatusConnection) -> None:
    """The query reading the host itself, which every overview starts with."""
    mock_livestatus.expect_query(
        ["GET hosts", "Filter: name = board"], match_type="loose", sites=["NO_SITE"]
    )


def _get_overview(
    mock_livestatus: MockLiveStatusConnection, *, unavailable: frozenset[str] = frozenset()
) -> Host:
    with mock_livestatus(expect_status_query=True):
        return LiveStatusHostRepository(
            connection=sites.live(), read_unavailable_sites=lambda: unavailable
        ).get_overview(hostname="board", site_id="NO_SITE")


@pytest.mark.parametrize(
    "related_count, more_expected",
    [
        pytest.param(1, False, id="all of them shown"),
        pytest.param(MAX_RESOLVED_RELATIONS + 1, True, id="cut at the cap"),
    ],
)
def test_get_overview_stops_resolving_at_the_relation_cap(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
    related_count: int,
    more_expected: bool,
) -> None:
    """Cut before the counterparts are read, so the query naming them stays bounded too."""
    shown = min(related_count, MAX_RESOLVED_RELATIONS)
    relations = [
        {"kind": "management", "direction": "parent", "host": f"os-{index}", "site": "NO_SITE"}
        for index in range(related_count)
    ]
    back = [{"kind": "management", "direction": "child", "host": "board", "site": "NO_SITE"}]
    mock_livestatus.add_table(
        "hosts",
        [
            _overview_row("board", relations),
            *(_overview_row(f"os-{index}", back) for index in range(related_count)),
        ],
    )
    _expect_overview_query(mock_livestatus)
    mock_livestatus.expect_query(
        ["GET hosts", *(f"Filter: name = os-{index}" for index in range(shown))],
        match_type="loose",
        sites=["NO_SITE"],
    )

    host = _get_overview(mock_livestatus)

    assert len(host.relations) == shown
    assert host.more_relations is more_expected


def test_get_overview_keeps_a_counterpart_whose_site_did_not_answer(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """ "The site is unreachable" and "the host is gone" look the same to the query, so the site
    states decide."""
    relations = [
        {"kind": "management", "direction": "parent", "host": "os-here", "site": "NO_SITE"},
        {"kind": "management", "direction": "parent", "host": "os-away", "site": "remote"},
        {"kind": "management", "direction": "parent", "host": "os-gone", "site": "NO_SITE"},
    ]
    back = [{"kind": "management", "direction": "child", "host": "board", "site": "NO_SITE"}]
    mock_livestatus.add_table(
        "hosts", [_overview_row("board", relations), _overview_row("os-here", back)]
    )
    _expect_overview_query(mock_livestatus)
    mock_livestatus.expect_query(
        ["GET hosts", "Or: 3"], match_type="loose", sites=["NO_SITE", "remote"]
    )

    host = _get_overview(mock_livestatus, unavailable=frozenset({"remote"}))

    assert [(related.name, related.health is None) for related in host.relations] == [
        ("os-here", False),
        ("os-away", True),
    ]


def test_get_overview_leaves_out_a_counterpart_that_does_not_carry_the_macro(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """What a site that has not activated the relation yet looks like; the relation count asks the
    same of a counterpart."""
    relations = [{"kind": "management", "direction": "parent", "host": "os-1", "site": "NO_SITE"}]
    mock_livestatus.add_table(
        "hosts", [_overview_row("board", relations), _overview_row("os-1", [])]
    )
    _expect_overview_query(mock_livestatus)
    mock_livestatus.expect_query(
        ["GET hosts", "Filter: name = os-1"], match_type="loose", sites=["NO_SITE"]
    )

    host = _get_overview(mock_livestatus)

    assert host.relations == ()


def test_get_overview_leaves_out_a_relation_of_a_kind_this_version_does_not_know(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """The card could not be worded, and the count leaves it out for the same reason."""
    relations = [
        {"kind": "peering", "direction": "symmetric", "host": "peer", "site": "NO_SITE"},
        {"kind": "management", "direction": "parent", "host": "os-1", "site": "NO_SITE"},
    ]
    back = [{"kind": "management", "direction": "child", "host": "board", "site": "NO_SITE"}]
    mock_livestatus.add_table(
        "hosts",
        [
            _overview_row("board", relations),
            _overview_row("peer", back),
            _overview_row("os-1", back),
        ],
    )
    _expect_overview_query(mock_livestatus)
    mock_livestatus.expect_query(
        ["GET hosts", "Filter: name = os-1"], match_type="loose", sites=["NO_SITE"]
    )

    host = _get_overview(mock_livestatus)

    assert [related.name for related in host.relations] == ["os-1"]


@pytest.mark.parametrize(
    "state, expected_unavailable",
    [
        pytest.param("online", False, id="answered"),
        pytest.param("disabled", False, id="the reader switched this site off themselves"),
        pytest.param("dead", True, id="dead"),
        pytest.param("unreach", True, id="unreachable"),
        pytest.param("waiting", True, id="waiting for its status host"),
    ],
)
def test_unavailable_sites(state: SiteState, expected_unavailable: bool) -> None:
    """A site the reader deselected is not one that could not be reached: saying so would be
    untrue, and would show a host whose site was never asked - and so never filtered by
    ``AuthUser`` - to someone who may not be its contact."""
    site_states = SiteStates({SiteId("remote"): SiteStatus(state=state)})

    assert (SiteId("remote") in unavailable_sites(site_states)) is expected_unavailable


def test_visible_relation_hosts_asks_nothing_when_no_relation_count_is_shown(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """The mock fails the test on any query, which is what "nothing to read" has to look like."""
    with mock_livestatus(expect_status_query=True):
        repo = LiveStatusHostRepository(connection=sites.live())
        assert repo.visible_relation_hosts(fields=frozenset(), sorters=[]) is None


def test_fetching_the_relation_count_without_its_counterparts_is_refused(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """Silently answering "n/a" for a field the caller asked for would show as an empty column."""
    with mock_livestatus(expect_status_query=True):
        repo = LiveStatusHostRepository(connection=sites.live())
        with pytest.raises(ValueError, match="counterparts"):
            repo.fetch(
                limit=None,
                query="",
                sorters=[],
                filters=HostFilter(""),
                fields=frozenset({HostOptionalField.NUM_RELATIONS}),
                visible_relations=None,
            )


def test_visible_relation_hosts_reads_them_for_a_listing_that_only_sorts_by_the_count(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """Sorting happens in Python, so the count is read even when the response omits it."""
    mock_livestatus.add_table("hosts", [_related_host_row("heute", "mgmt-heute")])
    mock_livestatus.expect_query(_VISIBLE_RELATION_HOSTS_QUERY, match_type="loose")

    with mock_livestatus(expect_status_query=True):
        repo = LiveStatusHostRepository(connection=sites.live())
        assert repo.visible_relation_hosts(
            fields=frozenset(),
            sorters=[HostSort(HostSortColumn.NUM_RELATIONS, HostSortDirection.ASC)],
        ) == frozenset({("NO_SITE", "heute")})


def test_fetch_counts_a_relation_on_both_of_its_ends(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    mock_livestatus.add_table(
        "hosts",
        [_related_host_row("heute", "mgmt-heute"), _related_host_row("mgmt-heute", "heute")],
    )
    mock_livestatus.expect_query(_VISIBLE_RELATION_HOSTS_QUERY, match_type="loose")
    mock_livestatus.expect_query(_RELATION_LISTING_QUERY, match_type="loose")

    with mock_livestatus(expect_status_query=True):
        assert _fetch_relation_counts() == [1, 1]


def test_fetch_leaves_a_counterpart_the_core_does_not_answer_for_out_of_the_count(
    request_context: None,  # noqa: ARG001  # Unused fixtures are needed for setup side effects
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    """A counterpart the user may not see and one no site knows both go missing from the answer,
    and the host details leave out the card in both cases."""
    mock_livestatus.add_table("hosts", [_related_host_row("heute", "mgmt-heute")])
    mock_livestatus.expect_query(_VISIBLE_RELATION_HOSTS_QUERY, match_type="loose")
    mock_livestatus.expect_query(_RELATION_LISTING_QUERY, match_type="loose")

    with mock_livestatus(expect_status_query=True):
        assert _fetch_relation_counts() == [0]

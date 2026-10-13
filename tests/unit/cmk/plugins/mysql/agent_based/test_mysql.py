#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.mysql.agent_based.mysql import (
    check_mysql_connections,
    check_mysql_galeradonor,
    check_mysql_galerasize,
    check_mysql_galerastartup,
    check_mysql_galerastatus,
    check_mysql_galerasync,
    check_mysql_version,
    discover_mysql_galeradonor,
    discover_mysql_galerasize,
    discover_mysql_galerastartup,
    discover_mysql_galerastatus,
    discover_mysql_galerasync,
    parse_mysql,
    Section,
)

SECTION = parse_mysql(
    [
        ["[[galera]]"],
        ["version", "10.6.12-MariaDB"],
        ["wsrep_provider", "/usr/lib/galera/libgalera_smm.so"],
        ["wsrep_local_state_comment", "Synced"],
        ["wsrep_sst_donor", "node2"],
        ["wsrep_cluster_address", "gcomm://10.0.0.1,10.0.0.2"],
        ["wsrep_cluster_size", "3"],
        ["wsrep_cluster_status", "Primary"],
        ["[[standalone]]"],
        ["wsrep_provider", "none"],
        ["wsrep_local_state_comment", "Synced"],
        ["wsrep_sst_donor", "node2"],
        ["wsrep_cluster_address", "gcomm://"],
        ["wsrep_cluster_size", "1"],
        ["wsrep_cluster_status", "Primary"],
        ["Max_used_connections", "10"],
        ["incomplete"],
    ]
)


def test_lines_without_value_are_skipped_and_non_numbers_kept_as_strings() -> None:
    assert SECTION["standalone"] == {
        "wsrep_provider": "none",
        "wsrep_local_state_comment": "Synced",
        "wsrep_sst_donor": "node2",
        "wsrep_cluster_address": "gcomm://",
        "wsrep_cluster_size": 1,
        "wsrep_cluster_status": "Primary",
        "Max_used_connections": 10,
    }


def test_version_is_reported() -> None:
    assert list(check_mysql_version("galera", SECTION)) == [
        Result(state=State.OK, summary="Version: 10.6.12-MariaDB"),
    ]


def test_missing_version_yields_nothing() -> None:
    assert not list(check_mysql_version("standalone", SECTION))


def test_connections_without_usage_data_are_unknown() -> None:
    assert list(check_mysql_connections("galera", {}, SECTION)) == [
        Result(state=State.UNKNOWN, summary="Connection information is missing"),
    ]


def test_connection_usage_is_checked_against_levels() -> None:
    section = parse_mysql(
        [["Max_used_connections", "80"], ["Threads_connected", "10"], ["max_connections", "100"]]
    )

    assert list(check_mysql_connections("mysql", {"perc_used": (75.0, 90.0)}, section)) == [
        Result(
            state=State.WARN,
            summary="Max. parallel connections since server start: 80.00% (warn/crit at 75.00%/90.00%)",
        ),
        Metric("connections_perc_used", 80.0, levels=(75.0, 90.0)),
        Metric("connections_max_used", 80.0),
        Metric("connections_max", 100.0),
        Result(state=State.OK, summary="Currently open connections: 10.00%"),
        Metric("connections_perc_conn_threads", 10.0),
        Metric("connections_conn_threads", 10.0),
    ]


# Instances without a wsrep provider ("none") are no Galera cluster members.
@pytest.mark.parametrize(
    "discover, expected",
    [
        pytest.param(discover_mysql_galerasync, [Service(item="galera")], id="sync"),
        pytest.param(
            discover_mysql_galeradonor,
            [Service(item="galera", parameters={"wsrep_sst_donor": "node2"})],
            id="donor",
        ),
        pytest.param(discover_mysql_galerastartup, [Service(item="galera")], id="startup"),
        pytest.param(
            discover_mysql_galerasize,
            [Service(item="galera", parameters={"invsize": 3})],
            id="size",
        ),
        pytest.param(discover_mysql_galerastatus, [Service(item="galera")], id="status"),
    ],
)
def test_galera_services_are_only_discovered_with_wsrep_provider(
    discover: Callable[[Section], DiscoveryResult], expected: list[Service]
) -> None:
    assert list(discover(SECTION)) == expected


@pytest.mark.parametrize(
    "comment, expected_state",
    [
        pytest.param("Synced", State.OK, id="synced"),
        pytest.param("Donor/Desynced", State.CRIT, id="desynced"),
    ],
)
def test_galera_sync_is_ok_only_when_synced(comment: str, expected_state: State) -> None:
    section: Section = {"galera": {"wsrep_local_state_comment": comment}}

    assert list(check_mysql_galerasync("galera", section)) == [
        Result(state=expected_state, summary=f"WSREP local state comment: {comment}"),
    ]


def test_galera_donor_unchanged_since_discovery_is_ok() -> None:
    assert list(check_mysql_galeradonor("galera", {"wsrep_sst_donor": "node2"}, SECTION)) == [
        Result(state=State.OK, summary="WSREP SST donor: node2"),
    ]


def test_galera_donor_changed_since_discovery_is_warn() -> None:
    assert list(check_mysql_galeradonor("galera", {"wsrep_sst_donor": "node1"}, SECTION)) == [
        Result(state=State.WARN, summary="WSREP SST donor: node2 (at discovery: node1)"),
    ]


@pytest.mark.parametrize(
    "item, expected",
    [
        pytest.param(
            "galera",
            Result(state=State.OK, summary="WSREP cluster address: gcomm://10.0.0.1,10.0.0.2"),
            id="address set",
        ),
        pytest.param(
            "standalone",
            Result(state=State.CRIT, summary="WSREP cluster address is empty"),
            id="address empty",
        ),
    ],
)
def test_galera_startup_requires_cluster_address(item: str, expected: Result) -> None:
    assert list(check_mysql_galerastartup(item, SECTION)) == [expected]


def test_galera_cluster_size_unchanged_since_discovery_is_ok() -> None:
    assert list(check_mysql_galerasize("galera", {"invsize": 3}, SECTION)) == [
        Result(state=State.OK, summary="WSREP cluster size: 3"),
    ]


def test_galera_cluster_size_changed_since_discovery_is_crit() -> None:
    assert list(check_mysql_galerasize("galera", {"invsize": 5}, SECTION)) == [
        Result(state=State.CRIT, summary="WSREP cluster size: 3 (at discovery: 5)"),
    ]


@pytest.mark.parametrize(
    "status, expected_state",
    [
        pytest.param("Primary", State.OK, id="primary"),
        pytest.param("non-Primary", State.CRIT, id="non primary"),
    ],
)
def test_galera_status_is_ok_only_when_primary(status: str, expected_state: State) -> None:
    section: Section = {"galera": {"wsrep_cluster_status": status}}

    assert list(check_mysql_galerastatus("galera", section)) == [
        Result(state=expected_state, summary=f"WSREP cluster status: {status}"),
    ]


@pytest.mark.parametrize(
    "check",
    [
        pytest.param(check_mysql_galerasync, id="sync"),
        pytest.param(check_mysql_galerastartup, id="startup"),
        pytest.param(check_mysql_galerastatus, id="status"),
    ],
)
def test_galera_checks_without_data_yield_nothing(
    check: Callable[[str, Section], CheckResult],
) -> None:
    assert not list(check("galera", {"galera": {"version": "10.6"}}))

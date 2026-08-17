#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Graph discovery / data via the REST API.

Discovery matches a service's metrics against the graph plugins the site ships, so only a
site can say what a real service resolves to - the engine's own unit tests match against
synthetic plugins instead.

The missing-RRD case lives here too: it needs the same site, and its subject is a service
this module's fixture already monitors.
"""

import time
from collections.abc import Iterator

import pytest

from cmk.graphing_engine import (
    AutoPrecision,
    Curve,
    CurveAttributes,
    DecimalNotation,
    Graph,
    HostName,
    MetricName,
    RRDMetric,
    ServiceName,
    Stack,
    Unit,
)
from cmk.gui.graphing._engine_codec import community_graph_codec
from tests.testlib.graphing import discovered_graphs
from tests.testlib.site import Site

pytestmark = pytest.mark.skip_if_edition("cloud")

_PING_HOST = "graph-discovery-ping"
_CUSTOM_CHECKS_HOST = "graph-discovery-custom"

_PING_SERVICE = "PING"
_NO_METRICS_SERVICE = "Discovery without metrics"
_UNCLAIMED_METRICS_SERVICE = "Discovery with unclaimed metrics"
_UNCLAIMED_METRICS = ("unclaimed_one", "unclaimed_two")
# Asked of the service that reports no perf data, so nothing ever wrote an RRD for it.
_NEVER_RECORDED_METRIC = "never_recorded"

_HOST_ATTRIBUTES = {
    "tag_address_family": "ip-v4-only",
    "ipaddress": "127.0.0.1",
    "tag_agent": "no-agent",
}


@pytest.fixture(name="discovery_hosts", scope="module")
def fixture_discovery_hosts(site: Site) -> Iterator[None]:
    rule_ids = []
    perf_data = " ".join(f"{metric_name}=5" for metric_name in _UNCLAIMED_METRICS)
    try:
        for host_name in (_PING_HOST, _CUSTOM_CHECKS_HOST):
            site.openapi.hosts.create(hostname=host_name, attributes=_HOST_ATTRIBUTES)
        for service_description, output in (
            (_NO_METRICS_SERVICE, "OK - no metrics"),
            (_UNCLAIMED_METRICS_SERVICE, f"OK - unclaimed metrics|{perf_data}"),
        ):
            rule_ids.append(
                site.openapi.rules.create(
                    ruleset_name="custom_checks",
                    value={
                        "service_description": service_description,
                        "command_line": f'echo "{output}"',
                    },
                    conditions={
                        "host_name": {"match_on": [_CUSTOM_CHECKS_HOST], "operator": "one_of"}
                    },
                )
            )
        site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)
        site.wait_until_service_has_been_checked(_PING_HOST, _PING_SERVICE)
        for service_description in (_NO_METRICS_SERVICE, _UNCLAIMED_METRICS_SERVICE):
            site.wait_until_service_has_been_checked(_CUSTOM_CHECKS_HOST, service_description)
        yield
    finally:
        for rule_id in rule_ids:
            site.openapi.rules.delete(rule_id)
        site.openapi.hosts.bulk_delete([_PING_HOST, _CUSTOM_CHECKS_HOST])
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


@pytest.mark.usefixtures("discovery_hosts")
def test_discovery_of_ping_claims_every_metric(site: Site) -> None:
    discovered = site.openapi.graph.discover_template_graphs(_PING_HOST, _PING_SERVICE)

    assert {graph.name for graph in discovered_graphs(discovered)} == {
        "round_trip_average",
        "packet_loss",
    }
    assert discovered["no_data_message"] is None


@pytest.mark.usefixtures("discovery_hosts")
def test_discovery_of_a_service_without_perfdata_returns_no_graphs(site: Site) -> None:
    discovered = site.openapi.graph.discover_template_graphs(
        _CUSTOM_CHECKS_HOST, _NO_METRICS_SERVICE
    )

    assert discovered["graphs"] == []
    assert discovered["no_data_message"]


@pytest.mark.usefixtures("discovery_hosts")
def test_discovery_of_an_unknown_graph_id_returns_no_graphs(site: Site) -> None:
    discovered = site.openapi.graph.discover_template_graphs(
        _PING_HOST, _PING_SERVICE, graph_id="no_such_graph"
    )

    assert discovered["graphs"] == []
    assert discovered["no_data_message"]


@pytest.mark.usefixtures("discovery_hosts")
def test_discovery_falls_back_to_one_graph_per_unclaimed_metric(site: Site) -> None:
    discovered = site.openapi.graph.discover_template_graphs(
        _CUSTOM_CHECKS_HOST, _UNCLAIMED_METRICS_SERVICE
    )

    assert {graph.name for graph in discovered_graphs(discovered)} == set(_UNCLAIMED_METRICS)


@pytest.mark.usefixtures("discovery_hosts")
def test_graph_data_for_missing_rrd_returns_empty_not_error(site: Site) -> None:
    """Graph data for a service with no RRD is empty, not a 500.

    The service is monitored and checked, so it is in livestatus, but it reports no perf data
    and the core therefore never created an RRD for it. That is the state a freshly discovered
    service is in, without the race of catching one before its first check.

    The graph is built here rather than discovered: discovery matches against the perf data
    this service does not have, so it is the one definition no discovery can hand out. It goes
    over the wire through the codec, not `_engine_dispatch.serialize_graphs`, whose per-kind
    registry is filled by the GUI at startup and so is empty in this process.
    """
    graph = Graph(
        name="missing_rrd",
        title="Missing RRD",
        kind="template",
        stacks=[
            Stack(
                members=[
                    Curve(
                        quantity=RRDMetric(
                            host_name=HostName(_CUSTOM_CHECKS_HOST),
                            service_name=ServiceName(_NO_METRICS_SERVICE),
                            metric_name=MetricName(_NEVER_RECORDED_METRIC),
                        ),
                        attributes=CurveAttributes(
                            title=_NEVER_RECORDED_METRIC,
                            unit=Unit(notation=DecimalNotation(""), precision=AutoPrecision(2)),
                            color="#ff0000",
                        ),
                    )
                ],
                inverse=False,
            )
        ],
    )
    end = int(time.time())

    # The client raises on any non-2xx, so reaching the assertions at all is the "not a 500" half.
    response = site.openapi.graph.fetch_data(
        internal=community_graph_codec().serialize_graphs([graph]),
        requested_time_range={"start": end - 3600, "end": end, "step": 60},
        consolidation_function="avg",
    )

    assert all(
        point is None for metric in response["metrics"] for point in metric["data_points"]
    ), f"A service with no RRD resolved to actual data: {response['metrics']}"

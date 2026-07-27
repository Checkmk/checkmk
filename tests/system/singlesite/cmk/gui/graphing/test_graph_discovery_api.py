#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Graph discovery / data via the REST API (R1.1 Area 1).

D-01 and D-02, plus the graph set a real service resolves to. Discovery matches a service's
metrics against the graph plugins the site ships, so only a site can say what a real service
resolves to - the engine's own unit tests match against synthetic plugins instead.

E-05 (R1.4 Area 3, folded from the struck R1.1 E-01) is still a skipped skeleton.
"""

from collections.abc import Iterator

import pytest

from tests.testlib.graphing import discovered_graphs, SKIP_PENDING_GRAPH_BACKEND
from tests.testlib.site import Site

pytestmark = pytest.mark.skip_if_edition("cloud")

_PING_HOST = "graph-discovery-ping"
_CUSTOM_CHECKS_HOST = "graph-discovery-custom"

_PING_SERVICE = "PING"
_NO_METRICS_SERVICE = "Discovery without metrics"
_UNCLAIMED_METRICS_SERVICE = "Discovery with unclaimed metrics"
_UNCLAIMED_METRICS = ("unclaimed_one", "unclaimed_two")

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


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_BACKEND)
def test_graph_data_for_missing_rrd_returns_empty_not_error(site: Site) -> None:
    """E-05 (R1.4 Area 3): graph data for a never-checked service is empty, not a 500.

    Do: create and discover a host but let no check run (no RRD yet); call graph-data.
    Assert: HTTP 200 with an empty/all-null series; no traceback.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")

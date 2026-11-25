#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The metrics the dashboard widget wizard offers, via the 'monitored_metrics' autocompleter.

The wizard scopes the metric dropdown by the hosts and services it selects, and the scoping is
done by Livestatus over what the services actually report, so only a site can say which
metrics a selection resolves to.
"""

from collections.abc import Iterator

import pytest

from tests.testlib.system.site import Site

pytestmark = pytest.mark.skip_if_edition("cloud")

_HOST_A = "monitored-metrics-a"
_HOST_B = "monitored-metrics-b"

# Host A runs two services, so a host-only scope differs from a host-and-service one.
_SERVICE_A = "Metrics A"
_SERVICE_A_OTHER = "Metrics A other"
_SERVICE_B = "Metrics B"

# Registered metrics, so they are offered by their ID independently of any context, too.
_METRICS_BY_HOST_AND_SERVICE = {
    (_HOST_A, _SERVICE_A): ("load1", "load5"),
    (_HOST_A, _SERVICE_A_OTHER): ("load15",),
    (_HOST_B, _SERVICE_B): ("execution_time", "user_time"),
}

# Without an address the hosts get neither a PING service nor a host check reporting metrics,
# so the services above are the only source of metrics.
_HOST_ATTRIBUTES = {"tag_address_family": "no-ip", "tag_agent": "no-agent"}


@pytest.fixture(name="metric_hosts", scope="module")
def fixture_metric_hosts(site: Site) -> Iterator[None]:
    rule_ids = []
    try:
        for host_name in (_HOST_A, _HOST_B):
            site.openapi.hosts.create(hostname=host_name, attributes=_HOST_ATTRIBUTES)
        for (host_name, service_name), metric_names in _METRICS_BY_HOST_AND_SERVICE.items():
            perf_data = " ".join(f"{metric_name}=1" for metric_name in metric_names)
            rule_ids.append(
                site.openapi.rules.create(
                    ruleset_name="custom_checks",
                    value={
                        "service_description": service_name,
                        "command_line": f'echo "OK - metrics|{perf_data}"',
                    },
                    conditions={"host_name": {"match_on": [host_name], "operator": "one_of"}},
                )
            )
        site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)
        for host_name, service_name in _METRICS_BY_HOST_AND_SERVICE:
            site.schedule_check(host_name, service_name, 0)
        yield
    finally:
        for rule_id in rule_ids:
            site.openapi.rules.delete(rule_id)
        site.openapi.hosts.bulk_delete([_HOST_A, _HOST_B], ignore_missing=True)
        site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)


@pytest.mark.usefixtures("metric_hosts")
def test_one_host_and_service_offers_the_metrics_of_that_service(site: Site) -> None:
    metrics = site.openapi.autocomplete.monitored_metrics(
        {"host": {"host": _HOST_A}, "service": {"service": _SERVICE_A}}
    )

    assert set(metrics) == {"load1", "load5"}


@pytest.mark.usefixtures("metric_hosts")
def test_one_host_offers_the_metrics_of_all_its_services(site: Site) -> None:
    metrics = site.openapi.autocomplete.monitored_metrics({"host": {"host": _HOST_A}})

    assert set(metrics) == {"load1", "load5", "load15"}


@pytest.mark.usefixtures("metric_hosts")
def test_multiple_hosts_and_services_offer_the_union_of_their_metrics(site: Site) -> None:
    metrics = site.openapi.autocomplete.monitored_metrics(
        {
            "hostregex": {"host_regex": f"^({_HOST_A}|{_HOST_B})$"},
            "serviceregex": {"service_regex": f"^({_SERVICE_A}|{_SERVICE_B})$"},
        }
    )

    assert set(metrics) == {"load1", "load5", "execution_time", "user_time"}


def test_no_context_offers_every_registered_metric(site: Site) -> None:
    metrics = site.openapi.autocomplete.monitored_metrics({})

    assert {"load1", "execution_time"} <= set(metrics)

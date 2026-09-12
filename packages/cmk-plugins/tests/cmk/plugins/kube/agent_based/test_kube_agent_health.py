#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest
from pydantic import ValidationError

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State
from cmk.plugins.kube.agent_based.kube_agent_health import (
    AgentHealth,
    check_kube_agent_health,
    check_kube_agent_health_node,
    check_kube_agent_health_reflector,
    DEFAULT_DISCOVERY_PARAMS,
    DEFAULT_PARAMS,
    DEFAULT_REFLECTOR_PARAMS,
    DEFAULT_SCRAPER_PARAMS,
    discover_kube_agent_health,
    discover_kube_agent_health_node,
    discover_kube_agent_health_reflector,
    parse_kube_agent_health,
    ScraperParams,
)


@pytest.fixture
def section() -> AgentHealth:
    payload = {
        "last_heard_age_secs": 26.5,
        "scrape_time_secs": 0.15,
        "version": "1.0.0",
        "git_sha": "abc123",
    }
    parsed = parse_kube_agent_health(
        [
            [
                json.dumps(
                    {
                        "cluster_aggregator": {"version": "1.0.0", "git_sha": "abc123"},
                        "node_scrapers": {
                            "node01": {
                                "kubelet_stats": payload,
                                "kubelet_health": payload,
                                "system_agent": payload,
                            }
                        },
                        "reflector_healths": {
                            "Pod": {
                                "has_been_initialized": True,
                                "relist_started_age_secs": None,
                                "relist_completed_age_secs": 86400.0,
                                "relist_duration_secs": 0.5,
                                "last_error_age_secs": None,
                                "errors_total": 0,
                                "last_event_age_secs": 42.0,
                            }
                        },
                        "future_field": "ignored",
                    }
                )
            ]
        ]
    )
    assert parsed is not None
    return parsed


def worst_state(results: CheckResult) -> State:
    return State.worst(*(result.state for result in results if isinstance(result, Result)))


def test_empty_section_is_not_discovered() -> None:
    assert parse_kube_agent_health([]) is None


def test_malformed_section_does_not_become_healthy_empty_data() -> None:
    with pytest.raises(ValidationError):
        parse_kube_agent_health([['{"node_scrapers": {}}']])


def test_only_overview_and_reflectors_are_discovered_by_default(section: AgentHealth) -> None:
    discovered = [
        *discover_kube_agent_health(section),
        *discover_kube_agent_health_node(DEFAULT_DISCOVERY_PARAMS, section),
        *discover_kube_agent_health_reflector(DEFAULT_DISCOVERY_PARAMS, section),
    ]

    assert discovered == [Service(), Service(item="Pod")]


def test_healthy_overview_details_stay_compact(section: AgentHealth) -> None:
    results = list(check_kube_agent_health(DEFAULT_PARAMS, section))

    assert worst_state(results) == State.OK
    summaries = [result.summary for result in results if isinstance(result, Result)]
    assert summaries == [
        "Cluster aggregator version: 1.0.0",
        "Node scrapers: 1/1 healthy",
        "Reflectors: 1/1 healthy",
    ]
    node_result = next(
        result
        for result in results
        if isinstance(result, Result) and result.summary.startswith("Node scrapers:")
    )
    assert node_result.details == "Node scrapers: 1/1 healthy"
    assert Metric("kube_agent_scrapers", 1) in results
    assert Metric("kube_agent_scrapers_affected", 0) in results


@pytest.mark.parametrize(
    "age, state",
    [
        pytest.param(89.9, State.OK, id="below-warning"),
        pytest.param(90.0, State.WARN, id="at-warning"),
        pytest.param(120.0, State.CRIT, id="at-critical"),
        pytest.param(None, State.CRIT, id="no-cached-payload"),
    ],
)
def test_stale_statistics_are_not_hidden_by_other_fresh_payloads(
    section: AgentHealth, age: float | None, state: State
) -> None:
    section.node_scrapers["node01"].kubelet_stats.last_heard_age_secs = age

    results = list(check_kube_agent_health_node("node01", DEFAULT_SCRAPER_PARAMS, section))

    assert worst_state(results) == state


def test_node_metrics_keep_payload_streams_separate(section: AgentHealth) -> None:
    results = list(check_kube_agent_health_node("node01", DEFAULT_SCRAPER_PARAMS, section))

    assert [result.name for result in results if isinstance(result, Metric)] == [
        "kube_agent_kubelet_stats_age",
        "kube_agent_kubelet_stats_scrape_time",
        "kube_agent_kubelet_health_age",
        "kube_agent_kubelet_health_scrape_time",
        "kube_agent_system_agent_age",
        "kube_agent_system_agent_scrape_time",
    ]


def test_disabling_age_levels_keeps_missing_payload_detection(section: AgentHealth) -> None:
    section.node_scrapers["node01"].system_agent.last_heard_age_secs = None
    params: ScraperParams = {**DEFAULT_SCRAPER_PARAMS, "age": ("no_levels", None)}

    results = list(check_kube_agent_health_node("node01", params, section))

    assert (
        Result(
            state=State.CRIT,
            summary="System agent: No cached data",
            details="System agent: No cached data (never received or expired)",
        )
        in results
    )


def test_absent_optional_metadata_is_informational(section: AgentHealth) -> None:
    health = section.node_scrapers["node01"].system_agent
    health.version = health.git_sha = health.scrape_time_secs = None

    results = list(check_kube_agent_health_node("node01", DEFAULT_SCRAPER_PARAMS, section))

    assert worst_state(results) == State.OK
    assert any(
        isinstance(result, Result) and "System agent version: Not reported" in result.details
        for result in results
    )


@pytest.mark.parametrize(
    "version_state, expected",
    [
        pytest.param(0, State.OK, id="rolling-upgrade-default"),
        pytest.param(1, State.WARN, id="version-policy-enabled"),
    ],
)
def test_version_mismatch_obeys_configured_state(
    section: AgentHealth, version_state: int, expected: State
) -> None:
    section.node_scrapers["node01"].kubelet_health.version = "2.0.0"

    results = list(
        check_kube_agent_health_node(
            "node01", {**DEFAULT_SCRAPER_PARAMS, "version_state": version_state}, section
        )
    )

    assert worst_state(results) == expected


def test_healthy_reflector_reports_last_list_duration_and_age(section: AgentHealth) -> None:
    results = list(check_kube_agent_health_reflector("Pod", DEFAULT_REFLECTOR_PARAMS, section))

    assert Result(state=State.OK, summary="Initial resource list loaded") in results
    assert (
        Result(
            state=State.OK,
            notice="Last full list completed 1 day 0 hours ago and took 500 milliseconds",
        )
        in results
    )
    assert Metric("kube_agent_relist_duration", 0.5) in results
    assert (
        Result(
            state=State.OK,
            summary="Last resource event received: 42 seconds ago",
        )
        in results
    )
    assert Metric("kube_agent_last_event_age", 42.0) in results


def test_reflector_details_omit_unreported_list_duration(section: AgentHealth) -> None:
    section.reflector_healths["Pod"].relist_duration_secs = None

    results = list(check_kube_agent_health_reflector("Pod", DEFAULT_REFLECTOR_PARAMS, section))

    assert (
        Result(
            state=State.OK,
            notice="Last full list completed 1 day 0 hours ago",
        )
        in results
    )
    assert not any(
        isinstance(result, Metric) and result.name == "kube_agent_relist_duration"
        for result in results
    )


def test_reflector_summary_shows_first_list_progress_before_warning_threshold(
    section: AgentHealth,
) -> None:
    health = section.reflector_healths["Pod"]
    health.has_been_initialized = False
    health.relist_started_age_secs = 10.0
    health.relist_duration_secs = health.relist_completed_age_secs = None

    results = list(check_kube_agent_health_reflector("Pod", DEFAULT_REFLECTOR_PARAMS, section))

    assert Result(state=State.WARN, summary="Loading initial resource list") in results
    assert Result(state=State.OK, summary="Listing in progress for: 10 seconds") in results


@pytest.mark.parametrize(
    "age, expected",
    [
        pytest.param(119.9, State.OK, id="normal-list"),
        pytest.param(120.0, State.WARN, id="slow-list"),
        pytest.param(300.0, State.CRIT, id="stuck-list"),
    ],
)
def test_ongoing_relist_alerts_even_after_successful_initialization(
    section: AgentHealth, age: float, expected: State
) -> None:
    section.reflector_healths["Pod"].relist_started_age_secs = age

    results = list(check_kube_agent_health_reflector("Pod", DEFAULT_REFLECTOR_PARAMS, section))

    assert worst_state(results) == expected


def test_old_completed_list_and_historical_errors_are_not_failures(section: AgentHealth) -> None:
    health = section.reflector_healths["Pod"]
    health.errors_total = 9000
    health.last_error_age_secs = 86400.0
    health.relist_duration_secs = 600.0

    results = list(check_kube_agent_health_reflector("Pod", DEFAULT_REFLECTOR_PARAMS, section))

    assert worst_state(results) == State.OK
    assert Metric("kube_agent_watch_errors", 9000) in results


@pytest.mark.parametrize(
    "age, expected",
    [
        pytest.param(0.0, State.WARN, id="just-failed"),
        pytest.param(299.9, State.WARN, id="inside-window"),
        pytest.param(300.0, State.OK, id="window-expired"),
    ],
)
def test_recent_watch_error_warning_expires(
    section: AgentHealth, age: float, expected: State
) -> None:
    section.reflector_healths["Pod"].last_error_age_secs = age
    section.reflector_healths["Pod"].errors_total = 1

    results = list(
        check_kube_agent_health_reflector(
            "Pod", {**DEFAULT_REFLECTOR_PARAMS, "recent_error_window": ("enabled", 300.0)}, section
        )
    )

    assert worst_state(results) == expected


def test_recent_error_alerts_are_disabled_by_default_but_keep_details(
    section: AgentHealth,
) -> None:
    section.reflector_healths["Pod"].last_error_age_secs = 0.0

    results = list(check_kube_agent_health_reflector("Pod", DEFAULT_REFLECTOR_PARAMS, section))

    assert worst_state(results) == State.OK
    assert any(
        isinstance(result, Result) and "Last watch error:" in result.details for result in results
    )


def test_last_resource_event_age_uses_optional_thresholds(section: AgentHealth) -> None:
    section.reflector_healths["Pod"].last_event_age_secs = 120.0

    results = list(
        check_kube_agent_health_reflector(
            "Pod",
            {**DEFAULT_REFLECTOR_PARAMS, "last_event_age": ("fixed", (60.0, 120.0))},
            section,
        )
    )

    assert (
        Result(
            state=State.CRIT,
            summary=(
                "Last resource event received: 2 minutes 0 seconds ago "
                "(warn/crit at 1 minute 0 seconds ago/2 minutes 0 seconds ago)"
            ),
        )
        in results
    )


def test_reflector_without_resource_events_is_informational(section: AgentHealth) -> None:
    section.reflector_healths["Pod"].last_event_age_secs = None

    results = list(check_kube_agent_health_reflector("Pod", DEFAULT_REFLECTOR_PARAMS, section))

    assert Result(state=State.OK, summary="No resource events received") in results


def test_empty_expected_node_set_warns_instead_of_claiming_full_coverage(
    section: AgentHealth,
) -> None:
    section.node_scrapers.clear()

    results = list(check_kube_agent_health(DEFAULT_PARAMS, section))

    assert Result(state=State.WARN, summary="Node scrapers: None reported") in results


def test_empty_reflector_set_is_critical(section: AgentHealth) -> None:
    section.reflector_healths.clear()

    results = list(check_kube_agent_health(DEFAULT_PARAMS, section))

    assert Result(state=State.CRIT, summary="Reflectors: None reported") in results


def test_overview_shows_all_problems_when_below_details_limit(section: AgentHealth) -> None:
    node = section.node_scrapers.pop("node01")
    node.system_agent.last_heard_age_secs = None
    section.node_scrapers = {f"node{i}": node.model_copy(deep=True) for i in range(5)}

    results = list(check_kube_agent_health(DEFAULT_PARAMS, section))

    overview = next(
        result
        for result in results
        if isinstance(result, Result) and result.summary.startswith("Node scrapers:")
    )
    assert overview.state == State.CRIT
    assert "2 more problems (see details)" in overview.summary
    assert "node4" not in overview.summary
    assert "node4 [CRIT]: System agent: No cached data" in overview.details
    assert "[OK]" not in overview.details
    assert Metric("kube_agent_scrapers_affected", 5) in results


def test_overview_bounds_details_during_a_cluster_wide_scraper_outage(
    section: AgentHealth,
) -> None:
    node = section.node_scrapers.pop("node01")
    for payload in (node.kubelet_stats, node.kubelet_health, node.system_agent):
        payload.last_heard_age_secs = None
    section.node_scrapers = {f"node{i:02}": node for i in range(25)}

    results = list(check_kube_agent_health(DEFAULT_PARAMS, section))

    overview = next(
        result
        for result in results
        if isinstance(result, Result) and result.summary.startswith("Node scrapers:")
    )
    assert overview.state == State.CRIT
    assert overview.details.splitlines()[0] == "Node scrapers: 0/25 healthy, 75 problems"
    assert overview.details.count("[CRIT]") == 20
    assert "55 additional problems not shown." in overview.details
    assert "Kubernetes agent health service discovery" in overview.details
    assert len(overview.details.splitlines()) == 23
    assert Metric("kube_agent_scrapers_affected", 25) in results


def test_overview_prioritizes_critical_problems_beyond_the_alphabetical_cutoff(
    section: AgentHealth,
) -> None:
    node = section.node_scrapers.pop("node01")
    node.kubelet_stats.last_heard_age_secs = 100.0
    section.node_scrapers = {f"node{i:02}": node for i in range(25)}
    critical_node = node.model_copy(deep=True)
    critical_node.kubelet_stats.last_heard_age_secs = None
    section.node_scrapers["z-critical"] = critical_node
    unknown_node = node.model_copy(deep=True)
    unknown_node.kubelet_stats.version = "different"
    section.node_scrapers["z-unknown"] = unknown_node

    results = list(
        check_kube_agent_health(
            {
                **DEFAULT_PARAMS,
                "scrapers": {**DEFAULT_SCRAPER_PARAMS, "version_state": 3},
            },
            section,
        )
    )

    overview = next(
        result
        for result in results
        if isinstance(result, Result) and result.summary.startswith("Node scrapers:")
    )
    assert overview.state == State.CRIT
    assert "z-critical" in overview.summary
    assert "z-unknown" in overview.summary
    assert overview.details.splitlines()[1].startswith("z-critical [CRIT]:")
    assert overview.details.splitlines()[2].startswith("z-unknown [UNKNOWN]:")
    assert overview.details.splitlines()[3].startswith("node00 [WARN]:")
    assert "8 additional problems not shown." in overview.details


def test_disappeared_node_has_no_fabricated_result(section: AgentHealth) -> None:
    assert list(check_kube_agent_health_node("removed", DEFAULT_SCRAPER_PARAMS, section)) == []


def test_disappeared_reflector_has_no_fabricated_result(section: AgentHealth) -> None:
    assert (
        list(check_kube_agent_health_reflector("Removed", DEFAULT_REFLECTOR_PARAMS, section)) == []
    )

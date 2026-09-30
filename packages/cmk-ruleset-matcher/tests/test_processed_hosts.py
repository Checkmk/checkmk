#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.labels import Labels
from cmk.ruleset_matcher.matcher import RulesetMatcher, RuleSpec

HOST1, HOST2, HOST3 = HostName("host1"), HostName("host2"), HostName("host3")

# One ruleset object for all queries: the ruleset caches are keyed by its id.
HOST_NAME_RULES: Sequence[RuleSpec[str]] = [
    {
        "id": "host_names",
        "value": "matched",
        "condition": {"host_name": ["host1", "host2", "host3"]},
    },
]

# Label conditions are evaluated host by host, so the hosts whose labels are asked
# for are exactly the hosts the optimizer considers.
LABEL_RULES: Sequence[RuleSpec[str]] = [
    {
        "id": "labels",
        "value": "matched",
        "condition": {"host_label_groups": [("and", [("and", "os:linux")])]},
    },
]


class LabelsRecorder:
    def __init__(self) -> None:
        self.hosts: set[HostName] = set()

    def __call__(self, host_name: HostName) -> Labels:
        self.hosts.add(host_name)
        return {}


def _make_matcher() -> RulesetMatcher:
    return RulesetMatcher(
        host_tags={hn: {} for hn in (HOST1, HOST2, HOST3)},
        host_paths={},
        all_configured_hosts=frozenset((HOST1, HOST2, HOST3)),
        clusters_of={},
        nodes_of={},
    )


def _values(matcher: RulesetMatcher, host_name: HostName) -> Sequence[str]:
    return matcher.get_host_values_all(host_name, HOST_NAME_RULES, lambda hn: {})  # noqa: ARG005


def _considered_hosts(matcher: RulesetMatcher, host_name: HostName) -> set[HostName]:
    labels_of_host = LabelsRecorder()
    matcher.get_host_values_all(host_name, LABEL_RULES, labels_of_host)
    return labels_of_host.hosts


def test_narrowing_adds_only_the_related_clusters_and_nodes() -> None:
    c1, c2 = HostName("c1"), HostName("c2")
    matcher = RulesetMatcher(
        host_tags={hn: {} for hn in (HOST1, HOST2, HOST3, c1, c2)},
        host_paths={},
        all_configured_hosts=frozenset((HOST1, HOST2, HOST3, c1, c2)),
        clusters_of={HOST1: [c1], HOST2: [c1], HOST3: [c2]},
        nodes_of={c1: [HOST1, HOST2], c2: [HOST3]},
    )

    with matcher.ruleset_optimizer.processed_hosts({HOST1}):
        assert _considered_hosts(matcher, HOST1) == {HOST1, HOST2, c1}


def test_narrowed_scope_considers_only_its_hosts() -> None:
    matcher = _make_matcher()
    # Build a candidate set for the full scope, which narrowing must not reuse.
    _values(matcher, HOST1)

    with matcher.ruleset_optimizer.processed_hosts({HOST1}):
        assert _considered_hosts(matcher, HOST1) == {HOST1}


def test_narrowing_reuses_what_was_computed_for_the_wider_scope() -> None:
    matcher = _make_matcher()
    _considered_hosts(matcher, HOST1)

    with matcher.ruleset_optimizer.processed_hosts({HOST1}):
        assert _considered_hosts(matcher, HOST1) == set()


def test_leaving_a_nested_scope_restores_the_outer_one() -> None:
    matcher = _make_matcher()
    optimizer = matcher.ruleset_optimizer

    with optimizer.processed_hosts({HOST1, HOST2}):
        with optimizer.processed_hosts({HOST1}):
            _considered_hosts(matcher, HOST1)

        # This also relies on leaving the inner scope clearing what was computed inside it.
        assert _considered_hosts(matcher, HOST1) == {HOST1, HOST2}


def test_hosts_match_after_the_scope_is_left() -> None:
    matcher = _make_matcher()

    with matcher.ruleset_optimizer.processed_hosts({HOST1}):
        assert _values(matcher, HOST1) == ["matched"]

    assert _values(matcher, HOST2) == ["matched"]


def test_an_exception_restores_the_outer_scope() -> None:
    matcher = _make_matcher()

    with (
        pytest.raises(RuntimeError),
        matcher.ruleset_optimizer.processed_hosts({HOST1}),
    ):
        raise RuntimeError

    assert _considered_hosts(matcher, HOST1) == {HOST1, HOST2, HOST3}


def test_hosts_match_after_the_default_scope_grows() -> None:
    matcher = _make_matcher()
    optimizer = matcher.ruleset_optimizer

    optimizer.set_default_processed_hosts({HOST1})
    assert _values(matcher, HOST1) == ["matched"]

    optimizer.set_default_processed_hosts({HOST1, HOST2})
    assert _values(matcher, HOST2) == ["matched"]

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG002

import datetime
import logging
import time
from collections.abc import Container, Mapping
from io import StringIO
from typing import override
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.discovery._autochecks import AutocheckServiceWithNodes
from cmk.checkengine.discovery._autodiscovery import (
    _may_rediscover,
    _node_service_source,
    BasicTransition,
    get_host_services_by_host_name,
    Transition,
)
from cmk.checkengine.discovery._utils.filters import RediscoveryParameters
from cmk.checkengine.discovery.types import DiscoveredItem
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName

NODE_1 = HostAddress("node1")
NODE_2 = HostAddress("node2")
NODE_3 = HostAddress("node3")
CLUSTER = HostAddress("cluster")

AUTOCHECK_1A = AutocheckEntry(
    CheckPluginName("check_plugin_1"),
    "Item",
    {"parameter_common": "1A", "parameter_1a": "1A"},
    {"label_common": "1A", "label_1a": "1A"},
)
AUTOCHECK_1B = AutocheckEntry(
    CheckPluginName("check_plugin_1"),
    "Item",
    {"parameter_common": "1B", "parameter_1b": "1B"},
    {"label_common": "1B", "label_1b": "1B"},
)
AUTOCHECK_1MERGED = AutocheckEntry(
    CheckPluginName("check_plugin_1"),
    "Item",
    {"parameter_common": "1A", "parameter_1a": "1A", "parameter_1b": "1B"},
    {"label_common": "1A", "label_1a": "1A", "label_1b": "1B"},
)
AUTOCHECK_2 = AutocheckEntry(
    CheckPluginName("check_plugin_2"),
    "Item",
    {"parameter_common": "2", "parameter_2": "2"},
    {"label_common": "2", "label_2": "2"},
)
AUTOCHECK_3A = AutocheckEntry(
    CheckPluginName("check_plugin_3"),
    "Item",
    {"parameter_common": "a"},
    {"label_common": "a"},
)
AUTOCHECK_3B = AutocheckEntry(
    CheckPluginName("check_plugin_3"),
    "Item",
    {"parameter_common": "b"},
    {"label_common": "b"},
)
AUTOCHECK_3C = AutocheckEntry(
    CheckPluginName("check_plugin_3"),
    "Item",
    {"parameter_common": "c"},
    {"label_common": "c"},
)


class _AutochecksConfigDummy:
    def __init__(self, *, effective_host: HostName) -> None:
        self._effective_host = effective_host

    def ignore_plugin(self, hn: HostName, plugin: CheckPluginName) -> bool:
        return False

    def ignore_service(self, hn: HostName, entry: AutocheckEntry) -> bool:
        return False

    def effective_host(self, host_name: HostName, entry: AutocheckEntry) -> HostName:
        return self._effective_host

    def service_description(self, host_name: HostName, entry: AutocheckEntry) -> str:
        return f"{entry.check_plugin_name} / {entry.item}"

    def service_labels(self, host_name: HostName, entry: AutocheckEntry) -> Mapping[str, str]:
        return {}


class _AutochecksConfigIgnoreAll(_AutochecksConfigDummy):
    """AutochecksConfig where every service and plugin matches a disabled rule."""

    @override
    def ignore_plugin(self, hn: HostName, plugin: CheckPluginName) -> bool:
        return True

    @override
    def ignore_service(self, hn: HostName, entry: AutocheckEntry) -> bool:
        return True


def test_get_host_services_by_host_name_vanished_on_node() -> None:
    assert get_host_services_by_host_name(
        NODE_1,
        existing_services={NODE_1: [AUTOCHECK_1A]},
        discovered_services={NODE_1: []},
        is_cluster=False,
        cluster_nodes=(),
        autochecks_config=_AutochecksConfigDummy(effective_host=NODE_1),
        enforced_services={},
    ) == {
        NODE_1: {
            "vanished": [
                AutocheckServiceWithNodes(
                    service=DiscoveredItem(previous=AUTOCHECK_1A, new=None),
                    nodes=[NODE_1],
                ),
            ]
        }
    }


def test_vanished_service_matching_disabled_rule_is_discovered_as_vanished() -> None:
    """A service absent from the agent output must be classified as 'vanished' even when a
    disabled-services rule matches it.  Previously the ignore rule won and the service was
    hidden as 'ignored', masking the fact that it had disappeared from the host."""
    assert get_host_services_by_host_name(
        NODE_1,
        existing_services={NODE_1: [AUTOCHECK_1A]},
        discovered_services={NODE_1: []},
        is_cluster=False,
        cluster_nodes=(),
        autochecks_config=_AutochecksConfigIgnoreAll(effective_host=NODE_1),
        enforced_services={},
    ) == {
        NODE_1: {
            "vanished": [
                AutocheckServiceWithNodes(
                    service=DiscoveredItem(previous=AUTOCHECK_1A, new=None),
                    nodes=[NODE_1],
                ),
            ]
        }
    }


def test_get_host_services_by_host_name_unchanged_on_node() -> None:
    assert get_host_services_by_host_name(
        NODE_1,
        existing_services={NODE_1: [AUTOCHECK_1A]},
        discovered_services={NODE_1: [AUTOCHECK_1A]},
        is_cluster=False,
        cluster_nodes=(),
        autochecks_config=_AutochecksConfigDummy(effective_host=NODE_1),
        enforced_services={},
    ) == {
        NODE_1: {
            "unchanged": [
                AutocheckServiceWithNodes(
                    service=DiscoveredItem(previous=AUTOCHECK_1A, new=AUTOCHECK_1A),
                    nodes=[NODE_1],
                ),
            ]
        }
    }


def test_get_host_services_by_host_name_changed_on_node() -> None:
    assert get_host_services_by_host_name(
        NODE_1,
        existing_services={NODE_1: [AUTOCHECK_1A]},
        discovered_services={NODE_1: [AUTOCHECK_1B]},
        is_cluster=False,
        cluster_nodes=(),
        autochecks_config=_AutochecksConfigDummy(effective_host=NODE_1),
        enforced_services={},
    ) == {
        NODE_1: {
            "changed": [
                AutocheckServiceWithNodes(
                    service=DiscoveredItem(previous=AUTOCHECK_1A, new=AUTOCHECK_1B),
                    nodes=[NODE_1],
                ),
            ]
        }
    }


def test_get_host_services_by_host_name_new_on_node() -> None:
    assert get_host_services_by_host_name(
        NODE_1,
        existing_services={NODE_1: []},
        discovered_services={NODE_1: [AUTOCHECK_1B]},
        is_cluster=False,
        cluster_nodes=(),
        autochecks_config=_AutochecksConfigDummy(effective_host=NODE_1),
        enforced_services={},
    ) == {
        NODE_1: {
            "new": [
                AutocheckServiceWithNodes(
                    service=DiscoveredItem(previous=None, new=AUTOCHECK_1B),
                    nodes=[NODE_1],
                ),
            ]
        }
    }


def test_vanished_cluster_service_matching_disabled_rule_is_discovered_as_vanished() -> None:
    """A cluster service absent from all nodes must be classified as 'vanished' even
    when a disabled-services rule matches it on the cluster."""
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [],
        },
        discovered_services={
            NODE_1: [],
            NODE_2: [],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2),
        autochecks_config=_AutochecksConfigIgnoreAll(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "vanished": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_1A, new=None),
                nodes=[],
            )
        ],
    }


def test_get_host_services_by_host_name_vanished_on_cluster() -> None:
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [],
        },
        discovered_services={
            NODE_1: [],
            NODE_2: [],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2),
        autochecks_config=_AutochecksConfigDummy(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "vanished": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_1A, new=None),
                nodes=[],
            )
        ],
    }


def test_get_host_services_by_host_name_unchanged_on_cluster() -> None:
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [AUTOCHECK_1A],
        },
        discovered_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2),
        autochecks_config=_AutochecksConfigDummy(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "unchanged": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_1A, new=AUTOCHECK_1A),
                nodes=[NODE_1],
            )
        ],
    }


def test_get_host_services_by_host_name_changed_on_cluster() -> None:
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [AUTOCHECK_1A],
        },
        discovered_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [AUTOCHECK_1B],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2),
        autochecks_config=_AutochecksConfigDummy(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "changed": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_1A, new=AUTOCHECK_1MERGED),
                nodes=[NODE_1, NODE_2],
            )
        ],
    }


def test_get_host_services_by_host_name_new_on_cluster() -> None:
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [],
            NODE_2: [],
        },
        discovered_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2),
        autochecks_config=_AutochecksConfigDummy(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "new": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=None, new=AUTOCHECK_1A),
                nodes=[NODE_1],
            )
        ],
    }


def test_get_host_services_by_host_name_swaps_on_cluster() -> None:
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [],
        },
        discovered_services={
            NODE_1: [],
            NODE_2: [AUTOCHECK_1A],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2),
        autochecks_config=_AutochecksConfigDummy(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "unchanged": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_1A, new=AUTOCHECK_1A),
                nodes=[NODE_2],
            )
        ],
    }


def test_get_host_services_by_host_name_params_prio_on_active_nodes() -> None:
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [AUTOCHECK_3A],
            NODE_2: [AUTOCHECK_3B],
        },
        discovered_services={
            NODE_1: [],
            NODE_2: [AUTOCHECK_3B],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2),
        autochecks_config=_AutochecksConfigDummy(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "changed": [
            # I believe the above must be "changed". The service *now* is discovered on NODE_2,
            # but that does not mean we should prioritize NODE_2 over NODE_1 when computing the
            # previous service. When both nodes had the service in the autochecks, the checking
            # will have prioritized NODE_1, so the transition described here is a change.
            AutocheckServiceWithNodes(
                service=DiscoveredItem(
                    previous=AUTOCHECK_3A,
                    new=AUTOCHECK_3B,
                ),
                nodes=[NODE_2],
            )
        ],
    }


def test_get_host_services_by_host_name_params_prio_on_active_nodes_multiple_nodes() -> None:
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [AUTOCHECK_3A, AUTOCHECK_1A],
            NODE_2: [AUTOCHECK_3B],
            NODE_3: [AUTOCHECK_3C],
        },
        discovered_services={
            NODE_1: [AUTOCHECK_1A],
            NODE_2: [AUTOCHECK_3B],
            NODE_3: [],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2, NODE_3),
        autochecks_config=_AutochecksConfigDummy(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "unchanged": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_1A, new=AUTOCHECK_1A),
                nodes=[NODE_1],
            )
        ],
        "changed": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_3A, new=AUTOCHECK_3B),
                nodes=[NODE_2],
            ),
        ],
    }


def test_get_host_services_by_host_name_move_mutiple_nodes_and_autochecks() -> None:
    assert get_host_services_by_host_name(
        CLUSTER,
        existing_services={
            NODE_1: [AUTOCHECK_1A, AUTOCHECK_2],
            NODE_2: [],
            NODE_3: [],
        },
        discovered_services={
            NODE_1: [],
            NODE_2: [AUTOCHECK_1A],
            NODE_3: [AUTOCHECK_2],
        },
        is_cluster=True,
        cluster_nodes=(NODE_1, NODE_2, NODE_3),
        autochecks_config=_AutochecksConfigDummy(effective_host=CLUSTER),
        enforced_services={},
    )[CLUSTER] == {
        "unchanged": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_2, new=AUTOCHECK_2),
                nodes=[NODE_3],
            ),
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_1A, new=AUTOCHECK_1A),
                nodes=[NODE_2],
            ),
        ],
    }


def _setup_buffered_logging() -> StringIO:
    logger = logging.getLogger("cmk")
    buffer = StringIO()
    handler = logging.StreamHandler(stream=buffer)
    handler.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return buffer


def test_may_rediscover_relies_on_time_zone_when_disallowing() -> None:

    rediscovery_parameters = RediscoveryParameters(
        {"excluded_time": [((9, 15), (9, 45))], "group_time": 3600},
    )
    buffer = _setup_buffered_logging()
    with time_machine.travel(
        datetime.datetime(2026, 1, 6, 9, 30, tzinfo=ZoneInfo("Europe/Berlin")),
        tick=False,
    ):
        assert (
            _may_rediscover(
                host_name=NODE_1,
                rediscovery_parameters=rediscovery_parameters,
                reference_time=time.mktime(time.localtime()),
                oldest_queued=0.0,
            )
            is False
        )
    log_messages = buffer.getvalue().strip("\n").split("\n")
    assert len(log_messages) == 1
    assert "disallowed at this time of day" in log_messages[0]


def test_may_rediscover_relies_on_time_zone_when_allowing() -> None:

    rediscovery_parameters = RediscoveryParameters(
        {"excluded_time": [((9, 15), (9, 45))], "group_time": 3600},
    )
    buffer = _setup_buffered_logging()

    with time_machine.travel(
        datetime.datetime(2026, 1, 6, 10, 30, tzinfo=ZoneInfo("Europe/Berlin")),
        tick=False,
    ):
        assert (
            _may_rediscover(
                host_name=NODE_1,
                rediscovery_parameters=rediscovery_parameters,
                reference_time=time.mktime(time.localtime()),
                oldest_queued=0.0,
            )
            is True
        )
    assert buffer.getvalue().strip("\n").split("\n") == [""]


_BASIC_TRANSITIONS: tuple[BasicTransition, ...] = ("new", "unchanged", "changed", "vanished")


def _classify(
    host_name: HostName,
    *,
    check_source: BasicTransition,
    service_ignored_on: Container[HostName] = (),
    plugin_ignored_on: Container[HostName] = (),
) -> Transition:
    """Classify one service of `CLUSTER`, as seen from `host_name`.

    `service_ignored_on` / `plugin_ignored_on` are the hosts a *Disabled services* resp. plugin
    rule matches on -- which host the classifier consults is itself part of the behaviour under
    test.
    """
    return _node_service_source(
        host_name,
        AUTOCHECK_1A,
        ignore_service=lambda host_name, _entry: host_name in service_ignored_on,
        ignore_plugin=lambda host_name, _plugin_name: host_name in plugin_ignored_on,
        check_source=check_source,
        cluster_name=CLUSTER,
    )


def test_node_service_source_emits_exactly_eight_of_the_nine_transitions() -> None:
    """Characterization of the classifier's whole output space.

    `clustered_ignored` is declared in `Transition` and produced by nothing: since
    `692c918bf86` (2021-02-05) an early `return "ignored"` has replaced a mutate-then-prefix,
    silently reverting werk 7128. The counter, the `Transition` literal, `_case_clustered`'s match
    arm and the GUI's "Disabled clustered services" group are all still there and all unreachable.

    **§10.13 changes this set**: its fix returns `clustered_ignored` from the node branch, so this
    assertion gains a ninth element. The paired strict-xfail below is what makes that a deliberate
    edit rather than a mystery failure. See
    `packages/cmk-check-engine/docs/SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md` §2.1 and §10.13.
    """
    produced = {
        _classify(
            host_name,
            check_source=check_source,
            service_ignored_on=(CLUSTER, NODE_1) if service_ignored else (),
            plugin_ignored_on=(CLUSTER, NODE_1) if plugin_ignored else (),
        )
        for host_name in (CLUSTER, NODE_1)
        for check_source in _BASIC_TRANSITIONS
        for service_ignored in (True, False)
        for plugin_ignored in (True, False)
    }

    assert produced == {
        "new",
        "unchanged",
        "changed",
        "vanished",
        "ignored",
        "clustered_new",
        "clustered_old",
        "clustered_vanished",
    }


@pytest.mark.xfail(
    strict=True,
    reason="§10.13 -- a disabled clustered service must be classified as `clustered_ignored` so "
    "that it is filed under 'Disabled clustered services' on the node (no bulk actions) and shown "
    "on the cluster, which is the host that actually manages it. Today it lands in the generic "
    "'Disabled services' group with bulk actions enabled, and re-enabling it from the node writes "
    "a node-scoped rule that has no effect while reporting success",
)
@pytest.mark.parametrize("check_source", ["new", "unchanged", "changed"])
def test_disabled_clustered_service_is_classified_as_clustered_ignored(
    check_source: BasicTransition,
) -> None:
    assert _classify(NODE_1, check_source=check_source, service_ignored_on=(CLUSTER,)) == (
        "clustered_ignored"
    )


@pytest.mark.parametrize("check_source", ["new", "unchanged", "changed"])
def test_disabled_clustered_service_is_currently_classified_as_plain_ignored(
    check_source: BasicTransition,
) -> None:
    """Today's behaviour. Not an endorsement -- see the paired strict-xfail above."""
    assert _classify(NODE_1, check_source=check_source, service_ignored_on=(CLUSTER,)) == "ignored"


@pytest.mark.parametrize("check_source", ["new", "unchanged", "changed"])
def test_clustered_service_is_only_disabled_by_a_rule_matching_the_cluster(
    check_source: BasicTransition,
) -> None:
    """For a node row the classifier consults the rule on the **cluster**, not on the node.

    Surprising, but correct and preserved by §10.13's fix: the cluster owns the service, so the
    cluster's rules decide whether it is disabled. Pinned because the asymmetry against
    `appears_on_cluster` -- which tests the rule on the *node* -- is what makes §10.13's common
    case the worst one, and a fix that "tidies" this line would reintroduce it.
    """
    assert _classify(NODE_1, check_source=check_source, service_ignored_on=(NODE_1,)) not in (
        "ignored",
        "clustered_ignored",
    )
    assert _classify(NODE_1, check_source=check_source, service_ignored_on=(CLUSTER,)) in (
        "ignored",
        "clustered_ignored",
    )


@pytest.mark.parametrize("host_name", [CLUSTER, NODE_1])
def test_node_service_source_never_turns_a_vanished_service_into_ignored(
    host_name: HostName,
) -> None:
    """A service absent from the agent output stays `vanished`, disabled-services rule or not.

    Intended behaviour, not characterization: this is the classifier-side reason why `vanished`
    admits no `disable` command -- the state the command would produce is one the classifier never
    assigns to a not-discovered service. See the behaviour matrix §11.3 and §10.16.
    """
    assert (
        _classify(
            host_name,
            check_source="vanished",
            service_ignored_on=(CLUSTER, NODE_1),
            plugin_ignored_on=(CLUSTER, NODE_1),
        )
        != "ignored"
    )

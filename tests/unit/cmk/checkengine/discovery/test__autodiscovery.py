#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.checkengine.discovery._autochecks import AutocheckServiceWithNodes
from cmk.checkengine.discovery._autodiscovery import get_host_services_by_host_name
from cmk.checkengine.discovery._utils import DiscoveredItem
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

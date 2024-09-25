#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.hostaddress import HostAddress

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery._autochecks import AutocheckEntry, AutocheckServiceWithNodes
from cmk.checkengine.discovery._autodiscovery import get_host_services_by_host_name
from cmk.checkengine.discovery._utils import DiscoveredItem

NODE_1 = HostAddress("node1")
NODE_2 = HostAddress("node2")
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


def test_get_host_services_by_host_name_vanished_on_node() -> None:
    assert get_host_services_by_host_name(
        NODE_1,
        existing_services={NODE_1: [AUTOCHECK_1A]},
        discovered_services={NODE_1: []},
        is_cluster=False,
        cluster_nodes=(),
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: NODE_1,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
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
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: NODE_1,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
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
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: NODE_1,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
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
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: NODE_1,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
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
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: CLUSTER,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
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
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: CLUSTER,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
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
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: CLUSTER,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
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
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: CLUSTER,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
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
        ignore_service=lambda *args: False,
        ignore_plugin=lambda *args: False,
        get_effective_host=lambda *args: CLUSTER,
        get_service_description=lambda host, plugin, item: f"{plugin} / {item}",
        enforced_services={},
    )[CLUSTER] == {
        "unchanged": [
            AutocheckServiceWithNodes(
                service=DiscoveredItem(previous=AUTOCHECK_1A, new=AUTOCHECK_1A),
                nodes=[NODE_2],
            )
        ],
    }

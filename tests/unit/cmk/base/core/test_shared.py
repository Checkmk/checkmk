#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Mapping
from typing import Literal

from cmk.base.core.shared import get_cluster_nodes_for_config
from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.tags import HostTags
from cmk.utils import config_warnings
from cmk.utils.ip_lookup import IPStackConfig

CLUSTER = HostName("cluster")
NODE_1 = HostName("node1")
NODE_2 = HostName("node2")


def _cluster_warnings(
    ip_stack_configs: Mapping[HostName, IPStackConfig],
    primary_families: Mapping[
        HostName, Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6]
    ],
) -> list[str]:
    config_warnings.initialize()
    get_cluster_nodes_for_config(
        CLUSTER,
        [NODE_1, NODE_2],
        ip_stack_configs.__getitem__,
        primary_families.__getitem__,
        HostTags(host_tags_sequences={}, host_tags_maps={}, site_id="site"),
        [CLUSTER, NODE_1, NODE_2],
        lambda _host_name: True,
    )
    return config_warnings.get_configuration(additional_warnings=())


def test_dual_stack_cluster_with_dual_stack_nodes_is_not_mixed() -> None:
    assert (
        _cluster_warnings(
            dict.fromkeys((CLUSTER, NODE_1, NODE_2), IPStackConfig.DUAL_STACK),
            dict.fromkeys((CLUSTER, NODE_1, NODE_2), socket.AF_INET),
        )
        == []
    )


def test_node_with_other_primary_family_is_mixed() -> None:
    assert _cluster_warnings(
        dict.fromkeys((CLUSTER, NODE_1, NODE_2), IPStackConfig.DUAL_STACK),
        {CLUSTER: socket.AF_INET, NODE_1: socket.AF_INET, NODE_2: socket.AF_INET6},
    ) == [
        (
            "Cluster 'cluster' has different primary address families: "
            "cluster: IPv4, node1: IPv4, node2: IPv6"
        )
    ]


def test_node_without_ip_is_mixed() -> None:
    assert _cluster_warnings(
        {CLUSTER: IPStackConfig.IPv4, NODE_1: IPStackConfig.IPv4, NODE_2: IPStackConfig.NO_IP},
        dict.fromkeys((CLUSTER, NODE_1, NODE_2), socket.AF_INET),
    ) == [
        (
            "Cluster 'cluster' has different primary address families: "
            "cluster: IPv4, node1: IPv4, node2: NO_IP"
        )
    ]

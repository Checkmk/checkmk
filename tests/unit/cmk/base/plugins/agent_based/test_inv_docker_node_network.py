#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.inventory_docker_node_network import (
    inventory_docker_node_network,
    parse_docker_node_network,
)

from .utils_inventory import sort_inventory_result

AGENT_OUTPUT = (
    '@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}\n'
    '{"Name": "asd", "Id": "f42d7f03e6d710662f70ebab8d5ff83538a729022ae97ad65f92c479e98126af", "Scope": '
    '"local", "Driver": "bridge", "Containers": {"123456": {"Name": "foobar", "EndpointID": "123", "MacAddress": "00:00:00:00:00:00", "IPv4Address": "1.2.3.4", "IPv6Address": ""}}, "Options": {}, "Labels": '
    '{"label_asd": "1", "label_asd_2": "2"}}'
)


def test_inv_docker_node_network() -> None:
    pre_parsed = [line.split("\0") for line in AGENT_OUTPUT.split("\n")]
    assert sort_inventory_result(
        inventory_docker_node_network(parse_docker_node_network(pre_parsed))
    ) == sort_inventory_result(
        [
            TableRow(
                path=["software", "applications", "docker", "networks", "containers"],
                key_columns={
                    "id": "123456",
                },
                status_columns={
                    "network_id": "f42d7f03e6d710662f70ebab8d5ff83538a729022ae97ad65f92c479e98126af",
                    "name": "foobar",
                    "ipv4_address": "1.2.3.4",
                    "ipv6_address": "",
                    "mac_address": "00:00:00:00:00:00",
                },
            ),
            TableRow(
                path=["software", "applications", "docker", "networks"],
                key_columns={
                    "network_id": "f42d7f03e6d710662f70ebab8d5ff83538a729022ae97ad65f92c479e98126af",
                },
                inventory_columns={
                    "short_id": "f42d7f03e6d7",
                    "name": "asd",
                    "scope": "local",
                    "labels": "label_asd: 1, label_asd_2: 2",
                },
                status_columns={},
            ),
        ]
    )

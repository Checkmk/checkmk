#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import InventoryResult, StringTable, TableRow
from cmk.plugins.collection.agent_based.inventory_docker_container_network import (
    inventory_docker_container_network,
    parse_docker_container_network,
)
from cmk.plugins.lib import docker

AGENT_OUTPUT = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}',
    ],
    [
        '{"Networks": {"bridge": {"NetworkID": "8f2baa1938b7957f876c1f5aa6767b86395b6971f349793bd7fae12eae6b83f0", '
        '"Gateway": "172.17.0.1", "IPAddress": "172.17.0.2", "IPPrefixLen": 16, "IPv6Gateway": "", '
        '"GlobalIPv6Address": "", "GlobalIPv6PrefixLen": 0, "MacAddress": "02:42:ac:11:00:02", "DriverOpts": null}}}'
    ],
]

# this error message is not related to docker_container_network but it is
# the attempt of mk_docker.py to execute the agent inside the docker
# container. if this failes the error message is outputted without a
# section, so it is typically appendet to this section
AGENT_OUTPUT_WITH_OCI_ERROR = AGENT_OUTPUT + [
    [
        "OCI runtime exec failed: exec failed: container_linux.go:344: starting container process caused "
        '"exec: "check_mk_agent": executable file not found in $PATH": unknown'
    ]
]

AGENT_OUTPUT_MULTIPLE_NODES = [
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1","DockerPyVersion": "5.0.3","ApiVersion": "1.47"}',
    ],
    [
        'Networks": {"bridge": {"IPAMConfig": null,"Links": null,"Aliases": null,"MacAddress": '
        '"02:42:ac:11:00:02","DriverOpts": null,"NetworkID": "60b6b83f447ed3567bd7711bb9d337c2c69648dfc9bab88b441594e8fbdbc25a",'
        '"EndpointID": "9c942bb42d3e408c65f132870b689e26efac93f4ec3c8bbac74deb732d90f8f7","Gateway": "172.17.0.1","IPAddress": "172.17.0.2",'
        '"IPPrefixLen": 16,"IPv6Gateway": "","GlobalIPv6Address": "","GlobalIPv6PrefixLen": 0,"DNSNames": null}}'
    ],
    [
        "@docker_version_info",
        '{"PluginVersion": "0.1","DockerPyVersion": "5.0.3","ApiVersion": "1.47"}',
    ],
    [
        'Networks": {"bridge": {"IPAMConfig": null,"Links": null,"Aliases": null,"MacAddress": '
        '"02:42:ac:11:00:02","DriverOpts": null,"NetworkID": "60b6b83f447ed3567bd7711bb9d337c2c69648dfc9bab88b441594e8fbdbc25a",'
        '"EndpointID": "9c942bb42d3e408c65f132870b689e26efac93f4ec3c8bbac74deb732d90f8f7","Gateway": "172.17.0.1","IPAddress": "172.17.0.2",'
        '"IPPrefixLen": 16,"IPv6Gateway": "","GlobalIPv6Address": "","GlobalIPv6PrefixLen": 0,"DNSNames": null}}'
    ],
]

EXPECTED_RESULT = [
    TableRow(
        path=["software", "applications", "docker", "container", "networks"],
        key_columns={
            "name": "bridge",
            "network_id": "8f2baa1938b7957f876c1f5aa6767b86395b6971f349793bd7fae12eae6b83f0",
        },
        inventory_columns={
            "ip_address": "172.17.0.2",
            "ip_prefixlen": 16,
            "gateway": "172.17.0.1",
            "mac_address": "02:42:ac:11:00:02",
        },
        status_columns={},
    ),
]


def test_inventory_docker_container_network_empty() -> None:
    with pytest.raises(docker.AgentOutputMalformatted) as e:
        parse_docker_container_network([])
        assert (
            "Did not find expected '@docker_version_info' at beginning of agent section."
            " Agents <= 1.5.0 are no longer supported."
        ) in str(e)


@pytest.mark.parametrize(
    "string_table, expected_result",
    [
        (AGENT_OUTPUT, EXPECTED_RESULT),
        (AGENT_OUTPUT_WITH_OCI_ERROR, EXPECTED_RESULT),
        # (AGENT_OUTPUT_MULTIPLE_NODES, []),
    ],
)
def test_inventory_docker_container_network(
    string_table: StringTable, expected_result: InventoryResult
) -> None:
    section = parse_docker_container_network(string_table)
    assert list(inventory_docker_container_network(section)) == expected_result

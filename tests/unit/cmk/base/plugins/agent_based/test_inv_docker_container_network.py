#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import InventoryPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow

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


@pytest.mark.parametrize("info", [AGENT_OUTPUT, AGENT_OUTPUT_WITH_OCI_ERROR])
def test_inv_docker_container_network(fix_register, info):
    plugin = fix_register.inventory_plugins[InventoryPluginName("docker_container_network")]
    assert list(plugin.inventory_function(info)) == [
        TableRow(
            path=["software", "applications", "docker", "container", "networks"],
            key_columns={
                "name": "bridge",
                "network_id": "8f2baa1938b7957f876c1f5aa6767b86395b6971f349793bd7fae12eae6b83f0",
                "ip_address": "172.17.0.2",
                "ip_prefixlen": 16,
                "gateway": "172.17.0.1",
                "mac_address": "02:42:ac:11:00:02",
            },
            inventory_columns={},
            status_columns={},
        )
    ]

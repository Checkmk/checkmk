#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow

AGENT_OUTPUT = (
    '@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}\n'
    '{"Networks": {"bridge": {"NetworkID": "8f2baa1938b7957f876c1f5aa6767b86395b6971f349793bd7fae12eae6b83f0", '
    '"Gateway": "172.17.0.1", "IPAddress": "172.17.0.2", "IPPrefixLen": 16, "IPv6Gateway": "", '
    '"GlobalIPv6Address": "", "GlobalIPv6PrefixLen": 0, "MacAddress": "02:42:ac:11:00:02", "DriverOpts": null}}}'
)


@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test_inv_docker_container_network():
    info = [
        line.split("\0") if "\0" in line else line.split(" ") for line in AGENT_OUTPUT.split("\n")
    ]
    plugin = agent_based_register.get_inventory_plugin(
        InventoryPluginName('docker_container_network'))
    assert plugin
    assert list(plugin.inventory_function(info)) == [
        TableRow(
            path=['software', 'applications', 'docker', 'container', 'networks'],
            key_columns={
                'name': 'bridge',
                'network_id': '8f2baa1938b7957f876c1f5aa6767b86395b6971f349793bd7fae12eae6b83f0',
                'ip_address': '172.17.0.2',
                'ip_prefixlen': 16,
                'gateway': '172.17.0.1',
                'mac_address': '02:42:ac:11:00:02'
            },
            inventory_columns={},
            status_columns={})
    ]

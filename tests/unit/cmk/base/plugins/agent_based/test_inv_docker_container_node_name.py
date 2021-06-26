#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import InventoryPluginName
import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.plugins.agent_based.utils.docker import AgentOutputMalformatted
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes

AGENT_OUTPUT = """@docker_version_info\0{"PluginVersion": "0.1", "DockerPyVersion": "4.1.0", "ApiVersion": "1.41"}
{"NodeName": "klappben"}"""


@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test_inv_docker_container_node_name():
    info = [line.split("\0") for line in AGENT_OUTPUT.split("\n")]
    plugin = agent_based_register.get_inventory_plugin(
        InventoryPluginName('docker_container_node_name'))
    assert plugin
    assert list(plugin.inventory_function(info)) == [
        Attributes(path=['software', 'applications', 'docker', 'container'],
                   inventory_attributes={'node_name': 'klappben'},
                   status_attributes={})
    ]


@pytest.mark.usefixtures("load_all_agent_based_plugins")
def test_inv_docker_container_node_name_legacy_agent_output():
    plugin = agent_based_register.get_inventory_plugin(
        InventoryPluginName('docker_container_node_name'))
    assert plugin
    with pytest.raises(AgentOutputMalformatted):
        list(plugin.inventory_function([['node_name']]))

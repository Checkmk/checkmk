#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based import register
from cmk.utils.type_defs import SectionName, CheckPluginName
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [([
    ["[[HXE", "90]]"],
    ["mode:", "primary"],
    ["systemReplicationStatus:", "10"],
    ["this", "system", "is", "not", "a", "system", "replication", "site"],
], {
    "HXE 90": {
        "sys_repl_status": "10",
        "mode": "primary"
    }
})])
def test_parse_sap_hana_replication_status(info, expected_result):
    section_name = SectionName("sap_hana_replication_status")
    section_plugin = register.get_section_plugin(section_name)
    result = section_plugin.parse_function(info)
    assert result == expected_result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE", "90]]"],
        ["mode:", "primary"],
        ["systemReplicationStatus:", "12"],
        ["this", "system", "is", "not", "a", "system", "replication", "site"],
    ], [Service(item="HXE 90")]),
    ([
        ["[[HXE", "90]]"],
        ["mode:", "primary"],
        ["systemReplicationStatus:", "10"],
        ["this", "system", "is", "not", "a", "system", "replication", "site"],
    ], []),
])
def test_discovery_sap_hana_replication_status(info, expected_result):
    section_name = SectionName("sap_hana_replication_status")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_replication_status")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 90",
        [
            ["[[HXE", "90]]"],
            ["mode:", "primary"],
            ["systemReplicationStatus:", "12"],
            ["this", "system", "is", "not", "a", "system", "replication", "site"],
        ],
        [Result(state=State.OK, summary="System replication: passive")],
    ),
    (
        "HXE 90",
        [
            ["[[HXE", "90]]"],
            ["mode:", "primary"],
            ["systemReplicationStatus:", "88"],
            ["this", "system", "is", "not", "a", "system", "replication", "site"],
        ],
        [Result(state=State.UNKNOWN, summary="System replication: unknown[88]")],
    ),
])
def test_check_sap_hana_replication_status(item, info, expected_result):
    section_name = SectionName("sap_hana_replication_status")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_replication_status")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.check_function(item, {}, section)) == expected_result

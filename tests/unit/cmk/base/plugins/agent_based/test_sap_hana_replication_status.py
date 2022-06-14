#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE", "90]]"],
                ["mode:", "primary"],
                ["systemReplicationStatus:", "10"],
                ["this", "system", "is", "not", "a", "system", "replication", "site"],
            ],
            {"HXE 90": {"sys_repl_status": "10", "mode": "primary"}},
        ),
        (
            [
                ["[[HXE", "90]]"],
                ["Mode:", "primary"],
                ["systemReplicationStatus:", "10"],
                ["this", "system", "is", "not", "a", "system", "replication", "site"],
            ],
            {"HXE 90": {"sys_repl_status": "10", "mode": "primary"}},
        ),
        (
            [
                ["[[HXE", "90]]"],
                ["mode:", "primary"],
                ["ReturnCode:", "10"],
                ["this", "system", "is", "not", "a", "system", "replication", "site"],
            ],
            {"HXE 90": {"sys_repl_status": "10", "mode": "primary"}},
        ),
    ],
)
def test_parse_sap_hana_replication_status(fix_register, info, expected_result) -> None:
    section_plugin = fix_register.agent_sections[SectionName("sap_hana_replication_status")]
    assert section_plugin.parse_function(info) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE", "90]]"],
                ["mode:", "primary"],
                ["systemReplicationStatus:", "12"],
                ["this", "system", "is", "not", "a", "system", "replication", "site"],
            ],
            [Service(item="HXE 90")],
        ),
        (
            [
                ["[[HXE", "90]]"],
                ["mode:", "primary"],
                ["systemReplicationStatus:", "10"],
                ["this", "system", "is", "not", "a", "system", "replication", "site"],
            ],
            [],
        ),
        (
            [
                ["[[HXE", "90]]"],
            ],
            [Service(item="HXE 90")],
        ),
    ],
)
def test_discovery_sap_hana_replication_status(fix_register, info, expected_result) -> None:
    section = fix_register.agent_sections[
        SectionName("sap_hana_replication_status")
    ].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_replication_status")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
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
    ],
)
def test_check_sap_hana_replication_status(fix_register, item, info, expected_result) -> None:
    section = fix_register.agent_sections[
        SectionName("sap_hana_replication_status")
    ].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_replication_status")]
    assert list(plugin.check_function(item, {}, section)) == expected_result

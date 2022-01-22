#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Dict, List

import pytest
from _pytest.monkeypatch import MonkeyPatch

# No stub file
from tests.testlib.base import Scenario

from cmk.utils.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.utils.type_defs import CheckPluginName, HostName, LegacyCheckParameters

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base import check_table, config
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.autochecks import AutocheckEntry
from cmk.base.check_table import HostCheckTable
from cmk.base.check_utils import Service, ServiceID


@pytest.mark.usefixtures("fix_register")
def test_cluster_ignores_nodes_parameters(monkeypatch: MonkeyPatch) -> None:

    node = HostName("node")
    cluster = HostName("cluster")

    service_id = CheckPluginName("smart_temp"), "auto-clustered"

    ts = Scenario()
    ts.add_host("node")
    ts.add_cluster("cluster", nodes=["node"])
    ts.set_ruleset(
        "clustered_services",
        [([], ["node"], ["Temperature SMART auto-clustered$"])],
    )
    ts.set_autochecks("node", [AutocheckEntry(*service_id, {}, {})])
    ts.apply(monkeypatch)

    # a rule for the node:
    monkeypatch.setattr(
        config,
        "_get_configured_parameters",
        lambda host, plugin, item: (
            TimespecificParameters(
                (TimespecificParameterSet.from_parameters({"levels_for_node": (1, 2)}),)
            )
            if host == node
            else TimespecificParameters()
        ),
    )

    clustered_service = check_table.get_check_table(cluster)[service_id]
    assert clustered_service.parameters.entries == (
        TimespecificParameterSet.from_parameters({"levels": (35, 40)}),
    )


# TODO: This misses a lot of cases
# - different get_check_table arguments
@pytest.mark.parametrize(
    "hostname_str,expected_result",
    [
        ("empty-host", {}),
        # Skip the autochecks automatically for ping hosts
        ("ping-host", {}),
        (
            "no-autochecks",
            {
                (CheckPluginName("smart_temp"), "/dev/sda"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="/dev/sda",
                    parameters={"levels": (35, 40)},
                    description="Temperature SMART /dev/sda",
                ),
            },
        ),
        # Static checks overwrite the autocheck definitions
        (
            "autocheck-overwrite",
            {
                (CheckPluginName("smart_temp"), "/dev/sda"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="/dev/sda",
                    parameters={"levels": (35, 40)},
                    description="Temperature SMART /dev/sda",
                ),
                (CheckPluginName("smart_temp"), "/dev/sdb"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="/dev/sdb",
                    parameters={"is_autocheck": True},
                    description="Temperature SMART /dev/sdb",
                ),
            },
        ),
        (
            "ignore-not-existing-checks",
            {
                (CheckPluginName("bla_blub"), "ITEM"): Service(
                    check_plugin_name=CheckPluginName("bla_blub"),
                    item="ITEM",
                    description="Blub ITEM",
                    parameters={},
                ),
                (CheckPluginName("blub_bla"), "ITEM"): Service(
                    check_plugin_name=CheckPluginName("blub_bla"),
                    item="ITEM",
                    description="Unimplemented check blub_bla / ITEM",
                    parameters=None,
                ),
            },
        ),
        (
            "ignore-disabled-rules",
            {
                (CheckPluginName("smart_temp"), "ITEM2"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="ITEM2",
                    parameters={"levels": (35, 40)},
                    description="Temperature SMART ITEM2",
                ),
            },
        ),
        (
            "static-check-overwrite",
            {
                (CheckPluginName("smart_temp"), "/dev/sda"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="/dev/sda",
                    parameters={"levels": (35, 40), "rule": 1},
                    description="Temperature SMART /dev/sda",
                )
            },
        ),
        (
            "node1",
            {
                (CheckPluginName("smart_temp"), "auto-not-clustered"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="auto-not-clustered",
                    parameters={},
                    description="Temperature SMART auto-not-clustered",
                ),
                (CheckPluginName("smart_temp"), "static-node1"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="static-node1",
                    parameters={"levels": (35, 40)},
                    description="Temperature SMART static-node1",
                ),
            },
        ),
        (
            "cluster1",
            {
                (CheckPluginName("smart_temp"), "static-cluster"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="static-cluster",
                    parameters={"levels": (35, 40)},
                    description="Temperature SMART static-cluster",
                ),
                (CheckPluginName("smart_temp"), "auto-clustered"): Service(
                    check_plugin_name=CheckPluginName("smart_temp"),
                    item="auto-clustered",
                    parameters={"levels": (35, 40)},
                    description="Temperature SMART auto-clustered",
                ),
            },
        ),
    ],
)
def test_get_check_table(
    monkeypatch: MonkeyPatch, hostname_str: str, expected_result: HostCheckTable
) -> None:
    hostname = HostName(hostname_str)

    ts = Scenario()
    ts.add_host(hostname, tags={"criticality": "test"})
    ts.add_host("ping-host", tags={"agent": "no-agent"})
    ts.add_host("node1")
    ts.add_cluster("cluster1", nodes=["node1"])
    ts.set_option(
        "static_checks",
        {
            "temperature": [
                (("smart.temp", "/dev/sda", {}), [], ["no-autochecks", "autocheck-overwrite"]),
                (("blub.bla", "ITEM", {}), [], ["ignore-not-existing-checks"]),
                (("smart.temp", "ITEM1", {}), [], ["ignore-disabled-rules"], {"disabled": True}),
                (("smart.temp", "ITEM2", {}), [], ["ignore-disabled-rules"]),
                (("smart.temp", "/dev/sda", {"rule": 1}), [], ["static-check-overwrite"]),
                (("smart.temp", "/dev/sda", {"rule": 2}), [], ["static-check-overwrite"]),
                (("smart.temp", "static-node1", {}), [], ["node1"]),
                (("smart.temp", "static-cluster", {}), [], ["cluster1"]),
            ]
        },
    )
    ts.set_ruleset(
        "clustered_services",
        [
            ([], ["node1"], ["Temperature SMART auto-clustered$"]),
        ],
    )
    ts.set_autochecks(
        "ping-host",
        [
            AutocheckEntry(CheckPluginName("smart_temp"), "bla", {}, {}),
        ],
    )
    ts.set_autochecks(
        "autocheck-overwrite",
        [
            AutocheckEntry(CheckPluginName("smart_temp"), "/dev/sda", {"is_autocheck": True}, {}),
            AutocheckEntry(CheckPluginName("smart_temp"), "/dev/sdb", {"is_autocheck": True}, {}),
        ],
    )
    ts.set_autochecks(
        "ignore-not-existing-checks",
        [
            AutocheckEntry(CheckPluginName("bla_blub"), "ITEM", {}, {}),
        ],
    )
    ts.set_autochecks(
        "node1",
        [
            AutocheckEntry(CheckPluginName("smart_temp"), "auto-clustered", {}, {}),
            AutocheckEntry(CheckPluginName("smart_temp"), "auto-not-clustered", {}, {}),
        ],
    )

    ts.apply(monkeypatch)

    assert check_table.get_check_table(hostname) == expected_result


@pytest.mark.parametrize(
    "hostname_str, expected_result",
    [
        ("mgmt-board-ipmi", [(CheckPluginName("mgmt_ipmi_sensors"), "TEMP X")]),
        ("ipmi-host", [(CheckPluginName("ipmi_sensors"), "TEMP Y")]),
    ],
)
def test_get_check_table_of_mgmt_boards(
    monkeypatch: MonkeyPatch, hostname_str: str, expected_result: List[ServiceID]
) -> None:
    hostname = HostName(hostname_str)

    ts = Scenario()
    ts.add_host(
        "mgmt-board-ipmi",
        tags={
            "piggyback": "auto-piggyback",
            "networking": "lan",
            "address_family": "no-ip",
            "criticality": "prod",
            "snmp_ds": "no-snmp",
            "site": "heute",
            "agent": "no-agent",
        },
    )
    ts.add_host(
        "ipmi-host",
        tags={
            "piggyback": "auto-piggyback",
            "networking": "lan",
            "agent": "cmk-agent",
            "criticality": "prod",
            "snmp_ds": "no-snmp",
            "site": "heute",
            "address_family": "ip-v4-only",
        },
    )
    ts.set_option("management_protocol", {"mgmt-board-ipmi": "ipmi"})

    ts.set_autochecks(
        "mgmt-board-ipmi",
        [AutocheckEntry(CheckPluginName("mgmt_ipmi_sensors"), "TEMP X", {}, {})],
    )
    ts.set_autochecks(
        "ipmi-host",
        [AutocheckEntry(CheckPluginName("ipmi_sensors"), "TEMP Y", {}, {})],
    )

    ts.apply(monkeypatch)

    assert list(check_table.get_check_table(hostname).keys()) == expected_result


def test_get_check_table__static_checks_win(monkeypatch: MonkeyPatch) -> None:
    hostname_str = "df_host"
    hostname = HostName(hostname_str)
    plugin_name = CheckPluginName("df")
    item = "/snap/core/9066"

    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "static_checks",
        {
            "filesystem": [
                ((str(plugin_name), item, {"source": "static"}), [], [hostname_str]),
            ],
        },
    )
    ts.set_autochecks(hostname_str, [AutocheckEntry(plugin_name, item, {"source": "auto"}, {})])
    ts.apply(monkeypatch)

    chk_table = check_table.get_check_table(hostname)

    # assert check table is populated as expected
    assert len(chk_table) == 1
    # assert static checks won
    effective_params = chk_table[(plugin_name, item)].parameters.evaluate(lambda _: True)
    assert effective_params["source"] == "static"


@pytest.mark.parametrize(
    "check_group_parameters",
    [
        {},
        {
            "levels": (4, 5, 6, 7),
        },
    ],
)
def test_check_table__get_static_check_entries(
    monkeypatch: MonkeyPatch, check_group_parameters: LegacyCheckParameters
) -> None:
    hostname = HostName("hostname")

    static_parameters_default = {"levels": (1, 2, 3, 4)}
    static_checks: Dict[str, List] = {
        "ps": [(("ps", "item", static_parameters_default), [], [hostname], {})],
    }

    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("static_checks", static_checks)

    ts.set_ruleset(
        "checkgroup_parameters",
        {
            "ps": [(check_group_parameters, [hostname], [], {})],
        },
    )

    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(
        agent_based_register,
        "get_check_plugin",
        lambda cpn: CheckPlugin(
            CheckPluginName("ps"),
            [],
            "Process item",
            None,  # type: ignore
            None,  # type: ignore
            None,  # type: ignore
            None,  # type: ignore
            None,  # type: ignore
            {},
            "ps",  # type: ignore
            None,  # type: ignore
            None,  # type: ignore
        ),
    )

    host_config = config_cache.get_host_config(hostname)
    static_check_parameters = [
        service.parameters
        for service in check_table._get_static_check_entries(config_cache, host_config)
    ]

    entries = config._get_checkgroup_parameters(
        config_cache,
        hostname,
        "ps",
        "item",
        "Process item",
    )

    assert len(entries) == 1
    assert entries[0] == check_group_parameters

    assert len(static_check_parameters) == 1
    static_check_parameter = static_check_parameters[0]
    assert static_check_parameter == TimespecificParameters(
        (
            TimespecificParameterSet(static_parameters_default, ()),
            TimespecificParameterSet({}, ()),
        )
    )

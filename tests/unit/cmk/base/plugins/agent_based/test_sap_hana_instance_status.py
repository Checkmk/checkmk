#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based import register
from cmk.utils.type_defs import SectionName, CheckPluginName
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service
from cmk.base.plugins.agent_based.sap_hana_instance_status import InstanceStatus, InstanceProcess


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE 98]]"],
        ["instanceStatus: 3"],
        ["OK"],
        ["name", "description", "dispstatus", "textstatus", "starttime", "elapsedtime", "pid"],
        ["hdbdaemon", "HDB Daemon", "GREEN", "Running", "2021 05 19 07:50:33", "0:40:50", "2384"],
        [
            "hdbcompileserver", "HDB Compileserver", "GREEN", "Running", "2021 05 19 07:50:44",
            "0:40:39", "3546"
        ],
    ], {
        "HXE 98": InstanceStatus(status='3',
                                 processes=[
                                     InstanceProcess(name='HDB Daemon',
                                                     state='GREEN',
                                                     description='Running',
                                                     elapsed_time=2450.0,
                                                     pid='2384'),
                                     InstanceProcess(name='HDB Compileserver',
                                                     state='GREEN',
                                                     description='Running',
                                                     elapsed_time=2439.0,
                                                     pid='3546')
                                 ])
    }),
    ([
        ["[[HXE 98]]"],
        ["instanceStatus: 4"],
    ], {
        "HXE 98": InstanceStatus(status='4')
    }),
])
def test_parse_sap_hana_instance_status(info, expected_result):
    section_name = SectionName("sap_hana_instance_status")
    section_plugin = register.get_section_plugin(section_name)
    result = section_plugin.parse_function(info)
    assert result == expected_result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [
    (
        [
            ["[[HXE 98]]"],
            ["instanceStatus: 3"],
            ["OK"],
            ["name", "description", "dispstatus", "textstatus", "starttime", "elapsedtime", "pid"],
            [
                "hdbdaemon", "HDB Daemon", "GREEN", "Running", "2021 05 19 07:50:33", "0:40:50",
                "2384"
            ],
            [
                "hdbcompileserver", "HDB Compileserver", "GREEN", "Running", "2021 05 19 07:50:44",
                "0:40:39", "3546"
            ],
        ],
        [Service(item="HXE 98")],
    ),
])
def test_inventory_sap_hana_instance_status(info, expected_result):
    section_name = SectionName("sap_hana_instance_status")
    section = register.get_section_plugin(section_name).parse_function(info)
    plugin_name = CheckPluginName("sap_hana_instance_status")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 98",
        [
            ["[[HXE 98]]"],
            ["instanceStatus: 4"],
        ],
        [Result(state=State.CRIT, summary='All processes stopped')],
    ),
    (
        "HXE 99",
        [
            ["[[HXE 98]]"],
            ["instanceStatus: 4"],
        ],
        [],
    ),
    (
        "HXE 98",
        [
            ["[[HXE 98]]"],
            ["instanceStatus: 3"],
            ["OK"],
            ["name", "description", "dispstatus", "textstatus", "starttime", "elapsedtime", "pid"],
            [
                "hdbdaemon", "HDB Daemon", "GREEN", "Running", "2021 05 19 07:50:33", "0:40:50",
                "2384"
            ],
            [
                "hdbcompileserver", "HDB Compileserver", "RED", "Running", "2021 05 19 07:50:44",
                "0:40:39", "3546"
            ],
        ],
        [
            Result(state=State.OK, summary='OK'),
            Result(state=State.OK,
                   summary='HDB Daemon: Running for 40 minutes 50 seconds, PID: 2384'),
            Result(state=State.WARN,
                   summary='HDB Compileserver: Running for 40 minutes 39 seconds, PID: 3546'),
        ],
    ),
])
def test_check_sap_hana_instance_status(item, info, expected_result):
    section_name = SectionName("sap_hana_instance_status")
    section = register.get_section_plugin(section_name).parse_function(info)
    plugin_name = CheckPluginName("sap_hana_instance_status")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.check_function(item, section)) == expected_result

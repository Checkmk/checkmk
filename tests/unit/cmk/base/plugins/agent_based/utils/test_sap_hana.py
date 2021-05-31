#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from typing import Dict

from cmk.base.api.agent_based import register
from cmk.utils.type_defs import SectionName, CheckPluginName
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service
from cmk.base.plugins.agent_based.utils.sap_hana import get_cluster_check, get_cluster_check_with_params
from cmk.base.plugins.agent_based.sap_hana_replication_status import check_sap_hana_replication_status
from cmk.base.plugins.agent_based.sap_hana_instance_status import (InstanceStatus, InstanceProcess,
                                                                   check_sap_hana_instance_status)


@pytest.mark.parametrize("item, section, expected_result", [(
    "HXE 98",
    {
        "node1": {
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
                                     ]),
        },
        "node2": {
            "HXE 98": InstanceStatus(status='4'),
        }
    },
    [
        Result(state=State.OK, summary='Nodes: node1, node2'),
        Result(state=State.OK, summary='OK'),
        Result(state=State.OK, summary='HDB Daemon: Running for 40 minutes 50 seconds, PID: 2384'),
        Result(state=State.OK,
               summary='HDB Compileserver: Running for 40 minutes 39 seconds, PID: 3546'),
    ],
)])
def test_get_cluster_check(item, section, expected_result):
    cluster_func = get_cluster_check(check_sap_hana_instance_status)
    result = cluster_func(item, section)
    assert list(result) == expected_result


@pytest.mark.parametrize(
    "item, params, section, expected_result",
    [(
        "HXE 90",
        {
            "state_no_replication": State.OK
        },
        {
            "node1": {
                "HXE 90": {
                    "sys_repl_status": "10",
                    "mode": "primary"
                }
            },
            "node2": {
                "HXE 90": {
                    "sys_repl_status": "13",
                    "mode": "primary"
                }
            }
        },
        [
            Result(state=State.OK, summary='Nodes: node1, node2'),
            Result(state=State.OK, summary='System replication: no system replication')
        ],
    ),
     (
         "HXE 90",
         {},
         {
             "node1": {
                 "HXE 90": {
                     "sys_repl_status": "10",
                     "mode": "primary"
                 }
             },
             "node2": {
                 "HXE 90": {
                     "sys_repl_status": "13",
                     "mode": "primary"
                 }
             }
         },
         [
             Result(state=State.OK, summary='Nodes: node1, node2'),
             Result(state=State.WARN, summary='System replication: initializing')
         ],
     )])
def test_get_cluster_check_with_params(item, params, section, expected_result):
    cluster_func = get_cluster_check_with_params(check_sap_hana_replication_status)
    result = cluster_func(item, params, section)
    assert list(result) == expected_result

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based import cisco_asa_failover
# from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service, Metric

# from cmk.base.plugins.agent_based import fortigate_node_memory as fortigate_memory
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service, Metric


@pytest.mark.parametrize("string_table, expected", [
    ([[['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
       ['Primary unit (this device)', '9', 'Active unit'],
       ['Secondary unit', '10', 'Standby unit']]],
     {'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
      'local': ['primary', '9', 'active unit'],
      'remote': ['secondary', '10', 'standby unit']}),

    ([[['Failover LAN Interface', '3', 'not Configured'], ['Primary unit', '3', 'Failover Off'],
       ['Secondary unit (this device)', '3', 'Failover Off']]], None,),
])
def test_cisco_asa_failover_parse(string_table, expected):
    section = cisco_asa_failover.parse_cisco_asa_failover(string_table)
    assert section == expected


@pytest.mark.parametrize("section, expected", [
    ({'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
      'local': ['primary', '9', 'active unit'],
      'remote': ['secondary', '10', 'standby unit']}, [Service()]),
])
def test_cisco_asa_failover_discover(section, expected):
    services = list(cisco_asa_failover.discovery_cisco_asa_failover(section))
    assert services == expected


@pytest.mark.parametrize(
    "params, section, expected", [
        ({'failover_state': 1, 'primary': 'active', 'secondary': 'active'},
         {'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
          'local': ['primary', '9', 'active unit'],
          'remote': ['secondary', '10', 'standby unit']},
         [Result(state=State.OK, summary='Device (primary) is the active unit'), ]),
    ])
def test_cisco_asa_failover(params, section, expected):
    # section = cisco_asa_failover.parse_cisco_asa_failover(data)
    result = cisco_asa_failover.check_cisco_asa_failover(params, section)
    assert list(result) == expected

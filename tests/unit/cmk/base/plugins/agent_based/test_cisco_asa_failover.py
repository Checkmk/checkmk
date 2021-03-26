#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based import cisco_asa_failover
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service, Metric


@pytest.mark.parametrize("string_table, expected", [
    pytest.param(
        [[['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
          ['Primary unit (this device)', '9', 'Active unit'], ['Secondary unit', '10', 'Standby unit'], ], ],
        {'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
         'local': ['primary', '9', 'active unit'], 'remote': ['secondary', '10', 'standby unit'], },
        id='Primary unit == Active unit'
    ),
    pytest.param(
        [[['Failover LAN Interface', '3', 'not Configured'], ['Primary unit', '3', 'Failover Off'],
          ['Secondary unit (this device)', '3', 'Failover Off'], ], ],
        None,
        id='failover of/not configured'
    ),
])
def test_cisco_asa_failover_parse(string_table, expected):
    section = cisco_asa_failover.parse_cisco_asa_failover(string_table)
    assert section == expected


@pytest.mark.parametrize("section, expected", [
    pytest.param(
        {'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
         'local': ['primary', '9', 'active unit'], 'remote': ['secondary', '10', 'standby unit'], },
        [Service()],
        id='Primary unit == Active unit'
    )
])
def test_cisco_asa_failover_discover(section, expected):
    services = list(cisco_asa_failover.discovery_cisco_asa_failover(section))
    assert services == expected


@pytest.mark.parametrize("params, section, expected", [
    pytest.param(
        {'failover_state': 1, 'primary': 'active', 'secondary': 'standby'},
        {'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
         'local': ['primary', '9', 'active unit'], 'remote': ['secondary', '10', 'standby unit']},
        [Result(state=State.OK, summary='Device (primary) is the active unit'), ],
        id='Primary unit == Active unit'
    ),
    pytest.param(
        {'failover_state': 1, 'primary': 'active', 'secondary': 'standby'},
        {'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
         'local': ['primary', '10', 'standby unit'], 'remote': ['secondary', '9', 'active unit']},
        [Result(state=State.OK, summary='Device (primary) is the standby unit'),
         Result(state=State.WARN, summary='(The primary device should be active)'), ],
        id='Primary unit == Standby unit'
    ),
    pytest.param(
        {'failover_state': 1, 'primary': 'active', 'secondary': 'standby'},
        {'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
         'local': ['primary', '8', 'backup unit'], 'remote': ['secondary', '9', 'active unit']},
        [Result(state=State.OK, summary='Device (primary) is the backup unit'),
         Result(state=State.WARN, summary='(The primary device should be active)'),
         Result(state=State.WARN, summary='Unhandled state backup reported')],
        id='local unit not active/standby'
    ),
])
def test_cisco_asa_failover(params, section, expected):
    result = cisco_asa_failover.check_cisco_asa_failover(params, section)
    assert list(result) == expected

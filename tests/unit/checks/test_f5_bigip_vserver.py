#!/usr/bin/env python3

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]


@pytest.mark.parametrize("info, item, expected_item_data", [
    ([
        [
            u'/path/to-1',
            u'1',
            u'1',
            u'The virtual server is available',
            u'1.2.3.4',
            u'1',
            u'2',
            u'3',
            u'4',
            u'5',
            u'6',
            u'7',
            u'8',
            u'9',
            u'10',
        ],
    ], u'/path/to-1', {
        'connections': [9],
        'connections_duration_max': [0.002],
        'connections_duration_mean': [0.003],
        'connections_duration_min': [0.001],
        'connections_rate': [8],
        'detail': u'The virtual server is available',
        'enabled': u'1',
        'if_in_octets': [6],
        'if_in_pkts': [4],
        'if_out_octets': [7],
        'if_out_pkts': [5],
        'ip_address': '-',
        'packet_velocity_asic': [10],
        'status': u'1',
    }),
])
@pytest.mark.usefixtures("config_load_all_checks")
def test_wmi_cpu_load_discovery(info, item, expected_item_data):
    check = Check("f5_bigip_vserver")
    assert sorted(check.run_parse(info)[item].items()) == sorted(expected_item_data.items())

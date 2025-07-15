#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable
from pathlib import Path

import pytest

from cmk.agent_based.v1 import Metric, Result, Service, State
from cmk.agent_based.v1.type_defs import CheckResult, StringTable
from cmk.plugins.collection.agent_based import cisco_temperature as ct
from tests.unit.cmk.plugins.collection.agent_based.snmp import (
    get_parsed_snmp_section,
    snmp_is_detected,
)


@pytest.mark.parametrize(
    ["input_table", "expected_section"],
    [
        pytest.param(
            """
.1.3.6.1.2.1.1.1.0 cisco
.1.3.6.1.2.1.2.2.1.2.30 TenGigabitEthernet2/0/22
.1.3.6.1.2.1.2.2.1.7.30 1
.1.3.6.1.2.1.47.1.1.1.1.4.2262 2083
.1.3.6.1.2.1.47.1.1.1.1.4.2263 2262
.1.3.6.1.2.1.47.1.1.1.1.4.2264 2262
.1.3.6.1.2.1.47.1.1.1.1.4.2265 2262
.1.3.6.1.2.1.47.1.1.1.1.4.2266 2262
.1.3.6.1.2.1.47.1.1.1.1.4.2267 2262
.1.3.6.1.2.1.47.1.1.1.1.7.2262 Te2/0/22
.1.3.6.1.2.1.47.1.1.1.1.7.2263 Te2/0/22 Module Temperature Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.2264 Te2/0/22 Supply Voltage Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.2265 Te2/0/22 Bias Current Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.2266 Te2/0/22 Transmit Power Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.2267 Te2/0/22 Receive Power Sensor
.1.3.6.1.2.1.47.1.3.2.1.2.2262.0 .1.3.6.1.2.1.2.2.1.1.30
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.2263 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.2264 4
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.2265 5
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.2266 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.2267 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.2263 9
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.2264 9
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.2265 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.2266 9
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.2267 9
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.2263 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.2264 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.2265 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.2266 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.2267 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.2263 240
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.2264 32
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.2265 373
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.2266 -14
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.2267 -48
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.2263 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.2264 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.2265 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.2266 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.2267 1
""",
            {
                "8": {
                    "Te2/0/22 Module Temperature Sensor": {
                        "descr": "Te2/0/22 Module Temperature Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": 24.0,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    }
                },
                "14": {
                    "Te2/0/22 Transmit Power Sensor": {
                        "descr": "Te2/0/22 Transmit Power Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": -1.4000000000000001,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                    "Te2/0/22 Receive Power Sensor": {
                        "descr": "Te2/0/22 Receive Power Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": -4.800000000000001,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                },
            },
            id="Catalyst",
        ),
        pytest.param(
            """
.1.3.6.1.2.1.1.1.0 cisco
.1.3.6.1.2.1.2.2.1.2.1 GigabitEthernet0/0/0
.1.3.6.1.2.1.2.2.1.7.1 1
.1.3.6.1.2.1.47.1.1.1.1.4.1046 1015
.1.3.6.1.2.1.47.1.1.1.1.4.1047 1046
.1.3.6.1.2.1.47.1.1.1.1.4.1048 1047
.1.3.6.1.2.1.47.1.1.1.1.4.1050 1047
.1.3.6.1.2.1.47.1.1.1.1.4.1051 1047
.1.3.6.1.2.1.47.1.1.1.1.4.1052 1047
.1.3.6.1.2.1.47.1.1.1.1.4.1053 1047
.1.3.6.1.2.1.47.1.1.1.1.4.1054 1047
.1.3.6.1.2.1.47.1.1.1.1.7.1046 subslot 0/0 transceiver container 0
.1.3.6.1.2.1.47.1.1.1.1.7.1047 subslot 0/0 transceiver 0
.1.3.6.1.2.1.47.1.1.1.1.7.1048 GigabitEthernet0/0/0
.1.3.6.1.2.1.47.1.1.1.1.7.1050 subslot 0/0 transceiver 0 Temperature Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.1051 subslot 0/0 transceiver 0 Supply Voltage Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.1052 subslot 0/0 transceiver 0 Bias Current Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.1053 subslot 0/0 transceiver 0 Tx Power Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.1054 subslot 0/0 transceiver 0 Rx Power Sensor
.1.3.6.1.2.1.47.1.3.2.1.2.1048.0 .1.3.6.1.2.1.2.2.1.1.1
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.1050 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.1051 4
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.1052 5
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.1053 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.1054 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.1050 9
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.1051 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.1052 7
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.1053 9
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.1054 9
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.1050 3
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.1051 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.1052 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.1053 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.1054 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.1050 29218
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.1051 33261
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.1052 2782
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.1053 -61
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.1054 -54
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.1050 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.1051 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.1052 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.1053 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.1054 1
            """,
            {
                "8": {
                    "subslot 0/0 transceiver 0 Temperature Sensor": {
                        "descr": "subslot 0/0 transceiver 0 Temperature Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": 29.218,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                },
                "14": {
                    "subslot 0/0 transceiver 0 Tx Power Sensor": {
                        "descr": "subslot 0/0 transceiver 0 Tx Power Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": -6.1000000000000005,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                    "subslot 0/0 transceiver 0 Rx Power Sensor": {
                        "descr": "subslot 0/0 transceiver 0 Rx Power Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": -5.4,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                },
            },
            id="ASR",
        ),
        pytest.param(
            """
.1.3.6.1.2.1.1.1.0 cisco
.1.3.6.1.2.1.2.2.1.2.436207616 Ethernet1/1
.1.3.6.1.2.1.2.2.1.7.436207616 1
.1.3.6.1.2.1.47.1.1.1.1.4.300000002 4950
.1.3.6.1.2.1.47.1.1.1.1.4.300000004 4950
.1.3.6.1.2.1.47.1.1.1.1.4.300000007 4950
.1.3.6.1.2.1.47.1.1.1.1.4.300000013 4950
.1.3.6.1.2.1.47.1.1.1.1.4.300000014 4950
.1.3.6.1.2.1.47.1.1.1.1.7.300000002 Ethernet1/1 Lane 1 Transceiver Voltage Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000004 Ethernet1/1 Lane 1 Transceiver Bias Current Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000007 Ethernet1/1 Lane 1 Transceiver Temperature Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000013 Ethernet1/1 Lane 1 Transceiver Receive Power Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000014 Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor
.1.3.6.1.2.1.47.1.3.2.1.2.4950.0 .1.3.6.1.2.1.2.2.1.1.436207616
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000002 3
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000004 5
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000007 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000013 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000014 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000002 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000004 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000007 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000013 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000014 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000002 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000004 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000007 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000013 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000014 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000002 3
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000004 7
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000007 30
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000013 -2
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000014 -2
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000002 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000004 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000007 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000013 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000014 1
            """,
            {
                "14": {
                    "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor": {
                        "descr": "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": -0.002,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                    "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor": {
                        "descr": "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": -0.002,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                },
                "8": {
                    "Ethernet1/1 Lane 1 Transceiver Temperature Sensor": {
                        "descr": "Ethernet1/1 Lane 1 Transceiver Temperature Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": 0.03,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    }
                },
            },
            id="Nexus",
        ),
        pytest.param(
            """
.1.3.6.1.2.1.1.1.0 cisco
.1.3.6.1.2.1.2.2.1.2.436207616 Ethernet1/1
.1.3.6.1.2.1.2.2.1.2.436215808 Ethernet1/3
.1.3.6.1.2.1.2.2.1.7.436207616 2
.1.3.6.1.2.1.2.2.1.7.436215808 1
.1.3.6.1.2.1.47.1.1.1.1.4.31958 4950
.1.3.6.1.2.1.47.1.1.1.1.4.31960 4952
.1.3.6.1.2.1.47.1.1.1.1.7.300000003 Ethernet1/1 Lane 1 Transceiver Voltage Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000004 Ethernet1/1 Lane 1 Transceiver Bias Current Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000007 Ethernet1/1 Lane 1 Transceiver Temperature Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000013 Ethernet1/1 Lane 1 Transceiver Receive Power Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000014 Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300003523 Ethernet1/3 Lane 1 Transceiver Voltage Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300003524 Ethernet1/3 Lane 1 Transceiver Bias Current Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300003527 Ethernet1/3 Lane 1 Transceiver Temperature Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300003533 Ethernet1/3 Lane 1 Transceiver Receive Power Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300003534 Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor
.1.3.6.1.2.1.47.1.1.1.1.16.300028174 2
.1.3.6.1.2.1.47.1.3.2.1.2.4950.0 .1.3.6.1.2.1.2.2.1.1.436207616
.1.3.6.1.2.1.47.1.3.2.1.2.4952.0 .1.3.6.1.2.1.2.2.1.1.436215808
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000003 4
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000004 5
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000007 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000013 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000014 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300003523 4
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300003524 5
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300003527 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300003533 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300003534 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000003 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000004 7
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000007 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000013 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000014 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300003523 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300003524 7
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300003527 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300003533 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300003534 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000003 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000004 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000007 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000013 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000014 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300003523 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300003524 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300003527 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300003533 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300003534 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000003 3354
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000004 314
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000007 26757
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000013 -33010
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000014 -10788
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300003523 3337
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300003524 6172
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300003527 26949
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300003533 -2862
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300003534 -2369
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000003 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000004 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000007 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000013 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000014 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300003523 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300003524 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300003527 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300003533 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300003534 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300005283 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300005284 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300005287 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300005293 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300005294 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300028163 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300028164 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300028167 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300028173 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300028174 1
            """,
            {
                "14": {
                    "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor": {
                        "admin_state": "down",
                        "descr": "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor",
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                        "dev_state": (0, "OK"),
                        "raw_dev_state": "1",
                        "reading": -33.01,
                    },
                    "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor": {
                        "admin_state": "down",
                        "descr": "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor",
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                        "dev_state": (0, "OK"),
                        "raw_dev_state": "1",
                        "reading": -10.788,
                    },
                    "Ethernet1/3 Lane 1 Transceiver Receive Power Sensor": {
                        "admin_state": "up",
                        "descr": "Ethernet1/3 Lane 1 Transceiver Receive Power Sensor",
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                        "dev_state": (0, "OK"),
                        "raw_dev_state": "1",
                        "reading": -2.862,
                    },
                    "Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor": {
                        "admin_state": "up",
                        "descr": "Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor",
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                        "dev_state": (0, "OK"),
                        "raw_dev_state": "1",
                        "reading": -2.369,
                    },
                },
                "8": {
                    "Ethernet1/1 Lane 1 Transceiver Temperature Sensor": {
                        "admin_state": "down",
                        "descr": "Ethernet1/1 Lane 1 Transceiver Temperature Sensor",
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                        "dev_state": (0, "OK"),
                        "raw_dev_state": "1",
                        "reading": 26.757,
                    },
                    "Ethernet1/3 Lane 1 Transceiver Temperature Sensor": {
                        "admin_state": "up",
                        "descr": "Ethernet1/3 Lane 1 Transceiver Temperature Sensor",
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                        "dev_state": (0, "OK"),
                        "raw_dev_state": "1",
                        "reading": 26.949,
                    },
                },
            },
            id="NX-OS",
        ),
        pytest.param(
            """
.1.3.6.1.2.1.1.1.0 cisco
.1.3.6.1.2.1.2.2.1.2.436207616 Ethernet1/1
.1.3.6.1.2.1.2.2.1.7.436207616 1
.1.3.6.1.2.1.47.1.1.1.1.4.300000002 4950
.1.3.6.1.2.1.47.1.1.1.1.4.300000004 4950
.1.3.6.1.2.1.47.1.1.1.1.4.300000007 4950
.1.3.6.1.2.1.47.1.1.1.1.4.300000013 4950
.1.3.6.1.2.1.47.1.1.1.1.4.300000014 4950
.1.3.6.1.2.1.47.1.1.1.1.7.300000002 Ethernet1/1 Lane 1 Transceiver Voltage Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000004 Ethernet1/1 Lane 1 Transceiver Bias Current Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000007 Ethernet1/1 Lane 1 Transceiver Temperature Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000013 Ethernet1/1 Lane 1 Transceiver Receive Power Sensor
.1.3.6.1.2.1.47.1.1.1.1.7.300000014 Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000002 3
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000004 5
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000007 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000013 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.300000014 14
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000002 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000004 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000007 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000013 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.300000014 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000002 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000004 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000007 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000013 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.300000014 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000002 3
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000004 7
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000007 30
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000013 -2
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.300000014 -2
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000002 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000004 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000007 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000013 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.300000014 1
            """,
            {
                "14": {
                    "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor": {
                        "descr": "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": -0.002,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                    "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor": {
                        "descr": "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": -0.002,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    },
                },
                "8": {
                    "Ethernet1/1 Lane 1 Transceiver Temperature Sensor": {
                        "descr": "Ethernet1/1 Lane 1 Transceiver Temperature Sensor",
                        "raw_dev_state": "1",
                        "dev_state": (0, "OK"),
                        "admin_state": "up",
                        "reading": 0.03,
                        "dev_levels_lower": None,
                        "dev_levels_upper": None,
                    }
                },
            },
            id="fallback entAliasMapping missing",
        ),
    ],
)
def test_parse_admin_state_mapping(
    input_table: str,
    expected_section: ct.Section,
    as_path: Callable[[str], Path],
) -> None:
    snmp_walk = as_path(input_table)

    assert snmp_is_detected(ct.snmp_section_cisco_temperature, snmp_walk)

    assert expected_section == get_parsed_snmp_section(ct.snmp_section_cisco_temperature, snmp_walk)


@pytest.mark.parametrize(
    ["input_table", "expected_section"],
    [
        pytest.param(
            [
                [["1010", "", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    ["1010.1", "20", "4", "56"],
                    ["1010.2", "10", "4", "46"],
                    ["1010.3", "20", "2", "-5"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["oid_end", "description", "1"]],
                [],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (46.0, 56.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="Both upper thresholds",
        ),
        pytest.param(
            [
                [["2008", "Switch 2 - Temp Sensor 2"]],
                [["2008", "8", "9", "0", "37", "1"]],
                [
                    ["2008.1", "20", "4", "125"],
                    ["2008.2", "10", "4", "105"],
                    ["2008.3", "10", "2", "105"],
                    ["2008.4", "20", "2", "-10"],
                ],
                [["2008", "Switch 2 - Temp Sensor 2, GREEN", "37", "125", "1"]],
                [["description", "1"]],
            ],
            {
                "8": {
                    "Switch 2 - Temp Sensor 2": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (105.0, 125.0),
                        "dev_state": (0, "normal"),
                        "raw_env_mon_state": "1",
                        "reading": 37,
                    },
                }
            },
            id="Temp sensors with cisco_sensor_item(statustext, ...) == sensor_id",
        ),
        pytest.param(
            [
                [["1010", "", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    ["1010.1", "20", "4", "56"],
                    ["1010.2", "10", "2", "46"],
                    ["1010.3", "20", "2", "-5"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["oid_end", "description", "1"]],
                [],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (56.0, 56.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="Only 1 upper threshold",
        ),
        pytest.param(
            [
                [["1132", "", "TenGigabitEthernet1/1/7 Transmit Power Sensor"]],
                [["1132", "14", "9", "1", "-19", "2"]],
                [],
                [],
                [],
                [],
            ],
            {
                "14": {
                    "TenGigabitEthernet1/1/7 Transmit Power Sensor": {
                        "admin_state": None,
                        "descr": "TenGigabitEthernet1/1/7 Transmit Power Sensor",
                        "dev_state": (3, "unavailable"),
                        "raw_dev_state": "2",
                    }
                },
                "8": {},
            },
            id="Defect sensor",
        ),
        pytest.param(
            [
                [["1010", "", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    # threshold relations not applicable to check_levels:
                    # 3 -> greater than, 2 -> less or equal
                    ["1010.1", "20", "3", "76"],
                    ["1010.2", "10", "3", "66"],
                    ["1010.3", "20", "2", "-5"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["oid_end", "description", "1"]],
                [],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (56.0, 56.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="EnvMon threshold fallback",
        ),
        pytest.param(
            [
                [["1010", "", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    # thresholds with severity = "other":
                    # coercion of thresholds to levels, provided relations are ignored.
                    ["1010.1", "1", "1", "76"],
                    ["1010.2", "1", "1", "66"],
                    ["1010.3", "1", "4", "-5"],
                    ["1010.4", "1", "4", "-15"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["oid_end", "description", "1"]],
                [],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": (-5.0, -15.0),
                        "dev_levels_upper": (66.0, 76.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="coercion_for_severity_other_4_thresholds",
        ),
        pytest.param(
            [
                [["1010", "", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    # thresholds with severity = "other":
                    # coercion of thresholds to levels, provided relations are ignored.
                    ["1010.1", "1", "1", "76"],
                    ["1010.2", "1", "1", "66"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["oid_end", "description", "1"]],
                [],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (66.0, 76.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="coercion_for_severity_other_2_thresholds",
        ),
        pytest.param(
            [
                [["1010", "", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    # No coercion, 3 thresholds are not applicable to our 4 levels.
                    ["1010.1", "1", "1", "76"],
                    ["1010.2", "1", "1", "66"],
                    ["1010.3", "1", "4", "-5"],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["oid_end", "description", "1"]],
                [],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (56.0, 56.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="fallback_no_coercion_for_severity_other",
        ),
        pytest.param(
            [
                [["1010", "", "Switch 1 - Inlet Temp Sensor"]],
                [["1010", "8", "9", "0", "49", "1"]],
                [
                    # no threshold values
                    ["1010.1", "1", "1", ""],
                    ["1010.2", "1", "1", ""],
                ],
                [["1010", "Switch 1 - Inlet Temp Sensor", "49", "56", "2"]],
                [["oid_end", "description", "1"]],
                [],
            ],
            {
                "8": {
                    "Switch 1 - Inlet Temp Sensor": {
                        "dev_levels_lower": None,
                        "dev_levels_upper": (56.0, 56.0),
                        "dev_state": (1, "warning"),
                        "raw_env_mon_state": "2",
                        "reading": 49,
                    },
                }
            },
            id="no_threshold_values",
        ),
    ],
)
def test_parse_cisco_temperature_thresholds(
    input_table: list[StringTable], expected_section: ct.Section
) -> None:
    assert ct.parse_cisco_temperature(input_table) == expected_section


def test_defect_sensor() -> None:
    section = {"8": {"Chassis 1": {"dev_state": (3, "sensor defect"), "raw_dev_state": "1"}}}

    assert list(ct.discover_cisco_temperature(section))

    (defect_result,) = ct._check_cisco_temperature({}, "Chassis 1", {}, section)
    assert isinstance(defect_result, Result)
    assert defect_result.state is not State.OK


@pytest.fixture(name="section_not_ok_sensors", scope="module")
def _section_not_ok_sensors() -> ct.Section:
    return ct.parse_cisco_temperature(
        [
            [
                ["1107", "", "TenGigabitEthernet2/1/7 Module Temperature Sensor"],
                ["1110", "", "TenGigabitEthernet2/1/7 Transmit Power Sensor"],
                ["1111", "", "TenGigabitEthernet2/1/7 Receive Power Sensor"],
                ["1129", "", "TenGigabitEthernet1/1/7 Module Temperature Sensor"],
                ["1132", "", "TenGigabitEthernet1/1/7 Transmit Power Sensor"],
                ["1133", "", "TenGigabitEthernet1/1/7 Receive Power Sensor"],
            ],
            [
                ["1107", "8", "9", "1", "245", "3"],
                ["1110", "14", "9", "1", "-19", "3"],
                ["1111", "14", "9", "1", "-47", "3"],
                ["1129", "8", "9", "1", "245", "2"],
                ["1132", "14", "9", "1", "-19", "2"],
                ["1133", "14", "9", "1", "-47", "2"],
            ],
            [],
            [],
            [],
            [],
        ],
    )


@pytest.fixture(name="section_dom", scope="module")
def _get_section_dom() -> ct.Section:
    return ct.parse_cisco_temperature(
        [
            [
                ["300000013", "", "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor"],
                ["300000014", "", "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor"],
                ["300003533", "", "Ethernet1/3 Lane 1 Transceiver Receive Power Sensor"],
                ["300003534", "", "Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor"],
                ["300005293", "", "Ethernet1/4 Lane 1 Transceiver Receive Power Sensor"],
                ["300005294", "", "Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor"],
            ],
            [
                ["300000013", "14", "8", "0", "-3271", "1"],
                ["300000014", "14", "8", "0", "1000", "1"],
                ["300003533", "14", "8", "0", "-2823", "1"],
                ["300003534", "14", "8", "0", "-1000", "1"],
                ["300005293", "14", "8", "0", "-40000", "1"],
                ["300005294", "14", "8", "0", "0", "1"],
            ],
            [
                ["300000013.1", "20", "3", "2000"],
                ["300000013.2", "10", "3", "-1000"],
                ["300000013.3", "20", "1", "-13904"],
                ["300000013.4", "10", "1", "-9901"],
                ["300000014.1", "20", "3", "1699"],
                ["300000014.2", "10", "3", "-1300"],
                ["300000014.3", "20", "1", "-11301"],
                ["300000014.4", "10", "1", "-7300"],
                ["300003533.1", "20", "3", "2000"],
                ["300003533.2", "10", "3", "-1000"],
                ["300003533.3", "20", "1", "-13904"],
                ["300003533.4", "10", "1", "-9901"],
                ["300003534.1", "20", "3", "1699"],
                ["300003534.2", "10", "3", "-1300"],
                ["300003534.3", "20", "1", "-11301"],
                ["300003534.4", "10", "1", "-7300"],
                ["300005293.1", "20", "3", "2000"],
                ["300005293.2", "10", "3", "-1000"],
                ["300005293.3", "20", "1", "-13904"],
                ["300005293.4", "10", "1", "-9901"],
                ["300005294.1", "20", "3", "1699"],
                ["300005294.2", "10", "3", "-1300"],
                ["300005294.3", "20", "1", "-11301"],
                ["300005294.4", "10", "1", "-7300"],
            ],
            [],
            [
                ["20", "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor", "1"],
                ["21", "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor", "1"],
                ["43", "Ethernet1/3 Lane 1 Transceiver Receive Power Sensor", "2"],
                ["44", "Ethernet1/3 Lane 1 Transceiver Transmit Power Sensor", "2"],
                ["70", "Ethernet1/4 Lane 1 Transceiver Receive Power Sensor", "3"],
                ["71", "Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor", "3"],
            ],
            [],
        ]
    )


def test_discovery_dom(section_dom: ct.Section) -> None:
    assert not list(ct.discover_cisco_temperature(section_dom))

    assert sorted(
        ct.discover_cisco_temperature_dom({"admin_states": ["1", "3"]}, section_dom)
    ) == sorted(
        [
            Service(item="Ethernet1/1 Lane 1 Transceiver Receive Power Sensor"),
            Service(item="Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor"),
            Service(item="Ethernet1/4 Lane 1 Transceiver Receive Power Sensor"),
            Service(item="Ethernet1/4 Lane 1 Transceiver Transmit Power Sensor"),
        ]
    )


def test_discovery_not_ok_sensors(section_not_ok_sensors: ct.Section) -> None:
    assert not list(ct.discover_cisco_temperature(section_not_ok_sensors))
    assert not list(
        ct.discover_cisco_temperature_dom({"admin_states": ["1", "3"]}, section_not_ok_sensors)
    )


def test_check_dom_good_default(section_dom: ct.Section) -> None:
    assert list(
        ct.check_cisco_temperature_dom(
            "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor",
            {},
            section_dom,
        )
    ) == [
        Result(state=State.OK, summary="Status: OK"),
        Result(state=State.OK, summary="Signal power: -3.27 dBm"),
        Metric("input_signal_power_dbm", -3.271, levels=(-1.0, 2.0)),
    ]


def test_check_dom_no_levels() -> None:
    assert list(
        ct.check_cisco_temperature_dom(
            "NoLevels",
            {},
            {
                "14": {
                    "NoLevels": {
                        "descr": "",
                        "reading": 3.14,
                        "raw_dev_state": "1",
                        "dev_state": (0, "awesome"),
                        "dev_levels": None,
                    }
                }
            },
        )
    ) == [
        Result(state=State.OK, summary="Status: awesome"),
        Result(state=State.OK, summary="Signal power: 3.14 dBm"),
        Metric("signal_power_dbm", 3.14),
    ]


@pytest.fixture(name="section_temp", scope="module")
def _get_section_temp() -> ct.Section:
    return ct.parse_cisco_temperature(
        [
            [
                ["1176", "", "Filtered sensor"],
                ["1177", "", "Sensor with large precision"],
                ["2008", "", "Switch 1 - WS-C2960X-24PD-L - Sensor 0"],
                ["4950", "", "Linecard-1 Port-1"],
                ["21590", "", "module-1 Crossbar1(s1)"],
                ["21591", "", "module-1 Crossbar2(s2)"],
                ["21592", "", "module-1 Arb-mux (s3)"],
                ["31958", "", "Transceiver(slot:1-port:1)"],
                ["300000003", "", "Ethernet1/1 Lane 1 Transceiver Voltage Sensor"],
                ["300000004", "", "Ethernet1/1 Lane 1 Transceiver Bias Current Sensor"],
                ["300000007", "", "Ethernet1/1 Lane 1 Transceiver Temperature Sensor"],
                ["300000013", "", "Ethernet1/1 Lane 1 Transceiver Receive Power Sensor"],
                ["300000014", "", "Ethernet1/1 Lane 1 Transceiver Transmit Power Sensor"],
            ],
            [
                ["1176", "1", "9", "1613258611", "0", "1"],
                ["1177", "8", "9", "1613258611", "0", "1"],
                ["21590", "8", "9", "0", "62", "1"],
                ["21591", "8", "9", "0", "58", "1"],
                ["21592", "8", "9", "0", "49", "1"],
                ["300000003", "4", "8", "0", "3333", "1"],
                ["300000004", "5", "7", "0", "6002", "1"],
                ["300000007", "8", "8", "0", "24492", "1"],
                ["300000013", "14", "8", "0", "-3271", "1"],
                ["300000014", "14", "8", "0", "1000", "1"],
            ],
            [
                ["21590.1", "10", "4", "115"],
                ["21590.2", "20", "4", "125"],
                ["21591.1", "10", "4", "115"],
                ["21591.2", "20", "4", "125"],
                ["21592.1", "10", "4", "115"],
                ["21592.2", "20", "4", "125"],
                ["300000003.1", "10", "4", "3630"],
                ["300000003.2", "20", "4", "3465"],
                ["300000003.3", "10", "1", "2970"],
                ["300000003.4", "20", "1", "3135"],
                ["300000004.1", "10", "4", "10500"],
                ["300000004.2", "20", "4", "10500"],
                ["300000004.3", "10", "1", "2500"],
                ["300000004.4", "20", "1", "2500"],
                ["300000007.1", "10", "4", "70000"],
                ["300000007.2", "20", "4", "75000"],
                ["300000007.3", "10", "1", "-5000"],
                ["300000007.4", "20", "1", "0"],
                ["300000013.1", "10", "4", "2000"],
                ["300000013.2", "20", "4", "-1000"],
                ["300000013.3", "10", "1", "-13904"],
                ["300000013.4", "20", "1", "-9901"],
                ["300000014.1", "10", "4", "1699"],
                ["300000014.2", "20", "4", "-1300"],
                ["300000014.3", "10", "1", "-11301"],
                ["300000014.4", "20", "1", "-7300"],
            ],
            [
                ["2008", "SW#1, Sensor#1, GREEN", "36", "68", "1"],
                ["3008", "SW#2, Sensor#1, GREEN", "37", "68", "1"],
            ],
            [],
            [],
        ]
    )


def test_discovery_temp(section_temp: ct.Section) -> None:
    assert sorted(ct.discover_cisco_temperature(section_temp)) == sorted(
        [
            Service(item="Sensor with large precision"),
            Service(item="Ethernet1/1 Lane 1 Transceiver Temperature Sensor"),
            Service(item="SW 1 Sensor 1"),
            Service(item="SW 2 Sensor 1"),
            Service(item="module-1 Arb-mux (s3)"),
            Service(item="module-1 Crossbar1(s1)"),
            Service(item="module-1 Crossbar2(s2)"),
        ]
    )


@pytest.mark.usefixtures("initialised_item_state")
def test_check_temp(section_temp: ct.Section) -> None:
    assert list(
        ct.check_cisco_temperature(
            "Ethernet1/1 Lane 1 Transceiver Temperature Sensor", {}, section_temp
        )
    ) == [
        Metric("temp", 24.492, levels=(70.0, 75.0)),
        Result(state=State.OK, summary="Temperature: 24.5 °C"),
        Result(state=State.OK, notice="State on device: OK"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (used device levels)",
        ),
    ]


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["item", "expected_result"],
    [
        pytest.param(
            "TenGigabitEthernet1/1/7 Module Temperature Sensor",
            [Result(state=State.UNKNOWN, notice="Status: unavailable")],
        ),
        pytest.param(
            "TenGigabitEthernet2/1/7 Module Temperature Sensor",
            [Result(state=State.CRIT, notice="Status: non-operational")],
        ),
    ],
)
def test_check_temp_not_ok_sensors(
    item: str, expected_result: CheckResult, section_not_ok_sensors: ct.Section
) -> None:
    assert list(ct.check_cisco_temperature(item, {}, section_not_ok_sensors)) == expected_result


@pytest.mark.usefixtures("initialised_item_state")
@pytest.mark.parametrize(
    ["item", "expected_result"],
    [
        pytest.param(
            "TenGigabitEthernet1/1/7 Transmit Power Sensor",
            [Result(state=State.UNKNOWN, notice="Status: unavailable")],
        ),
        pytest.param(
            "TenGigabitEthernet2/1/7 Transmit Power Sensor",
            [Result(state=State.CRIT, notice="Status: non-operational")],
        ),
    ],
)
def test_check_dom_not_ok_sensors(
    item: str, expected_result: CheckResult, section_not_ok_sensors: ct.Section
) -> None:
    assert list(ct.check_cisco_temperature_dom(item, {}, section_not_ok_sensors)) == expected_result


def test_ensure_invalid_data_is_ignored(as_path: Callable[[str], Path]) -> None:
    input_table = """.1.3.6.1.2.1.1.1.0 Cisco NX-OS(tm) Nexus9000 C93240YC-FX2, Software (NXOS 64-bit), Version 10.2(5), RELEASE SOFTWARE Copyright (c) 2002-2023 by Cisco Systems, Inc. Compiled 3/10/2023 12:00:00
.1.3.6.1.4.1.9.9.91.1.1.1.1.1.38487 8
.1.3.6.1.4.1.9.9.91.1.1.1.1.2.38487 9
.1.3.6.1.4.1.9.9.91.1.1.1.1.3.38487 0
.1.3.6.1.4.1.9.9.91.1.1.1.1.4.38487 inf
.1.3.6.1.4.1.9.9.91.1.1.1.1.5.38487 1
.1.3.6.1.4.1.9.9.91.1.1.1.1.6.38487 554712961
.1.3.6.1.4.1.9.9.91.1.1.1.1.7.38487 60
.1.3.6.1.4.1.9.9.91.1.2.1.1.2.38487.1 10
.1.3.6.1.4.1.9.9.91.1.2.1.1.2.38487.2 20
.1.3.6.1.4.1.9.9.91.1.2.1.1.3.38487.1 4
.1.3.6.1.4.1.9.9.91.1.2.1.1.3.38487.2 4
.1.3.6.1.4.1.9.9.91.1.2.1.1.4.38487.1 70
.1.3.6.1.4.1.9.9.91.1.2.1.1.4.38487.2 80
.1.3.6.1.4.1.9.9.91.1.2.1.1.5.38487.1 2
.1.3.6.1.4.1.9.9.91.1.2.1.1.5.38487.2 2
.1.3.6.1.4.1.9.9.91.1.2.1.1.6.38487.1 1
.1.3.6.1.4.1.9.9.91.1.2.1.1.6.38487.2 1"""
    snmp_walk = as_path(input_table)
    parsed_section = get_parsed_snmp_section(ct.snmp_section_cisco_temperature, snmp_walk)
    assert parsed_section is not None
    value_store: dict = {}
    _ = list(ct._check_cisco_temperature(value_store, "38487", {}, parsed_section))
    assert not value_store

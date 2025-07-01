#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.aix_hacmp_nodes import (
    check_aix_hacmp_nodes,
    inventory_aix_hacmp_nodes,
    parse_aix_hacmp_nodes,
)

# The word "Node" is capitalized
_STRING_TABLE_1 = [
    ["pasv0450"],
    ["pasv0449"],
    ["NODE", "pasv1112:"],
    ["Interfaces", "to", "network", "TEST_net"],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasv0449,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.4",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0159,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.5",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0158,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.9",
    ],
    ["NODE", "pasv0449:"],
    ["Interfaces", "to", "network", "prod_net"],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasv0449,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.4",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0159,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.5",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0158,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.9",
    ],
    ["Interfaces", "to", "network", "TEST_net"],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasv0449,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.4",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0159,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.5",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0158,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.9",
    ],
    ["NODE", "pasv1111:"],
    ["Interfaces", "to", "network", "TEST_net"],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasv0449,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.4",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0159,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.5",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0158,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.9",
    ],
    ["NODE", "pasv0450:"],
    ["Interfaces", "to", "network", "prod_net"],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasv0450,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.15",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0159,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.5",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "pasc0158,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.9",
    ],
]

# The word "Node" is capitalized
_STRING_TABLE_2 = [
    ["sasv0121"],
    ["sasv0122"],
    ["NODE", "sasv0121:"],
    ["Interfaces", "to", "network", "prod_net"],
    [
        "Communication",
        "Interface:",
        "Name",
        "sasv0121,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.10",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "sasc0016,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.13",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "sasc0015,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.12",
    ],
    ["NODE", "sasv0122:"],
    ["Interfaces", "to", "network", "prod_net"],
    [
        "Communication",
        "Interface:",
        "Name",
        "sasv0122,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.11",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "sasc0016,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.13",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "sasc0015,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "1.2.3.12",
    ],
]

# The word "Node" is not capitalized
_STRING_TABLE_3 = [
    ["smaprok01tst"],
    ["trgprok02tst"],
    ["Node", "smaprok01tst"],
    ["Interfaces", "to", "network", "net_ether_01"],
    [
        "Communication",
        "Interface:",
        "Name",
        "smaprok01tst,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "10.0.18.111",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "proktst-s,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "10.0.18.110",
    ],
    ["Node", "trgprok02tst"],
    ["Interfaces", "to", "network", "net_ether_01"],
    [
        "Communication",
        "Interface:",
        "Name",
        "trgprok02tst,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "10.0.18.112",
    ],
    [
        "Communication",
        "Interface:",
        "Name",
        "proktst-s,",
        "Attribute",
        "public,",
        "IP",
        "address",
        "10.0.18.110",
    ],
]


@pytest.mark.parametrize(
    ("string_table", "expected_result"),
    [
        (_STRING_TABLE_1, [Service(item="pasv0450"), Service(item="pasv0449")]),
        (_STRING_TABLE_2, [Service(item="sasv0121"), Service(item="sasv0122")]),
        (_STRING_TABLE_3, [Service(item="smaprok01tst"), Service(item="trgprok02tst")]),
    ],
)
def test_inventory_aix_hacmp_nodes(
    string_table: StringTable,
    expected_result: DiscoveryResult,
) -> None:
    assert list(inventory_aix_hacmp_nodes(parse_aix_hacmp_nodes(string_table))) == expected_result


@pytest.mark.parametrize(
    ("string_table", "item", "expected_result"),
    [
        (
            _STRING_TABLE_1,
            "pasv0450",
            [
                Result(
                    state=State.OK,
                    summary="Network: prod_net, interface: pasv0450, attribute: public, IP: 1.2.3.15, interface: pasc0159, attribute: public, IP: 1.2.3.5, interface: pasc0158, attribute: public, IP: 1.2.3.9",
                )
            ],
        ),
        (
            _STRING_TABLE_2,
            "sasv0122",
            [
                Result(
                    state=State.OK,
                    summary="Network: prod_net, interface: sasv0122, attribute: public, IP: 1.2.3.11, interface: sasc0016, attribute: public, IP: 1.2.3.13, interface: sasc0015, attribute: public, IP: 1.2.3.12",
                )
            ],
        ),
        (
            _STRING_TABLE_3,
            "smaprok01tst",
            [
                Result(
                    state=State.OK,
                    summary="Network: net_ether_01, interface: smaprok01tst, attribute: public, IP: 10.0.18.111, interface: proktst-s, attribute: public, IP: 10.0.18.110",
                )
            ],
        ),
    ],
)
def test_check_aix_hacmp_nodes(
    string_table: StringTable,
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_aix_hacmp_nodes(
                item,
                parse_aix_hacmp_nodes(string_table),
            )
        )
        == expected_result
    )

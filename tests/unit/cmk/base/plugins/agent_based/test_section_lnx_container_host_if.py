#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.agent_based_api.v1 import Result
from cmk.base.plugins.agent_based.lnx_if import check_lnx_if, discover_lnx_if
from cmk.base.plugins.agent_based.section_lnx_container_host_if import parse_lnx_container_host_if
from cmk.base.plugins.agent_based.utils.interfaces import DISCOVERY_DEFAULT_PARAMETERS, Interface

STRING_TABLE = [
    [
        "name\vwlo1",
        "ifindex\v2",
        "ifalias\v",
        "address\v00:00:00:00:00:00",
        "type\v1",
        "carrier\v1",
        "speed\v",
        "rx_bytes\v1469505338",
        "rx_packets\v1401051",
        "rx_errors\v0",
        "rx_dropped\v9074",
        "multicast\v0",
        "tx_bytes\v278775802",
        "tx_packets\v707739",
        "tx_errors\v0",
        "tx_dropped\v0",
        "tx_fifo_errors\v0",
    ],
]

INTERFACE = Interface(
    index="2",
    descr="wlo1",
    alias="wlo1",
    type="6",
    speed=0.0,
    oper_status="1",
    out_qlen=0.0,
    phys_address="\x00\x00\x00\x00\x00\x00",
    oper_status_name="up",
    speed_as_text="",
    group=None,
    node=None,
    admin_status=None,
    extra_info=None,
    in_octets=1469505338.0,
    in_ucast=1401051.0,
    in_mcast=0.0,
    in_bcast=0.0,
    in_discards=9074.0,
    in_errors=0.0,
    out_octets=278775802.0,
    out_ucast=707739.0,
    out_mcast=0.0,
    out_bcast=0.0,
    out_discards=0.0,
    out_errors=0.0,
)


def test_parse_lnx_container_host_if() -> None:
    assert parse_lnx_container_host_if(STRING_TABLE) == ([INTERFACE], {})


def test_discover_lnx_if_default_discovery() -> None:
    """Interfaces are discovered per default if they are UP and not Loopback."""
    discovered_services = list(
        discover_lnx_if(
            params=[DISCOVERY_DEFAULT_PARAMETERS],
            section_lnx_if=([INTERFACE], {}),
            section_bonding=None,
        )
    )
    assert discovered_services
    assert len(discovered_services) == 1
    assert discovered_services[0].item == "2"


def test_check_lnx_if() -> None:
    check_results = list(
        check_lnx_if(item="2", params={}, section_lnx_if=([INTERFACE], {}), section_bonding=None)
    )
    assert check_results
    first_result = check_results[0]
    assert isinstance(first_result, Result)
    assert first_result.summary == "[wlo1]"

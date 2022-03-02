# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple

from .agent_based_api.v1 import check_levels, OIDEnd, register, render, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.ciena_ces import DETECT_CIENA_5171


class ByteTransfer(NamedTuple):
    transmitted: int
    received: int


Section = Mapping[str, ByteTransfer]


def parse_ciena_routing_instance(string_table: StringTable) -> Section:
    """
    >>> from pprint import pprint
    >>> string_table = [['1', '34_MX1to1000_1', '102520', '102904'],
    ... ['2', '3-Default', '', ''],
    ... ['3', '34-Default', '', ''],
    ... ['4', '34_MX1toKDZ_1', '946', '613'],
    ... ['11', '34_MX1to764_1', '459254', '668800'],
    ... ['12', '34_MX1to867_1', '0', '132'],
    ... ['25', '10_scsynergy-steinhoefel_1', '112645', '1061645'],
    ... ['26', '10-Default', '', ''],
    ... ['1004097', 'mz0100tomz0300_1', '', ''],
    ... ['1004098', 'mz0100tomz0300_2', '', ''],
    ... ['1200041', '1/1otu', '', ''],
    ... ['1300043', '2/1.1odu', '', '']]
    >>> pprint(parse_ciena_routing_instance(string_table))
    {'10_scsynergy-steinhoefel_1': ByteTransfer(transmitted=112645, received=1061645),
     '34_MX1to1000_1': ByteTransfer(transmitted=102520, received=102904),
     '34_MX1to764_1': ByteTransfer(transmitted=459254, received=668800),
     '34_MX1to867_1': ByteTransfer(transmitted=0, received=132),
     '34_MX1toKDZ_1': ByteTransfer(transmitted=946, received=613)}

    """
    return {
        item: ByteTransfer(int(transmit), int(receive))
        for oid_end, item, transmit, receive in string_table
        if transmit and receive
    }


def discover_ciena_routing_instance(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_ciena_routing_instance(item: str, section: Section) -> CheckResult:
    if item not in section:
        return

    yield from check_levels(
        value=section[item].transmitted,
        metric_name="if_out_octets",
        render_func=render.iobandwidth,
        boundaries=(0, None),
        label="Transmitted",
    )
    yield from check_levels(
        value=section[item].received,
        metric_name="if_in_octets",
        render_func=render.iobandwidth,
        boundaries=(0, None),
        label="Received",
    )


register.snmp_section(
    name="ciena_routing_instance",
    parse_function=parse_ciena_routing_instance,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1271.2.3.1.2",
        oids=[
            OIDEnd(),
            "2.1.1.2",  # cienaCesPmInstance
            "3.2.2.1.15",  # cienaCesPmBasicTxRxCurrBinTxBytesPerSec
            "3.2.2.1.13",  # cienaCesPmBasicTxRxCurrBinRxBytesPerSec
        ],
    ),
    # According to the customer these oids do not occur on SAOS6 devices
    detect=DETECT_CIENA_5171,
)

register.check_plugin(
    name="ciena_routing_instance",
    service_name="Routing instance %s",
    discovery_function=discover_ciena_routing_instance,
    check_function=check_ciena_routing_instance,
)

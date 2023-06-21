#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Output of vmstat on AIX:
# System configuration: lcpu=8 mem=6144MB ent=4.00
#
# kthr    memory              page              faults              cpu
# ----- -----------  ------------------------ ------------ -----------------------
#  r  b   avm   fre   re  pi  po  fr   sr  cy  in   sy  cs us sy id wa    pc    ec
#  2  1 669941 89605   0   0   0   3   12   0  12  531 240  0  0 99  0  0.02   0.5
#  0  1    2    3      4   5   6   7   8    9  10   11  12 13 14 15 16   17     18


import collections

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import render

VMStatAIX = collections.namedtuple(  # pylint: disable=collections-namedtuple-call
    "VMStatAIX", ["user", "system", "idle", "wait"]
)


def parse_vmstat_aix(info):
    try:
        data = info[0]
        return VMStatAIX(int(data[13]), int(data[14]), int(data[15]), int(data[16]))
    except (IndexError, ValueError):
        return None


def check_vmstat_aix(item, params, parsed):
    if item != "cpuperc":
        return None

    if parsed is None:
        return None

    return (
        0,
        "User: %s, System: %s, Idle: %s, Wait: %s"
        % (
            render.percent(parsed.user),
            render.percent(parsed.system),
            render.percent(parsed.idle),
            render.percent(parsed.wait),
        ),
        [
            ("us", parsed.user),
            ("sy", parsed.system),
            ("id", parsed.idle),
            ("wa", parsed.wait),
        ],
    )


check_info["vmstat_aix"] = LegacyCheckDefinition(
    parse_function=parse_vmstat_aix,
    check_function=check_vmstat_aix,
    service_name="vmstat %s",
)

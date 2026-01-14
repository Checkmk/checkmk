#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY

check_info = {}


def parse_mcafee_emailgateway_av_mcafee(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_mcafee_gateway_generic(info):
    return [(None, {})]


def check_mcafee_emailgateway_av_mcafee(item, params, info):
    eng_version, dat_version, extra_dat_version = info[0]
    return 0, f"Engine version: {eng_version}, DAT version: {dat_version} ({extra_dat_version})"


check_info["mcafee_emailgateway_av_mcafee"] = LegacyCheckDefinition(
    name="mcafee_emailgateway_av_mcafee",
    parse_function=parse_mcafee_emailgateway_av_mcafee,
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.3.6",
        oids=["1", "2", "3"],
    ),
    service_name="AV McAfee",
    discovery_function=discover_mcafee_gateway_generic,
    check_function=check_mcafee_emailgateway_av_mcafee,
)

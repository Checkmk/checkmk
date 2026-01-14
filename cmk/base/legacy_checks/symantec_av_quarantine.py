#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output from agent:
# List of Objects, else Empty


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_symantec_av_quarantine(info):
    return [(None, None)]


def check_symantec_av_quarantine(_no_item, _no_params, info):
    perf = [("objects", len(info))]
    if len(info) > 0:
        return 2, "%d objects in quarantine" % len(info), perf
    return 0, "No objects in quarantine", perf


def parse_symantec_av_quarantine(string_table: StringTable) -> StringTable:
    return string_table


check_info["symantec_av_quarantine"] = LegacyCheckDefinition(
    name="symantec_av_quarantine",
    parse_function=parse_symantec_av_quarantine,
    service_name="AV Quarantine",
    discovery_function=discover_symantec_av_quarantine,
    check_function=check_symantec_av_quarantine,
)

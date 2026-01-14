#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"

# Example output from agent:
# <<<ibm_svc_eventlog:sep(58)>>>
# 588:120404112526:mdiskgrp:6:md07_sas10k::alert:no:989001::Managed Disk Group space warning
# 589:120404112851:mdiskgrp:7:md08_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 590:120404112931:mdiskgrp:8:md09_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 591:120404113001:mdiskgrp:9:md10_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 592:120404113026:mdiskgrp:10:md11_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 593:120404113111:mdiskgrp:11:md12_nlsas7k_1t::alert:no:989001::Managed Disk Group space warning
# 1690:130801070656:drive:59:::alert:no:981020::Managed Disk error count warning threshold met
# 2058:131030112416:drive:42:::alert:no:981020::Managed Disk error count warning threshold met


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_ibm_svc_eventlog(info):
    return [(None, None)]


def check_ibm_svc_eventlog(item, _no_params, info):
    messagecount = 0
    last_err = ""

    for (
        _sequence_number,
        _last_timestamp,
        _object_type,
        _object_id,
        _object_name,
        _copy_id,
        _status,
        _fixed,
        _event_id,
        _error_code,
        description,
        *_,
    ) in info:
        messagecount += 1
        last_err = description

    if messagecount > 0:
        return 1, "%d messages not expired and not yet fixed found in event log, last was: %s" % (
            messagecount,
            last_err,
        )

    return 0, "No messages not expired and not yet fixed found in event log"


def parse_ibm_svc_eventlog(string_table: StringTable) -> StringTable:
    return string_table


check_info["ibm_svc_eventlog"] = LegacyCheckDefinition(
    name="ibm_svc_eventlog",
    parse_function=parse_ibm_svc_eventlog,
    service_name="Eventlog",
    discovery_function=discover_ibm_svc_eventlog,
    check_function=check_ibm_svc_eventlog,
)

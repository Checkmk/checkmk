#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Developed by Thorsten Bruhns from OPITZ CONSULTING Deutschland GmbH

# <<<oracle_crs_voting>>>
# 1. ONLINE   0a6884c063904f50bf7ef4516b728a2d (/dev/oracleasm/disks/DATA1) [DATA1]


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Result,
    Service,
    State,
    StringTable,
)


def inventory_oracle_crs_voting(section: StringTable) -> DiscoveryResult:
    if section:
        yield Service()


def check_oracle_crs_voting(section: StringTable) -> CheckResult:
    # state = -1 => no data for Service
    infotext = ""
    votecount = 0
    votedisk = ""
    for line in section:
        if line[1] == "ONLINE":
            votecount += 1
            votedisk += "[%s] " % line[3]
        elif len(line) == 3:
            votecount += 1
            votedisk += "[%s] " % line[2]

    if votecount in (1, 3, 5):
        infotext = "%d Voting Disks found. %s" % (votecount, votedisk)
        yield Result(state=State.OK, summary=infotext)
        return

    if votecount == 0:
        # cssd could not start without an existing voting disk!
        raise IgnoreResultsError("No Voting Disk(s) found. Maybe the cssd/crsd is not running!")

    infotext = "missing Voting Disks (!!). %d Votes found %s" % (votecount, votedisk)
    yield Result(state=State.CRIT, summary=infotext)


def parse_oracle_crs_voting(string_table: StringTable) -> StringTable:
    return string_table


agent_section_oracle_crs_voting = AgentSection(
    name="oracle_crs_voting",
    parse_function=parse_oracle_crs_voting,
)

check_plugin_oracle_crs_voting = CheckPlugin(
    name="oracle_crs_voting",
    service_name="ORA-GI Voting",
    discovery_function=inventory_oracle_crs_voting,
    check_function=check_oracle_crs_voting,
)

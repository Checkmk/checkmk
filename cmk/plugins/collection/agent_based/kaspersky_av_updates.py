#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# Example output from agent:
# Current AV databases date:     2014-05-27 03:54:00
# Last AV databases update date: 2014-05-27 09:00:40
# Current AV databases state:    UpToDate
# Current AV databases records:  8015301
# Update attempts:               48616
# Successful updates:            9791
# Update manual stops:           0
# Updates failed:                3333


from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)

Section = dict[str, str]


def parse_kaspersky_av_updates(string_table: StringTable) -> Section:
    """
    >>> parse_kaspersky_av_updates([["Current AV databases state", "    UpToDate"]])
    {'Current AV databases state': 'UpToDate'}
    """
    return {line[0]: ":".join(line[1:]).strip() for line in string_table}


agent_section_kaspersky_av_updates = AgentSection(
    name="kaspersky_av_updates",
    parse_function=parse_kaspersky_av_updates,
)


def discover_kaspersky_av_updates(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_kaspersky_av_updates(section: Section) -> CheckResult:
    yield Result(
        state=State.CRIT if section["Current AV databases state"] != "UpToDate" else State.OK,
        summary=f"Database State: {section['Current AV databases state']}",
    )
    yield Result(state=State.OK, summary=f"Database Date: {section['Current AV databases date']}")
    yield Result(state=State.OK, summary=f"Last Update: {section['Last AV databases update date']}")


check_plugin_kaspersky_av_updates = CheckPlugin(
    name="kaspersky_av_updates",
    service_name="AV Update Status",
    discovery_function=discover_kaspersky_av_updates,
    check_function=check_kaspersky_av_updates,
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
# Name:                                       Kaspersky Endpoint Security 10 SP1 for Linux
# Version:                                    10.1.0.5960
# Key status:                                 Valid
# License expiration date:                    2019-07-09
# Storage state:                              No time limit for objects in Storage
# Storage space usage:                        Storage size is unlimited
# Last run date of the Scan_My_Computer task: Never run
# Last release date of databases:             2018-08-23 04:11:00
# Anti-virus databases loaded:                Yes
# Anti-virus database records:                11969941
# KSN state:                                  Off
# File monitoring:                            Available and stopped
# Integrity monitoring:                       Unavailable due to license limitation
# Firewall Management:                        Available and stopped
# Anti-Cryptor:                               Available and stopped
# Application update state:                   No application updates available

import time

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

Section = dict[str, str]


def parse_kaspersky_av_kesl_updates(string_table: StringTable) -> Section:
    """
    >>> parse_kaspersky_av_kesl_updates([
    ...     ["Anti-virus databases loaded", "Yes"],
    ...     ["Last release date of databases", "1970-01-01 00:00:00"],
    ...     ["Anti-virus database recores", "1"],
    ... ])
    {'Anti-virus databases loaded': 'Yes', 'Last release date of databases': '1970-01-01 00:00:00', 'Anti-virus database recores': '1'}
    """
    return {line[0]: "|".join(line[1:]) for line in string_table}


agent_section_kaspersky_av_kesl_updates = AgentSection(
    name="kaspersky_av_kesl_updates",
    parse_function=parse_kaspersky_av_kesl_updates,
)


def discover_kaspersky_av_kesl_updates(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_kaspersky_av_kesl_updates(section: Section) -> CheckResult:
    loaded = section["Anti-virus databases loaded"] == "Yes"
    yield Result(state=State.OK if loaded else State.CRIT, summary=f"Databases loaded: {loaded}")
    db_release_date = time.mktime(
        time.strptime(section["Last release date of databases"], "%Y-%m-%d %H:%M:%S")
    )
    yield Result(state=State.OK, summary=f"Database date: {render.datetime(db_release_date)}")
    yield Result(
        state=State.OK, summary=f"Database records: {section['Anti-virus database records']}"
    )


check_plugin_kaspersky_av_kesl_updates = CheckPlugin(
    name="kaspersky_av_kesl_updates",
    service_name="AV Update Status",
    discovery_function=discover_kaspersky_av_kesl_updates,
    check_function=check_kaspersky_av_kesl_updates,
)

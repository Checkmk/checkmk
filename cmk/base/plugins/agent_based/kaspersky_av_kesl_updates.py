#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from agent:
#Name:                                       Kaspersky Endpoint Security 10 SP1 for Linux
#Version:                                    10.1.0.5960
#Key status:                                 Valid
#License expiration date:                    2019-07-09
#Storage state:                              No time limit for objects in Storage
#Storage space usage:                        Storage size is unlimited
#Last run date of the Scan_My_Computer task: Never run
#Last release date of databases:             2018-08-23 04:11:00
#Anti-virus databases loaded:                Yes
#Anti-virus database records:                11969941
#KSN state:                                  Off
#File monitoring:                            Available and stopped
#Integrity monitoring:                       Unavailable due to license limitation
#Firewall Management:                        Available and stopped
#Anti-Cryptor:                               Available and stopped
#Application update state:                   No application updates available

import time

from .agent_based_api.v1 import register, render, Service, Result, State


def parse_kaspersky_av_kesl_updates(string_table):
    return dict(string_table)


register.agent_section(
    name="kaspersky_av_kesl_updates",
    parse_function=parse_kaspersky_av_kesl_updates,
)


def discover_kaspersky_av_kesl_updates(section):
    yield Service()


def check_kaspersky_av_kesl_updates(section):
    loaded = section['Anti-virus databases loaded'] == 'Yes'
    yield Result(state=State.OK if loaded else State.CRIT, summary=f"Databases loaded: {loaded}")
    db_release_date = time.mktime(
        time.strptime(section['Last release date of databases'], "%Y-%m-%d %H:%M:%S"))
    yield Result(state=State.OK, summary=f"Database date: {render.datetime(db_release_date)}")
    yield Result(state=State.OK,
                 summary=f"Database records: {section['Anti-virus database records']}")


register.check_plugin(
    name="kaspersky_av_kesl_updates",
    service_name="AV Update Status",
    discovery_function=discover_kaspersky_av_kesl_updates,
    check_function=check_kaspersky_av_kesl_updates,
)

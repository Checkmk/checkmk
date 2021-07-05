#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<kaspersky_av_client>>>
# Signatures 08.05.2015 01:23:00
# Fullscan 08.05.2015 05:43:16 0

# <<<kaspersky_av_client>>>
# Signatures 13.12.2016 11:55:00

import time

from .agent_based_api.v1 import register, Service, State, Result, render


def parse_kaspersky_av_client(string_table):
    return _parse_kaspersky_av_client(string_table, now=time.time())


def _parse_kaspersky_av_client(string_table, now):
    """
    # Set up timezone to make doctests reproducable.
    >>> import os
    >>> os.environ["TZ"] = "0"

    >>> _parse_kaspersky_av_client([["Signatures", "01.01.1970"]], now=0)
    {'signature_age': 0.0}
    """
    parsed = {}

    for line in string_table:
        if line[1] == 'Missing':
            continue

        date_text = line[1]
        time_text = line[2] if len(line) > 2 else "00:00:00"
        # We assume that the timestamp is to be interpreted in the timezone of
        # the Checkmk server. This might be a problem, if e.g. the agent is located
        # in China and the Checkmk server in USA.
        age = now - time.mktime(time.strptime(f"{date_text} {time_text}", '%d.%m.%Y %H:%M:%S'))

        if line[0] == "Signatures":
            parsed['signature_age'] = age

        elif line[0] == "Fullscan":
            parsed['fullscan_age'] = age

            # handle state of last fullscan if provided
            if len(line) == 4:
                parsed['fullscan_failed'] = line[3] != "0"

    return parsed


register.agent_section(
    name="kaspersky_av_client",
    parse_function=parse_kaspersky_av_client,
)


def discover_kaspersky_av_client(section):
    if section:
        yield Service()


def check_kaspersky_av_client(params, section):
    for key, what in [
        ("signature_age", "Last update of signatures"),
        ("fullscan_age", "Last fullscan"),
    ]:
        age = section.get(key)
        if age is None:
            yield Result(state=State.UNKNOWN, summary=f"{what} unkown")
        else:
            warn, crit = params[key]
            if age >= crit:
                state = State.CRIT
            elif age >= warn:
                state = State.WARN
            else:
                state = State.OK

            infotext = "%s %s ago" % (what, render.timespan(age))
            if state in (State.CRIT, State.WARN):
                infotext += " (warn/crit at %s/%s)" % (render.timespan(warn), render.timespan(crit))

            yield Result(state=state, summary=infotext)

    if section.get("fullscan_failed"):
        yield Result(state=State.CRIT, summary="Last fullscan failed")


register.check_plugin(
    name="kaspersky_av_client",
    service_name="Kaspersky AV",
    discovery_function=discover_kaspersky_av_client,
    check_function=check_kaspersky_av_client,
    check_default_parameters={
        'signature_age': (86400, 7 * 86400),
        'fullscan_age': (86400, 7 * 86400),
    },
    check_ruleset_name="kaspersky_av_client",
)

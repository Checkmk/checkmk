#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.domino import DETECT

check_info = {}

MAILQUEUES_LABEL = (
    ("lnDeadMail", "Dead mails"),
    ("lnWaitingMail", "Waiting mails"),
    ("lnMailHold", "Mails on hold"),
    ("lnMailTotalPending", "Total pending mails"),
    ("InMailWaitingforDNS", "Mails waiting for DNS"),
)


def parse_domino_mailqueues(string_table):
    if not string_table:
        return {}

    return {
        item: (label, int(raw_value))
        for (item, label), raw_value in zip(MAILQUEUES_LABEL, string_table[0])
    }


def check_domino_mailqueues(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    label, value = data
    yield check_levels(
        value,
        "mails",
        params.get("queue_length"),
        infoname=label,
        human_readable_func=lambda d: "%d" % int(d),
    )


def discover_domino_mailqueues(section):
    yield from ((item, {}) for item in section)


check_info["domino_mailqueues"] = LegacyCheckDefinition(
    name="domino_mailqueues",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.4",
        oids=["1", "6", "21", "31", "34"],
    ),
    parse_function=parse_domino_mailqueues,
    service_name="Domino Queue %s",
    discovery_function=discover_domino_mailqueues,
    check_function=check_domino_mailqueues,
    check_ruleset_name="domino_mailqueues",
    check_default_parameters={"queue_length": (300, 350)},
)

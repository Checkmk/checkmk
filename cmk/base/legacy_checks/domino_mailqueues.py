#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, discover, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.domino import DETECT

MAILQUEUES_LABEL = (
    ("lnDeadMail", "Dead mails"),
    ("lnWaitingMail", "Waiting mails"),
    ("lnMailHold", "Mails on hold"),
    ("lnMailTotalPending", "Total pending mails"),
    ("InMailWaitingforDNS", "Mails waiting for DNS"),
)


def parse_domino_mailqueues(info):
    if not info:
        return {}

    return {
        item: (label, int(raw_value)) for (item, label), raw_value in zip(MAILQUEUES_LABEL, info[0])
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


check_info["domino_mailqueues"] = LegacyCheckDefinition(
    detect=DETECT,
    parse_function=parse_domino_mailqueues,
    discovery_function=discover(),
    check_function=check_domino_mailqueues,
    service_name="Domino Queue %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.4",
        oids=["1", "6", "21", "31", "34"],
    ),
    check_ruleset_name="domino_mailqueues",
    check_default_parameters={"queue_length": (300, 350)},
)

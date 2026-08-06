#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.domino.lib import DETECT
from cmk.rulesets.v1.form_specs import SimpleLevelsConfigModel

MAILQUEUES_LABEL = (
    ("lnDeadMail", "Dead mails"),
    ("lnWaitingMail", "Waiting mails"),
    ("lnMailHold", "Mails on hold"),
    ("lnMailTotalPending", "Total pending mails"),
    ("InMailWaitingforDNS", "Mails waiting for DNS"),
)

Section = Mapping[str, tuple[str, int]]


class DominoMailqueuesParams(TypedDict):
    queue_length: SimpleLevelsConfigModel[int]


def parse_domino_mailqueues(string_table: StringTable) -> Section:
    if not string_table:
        return {}

    return {
        item: (label, int(raw_value))
        for (item, label), raw_value in zip(MAILQUEUES_LABEL, string_table[0])
    }


def check_domino_mailqueues(
    item: str, params: DominoMailqueuesParams, section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return
    label, value = data
    yield from check_levels(
        value,
        levels_upper=params["queue_length"],
        metric_name="mails",
        render_func=lambda d: "%d" % int(d),
        label=label,
    )


def discover_domino_mailqueues(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_domino_mailqueues = SimpleSNMPSection(
    name="domino_mailqueues",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.334.72.1.1.4",
        oids=["1", "6", "21", "31", "34"],
    ),
    parse_function=parse_domino_mailqueues,
)


check_plugin_domino_mailqueues = CheckPlugin(
    name="domino_mailqueues",
    service_name="Domino Queue %s",
    discovery_function=discover_domino_mailqueues,
    check_function=check_domino_mailqueues,
    check_ruleset_name="domino_mailqueues",
    check_default_parameters=DominoMailqueuesParams(queue_length=("fixed", (300, 350))),
)

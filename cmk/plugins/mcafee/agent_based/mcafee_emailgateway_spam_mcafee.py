#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY


def parse_mcafee_emailgateway_spam_mcafee(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_mcafee_emailgateway_spam_mcafee(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_mcafee_emailgateway_spam_mcafee(section: StringTable) -> CheckResult:
    eng_version, rules_version = section[0]
    yield Result(
        state=State.OK,
        summary=f"Engine version: {eng_version}, Rules version: {rules_version}",
    )


snmp_section_mcafee_emailgateway_spam_mcafee = SimpleSNMPSection(
    name="mcafee_emailgateway_spam_mcafee",
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.3.6",
        oids=["10", "11"],
    ),
    parse_function=parse_mcafee_emailgateway_spam_mcafee,
)


check_plugin_mcafee_emailgateway_spam_mcafee = CheckPlugin(
    name="mcafee_emailgateway_spam_mcafee",
    service_name="Spam McAfee",
    discovery_function=discover_mcafee_emailgateway_spam_mcafee,
    check_function=check_mcafee_emailgateway_spam_mcafee,
)

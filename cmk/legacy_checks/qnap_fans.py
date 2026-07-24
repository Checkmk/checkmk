#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.fan import check_fan
from cmk.plugins.qnap.lib import DETECT_QNAP


def parse_qnap_fans(string_table: StringTable) -> Mapping[str, int]:
    parsed: dict[str, int] = {}
    for fan, value in string_table:
        with contextlib.suppress(ValueError):
            parsed[fan] = int(value.replace("RPM", ""))
    return parsed


def check_qnap_fans(
    item: str, params: Mapping[str, Any], section: Mapping[str, int]
) -> CheckResult:
    if not (data := section.get(item)):
        return
    yield from check_fan(data, params)


def discover_qnap_fans(section: Mapping[str, int]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


snmp_section_qnap_fans = SimpleSNMPSection(
    name="qnap_fans",
    detect=DETECT_QNAP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.24681.1.2.15.1",
        oids=[OIDEnd(), "3"],
    ),
    parse_function=parse_qnap_fans,
)


check_plugin_qnap_fans = CheckPlugin(
    name="qnap_fans",
    service_name="QNAP FAN %s",
    discovery_function=discover_qnap_fans,
    check_function=check_qnap_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (2000, 1000),
    },
)

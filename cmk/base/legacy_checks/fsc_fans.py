#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, exists, not_exists, SNMPTree, startswith
from cmk.base.check_legacy_includes.fan import check_fan

check_info = {}


def parse_fsc_fans(string_table):
    parsed = {}
    for fan_name, rpm_str in string_table:
        try:
            rpm = int(rpm_str)
        except ValueError:
            continue
        parsed.setdefault(fan_name, rpm)
    return parsed


def discover_fsc_fans(parsed):
    return [(fan_name, {}) for fan_name in parsed]


def check_fsc_fans(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    if isinstance(params, tuple):
        params = {"lower": params}
    yield check_fan(data, params)


check_info["fsc_fans"] = LegacyCheckDefinition(
    name="fsc_fans",
    detect=all_of(
        all_of(
            any_of(
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.231"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.311"),
                startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072"),
            ),
            exists(".1.3.6.1.4.1.231.2.10.2.1.1.0"),
        ),
        not_exists(".1.3.6.1.4.1.231.2.10.2.2.10.5.2.1.3.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.231.2.10.2.2.5.2.2.1",
        oids=["16", "8"],
    ),
    parse_function=parse_fsc_fans,
    service_name="FSC %s",
    discovery_function=discover_fsc_fans,
    check_function=check_fsc_fans,
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "lower": (2000, 1000),
    },
)

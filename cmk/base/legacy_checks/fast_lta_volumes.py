#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import all_of, any_of, exists, SNMPTree, startswith

check_info = {}


def parse_fast_lta_volumes(string_table):
    parsed = {}
    for volname, volquota, volused in string_table:
        try:
            size_mb = int(volquota) / 1048576.0
            avail_mb = (int(volquota) - int(volused)) / 1048576.0
        except ValueError:
            continue
        parsed.setdefault(volname, []).append((volname, size_mb, avail_mb, 0))

    return parsed


def check_fast_lta_volumes(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield df_check_filesystem_list(item, params, data)


def discover_fast_lta_volumes(section):
    yield from ((item, {}) for item in section)


check_info["fast_lta_volumes"] = LegacyCheckDefinition(
    name="fast_lta_volumes",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.8072.3.2.10"),
        any_of(exists(".1.3.6.1.4.1.27417.5.1.1.2"), exists(".1.3.6.1.4.1.27417.5.1.1.2.0")),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.27417.5.1.1",
        oids=["2", "9", "11"],
    ),
    parse_function=parse_fast_lta_volumes,
    service_name="Fast LTA Volume %s",
    discovery_function=discover_fast_lta_volumes,
    check_function=check_fast_lta_volumes,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)

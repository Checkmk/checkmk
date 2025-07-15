#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.emcvnx import preparse_emcvnx_info

check_info = {}


def parse_emcvnx_agent(string_table):
    return preparse_emcvnx_info(string_table)


def inventory_emcvnx_agent(parsed):
    output, _errors = parsed
    if output:
        return [(None, None)]
    return []


def check_emcvnx_agent(item, _no_params, parsed):
    output, errors = parsed
    for line in errors:
        # Only handle real errors here not e.g. certificate errors handled by
        # the info check.
        if line.startswith("Error"):
            yield 2, line

    for key, value in output:
        yield 0, f"{key}: {value}"


check_info["emcvnx_agent"] = LegacyCheckDefinition(
    name="emcvnx_agent",
    parse_function=parse_emcvnx_agent,
    service_name="EMC VNX Agent",
    discovery_function=inventory_emcvnx_agent,
    check_function=check_emcvnx_agent,
)

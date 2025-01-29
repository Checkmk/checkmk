#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.elphase import check_elphase

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.plugins.lib.apc import DETECT

check_info = {}

# .1.3.6.1.4.1.318.1.1.1.4.2.1.0 231
# .1.3.6.1.4.1.318.1.1.1.4.2.4.0
# .1.3.6.1.4.1.318.1.1.1.4.2.3.0 37


def parse_apc_symmetra_output(string_table):
    if not string_table:
        return {}

    data = {}
    for key, value_str in zip(["voltage", "current", "output_load"], string_table[0]):
        try:
            value = float(value_str)
        except ValueError:
            continue
        else:
            data.setdefault("Output", {})
            data["Output"].setdefault(key, value)
    return data


def discover_apc_symmetra_output(section):
    yield from ((item, {}) for item in section)


check_info["apc_symmetra_output"] = LegacyCheckDefinition(
    name="apc_symmetra_output",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.1.4.2",
        oids=["1", "4", "3"],
    ),
    parse_function=parse_apc_symmetra_output,
    service_name="Phase %s",
    discovery_function=discover_apc_symmetra_output,
    check_function=check_elphase,
    check_ruleset_name="ups_outphase",
    check_default_parameters={
        "voltage": (220, 220),
    },
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v1 import (
    check_levels as check_levels_v1,  # we can only use v2 after migrating the ruleset!
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
)
from cmk.plugins.liebert.agent_based.lib import DETECT_LIEBERT, parse_liebert_float, Section

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5298.1 Pump Hours
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5298.2 Pump Hours
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5298.1 3423
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5298.2 1
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5298.1 hr
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5298.2 hr
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5299.1 Pump Hours Threshold
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5299.2 Pump Hours Threshold
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5299.1 32000
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5299.2 32000
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5299.1 hr
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5299.2 hr


def discover_liebert_pump(section: Section[float]) -> DiscoveryResult:
    yield from (Service(item=item) for item in section if "threshold" not in item.lower())


def check_liebert_pump(item: str, section: Section[float]) -> CheckResult:
    try:
        value, unit = section[item]
    except KeyError:
        return

    # TODO: this should be done in the parse function, per OID end.
    threshold = None
    for key, (t_value, _unit) in section.items():
        if "Threshold" in key and key.replace(" Threshold", "") == item:
            threshold = t_value

    yield from check_levels_v1(
        value,
        levels_upper=None if threshold is None else (threshold, threshold),
        render_func=lambda x: f"{x:.2f} {unit}",
    )


snmp_section_liebert_pump = SimpleSNMPSection(
    name="liebert_pump",
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=[
            "10.1.2.1.5298",
            "20.1.2.1.5298",
            "30.1.2.1.5298",
            "10.1.2.1.5299",
            "20.1.2.1.5299",
            "30.1.2.1.5299",
        ],
    ),
    parse_function=parse_liebert_float,
)
check_plugin_liebert_pump = CheckPlugin(
    name="liebert_pump",
    service_name="%s",
    discovery_function=discover_liebert_pump,
    check_function=check_liebert_pump,
)

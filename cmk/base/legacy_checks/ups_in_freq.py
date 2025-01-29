#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.lib.ups import DETECT_UPS_GENERIC

check_info = {}


def parse_ups_in_freq(string_table):
    parsed = {}
    for name, freq_str in string_table:
        try:
            freq = int(freq_str) / 10.0
        except ValueError:
            freq = None
        parsed.setdefault(name, freq)
    return parsed


def discover_ups_in_freq(parsed):
    yield from ((item, {}) for item, freq in parsed.items() if freq is not None and freq > 0)


def check_ups_in_freq(item, params, parsed):
    freq = parsed.get(item)
    if freq is None:
        return None

    infotext = "%.1f Hz" % freq
    state = 0
    warn, crit = params["levels_lower"]
    if freq < crit:
        state = 2
    elif freq < warn:
        state = 1
    if state:
        infotext += f" (warn/crit below {warn} Hz/{crit} Hz)"
    return state, infotext, [("in_freq", freq, warn, crit, 30, 70)]


check_info["ups_in_freq"] = LegacyCheckDefinition(
    name="ups_in_freq",
    detect=DETECT_UPS_GENERIC,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.3.3.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=parse_ups_in_freq,
    service_name="IN frequency phase %s",
    discovery_function=discover_ups_in_freq,
    check_function=check_ups_in_freq,
    check_ruleset_name="efreq",
    check_default_parameters={"levels_lower": (45, 40)},
)

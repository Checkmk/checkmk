#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.ups import DETECT_UPS_GENERIC

factory_settings["ups_in_freq_default_levels"] = {"levels_lower": (45, 40)}


def parse_ups_in_freq(info):
    parsed = {}
    for name, freq_str in info:
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
        infotext += " (warn/crit below %s Hz/%s Hz)" % (warn, crit)
    return state, infotext, [("in_freq", freq, warn, crit, 30, 70)]


check_info["ups_in_freq"] = {
    "detect": DETECT_UPS_GENERIC,
    "parse_function": parse_ups_in_freq,
    "discovery_function": discover_ups_in_freq,
    "check_function": check_ups_in_freq,
    "service_name": "IN frequency phase %s",
    "check_ruleset_name": "efreq",
    "fetch": SNMPTree(
        base=".1.3.6.1.2.1.33.1.3.3.1",
        oids=[OIDEnd(), "2"],
    ),
    "default_levels_variable": "ups_in_freq_default_levels",
}

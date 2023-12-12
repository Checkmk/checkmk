#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.liebert import DETECT_LIEBERT, parse_liebert_float

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5266.1 Compressor Head Pressure
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5266.2 Compressor Head Pressure
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5266.3 Compressor Head Pressure
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5266.4 Compressor Head Pressure
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5266.1 5.9
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5266.2 Unavailable
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5266.3 6.1
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5266.4 0.0
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5266.1 bar
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5266.2 bar
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5266.3 bar
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5266.4 bar


def check_liebert_compressor(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_levels(data[0], None, params["levels"], unit=data[1], infoname="Head pressure")


def discover_liebert_compressor(section):
    yield from ((item, {}) for item in section)


check_info["liebert_compressor"] = LegacyCheckDefinition(
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5266", "20.1.2.1.5266", "30.1.2.1.5266"],
    ),
    parse_function=parse_liebert_float,
    service_name="%s",
    discovery_function=discover_liebert_compressor,
    check_function=check_liebert_compressor,
    check_default_parameters={
        "levels": (8, 12),
    },
)

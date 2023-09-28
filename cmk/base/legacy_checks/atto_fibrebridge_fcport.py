#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    get_rate,
    get_value_store,
    OIDEnd,
    SNMPTree,
    startswith,
)


def inventory_atto_fibrebridge_fcport(info):
    for line in info:
        yield line[0], {}


def check_atto_fibrebridge_fcport(item, params, info):
    now = time.time()
    for line in info:
        if line[0] == item:
            fc_tx_words = get_rate(get_value_store(), "tx", now, int(line[1]), raise_overflow=True)
            fc_rx_words = get_rate(get_value_store(), "rx", now, int(line[2]), raise_overflow=True)

    if not params["fc_tx_words"]:
        yield 0, "TX: %.2f words/s" % fc_tx_words, [("fc_tx_words", fc_tx_words)]
    else:
        yield check_levels(fc_tx_words, "fc_tx_words", params["fc_tx_words"], infoname="TX")

    if not params["fc_rx_words"]:
        yield 0, "RX: %.2f words/s" % fc_rx_words, [("fc_rx_words", fc_rx_words)]
    else:
        yield check_levels(fc_rx_words, "fc_rx_words", params["fc_rx_words"], infoname="RX")


check_info["atto_fibrebridge_fcport"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4547"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4547.2.3.3.2.1",
        oids=[OIDEnd(), "2", "3"],
    ),
    service_name="FC Port %s",
    discovery_function=inventory_atto_fibrebridge_fcport,
    check_function=check_atto_fibrebridge_fcport,
    check_ruleset_name="fcport_words",
    check_default_parameters={
        "fc_tx_words": None,
        "fc_rx_words": None,
    },
)

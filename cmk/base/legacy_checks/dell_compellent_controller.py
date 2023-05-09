#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes import dell_compellent
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.dell import DETECT_DELL_COMPELLENT

# example output
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.2.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.2.2 2
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.3.1 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.3.2 1
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.4.1 "Controller A"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.4.2 "Controller B"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.5.1 "10.20.30.41"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.5.2 "10.20.30.42"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.7.1 "CT_SC4020"
# .1.3.6.1.4.1.674.11000.2000.500.1.2.13.1.7.2 "CT_SC4020"


def check_dell_compellent_controller(item, _no_params, info):
    for number, status, name, addr, model in info:
        if number == item:
            state, state_readable = dell_compellent.dev_state_map(status)
            yield state, "Status: %s" % state_readable
            yield 0, "Model: %s, Name: %s, Address: %s" % (model, name, addr)


check_info["dell_compellent_controller"] = {
    "detect": DETECT_DELL_COMPELLENT,
    "discovery_function": dell_compellent.discover,
    "check_function": check_dell_compellent_controller,
    "service_name": "Controller %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.674.11000.2000.500.1.2.13.1",
        oids=["2", "3", "4", "5", "7"],
    ),
}

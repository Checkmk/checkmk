#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ibm_mq import is_ibm_mq_service_vanished

check_info = {}

# <<<ibm_mq_channels:sep(10)>>>
# QMNAME(MY.TEST)                                           STATUS(RUNNING)
# 5724-H72 (C) Copyright IBM Corp. 1994, 2015.
# Starting MQSC for queue manager MY.TEST.
#
# AMQ8414: Display Channel details.
#    CHANNEL(MY.SENDER.ONE)                  CHLTYPE(SDR)
#    XMITQ(MY.SENDER.ONE.XMIT)
# AMQ8417: Display Channel Status details.
#    CHANNEL(MY.SENDER.ONE)                  CHLTYPE(SDR)
#    CONNAME(99.999.999.999(1414),44.555.666.777(1414))
#    CURRENT                                 RQMNAME( )
#    STATUS(RETRYING)                        SUBSTATE( )
#    XMITQ(MY.SENDER.ONE.XMIT)
# 3 MQSC commands read.
# No commands have a syntax error.
# One valid MQSC command could not be processed.

_DEFAULT_STATUS_MAP = {
    "INACTIVE": ("inactive", 0),
    "INITIALIZING": ("initializing", 0),
    "BINDING": ("binding", 0),
    "STARTING": ("starting", 0),
    "RUNNING": ("running", 0),
    "RETRYING": ("retrying", 1),
    "STOPPING": ("stopping", 0),
    "STOPPED": ("stopped", 2),
}


def map_ibm_mq_channel_status(status, params):
    wato_key, check_state = _DEFAULT_STATUS_MAP.get(status, ("unknown", 3))
    if "mapped_states" in params:
        mapped_states = dict(params["mapped_states"])
        if wato_key in mapped_states:
            check_state = mapped_states[wato_key]
        elif "mapped_states_default" in params:
            check_state = params["mapped_states_default"]
    return check_state


def inventory_ibm_mq_channels(parsed):
    for service_name in parsed:
        if ":" not in service_name:
            # Do not show queue manager entry in inventory
            continue
        yield service_name, {}


#
# See http://www-01.ibm.com/support/docview.wss?uid=swg21667353
# or search for 'inactive channels' in 'display chstatus' command manual
# to learn more about INACTIVE status of channels
#
def check_ibm_mq_channels(item, params, parsed):
    if is_ibm_mq_service_vanished(item, parsed):
        return
    data = parsed[item]
    status = data.get("STATUS", "INACTIVE")
    check_state = map_ibm_mq_channel_status(status, params)
    chltype = data.get("CHLTYPE")
    infotext = f"Status: {status}, Type: {chltype}"
    if "XMITQ" in data:
        infotext += ", Xmitq: %s" % data["XMITQ"]
    yield check_state, infotext, []


check_info["ibm_mq_channels"] = LegacyCheckDefinition(
    name="ibm_mq_channels",
    service_name="IBM MQ Channel %s",
    discovery_function=inventory_ibm_mq_channels,
    check_function=check_ibm_mq_channels,
    check_ruleset_name="ibm_mq_channels",
)

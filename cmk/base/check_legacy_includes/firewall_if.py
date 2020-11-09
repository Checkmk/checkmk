#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import RAISE
import time
from cmk.base.check_api import get_average
from cmk.base.check_api import get_rate
from cmk.base.check_api import check_levels
from cmk.base.check_api import get_parsed_item_data


@get_parsed_item_data
def check_firewall_if(item, params, data):

    infotext_names = {
        "ip4_in_blocked": "Incoming IPv4 packets blocked: ",
    }

    this_time = time.time()

    for what, counter in data.items():
        rate = get_rate("firewall_if-%s.%s" % (what, item), this_time, counter, onwrap=RAISE)

        if params.get("averaging"):
            backlog_minutes = params["averaging"]
            avgrate = get_average("firewall_if-%s.%s" % (what, item), this_time, rate,
                                  backlog_minutes)
            check_against = avgrate
        else:
            check_against = rate

        status, infotext, extraperf = check_levels(check_against,
                                                   what,
                                                   params.get(what),
                                                   human_readable_func=lambda x: "%.2f pkts/s" % x,
                                                   infoname=infotext_names[what])

        perfdata = [(what, rate)] + extraperf[:1]

        yield status, infotext, perfdata

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
from cmk.base.check_api import check_levels

# Item is a user defined identifier of the connection.
# Example for params:
# {
#    "proto"       : "UDP",
#    "local_ip"    : "10.1.1.99",
#    "remote_port" : 5665,
#    "state"       : "ESTABLISHED",
# }
# Other keys: local_port, remote_ip. Missing entries do not care.


def check_netstat_generic(item, params, connections):
    found = 0
    for proto, (local_ip, local_port), (remote_ip, remote_port), connstate in connections:
        # Beware: port numbers are strings here.
        match = True
        for k, v in [
            ("local_ip", local_ip),
            ("local_port", local_port),
            ("remote_ip", remote_ip),
            ("remote_port", remote_port),
            ("proto", proto),
            ("state", connstate),
        ]:
            if k in params and str(params[k]) != v:
                match = False
                break
        if match:
            found += 1

    warn_lower, crit_lower = params.get("min_states", (None, None))
    warn_upper, crit_upper = params.get("max_states", (None, None))
    yield check_levels(
        found,
        "connections",
        (warn_upper, crit_upper, warn_lower, crit_lower),
        infoname="Matching entries found",
        human_readable_func=lambda x: "%d" % x,
    )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# pylint: disable=no-else-return


def scan_fireeye(oid):
    return oid(".1.3.6.1.2.1.1.2.0").startswith(".1.3.6.1.4.1.25597.1")


def inventory_fireeye_generic(info, has_item, has_params=False):
    if info:
        params: dict | None = None
        if has_params:
            params = {}
        for line in info:
            item = None
            if has_item:
                item = line[0]
            yield item, params


def check_fireeye_states(states):
    # Now we only known the OK states and health states
    # but we can expand if we know more
    map_states = {
        "status": {
            "good": (0, "good"),
            "ok": (0, "OK"),
        },
        "disk status": {
            "online": (0, "online"),
        },
        "health": {
            "1": (0, "healthy"),
            "2": (2, "unhealthy"),
        },
    }
    states_evaluated: dict = {}
    for what, text in states:
        states_evaluated.setdefault(
            text, map_states[text.lower()].get(what.lower(), (2, "not %s" % what.lower()))
        )

    return states_evaluated

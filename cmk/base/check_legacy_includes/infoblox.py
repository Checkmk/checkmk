#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict


def scan_infoblox(oid):
    return "infoblox" in oid(".1.3.6.1.2.1.1.1.0").lower() or oid(".1.3.6.1.2.1.1.2.0").startswith(
        ".1.3.6.1.4.1.7779.1"
    )


def inventory_infoblox_statistics(info):
    return [(None, None)]


def check_infoblox_statistics(ty, stats):
    texts: Dict[Any, Any] = {}
    perfdata = []
    for what, what_val, what_textfield, what_info in stats:
        texts.setdefault(what_textfield, [])
        texts[what_textfield].append("%d %s" % (what_val, what_info))
        perfdata.append(("%s_%s" % (ty, what), what_val))

    infotexts = []
    for what, entries in texts.items():
        infotexts.append("%s: %s" % (what, ", ".join(entries)))

    return 0, " - ".join(infotexts), perfdata

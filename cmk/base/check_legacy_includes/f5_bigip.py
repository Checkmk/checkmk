#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

F5_BIGIP_CLUSTER_CHECK_DEFAULT_PARAMETERS = {
    "type": "active_standby",
}


def scan_f5_bigip(oid):
    return (
        ".1.3.6.1.4.1.3375.2" in oid(".1.3.6.1.2.1.1.2.0")
        and "big-ip" in oid(".1.3.6.1.4.1.3375.2.1.4.1.0", "").lower()
    )

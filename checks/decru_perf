#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.decru import DETECT_DECRU


def inventory_decru_perf(info):
    perf_names = {
        1: "read (bytes/s)",  # readBytesPerSec
        2: "write (bytes/s)",  # writeBytesPerSec
        3: "operations (/s)",  # opsPerSec
        4: "CIFS read (bytes/s)",  # cifs-readBytesPerSec
        5: "CIFS write (bytes/s)",  # cifs-writeBytesPerSec
        6: "CIFS operations (/s)",  # cifs-opsPerSec
        7: "NFS read (bytes/s)",  # nfs-readBytesPerSec
        8: "NFS write (bytes/s)",  # nfs-writeBytesPerSec
        9: "NFS operations (/s)",  # nfs-opsPerSec
    }

    inventory = []
    for index, rate in info:
        def_name = "unknown %s" % index
        name = perf_names.get(int(index), def_name)
        item = "%s: %s" % (index, name)
        inventory.append((item, rate, None))
    return inventory


def check_decru_perf(item, _no_params, info):
    index, _name = item.split(":", 1)
    for perf in info:
        if perf[0] == index:
            rate = int(perf[1])
            return (0, "current rate is %d/s" % rate, [("rate", rate)])

    return (3, "item not found")


check_info["decru_perf"] = {
    "detect": DETECT_DECRU,
    "check_function": check_decru_perf,
    "discovery_function": inventory_decru_perf,
    "service_name": "COUNTER %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.12962.1.1.2.1.1",
        oids=["1", "2"],
    ),
}

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.netapp_api import netapp_api_parse_lines
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import get_rate, get_value_store

# <<<netapp_api_protocol:sep(9)>>>
# protocol nfs nfsv3_write_ops 0   instance_name nfs   nfsv3_read_ops 0
# protocol nfsv4   instance_name nfsv4 nfsv4_read_ops 0    nfsv4_write_ops 0
# protocol iscsi   instance_name iscsi iscsi_read_ops 0    iscsi_write_ops 0
# protocol cifs    instance_name cifs  cifs_read_ops 0 cifs_write_ops 0
# protocol fcp instance_name fcp   fcp_write_ops 0 fcp_read_ops 0


def inventory_netapp_api_protocol(parsed):
    for values in parsed.values():
        if len(values) > 2:  # only create checks for protocols with infos
            yield values["protocol"], None


def check_netapp_api_protocol(item, _no_params, parsed):
    counter_data = parsed.get(item)
    if not counter_data:
        return

    value_store = get_value_store()
    now = time.time()
    for key, value in counter_data.items():
        for what in ["read", "write"]:
            if key.endswith("%s_ops" % what):
                per_sec = get_rate(value_store, key, now, int(value), raise_overflow=True)
                yield 0, f"{what.title()} OPs: {per_sec}", [(f"{item}_{what}_ios", per_sec)]


check_info["netapp_api_protocol"] = LegacyCheckDefinition(
    parse_function=netapp_api_parse_lines,
    service_name="Protocol %s",
    discovery_function=inventory_netapp_api_protocol,
    check_function=check_netapp_api_protocol,
)

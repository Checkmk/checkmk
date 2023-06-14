#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.fireeye import inventory_fireeye_generic
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.fireeye import DETECT

# .1.3.6.1.4.1.25597.13.1.46.0 8


def check_fireeye_smtp_conn(_no_item, _no_params, info):
    smtp_conns = int(info[0][0])
    yield 0, "Open SMTP connections: %d" % smtp_conns, [("connections", smtp_conns)]


check_info["fireeye_smtp_conn"] = LegacyCheckDefinition(
    detect=DETECT,
    discovery_function=lambda info: inventory_fireeye_generic(info, False),
    check_function=check_fireeye_smtp_conn,
    service_name="SMTP Connections",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=["46"],
    ),
)

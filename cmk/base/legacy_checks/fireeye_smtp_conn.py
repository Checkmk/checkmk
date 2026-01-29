#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.fireeye.lib import DETECT

check_info = {}

# .1.3.6.1.4.1.25597.13.1.46.0 8


def check_fireeye_smtp_conn(_no_item, _no_params, info):
    smtp_conns = int(info[0][0])
    yield 0, "Open SMTP connections: %d" % smtp_conns, [("connections", smtp_conns)]


def parse_fireeye_smtp_conn(string_table: StringTable) -> StringTable:
    return string_table


def discover_fireeye_smtp_conn(info):
    yield from [(None, None)] if info else []


check_info["fireeye_smtp_conn"] = LegacyCheckDefinition(
    name="fireeye_smtp_conn",
    parse_function=parse_fireeye_smtp_conn,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=["46"],
    ),
    service_name="SMTP Connections",
    discovery_function=discover_fireeye_smtp_conn,
    check_function=check_fireeye_smtp_conn,
)

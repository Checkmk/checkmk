#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    exists,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def inventory_brocade_info(section: Sequence[StringTable]) -> DiscoveryResult:
    data = "".join(brocade_info_try_it(section))
    if data != "----":
        yield Service()


def brocade_info_try_it(info):
    try:
        model = info[0][0][0]
    except Exception:
        model = "-"
    try:
        wwn = info[2][0][0]
        wwn = " ".join(["%02X" % ord(tok) for tok in wwn])
    except Exception:
        wwn = "-"
    try:
        fw = info[1][0][0]
    except Exception:
        fw = "-"
    try:
        ssn = info[1][0][1]
    except Exception:
        ssn = "-"

    return model, ssn, fw, wwn


def brocade_info_parse_wwn(val):
    if val == "":
        val = "-"
    elif val != "-":
        val = ":".join(val.split(" ")[:8])
    return val


def check_brocade_info(section: Sequence[StringTable]) -> CheckResult:
    model, ssn, fw, wwn = brocade_info_try_it(section)
    data = "".join((model, ssn, fw, wwn))
    if data != "----":
        wwn = brocade_info_parse_wwn(wwn)
        infotext = f"Model: {model}, SSN: {ssn}, Firmware Version: {fw}, WWN: {wwn}"
        yield Result(state=State.OK, summary=infotext)
        return
    yield Result(state=State.UNKNOWN, summary="no information found")
    return


def parse_brocade_info(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_brocade_info = SNMPSection(
    name="brocade_info",
    detect=all_of(
        any_of(
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588"),
            startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.24.1.1588.2.1.1"),
            equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1916.2.306"),
        ),
        exists(".1.3.6.1.4.1.1588.2.1.1.1.1.6.0"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1.2",
            oids=["1"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.1588.2.1.1.1.1",
            oids=["6", "10"],
        ),
        SNMPTree(
            base=".1.3.6.1.3.94.1.6.1",
            oids=["1"],
        ),
    ],
    parse_function=parse_brocade_info,
)
check_plugin_brocade_info = CheckPlugin(
    name="brocade_info",
    service_name="Brocade Info",
    discovery_function=inventory_brocade_info,
    check_function=check_brocade_info,
)

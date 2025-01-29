#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    any_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    equals,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

aironet_default_strength_levels = (-25, -20)
aironet_default_quality_levels = (40, 35)

# Note: this check uses three different items in order
# to distinguish three independent aspects. This should rather
# be converted to subchecks, because:
# - Subchecks can ship separate PNP templates.
# - Perf-O-Meters need separate checks, as well.
# - WATO configuration is done on a per-check basis and
#   the parameters for the three aspects are not of the same
#   meaing and type


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def inventory_aironet_clients(section: StringTable) -> DiscoveryResult:
    if not section:
        return
    yield Service(item="strength")
    yield Service(item="quality")
    yield Service(item="clients")


def check_aironet_clients(item: str, section: StringTable) -> CheckResult:
    section = [line for line in section if line[0] != ""]

    if len(section) == 0:
        yield Result(state=State.OK, summary="No clients currently logged in")
        return

    if item == "clients":
        yield Result(state=State.OK, summary="%d clients currently logged in" % len(section))
        yield Metric("clients", len(section), boundaries=(0, None))
        return

    # item = "quality" or "strength"
    if item == "quality":
        index = 1
        mmin = 0
        mmax = 100
        unit = "%"
        neg = 1
    else:
        index = 0
        mmin = None
        mmax = 0
        unit = "dB"
        neg = -1

    avg = sum(saveint(line[index]) for line in section) / float(len(section))
    warn, crit = (
        aironet_default_quality_levels if item == "quality" else aironet_default_strength_levels
    )
    yield Metric(item, avg, levels=(warn, crit), boundaries=(mmin, mmax))

    infotxt = f"signal {item} at {avg:.1f}{unit} (warn/crit at {warn}{unit}/{crit}{unit})"

    if neg * avg <= neg * crit:
        yield Result(state=State.CRIT, summary=infotxt)
        return
    if neg * avg <= neg * warn:
        yield Result(state=State.WARN, summary=infotxt)
        return
    yield Result(state=State.OK, summary=infotxt)


def parse_aironet_clients(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_aironet_clients = SimpleSNMPSection(
    name="aironet_clients",
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.525"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.618"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.685"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.758"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1034"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1247"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1873"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1875"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1661"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.2240"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.273.1.3.1.1",
        oids=["3", "4"],
    ),
    parse_function=parse_aironet_clients,
)
check_plugin_aironet_clients = CheckPlugin(
    name="aironet_clients",
    service_name="Average client signal %s",
    discovery_function=inventory_aironet_clients,
    check_function=check_aironet_clients,
)

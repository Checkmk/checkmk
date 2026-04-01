#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    Metric,
    not_exists,
    OIDBytes,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)
from cmk.legacy_includes.fc_port import fc_parse_counter

# Taken from connUnitPortState
# user selected state of the port hardware
fc_port_admstates: dict[int, tuple[str, State]] = {
    1: ("unknown", State.WARN),
    2: ("online", State.OK),
    3: ("offline", State.OK),
    4: ("bypassed", State.WARN),
    5: ("diagnostics", State.WARN),
}
# Taken from connUnitPortStatus
# operational status for the port
fc_port_opstates: dict[int, tuple[str, State]] = {
    1: ("unknown", State.WARN),
    2: ("unused", State.WARN),
    3: ("ready", State.OK),
    4: ("warning", State.WARN),
    5: ("failure", State.CRIT),
    6: ("not participating", State.WARN),
    7: ("initializing", State.WARN),
    8: ("bypass", State.WARN),
    9: ("ols", State.OK),
}
# Taken from connUnitPortHWState
# hardware detected state of the port
fc_port_phystates: dict[int, tuple[str, State]] = {
    1: ("unknown", State.WARN),
    2: ("failed", State.CRIT),
    3: ("bypassed", State.WARN),
    4: ("active", State.OK),
    5: ("loopback", State.WARN),
    6: ("txfault", State.WARN),
    7: ("no media", State.WARN),
    8: ("link down", State.CRIT),
}

# taken from connUnitPortType
porttype_list = (
    "unknown",
    "unknown",
    "other",
    "not-present",
    "hub-port",
    "n-port",
    "l-port",
    "fl-port",
    "f-port",
    "e-port",
    "g-port",
    "domain-ctl",
    "hub-controller",
    "scsi",
    "escon",
    "lan",
    "wan",
    "ac",
    "dc",
    "ssa",
)

# settings for inventory: which ports should not be inventorized
fc_port_no_inventory_types = [3]
fc_port_no_inventory_admstates = [1, 3]
fc_port_no_inventory_opstates: list[int] = []
fc_port_no_inventory_phystates: list[int] = []
fc_port_inventory_use_portname = False  # use connUnitPortName as service name


# Helper function for computing item from port number
def fc_port_getitem(num_ports: int, index: int, portname: str) -> str:
    fmt = "%%0%dd" % len(str(num_ports))  # number of digits for index
    itemname = fmt % (index - 1)  # leading zeros
    if portname.strip() and fc_port_inventory_use_portname:
        return f"{itemname} {portname.strip()}"
    return itemname


def discover_fc_port(section: StringTable) -> DiscoveryResult:
    for line in section:
        try:
            index = int(line[0])
            porttype = int(line[1])
            admstate = int(line[2])
            opstate = int(line[3])
            phystate = int(line[6])
        except Exception:  # missing vital data. Skipping this port
            continue
        portname = line[5]

        if porttype in fc_port_no_inventory_types:
            continue
        if admstate in fc_port_no_inventory_admstates:
            continue
        if opstate in fc_port_no_inventory_opstates:
            continue
        if phystate in fc_port_no_inventory_phystates:
            continue

        item = fc_port_getitem(len(section), index, portname)
        yield Service(item=item)


def _make_levels(warn: float | None, crit: float | None) -> tuple[float, float] | None:
    if warn is not None and crit is not None:
        return (warn, crit)
    return None


def check_fc_port(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    value_store = get_value_store()

    # Accept item, even if port name has changed
    item_index = int(item.split(maxsplit=1)[0])
    portinfo = [line for line in section if int(line[0]) == item_index + 1]
    index = int(portinfo[0][0])
    porttype = int(portinfo[0][1])
    admstate = int(portinfo[0][2])
    opstate = int(portinfo[0][3])
    phystate = int(portinfo[0][6])
    (
        txobjects,
        rxobjects,
        txelements,
        rxelements,
        notxcredits,
        c3discards,
        rxcrcs,
        rxencoutframes,
    ) = map(fc_parse_counter, portinfo[0][7:])  # type: ignore[arg-type]  # OIDBytes

    summarystate = 0
    output: list[str] = []

    try:
        wirespeed = float(portinfo[0][4]) * 1000.0  # speed in Bytes/sec
    except (ValueError, TypeError):
        # let user specify assumed speed via check parameter, default is 16.0 Gbit/sec
        gbit = params.get("assumed_speed", 16.0)
        wirespeed = gbit * 1000.0 * 1000.0 * 1000.0 / 8.0  # in Bytes/sec
        speedmsg = "assuming %g Gbit/s" % gbit
    else:
        gbit = wirespeed * 8.0 / (1000.0 * 1000.0 * 1000.0)  # in Gbit/sec
        speedmsg = "%.1f Gbit/s" % gbit
    output.append(speedmsg)

    # Now check rates of various counters
    this_time = time.time()

    in_bytes = get_rate(
        value_store,
        f"fc_port.rxelements.{index}",
        this_time,
        rxelements,
        raise_overflow=True,
    )
    out_bytes = get_rate(
        value_store,
        f"fc_port.txelements.{index}",
        this_time,
        txelements,
        raise_overflow=True,
    )

    average = params.get("average")  # range in minutes

    # B A N D W I D T H
    # convert thresholds in percentage into MB/s
    bw_thresh = params.get("bw")
    if bw_thresh is None:  # no levels
        warn_bytes, crit_bytes = None, None
    else:
        warn, crit = bw_thresh
        if isinstance(warn, float):
            warn_bytes = wirespeed * warn / 100.0
        else:  # in MB
            warn_bytes = warn * 1048576.0
        if isinstance(crit, float):
            crit_bytes = wirespeed * crit / 100.0
        else:  # in MB
            crit_bytes = crit * 1048576.0

    bw_levels = _make_levels(warn_bytes, crit_bytes)

    for what, value in [("In", in_bytes), ("Out", out_bytes)]:
        output.append(f"{what}: {render.iobandwidth(value)}")
        yield Metric(what.lower(), value, levels=bw_levels, boundaries=(0, wirespeed))

        # average turned on: use averaged traffic values instead of current ones
        if average:
            value = get_average(
                value_store, f"fc_port.{what}.{item}.avg", this_time, value, average
            )
            output.append(f"Avg({average}min): {render.iobandwidth(value)}")
            yield Metric(f"{what.lower()}_avg", value, levels=bw_levels, boundaries=(0, wirespeed))

        # handle levels for in/out
        if crit_bytes is not None and value >= crit_bytes:
            summarystate = 2
            output.append(f" >= {render.iobandwidth(crit_bytes)}(!!)")
        elif warn_bytes is not None and value >= warn_bytes:
            summarystate = max(1, summarystate)
            output.append(f" >= {render.iobandwidth(warn_bytes)}(!!)")

    # R X O B J E C T S & T X O B J E C T S
    # Put number of objects into performance data (honor averaging)
    rxobjects_rate = get_rate(
        value_store, f"fc_port.rxobjects.{index}", this_time, rxobjects, raise_overflow=True
    )
    txobjects_rate = get_rate(
        value_store, f"fc_port.txobjects.{index}", this_time, txobjects, raise_overflow=True
    )
    for what, value in [("rxobjects", rxobjects_rate), ("txobjects", txobjects_rate)]:
        yield Metric(what, value)
        if average:
            value = get_average(
                value_store, f"fc_port.{what}.{item}.avg", this_time, value, average
            )
            yield Metric(f"{what}_avg", value)

    # E R R O R C O U N T E R S
    # handle levels on error counters

    for descr, counter, value, ref in [
        (
            "CRC errors",
            "rxcrcs",
            rxcrcs,
            rxobjects_rate,
        ),
        (
            "ENC-Out",
            "rxencoutframes",
            rxencoutframes,
            rxobjects_rate,
        ),
        (
            "C3 discards",
            "c3discards",
            c3discards,
            txobjects_rate,
        ),
        (
            "no TX buffer credits",
            "notxcredits",
            notxcredits,
            txobjects_rate,
        ),
    ]:
        per_sec = get_rate(
            value_store,
            f"fc_port.{counter}.{index}",
            this_time,
            value,
            raise_overflow=True,
        )

        yield Metric(counter, per_sec)

        # if averaging is on, compute average and apply levels to average
        if average:
            per_sec_avg = get_average(
                value_store, f"fc_port.{counter}.{item}.avg", this_time, per_sec, average
            )
            yield Metric(f"{counter}_avg", per_sec_avg)

        # compute error rate (errors in relation to number of frames) (from 0.0 to 1.0)
        if ref > 0 or per_sec > 0:
            rate = per_sec / (ref + per_sec)  # fixed: true-division
        else:
            rate = 0
        text = f"{descr}: {rate * 100.0:.2f}%"

        # Honor averaging of error rate
        if average:
            rate = get_average(
                value_store, f"fc_port.{counter}.{item}.avgrate", this_time, rate, average
            )
            text += ", Avg: %.2f%%" % (rate * 100.0)

        error_percentage = rate * 100.0
        warn, crit = params[counter]
        if crit is not None and error_percentage >= crit:
            summarystate = 2
            text += "(!!)"
            output.append(text)
        elif warn is not None and error_percentage >= warn:
            summarystate = max(1, summarystate)
            text += "(!)"
            output.append(text)

    yield Result(state=State(summarystate), summary=", ".join(output))

    statetxt, state = fc_port_admstates.get(int(admstate), ("unknown", State.UNKNOWN))
    yield Result(state=state, summary=statetxt)

    statetxt, state = fc_port_opstates.get(int(opstate), ("unknown", State.UNKNOWN))
    yield Result(state=state, summary=statetxt)

    statetxt, state = fc_port_phystates.get(int(phystate), ("unknown", State.UNKNOWN))
    yield Result(state=state, summary=statetxt)

    yield Result(state=State.OK, summary=porttype_list[int(porttype)])


def parse_fc_port(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_fc_port = SimpleSNMPSection(
    name="fc_port",
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.2.1.1"),
        not_exists(".1.3.6.1.4.1.1588.2.1.1.1.6.2.1.*"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.3.94",
        oids=[
            "1.10.1.2",
            "1.10.1.3",
            "1.10.1.6",
            "1.10.1.7",
            "1.10.1.15",
            "1.10.1.17",
            "1.10.1.23",
            OIDBytes("4.5.1.4"),
            OIDBytes("4.5.1.5"),
            OIDBytes("4.5.1.6"),
            OIDBytes("4.5.1.7"),
            OIDBytes("4.5.1.8"),
            OIDBytes("4.5.1.28"),
            OIDBytes("4.5.1.40"),
            OIDBytes("4.5.1.50"),
        ],
    ),
    parse_function=parse_fc_port,
)


check_plugin_fc_port = CheckPlugin(
    name="fc_port",
    service_name="FC Interface %s",
    discovery_function=discover_fc_port,
    check_function=check_fc_port,
    check_ruleset_name="fc_port",
    check_default_parameters={
        "rxcrcs": (3.0, 20.0),  # allowed percentage of CRC errors
        "rxencoutframes": (3.0, 20.0),  # allowed percentage of Enc-OUT Frames
        "notxcredits": (3.0, 20.0),  # allowed percentage of No Tx Credits
        "c3discards": (3.0, 20.0),  # allowed percentage of C3 discards
    },
)

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="arg-type"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="var-annotated"

import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import (
    all_of,
    get_average,
    get_rate,
    get_value_store,
    not_exists,
    OIDBytes,
    render,
    SNMPTree,
    startswith,
    StringTable,
)
from cmk.base.check_legacy_includes.fc_port import fc_parse_counter

check_info = {}

# Taken from connUnitPortState
# user selected state of the port hardware
fc_port_admstates = {
    1: ("unknown", 1),
    2: ("online", 0),
    3: ("offline", 0),
    4: ("bypassed", 1),
    5: ("diagnostics", 1),
}
# Taken from connUnitPortStatus
# operational status for the port
fc_port_opstates = {
    1: ("unknown", 1),
    2: ("unused", 1),
    3: ("ready", 0),
    4: ("warning", 1),
    5: ("failure", 2),
    6: ("not participating", 1),
    7: ("initializing", 1),
    8: ("bypass", 1),
    9: ("ols", 0),
}
# Taken from connUnitPortHWState
# hardware detected state of the port
fc_port_phystates = {
    1: ("unknown", 1),
    2: ("failed", 2),
    3: ("bypassed", 1),
    4: ("active", 0),
    5: ("loopback", 1),
    6: ("txfault", 1),
    7: ("no media", 1),
    8: ("link down", 2),
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
fc_port_no_inventory_opstates = []
fc_port_no_inventory_phystates = []
fc_port_inventory_use_portname = False  # use connUnitPortName as service name


# Helper function for computing item from port number
def fc_port_getitem(num_ports, index, portname):
    fmt = "%%0%dd" % len(str(num_ports))  # number of digits for index
    itemname = fmt % (index - 1)  # leading zeros
    if portname.strip() and fc_port_inventory_use_portname:
        return f"{itemname} {portname.strip()}"
    return itemname


def discover_fc_port(info):
    for line in info:
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

        item = fc_port_getitem(len(info), index, portname)
        yield item, {}


def check_fc_port(item, params, info):
    value_store = get_value_store()

    # Accept item, even if port name has changed
    item_index = int(item.split()[0])
    portinfo = [line for line in info if int(line[0]) == item_index + 1]
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
    ) = map(fc_parse_counter, portinfo[0][7:])

    summarystate = 0
    output = []
    perfdata = []
    perfaverages = []

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
        get_value_store(),
        "fc_port.rxelements.%s" % index,
        this_time,
        rxelements,
        raise_overflow=True,
    )
    out_bytes = get_rate(
        get_value_store(),
        "fc_port.txelements.%s" % index,
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

    for what, value in [("In", in_bytes), ("Out", out_bytes)]:
        output.append(f"{what}: {render.iobandwidth(value)}")
        perfdata.append((what.lower(), value, warn_bytes, crit_bytes, 0, wirespeed))

        # average turned on: use averaged traffic values instead of current ones
        if average:
            value = get_average(
                value_store, f"fc_port.{what}.{item}.avg", this_time, value, average
            )
            output.append("Avg(%dmin): %s" % (average, render.iobandwidth(value)))
            perfaverages.append(
                ("%s_avg" % what.lower(), value, warn_bytes, crit_bytes, 0, wirespeed)
            )

        # handle levels for in/out
        if crit_bytes is not None and value >= crit_bytes:
            summarystate = 2
            output.append(" >= %s(!!)" % (render.iobandwidth(crit_bytes)))
        elif warn_bytes is not None and value >= warn_bytes:
            summarystate = max(1, summarystate)
            output.append(" >= %s(!!)" % (render.iobandwidth(warn_bytes)))

    # put perfdata of averages after perfdata for in and out in order not to confuse the perfometer
    perfdata.extend(perfaverages)

    # R X O B J E C T S & T X O B J E C T S
    # Put number of objects into performance data (honor averaging)
    rxobjects_rate = get_rate(
        get_value_store(), "fc_port.rxobjects.%s" % index, this_time, rxobjects, raise_overflow=True
    )
    txobjects_rate = get_rate(
        get_value_store(), "fc_port.txobjects.%s" % index, this_time, txobjects, raise_overflow=True
    )
    for what, value in [("rxobjects", rxobjects_rate), ("txobjects", txobjects_rate)]:
        perfdata.append((what, value))
        if average:
            value = get_average(
                value_store, f"fc_port.{what}.{item}.avg", this_time, value, average
            )
            perfdata.append(("%s_avg" % what, value))

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
            get_value_store(),
            f"fc_port.{counter}.{index}",
            this_time,
            value,
            raise_overflow=True,
        )

        perfdata.append((counter, per_sec))

        # if averaging is on, compute average and apply levels to average
        if average:
            per_sec_avg = get_average(
                value_store, f"fc_port.{counter}.{item}.avg", this_time, per_sec, average
            )
            perfdata.append(("%s_avg" % counter, per_sec_avg))

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

    yield summarystate, ", ".join(output), perfdata

    statetxt, state = fc_port_admstates.get(int(admstate), ("unknown", 3))
    yield state, statetxt

    statetxt, state = fc_port_opstates.get(int(opstate), ("unknown", 3))
    yield state, statetxt

    statetxt, state = fc_port_phystates.get(int(phystate), ("unknown", 3))
    yield state, statetxt

    yield 0, porttype_list[int(porttype)]


def parse_fc_port(string_table: StringTable) -> StringTable:
    return string_table


check_info["fc_port"] = LegacyCheckDefinition(
    name="fc_port",
    parse_function=parse_fc_port,
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
            # The number of frames/packets/IOs/etc that have been transmitted
            # by this port. Note: A Fibre Channel frame starts with SOF and
            # ends with EOF. FC loop devices should not count frames passed
            # through. This value represents the sum total for all other Tx
            OIDBytes("4.5.1.5"),
            # The number of frames/packets/IOs/etc that have been received
            # by this port. Note: A Fibre Channel frame starts with SOF and
            # ends with EOF. FC loop devices should not count frames passed
            # through. This value represents the sum total for all other Rx
            OIDBytes("4.5.1.6"),
            # The number of octets or bytes that have been transmitted
            # by this port. One second periodic polling of the port. This
            # value is saved and compared with the next polled value to
            # compute net throughput. Note, for Fibre Channel, ordered
            # sets are not included in the count.
            OIDBytes("4.5.1.7"),
            # The number of octets or bytes that have been received.
            # by this port. One second periodic polling of the port. This
            # value is saved and compared with the next polled value to
            # compute net throughput. Note, for Fibre Channel, ordered
            # sets are not included in the count.
            OIDBytes("4.5.1.8"),
            # Count of transitions in/out of BBcredit zero state.
            # The other side is not providing any credit.
            OIDBytes("4.5.1.28"),
            # Count of Class 3 Frames that were discarded upon reception
            # at this port.  There is no FBSY or FRJT generated for Class 3
            # Frames.  They are simply discarded if they cannot be delivered.
            OIDBytes("4.5.1.40"),
            # Count of frames received with invalid CRC. This count is
            # part of the Link Error Status Block (LESB). (FC-PH 29.8). Loop
            # ports should not count CRC errors passing through when
            # monitoring.
            OIDBytes("4.5.1.50"),
            # Count of disparity errors received at this port.
        ],
    ),
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

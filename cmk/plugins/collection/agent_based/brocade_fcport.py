#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any, cast

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    Metric,
    OIDBytes,
    OIDEnd,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.brocade import (
    brocade_fcport_getitem,
    brocade_fcport_inventory_this_port,
    DETECT,
    DISCOVERY_DEFAULT_PARAMETERS,
)

Section = Sequence[Mapping[str, Any]]


# lookup tables for check implementation
# Taken from swFCPortPhyState
_BROCADE_FCPORT_PHYSTATES = {
    0: "",
    1: "no card",
    2: "no transceiver",
    3: "laser fault",
    4: "no light",
    5: "no sync",
    6: "in sync",
    7: "port fault",
    8: "diag fault",
    9: "lock ref",
    10: "validating",
    11: "invalid module",
    12: "remote fault",
    13: "local fault",
    14: "no sig det",
    15: "hard fault",
    16: "unsupported module",
    17: "module fault",
    255: "unknown",
}

# Taken from swFCPortOpStatus
_BROCADE_FCPORT_OPSTATES = {
    0: "unknown",
    1: "online",
    2: "offline",
    3: "testing",
    4: "faulty",
}

# Taken from swFCPortAdmStatus
_BROCADE_FCPORT_ADMSTATES = {
    0: "",
    1: "online",
    2: "offline",
    3: "testing",
    4: "faulty",
}

# Taken from swFCPortSpeed
_BROCADE_FCPORT_SPEED = {
    0: "unknown",
    1: "1Gbit",
    2: "2Gbit",
    3: "auto-Neg",
    4: "4Gbit",
    5: "8Gbit",
    6: "10Gbit",
    7: "unknown",
    8: "16Gbit",
}

# Taken from swNbBaudRate
_ISL_SPEED_MAP = {
    "1": 0,  # other (1) - None of the following.
    "2": 0.155,  # oneEighth (2) - 155 Mbaud.
    "4": 0.266,  # quarter (4) - 266 Mbaud.
    "8": 0.532,  # half (8) - 532 Mbaud.
    "16": 1,  # full (16) - 1 Gbaud.
    "32": 2,  # double (32) - 2 Gbaud.
    "64": 4,  # quadruple (64) - 4 Gbaud.
    "128": 8,  # octuple (128) - 8 Gbaud.
    "256": 10,  # decuple (256) - 10 Gbaud.
    "512": 16,  # sexdecuple (512) - 16 Gbaud
}


def _try_int(int_str: str) -> int | None:
    try:
        return int(int_str)
    except ValueError:
        return None


def _to_int(raw_value: Sequence[int]) -> int:
    """Convert a raw integer

    This is done by considering the string to be a little endian byte string.
    Such strings are sometimes used by SNMP to encode 64 bit counters without
    needed COUNTER64 (which is not available in SNMP v1).
    """
    value = 0
    mult = 1
    for ord_int in raw_value[::-1]:
        value += mult * ord_int
        mult *= 256
    return value


def _get_if_table_offset(speed_info: StringTable, offset: int) -> int | None:
    # http://community.brocade.com/t5/Fibre-Channel-SAN/SNMP-FC-port-speed/td-p/64980
    # says that "1073741824" from if-table correlates with index 1 from
    # brocade-if-table.
    # But: In logically separated Brocade FC switches, the interface indices do
    # not start with 1. Therefor the index in the speed table does not start
    # with "1073741824". It is necessary to add the first interface index as
    # offset to find the table offset in the speed table.
    for index, entry in enumerate(speed_info):
        if int(entry[0]) == 1073741823 + offset:
            return index
    return None


def _get_relevant_part_of_speed_info(speed_info: StringTable, offset: int) -> StringTable:
    # if-table and brocade-if-table do NOT have same length
    # first remove interfaces at the beginning of the speed info table:
    speed_info = [x[1:] for x in speed_info[_get_if_table_offset(speed_info, offset) :]]

    # but there may also be some vlan (or other non fc) interfaces at the bottom of speed_info:
    while speed_info and speed_info[-1] and speed_info[-1][0] != "56":
        speed_info.pop()

    return speed_info


def parse_brocade_fcport(string_table: Sequence[StringTable]) -> Section | None:
    if_info: StringTable = string_table[0]
    link_info: StringTable = string_table[1]
    speed_info: StringTable = string_table[2]
    # The typing of string_table is wrong here. OIDBytes tells the data not as a string.
    # Unfortunately we can not change the type of string_table in the signature without
    # touching a lot of other code.
    if64_info = cast(
        list[tuple[str, Sequence[int], Sequence[int], Sequence[int], Sequence[int], Sequence[int]]],
        string_table[3],
    )

    try:
        offset = int(if_info[0][0])
    except (ValueError, IndexError):
        return None

    isl_ports = dict(link_info)
    speed_info = _get_relevant_part_of_speed_info(speed_info, offset)

    if len(if_info) == len(speed_info):
        # extract the speed from IF-MIB::ifHighSpeed.
        # unfortunately ports in the IF-MIB and the brocade MIB
        # dont have a common index. We hope that at least
        # the FC ports have the same sequence in both lists.
        # here we go through ports of the IF-NIB, but consider only FC ports (type 56)
        # and assume that the sequence number of the FC port here is the same
        # as the sequence number in the borcade MIB (pindex = item_index)
        if_table = [x + (y if y[0] == "56" else ["", x[-2]]) for x, y in zip(if_info, speed_info)]
    else:
        if_table = [x + ["", x[-2]] for x in if_info]

    parsed = []
    for (
        index,
        phystate,
        opstate,
        admstate,
        txwords,
        rxwords,
        txframes,
        rxframes,
        notxcredits,
        rxcrcs,
        rxencinframes,
        rxencoutframes,
        c3discards,
        brocade_speed,
        portname,
        porttype,
        ifspeed,
    ) in if_table:
        # Since FW v8.0.1b [rx/tx]words are no longer available
        # Use 64bit counters if available
        bbcredits = None
        if if64_info:
            fcmgmt_portstats = []
            for oidend, tx_objects, rx_objects, tx_elements, rx_elements, bbcredits_64 in if64_info:
                if index == str(oidend).rsplit(".", 1)[-1]:
                    fcmgmt_portstats = [
                        _to_int(tx_objects),
                        _to_int(rx_objects),
                        int(_to_int(tx_elements) / 4),
                        int(_to_int(rx_elements) / 4),
                        _to_int(bbcredits_64),
                    ]
                    break
            if fcmgmt_portstats:
                txframes = str(fcmgmt_portstats[0])
                rxframes = str(fcmgmt_portstats[1])
                txwords = str(fcmgmt_portstats[2])
                rxwords = str(fcmgmt_portstats[3])
                bbcredits = str(fcmgmt_portstats[4])
            else:
                txframes = "0"
                rxframes = "0"
                txwords = "0"
                rxwords = "0"

        islspeed = None
        if index in isl_ports:
            islspeed = _ISL_SPEED_MAP.get(isl_ports[index])

        try:
            data = {
                "index": int(index),
                "phystate": int(phystate),
                "opstate": int(opstate),
                "admstate": int(admstate),
                "txwords": int(txwords),
                "rxwords": int(rxwords),
                "txframes": int(txframes),
                "rxframes": int(rxframes),
                "notxcredits": int(notxcredits),
                "rxcrcs": int(rxcrcs),
                "rxencinframes": int(rxencinframes),
                "rxencoutframes": int(rxencoutframes),
                "c3discards": int(c3discards),
                "brocade_speed": _try_int(brocade_speed),
                "portname": portname,
                "porttype": porttype,
                "ifspeed": _try_int(ifspeed),
                "is_isl": index in isl_ports,
                "islspeed": islspeed,  # Might be None
                "bbcredits": int(bbcredits) if bbcredits is not None else None,
            }
        except ValueError:
            continue

        parsed.append(data)

    return parsed


snmp_section_brocade_fcport = SNMPSection(
    name="brocade_fcport",
    parse_function=parse_brocade_fcport,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.1588.2.1.1.1.6.2.1",
            oids=[
                "1",  # swFCPortIndex
                "3",  # swFCPortPhyState
                "4",  # swFCPortOpStatus
                "5",  # swFCPortAdmStatus
                "11",  # swFCPortTxWords
                "12",  # swFCPortRxWords
                "13",  # swFCPortTxFrames
                "14",  # swFCPortRxFrames
                "20",  # swFCPortNoTxCredits
                "22",  # swFCPortRxCrcs
                "21",  # swFCPortRxEncInFrs
                "26",  # swFCPortRxEncOutFrs
                "28",  # swFCPortC3Discards
                "35",  # swFCPortSpeed, deprecated from at least firmware version 7.2.1
                "36",  # swFCPortName  (not supported by all devices)
            ],
        ),
        # Information about Inter-Switch-Links (contains baud rate of port)
        SNMPTree(
            base=".1.3.6.1.4.1.1588.2.1.1.1.2.9.1",
            oids=[
                "2",  # swNbMyPort
                "5",  # swNbBaudRate
            ],
        ),
        # new way to get port speed supported by Brocade
        SNMPTree(
            base=".1.3.6.1.2.1",
            oids=[
                OIDEnd(),
                "2.2.1.3",  # ifType, needed to extract fibre channel ifs only (type 56)
                "31.1.1.1.15",  # IF-MIB::ifHighSpeed
            ],
        ),
        # Not every device supports that
        SNMPTree(
            base=".1.3.6.1.3.94.4.5.1",
            oids=[
                OIDEnd(),
                OIDBytes("4"),  # FCMGMT-MIB::connUnitPortStatCountTxObjects
                OIDBytes("5"),  # FCMGMT-MIB::connUnitPortStatCountRxObjects
                OIDBytes("6"),  # FCMGMT-MIB::connUnitPortStatCountTxElements
                OIDBytes("7"),  # FCMGMT-MIB::connUnitPortStatCountRxElements
                OIDBytes("8"),  # FCMGMT-MIB::connUnitPortStatCountBBCreditZero
            ],
        ),
    ],
    detect=DETECT,
)


def discover_brocade_fcport(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    for if_entry in section:
        admstate = if_entry["admstate"]
        phystate = if_entry["phystate"]
        opstate = if_entry["opstate"]
        if brocade_fcport_inventory_this_port(
            admstate=admstate,
            phystate=phystate,
            opstate=opstate,
            settings=params,
        ):
            yield Service(
                item=brocade_fcport_getitem(
                    number_of_ports=len(section),
                    index=if_entry["index"],
                    portname=if_entry["portname"],
                    is_isl=if_entry["is_isl"],
                    settings=params,
                ),
                parameters={
                    "phystate": [phystate],
                    "opstate": [opstate],
                    "admstate": [admstate],
                },
            )


def _get_speed_msg_and_value(
    is_isl: bool,
    isl_speed: float | None,
    brocade_speed: int,
    porttype: str,
    if_speed: float | None,
    params: Mapping[str, float],
) -> tuple[str, float]:
    # Lookup port speed in ISL table for ISL ports (older switches do not provide this
    # information in the normal table)
    if is_isl and isl_speed is not None:
        return "ISL speed: %.0f Gbit/s", isl_speed

    brocade_speed_value = _BROCADE_FCPORT_SPEED.get(brocade_speed, "unknown")
    if brocade_speed_value not in ("auto-Neg", "unknown") and porttype != "56":
        return "%.0f Gbit/s", float(brocade_speed_value.replace("Gbit", ""))

    if if_speed:
        # use actual speed of port if available
        return "Speed: %g Gbit/s", if_speed / 1000.0

    # let user specify assumed speed via check parameter, default is 2.0
    return "Assumed speed: %g Gbit/s", params["assumed_speed"]


def check_brocade_fcport(
    item: str,
    params: Mapping[str, Any],
    section: Section,
) -> CheckResult:
    """
    Reference: https://dl.dell.com/manuals/all-products/esuprt_ser_stor_net/esuprt_poweredge/poweredge-m1000e_service%20manual7_en-us.pdf
    """
    yield from _check_brocade_fcport(item, params, section, time.time(), get_value_store())


def _check_brocade_fcport(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    this_time: float,
    value_store: MutableMapping[str, Any],
) -> CheckResult:
    for if_entry in section:
        if int(item.split()[0]) + 1 == if_entry["index"]:
            found_entry = if_entry
            break
    else:
        return

    index = found_entry["index"]
    txwords = found_entry["txwords"]
    rxwords = found_entry["rxwords"]
    txframes = found_entry["txframes"]
    rxframes = found_entry["rxframes"]
    notxcredits = found_entry["notxcredits"]
    rxcrcs = found_entry["rxcrcs"]
    rxencinframes = found_entry["rxencinframes"]
    rxencoutframes = found_entry["rxencoutframes"]
    c3discards = found_entry["c3discards"]
    brocade_speed = found_entry["brocade_speed"]
    is_isl = found_entry["is_isl"]
    isl_speed = found_entry["islspeed"]
    bbcredits = found_entry["bbcredits"]
    porttype = found_entry["porttype"]
    speed = found_entry.get("ifspeed")

    average = params.get("average")  # range in minutes
    bw_thresh = params.get("bw")

    summarystate = 0
    output = []
    perfdata = []
    perfaverages = []

    speedmsg, gbit = _get_speed_msg_and_value(
        is_isl, isl_speed, brocade_speed, porttype, speed, params
    )
    output.append(speedmsg % gbit)

    # convert gbit link-rate to Byte/s (8/10 enc)
    wirespeed = gbit * 1e9 / 8
    # from word to bytes: 4 bytes per word
    in_bytes = 4 * get_rate(value_store, "rxwords.%s" % index, this_time, rxwords)
    out_bytes = 4 * get_rate(value_store, "txwords.%s" % index, this_time, txwords)

    # B A N D W I D T H
    # convert thresholds in percentage into MB/s
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
        perfdata.append(
            Metric(what.lower(), value, levels=(warn_bytes, crit_bytes), boundaries=(0, wirespeed))
        )
        # average turned on: use averaged traffic values instead of current ones
        if average:
            value = get_average(value_store, f"{what}.{item}.avg", this_time, value, average)
            output.append("Average (%d min): %s" % (average, render.iobandwidth(value)))
            perfaverages.append(
                Metric(
                    "%s_avg" % what.lower(),
                    value,
                    levels=(warn_bytes, crit_bytes),
                    boundaries=(0, wirespeed),
                )
            )

        # handle levels for in/out
        if crit_bytes is not None and value >= crit_bytes:
            summarystate = 2
            output.append(" >= %s(!!)" % (render.iobandwidth(crit_bytes)))
        elif warn_bytes is not None and value >= warn_bytes:
            summarystate = max(1, summarystate)
            output.append(" >= %s(!)" % (render.iobandwidth(warn_bytes)))

    # put perfdata of averages after perfdata for in and out in order not to confuse the perfometer
    perfdata.extend(perfaverages)

    # R X F R A M E S & T X F R A M E S
    # Put number of frames into performance data (honor averaging)
    rxframes_rate = get_rate(value_store, "rxframes.%s" % index, this_time, rxframes)
    txframes_rate = get_rate(value_store, "txframes.%s" % index, this_time, txframes)
    for what, value in [("rxframes", rxframes_rate), ("txframes", txframes_rate)]:
        perfdata.append(Metric(what, value))
        if average:
            value = get_average(value_store, f"{what}.{item}.avg", this_time, value, average)
            perfdata.append(Metric("%s_avg" % what, value))

    # E R R O R C O U N T E R S
    # handle levels on error counters
    for descr, counter, value, ref in [
        ("CRC errors", "rxcrcs", rxcrcs, rxframes_rate),
        ("ENC-Out", "rxencoutframes", rxencoutframes, rxframes_rate),
        ("ENC-In", "rxencinframes", rxencinframes, rxframes_rate),
        ("C3 discards", "c3discards", c3discards, txframes_rate),
        ("No TX buffer credits", "notxcredits", notxcredits, txframes_rate),
    ]:
        per_sec = get_rate(value_store, f"{counter}.{index}", this_time, value)
        perfdata.append(Metric(counter, per_sec))

        # if averaging is on, compute average and apply levels to average
        if average:
            per_sec_avg = get_average(
                value_store, f".{counter}.{item}.avg", this_time, per_sec, average
            )
            perfdata.append(Metric("%s_avg" % counter, per_sec_avg))

        # compute error rate (errors in relation to number of frames) (from 0.0 to 1.0)
        if ref > 0 or per_sec > 0:
            rate = per_sec / (ref + per_sec)  # fixed: true-division
        else:
            rate = 0
        text = f"{descr}: {rate * 100.0:.2f}%"

        # Honor averaging of error rate
        if average:
            rate = get_average(value_store, f"{counter}.{item}.avgrate", this_time, rate, average)
            text += ", Average: %.2f%%" % (rate * 100.0)

        error_percentage = rate * 100.0
        warn, crit = params.get(counter, (None, None))
        if crit is not None and error_percentage >= crit:
            summarystate = 2
            text += "(!!)"
            output.append(text)
        elif warn is not None and error_percentage >= warn:
            summarystate = max(1, summarystate)
            text += "(!)"
            output.append(text)

    # P O R T S T A T E
    for state_key, state_info, warn_states, state_map in [
        ("phystate", "Physical", (1, 6), _BROCADE_FCPORT_PHYSTATES),
        ("opstate", "Operational", (1, 3), _BROCADE_FCPORT_OPSTATES),
        ("admstate", "Administrative", (0, 1, 3), _BROCADE_FCPORT_ADMSTATES),
    ]:
        dev_state = found_entry[state_key]
        errorflag = ""
        state_value = params.get(state_key)
        if (
            state_value is not None
            and dev_state != state_value
            and not (isinstance(state_value, list) and dev_state in map(int, state_value))
        ):
            if dev_state in warn_states:
                errorflag = "(!)"
                summarystate = max(summarystate, 1)
            else:
                errorflag = "(!!)"
                summarystate = 2
        output.append(f"{state_info}: {state_map[dev_state]}{errorflag}")

    if bbcredits is not None:
        bbcredit_rate = get_rate(value_store, "bbcredit.%s" % (item), this_time, bbcredits)
        perfdata.append(Metric("fc_bbcredit_zero", bbcredit_rate))

    yield Result(state=State(summarystate), summary=", ".join(output))
    yield from perfdata


check_plugin_brocade_fcport = CheckPlugin(
    name="brocade_fcport",
    service_name="Port %s",
    discovery_function=discover_brocade_fcport,
    discovery_ruleset_name="brocade_fcport_inventory",
    discovery_default_parameters=DISCOVERY_DEFAULT_PARAMETERS,
    check_function=check_brocade_fcport,
    check_ruleset_name="brocade_fcport",
    check_default_parameters={
        "rxcrcs": (3.0, 20.0),  # allowed percentage of CRC errors
        "rxencoutframes": (3.0, 20.0),  # allowed percentage of Enc-OUT Frames
        "rxencinframes": (3.0, 20.0),  # allowed percentage of Enc-In Frames
        "notxcredits": (3.0, 20.0),  # allowed percentage of No Tx Credits
        "c3discards": (3.0, 20.0),  # allowed percentage of C3 discards
        "assumed_speed": 2.0,  # used if speed not available in SNMP data
    },
)

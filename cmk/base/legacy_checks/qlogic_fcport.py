#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, LegacyResult
from cmk.agent_based.v2 import (
    any_of,
    get_rate,
    get_value_store,
    OIDEnd,
    render,
    SNMPTree,
    startswith,
    StringTable,
)

check_info = {}

# settings for inventory: which ports should be inventorized
qlogic_fcport_inventory_opstates = ["1", "3"]
qlogic_fcport_inventory_admstates = ["1", "3"]


# this function is needed to have the same port IDs in Checkmk
# as within the Management interface of the device
def qlogic_fcport_generate_port_id(port_id: str) -> str:
    major, minor = port_id.split(".", 1)
    minor_int = int(minor) - 1
    return f"{major}.{minor_int}"


def discover_qlogic_fcport(info: StringTable) -> list[tuple[str, None]]:
    inventory = []

    for (
        port_id,
        _oper_mode,
        admin_status,
        oper_status,
        _link_failures,
        _sync_losses,
        _prim_seq_proto_errors,
        _invalid_tx_words,
        _invalid_crcs,
        _address_id_errors,
        _link_reset_ins,
        _link_reset_outs,
        _ols_ins,
        _ols_outs,
        _c2_in_frames,
        _c2_out_frames,
        _c2_in_octets,
        _c2_out_octets,
        _c2_discards,
        _c2_fbsy_frames,
        _c2_frjt_frames,
        _c3_in_frames,
        _c3_out_frames,
        _c3_in_octets,
        _c3_out_octets,
        _c3_discards,
    ) in info:
        # There are devices out there which are totally missing the status related
        # SNMP tables. In this case we add all interfaces.
        if (admin_status == "" and oper_status == "") or (
            admin_status in qlogic_fcport_inventory_admstates
            and oper_status in qlogic_fcport_inventory_opstates
        ):
            inventory.append((qlogic_fcport_generate_port_id(port_id), None))

    return inventory


def check_qlogic_fcport(item: str, _no_params: None, info: StringTable) -> LegacyResult:
    for (
        port_id,
        oper_mode,
        admin_status,
        oper_status,
        link_failures,
        sync_losses,
        prim_seq_proto_errors,
        invalid_tx_words,
        invalid_crcs,
        address_id_errors,
        link_reset_ins,
        link_reset_outs,
        ols_ins,
        ols_outs,
        c2_in_frames,
        c2_out_frames,
        c2_in_octets,
        c2_out_octets,
        c2_discards,
        c2_fbsy_frames,
        c2_frjt_frames,
        c3_in_frames,
        c3_out_frames,
        c3_in_octets,
        c3_out_octets,
        c3_discards,
    ) in info:
        port_id = qlogic_fcport_generate_port_id(port_id)
        if port_id == item:
            status = 0
            perfdata = []
            message = "Port %s" % port_id

            # fcFxPortPhysAdminStatus
            if admin_status == "1":
                message += " AdminStatus: online"
                status = 0
            elif admin_status == "2":
                message += " AdminStatus: offline (!!)"
                status = 2
            elif admin_status == "3":
                message += " AdminStatus: testing (!)"
                status = 1
            elif admin_status == "":
                # Is not a possible valid value in the MIB, but some devices don't
                # provide status information at all (SNMP table missing).
                message += " AdminStatus: not reported"
                status = 0
            else:
                message += " unknown AdminStatus %s (!)" % admin_status
                status = 1

            # fcFxPortPhysOperStatus
            if oper_status == "1":
                message += ", OperStatus: online"
                status = max(status, 0)
            elif oper_status == "2":
                message += ", OperStatus: offline (!!)"
                status = max(status, 2)
            elif oper_status == "3":
                message += ", OperStatus: testing (!)"
                status = max(status, 1)
            elif oper_status == "4":
                message += ", OperStatus: linkFailure (!!)"
                status = max(status, 2)
            elif admin_status == "":
                # Is not a possible valid value in the MIB, but some devices don't
                # provide status information at all (SNMP table missing).
                message += ", OperStatus: not reported"
                status = 0
            else:
                message += ", unknown OperStatus %s (!)" % oper_status
                status = max(status, 1)

            # fcFxPortOperMode (for display only)
            if oper_mode == "2":
                message += ", OperMode: fPort"
            elif oper_mode == "3":
                message += ", OperMode: flPort"

            # Counters
            this_time = time.time()

            # Bytes/sec in and out
            in_octets = int(c2_in_octets) + int(c3_in_octets)
            out_octets = int(c2_out_octets) + int(c3_out_octets)

            in_octet_rate = get_rate(
                get_value_store(),
                "qlogic_fcport.in_octets.%s" % port_id,
                this_time,
                in_octets,
                raise_overflow=True,
            )
            out_octet_rate = get_rate(
                get_value_store(),
                "qlogic_fcport.out_octets.%s" % port_id,
                this_time,
                out_octets,
                raise_overflow=True,
            )

            message += ", In: %s" % render.iobandwidth(in_octet_rate)
            message += ", Out: %s" % render.iobandwidth(out_octet_rate)

            perfdata.append(("in", in_octet_rate))
            perfdata.append(("out", out_octet_rate))

            # Frames in and out
            in_frames = int(c2_in_frames) + int(c3_in_frames)
            out_frames = int(c2_out_frames) + int(c3_out_frames)

            in_frame_rate = get_rate(
                get_value_store(),
                "qlogic_fcport.in_frames.%s" % port_id,
                this_time,
                in_frames,
                raise_overflow=True,
            )
            out_frame_rate = get_rate(
                get_value_store(),
                "qlogic_fcport.out_frames.%s" % port_id,
                this_time,
                out_frames,
                raise_overflow=True,
            )

            message += ", in frames: %s/s" % in_frame_rate
            message += ", out frames: %s/s" % out_frame_rate

            perfdata.append(("rxframes", in_frame_rate))
            perfdata.append(("txframes", out_frame_rate))

            # error rates
            discards = int(c2_discards) + int(c3_discards)
            error_sum = 0.0
            for descr, counter, value in [
                ("Link Failures", "link_failures", link_failures),
                ("Sync Losses", "sync_losses", sync_losses),
                ("PrimitSeqErrors", "prim_seq_proto_errors", prim_seq_proto_errors),
                ("Invalid TX Words", "invalid_tx_words", invalid_tx_words),
                ("Invalid CRCs", "invalid_crcs", invalid_crcs),
                ("Address ID Errors", "address_id_errors", address_id_errors),
                ("Link Resets In", "link_reset_ins", link_reset_ins),
                ("Link Resets Out", "link_reset_outs", link_reset_outs),
                ("Offline Sequences In", "ols_ins", ols_ins),
                ("Offline Sequences Out", "ols_outs", ols_outs),
                ("Discards", "discards", discards),
                ("F_BSY frames", "c2_fbsy_frames", c2_fbsy_frames),
                ("F_RJT frames", "c2_frjt_frames", c2_frjt_frames),
            ]:
                value_int = int(value)  # type: ignore[call-overload]
                per_sec = get_rate(
                    get_value_store(),
                    f"qlogic_fcport.{counter}.{port_id}",
                    this_time,
                    value_int,
                    raise_overflow=True,
                )
                perfdata.append((counter, per_sec))
                error_sum += per_sec

                if per_sec > 0:
                    message += f", {descr}: {per_sec}/s"
            if error_sum == 0:
                message += ", no protocol errors"

            return status, message, perfdata

    return 3, "Port %s not found" % item


def parse_qlogic_fcport(string_table: StringTable) -> StringTable:
    return string_table


check_info["qlogic_fcport"] = LegacyCheckDefinition(
    name="qlogic_fcport",
    parse_function=parse_qlogic_fcport,
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1663.1.1"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.8"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.9"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.11"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.12"),
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3873.1.14"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.75.1",
        oids=[
            OIDEnd(),
            "2.1.1.3",
            "2.2.1.1",
            "2.2.1.2",
            "3.1.1.1",
            "3.1.1.2",
            "3.1.1.4",
            "3.1.1.5",
            "3.1.1.6",
            "3.1.1.8",
            "3.1.1.9",
            "3.1.1.10",
            "3.1.1.11",
            "3.1.1.12",
            "4.2.1.1",
            "4.2.1.2",
            "4.2.1.3",
            "4.2.1.4",
            "4.2.1.5",
            "4.2.1.6",
            "4.2.1.7",
            "4.3.1.1",
            "4.3.1.2",
            "4.3.1.3",
            "4.3.1.4",
            "4.3.1.5",
        ],
    ),
    service_name="FC Port %s",
    discovery_function=discover_qlogic_fcport,
    check_function=check_qlogic_fcport,
)

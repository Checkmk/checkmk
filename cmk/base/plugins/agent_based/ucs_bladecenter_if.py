#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Union

from .agent_based_api.v1 import register, type_defs
from .utils import interfaces, ucs_bladecenter

# <<ucs_bladecenter_if:sep(9)>>>
# fcStats Dn sys/switch-A/slot-1/switch-fc/port-37/stats  BytesRx 2411057759048   BytesTx 1350394110752   Suspect no
# fcStats Dn sys/switch-A/slot-1/switch-fc/port-40/stats  BytesRx 0   BytesTx 0   Suspect no
# fcErrStats      Dn sys/switch-B/slot-1/switch-fc/port-47/err-stats      CrcRx 0 DiscardRx 0     DiscardTx 0
# fcErrStats      Dn sys/switch-B/slot-1/switch-fc/port-48/err-stats      CrcRx 0 DiscardRx 0     DiscardTx 0
# fabricFcSanEp   Dn fabric/san/A/phys-slot-1-port-40     EpDn sys/switch-A/slot-1/switch-fc/port-40      AdminState disabled     OperState up
# fabricFcSanEp   Dn fabric/san/A/phys-slot-1-port-41     EpDn sys/switch-A/slot-1/switch-fc/port-41      AdminState disabled     OperState up

# Example interfaces
# fibrechannel:
# 'sys/switch-A/slot-1/switch-fc/port-38':
#           {'AdminState': 'enabled',
#            'BytesRx': '51789849113704',
#            'BytesTx': '15914991789936',
#            'CrcRx': '1',
#            'DiscardRx': '0',
#            'DiscardTx': '0',
#            'EpDn': 'sys/switch-A/slot-1/switch-fc/port-38',
#            'OperState': 'up',
#            'PacketsRx': '26771306796',
#            'PacketsTx': '8735571946',
#            'PortId': '38',
#            'Rx': '1',
#            'SlotId': '1',
#            'Suspect': 'no',
#            'SwitchId': 'A',
#            'Tx': '0'},
# ethernet:
# 'sys/switch-A/slot-1/switch-ether/port-18':
#           {'AdminState': 'enabled',
#            'Dn': 'fabric/lan/A/pc-1/ep-slot-1-port-18',
#            'EpDn': 'sys/switch-A/slot-1/switch-ether/port-18',
#            'OperState': 'up',
#            'PortId': '18',
#            'SlotId': '1',
#            'SwitchId': 'A',
#            'etherRxStats': {'BroadcastPackets': '116544272',
#                             'Dn': 'sys/switch-A/slot-1/switch-ether/port-18/rx-stats',
#                             'MulticastPackets': '560456841',
#                             'TotalBytes': '53066141169147',
#                             'UnicastPackets': '138412352259'},
#            'etherTxStats': {'BroadcastPackets': '4922247',
#                             'Dn': 'sys/switch-A/slot-1/switch-ether/port-18/tx-stats',
#                             'MulticastPackets': '82743790',
#                             'TotalBytes': '79420242621595',
#                             'UnicastPackets': '135007642584'},
# interconnect:
# 'sys/switch-A/slot-1/switch-ether/port-2':
#            {'AdminState': 'enabled',
#             'Dn': 'fabric/server/sw-A/pc-1025/ep-slot-1-port-2',
#             'EpDn': 'sys/switch-A/slot-1/switch-ether/port-2',
#             'OperState': 'up',
#             'PortId': '2',
#             'SlotId': '1',
#             'SwitchId': 'A',
#             'etherErrStats': {'Dn': 'sys/switch-A/slot-1/switch-ether/port-2/err-stats',
#                               'OutDiscard': '0',
#                               'Rcv': '0'},
#             'etherRxStats': {'BroadcastPackets': '50432549',
#                              'Dn': 'sys/switch-A/slot-1/switch-ether/port-2/rx-stats',
#                              'MulticastPackets': '80349542',
#                              'TotalBytes': '50633308808192',
#                              'UnicastPackets': '53535107978'},
#             'etherTxStats': {'BroadcastPackets': '4892153',
#                              'Dn': 'sys/switch-A/slot-1/switch-ether/port-2/tx-stats',
#                              'MulticastPackets': '328878878',
#                              'TotalBytes': '97004901202254',
#                              'UnicastPackets': '79555260499'},
#             'portchannel': {'AdminState': 'enabled',
#                             'Dn': 'fabric/server/sw-A/pc-1025',
#                             'OperSpeed': '10gbps',
#                             'OperState': 'up',
#                             'PortId': '1025',
#                             'members': 4}},

# Specify which values are to put into the resulting interface
_UCS_FIELDS_TO_IF_FIELDS = {
    "fibrechannel": {
        "in_octets": [("fcStats", "BytesRx")],
        "in_ucast": [("fcStats", "PacketsRx")],
        "in_discards": [("fcErrStats", "DiscardRx")],
        "in_errors": [("fcErrStats", "Rx"), ("fcErrStats", "CrcRx")],
        "out_octets": [("fcStats", "BytesTx")],
        "out_ucast": [("fcStats", "PacketsTx")],
        "out_discards": [("fcErrStats", "DiscardTx")],
        "out_errors": [("fcErrStats", "Tx")],
    },
    "ethernet": {
        "in_octets": [("etherRxStats", "TotalBytes")],
        "in_ucast": [("etherRxStats", "UnicastPackets")],
        "in_mcast": [("etherRxStats", "MulticastPackets")],
        "in_bcast": [("etherRxStats", "BroadcastPackets")],
        "in_errors": [("etherErrStats", "Rcv")],
        "out_octets": [("etherTxStats", "TotalBytes")],
        "out_ucast": [("etherTxStats", "UnicastPackets")],
        "out_mcast": [("etherTxStats", "MulticastPackets")],
        "out_bcast": [("etherTxStats", "BroadcastPackets")],
        "out_discards": [("etherErrStats", "OutDiscard")],
    },
    "interconnect": {
        "in_octets": [("etherRxStats", "TotalBytes")],
        "in_ucast": [("etherRxStats", "UnicastPackets")],
        "in_mcast": [("etherRxStats", "MulticastPackets")],
        "in_bcast": [("etherRxStats", "BroadcastPackets")],
        "in_errors": [("etherErrStats", "Rcv")],
        "out_octets": [("etherTxStats", "TotalBytes")],
        "out_ucast": [("etherTxStats", "UnicastPackets")],
        "out_mcast": [("etherTxStats", "MulticastPackets")],
        "out_bcast": [("etherTxStats", "BroadcastPackets")],
        "out_discards": [("etherErrStats", "OutDiscard")],
    },
}


def parse_ucs_bladecenter_if(string_table: type_defs.StringTable) -> interfaces.Section:
    data = ucs_bladecenter.generic_parse(string_table)
    converted = []
    last_index = 0
    for what, group_prefix, ifaces, item_template in [
        (
            "fibrechannel",
            "Fibrechannel-Group",
            _parse_fc_interfaces(data),
            "Slot %s FC-Switch %s Port %s",
        ),
        ("ethernet", "Ethernet-Group", _parse_eth_interfaces(data), "Slot %s Switch %s Port %s"),
        (
            "interconnect",
            "Interconnect-Group",
            _parse_icnt_interfaces(data),
            "Slot %s IC-Switch %s Port %s",
        ),
    ]:
        index = 0
        for index, (_name, values) in enumerate(ifaces.items()):
            item = item_template % (
                values.get("SlotId"),
                values.get("SwitchId"),
                values.get("PortId"),
            )
            iface_index = str(last_index + index)

            # Interfaces in portchannels are grouped by setting the group-attribute of
            # interfaces.Interface
            if "portchannel" in values:
                port_name = values["portchannel"].get("Name")
                if not port_name:
                    port_name = values["portchannel"].get("PortId", "")

                group = group_prefix + " " + port_name
                speed = values["portchannel"].get("AdminSpeed") or values["portchannel"].get(
                    "OperSpeed", ""
                )
                # It looks like that the AdminSpeed of a portchannel is the speed of one member
                # speed = str(int(float(speed.replace("gbps", "000000000")) / values["portchannel"]["members"]))
                is_up = (
                    values["portchannel"].get("AdminState", "disabled") == "enabled"
                    and values["portchannel"].get("OperState", "down") == "up"
                )
            else:
                group = None
                speed = values.get("AdminSpeed", "")
                is_up = (
                    values.get("AdminState", "disabled") == "enabled"
                    and values.get("OperState", "down") == "up"
                )

            speed = speed.replace("gbps", "000000000")

            iface = interfaces.Interface(
                index=iface_index,
                descr=item,
                alias=item,
                # This means Ethernet. We should set the real type here, but 56 is currently not
                # supported.
                type="6",
                speed=interfaces.saveint(speed),
                oper_status=is_up and "1" or "2",
                group=group,
                # On summing keys there is a possiblility to overlook some counter wraps.
                # Right now, it's only Recv-Errors (therefore unlikely). We can live with that
                **{  # type: ignore[arg-type]
                    iface_field: sum(
                        int(values[ctr_class].get(ctr_key, "0")) for ctr_class, ctr_key in ctr_keys
                    )
                    for iface_field, ctr_keys in _UCS_FIELDS_TO_IF_FIELDS[what].items()
                },
            )

            converted.append(iface)

        last_index += index + 1

    return converted


def _extract_counters(
    data,
    counter_specs,
    ifaces,
):
    for what, cut in counter_specs:
        if what in data:
            for key, values in data[what].items():
                fc_name = key[:-cut]
                if fc_name in ifaces:
                    ifaces[fc_name].setdefault(what, {})
                    ifaces[key[:-cut]][what].update(values)
    return ifaces


PleaseDont = Dict[str, Dict[str, Union[str, Dict[str, str]]]]


def _parse_fc_interfaces(data):
    """Fibrechannels"""
    fc_interfaces: PleaseDont = {}
    for values in data.get("fabricFcSanEp", {}).values():
        fc_interfaces.setdefault(values["EpDn"], {}).update(values)
    # TODO: fabricFcSanPc
    # TODO: fabricFcSanPcEp
    return _extract_counters(
        data,
        [("fcStats", 6), ("fcErrStats", 10)],
        fc_interfaces,
    )


def _parse_eth_interfaces(data):
    eth_interfaces: PleaseDont = {}
    for key, values in data.get("fabricEthLanEp", {}).items():
        eth_interfaces.setdefault(values["EpDn"], {}).update(values)

    # Get info for each portchannel
    eth_pc_info = {}
    for key, values in data.get("fabricEthLanPc", {}).items():
        eth_pc_info[key] = values

    # Ethernet-Portchannel Members
    for key, values in data.get("fabricEthLanPcEp", {}).items():
        pc_name = "/".join(values["Dn"].split("/")[:-1])
        values["portchannel"] = eth_pc_info[pc_name]
        eth_pc_info[pc_name].setdefault("members", 0)
        eth_pc_info[pc_name]["members"] += 1
        eth_interfaces.setdefault(values["EpDn"], {}).update(values)

    return _extract_counters(
        data,
        [("etherRxStats", 9), ("etherTxStats", 9), ("etherErrStats", 10)],
        eth_interfaces,
    )


def _parse_icnt_interfaces(data):
    icnt_interfaces: PleaseDont = {}
    for key, values in data.get("fabricDceSwEp", {}).items():
        icnt_interfaces.setdefault(values["EpDn"], {}).update(values)

    for key, values in data.get("fabricDceSwSrvEp", {}).items():
        icnt_interfaces.setdefault(values["EpDn"], {}).update(values)

    # Get info for each portchannel
    icnt_pc_info = {}
    for key, values in data.get("fabricDceSwSrvPc", {}).items():
        icnt_pc_info[key] = values

    # Interconnect-Portchannel Members
    for key, values in data.get("fabricDceSwSrvPcEp", {}).items():
        if len(values.get("Dn").split("/")[:-1]) == 4:
            pc_name = "/".join(values["Dn"].split("/")[:-1])
        else:
            pc_name = "/".join(values["Dn"].split("/")[:-2])
        values["portchannel"] = icnt_pc_info[pc_name]
        icnt_pc_info[pc_name].setdefault("members", 0)
        icnt_pc_info[pc_name]["members"] += 1
        icnt_interfaces.setdefault(values["EpDn"], {}).update(values)

    return _extract_counters(
        data,
        [("etherRxStats", 9), ("etherTxStats", 9), ("etherErrStats", 10)],
        icnt_interfaces,
    )


register.agent_section(
    name="ucs_bladecenter_if",
    parse_function=parse_ucs_bladecenter_if,
    parsed_section_name="interfaces",
)

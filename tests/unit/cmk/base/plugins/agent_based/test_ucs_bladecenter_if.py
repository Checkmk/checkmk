#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.ucs_bladecenter_if import parse_ucs_bladecenter_if
from cmk.base.plugins.agent_based.utils.interfaces import Interface


def test_parse_ucs_bladecenter_if() -> None:
    assert parse_ucs_bladecenter_if(
        [
            [
                "fcStats",
                "Dn sys/switch-B/slot-1/switch-fc/port-5/stats",
                "BytesRx 6000859585097280",
                "BytesTx 11433477817196880",
                "PacketsRx 3199011900400260",
                "PacketsTx 2858352274430040",
                "Suspect no",
            ],
            [
                "fcStats",
                "Dn sys/switch-A/slot-1/switch-fc/port-5/stats",
                "BytesRx 6269002983258720",
                "BytesTx 11970108210903360",
                "PacketsRx 3349919871277380",
                "PacketsTx 2992509872856660",
                "Suspect no",
            ],
            [
                "fcErrStats",
                "Dn sys/switch-B/slot-1/switch-fc/port-5/err-stats",
                "Rx 714588068607510",
                "Tx 0",
                "CrcRx 0",
                "DiscardRx 0",
                "DiscardTx 0",
            ],
            [
                "fcErrStats",
                "Dn sys/switch-A/slot-1/switch-fc/port-5/err-stats",
                "Rx 748131763181460",
                "Tx 0",
                "CrcRx 0",
                "DiscardRx 0",
                "DiscardTx 0",
            ],
            [
                "fabricFcSanEp",
                "Dn fabric/san/A/phys-slot-1-port-5",
                "EpDn sys/switch-A/slot-1/switch-fc/port-5",
                "AdminState disabled",
                "OperState up",
                "PortId 5",
                "SwitchId A",
                "SlotId 1",
            ],
            [
                "fabricFcSanEp",
                "Dn fabric/san/B/phys-slot-1-port-5",
                "EpDn sys/switch-B/slot-1/switch-fc/port-5",
                "AdminState disabled",
                "OperState up",
                "PortId 5",
                "SwitchId B",
                "SlotId 1",
            ],
        ]
    ) == [
        Interface(
            index="0",
            descr="Slot 1 FC-Switch A Port 5",
            alias="Slot 1 FC-Switch A Port 5",
            type="6",
            speed=0,
            oper_status="2",
            in_octets=6269002983258720,
            in_ucast=3349919871277380,
            in_mcast=0,
            in_bcast=0,
            in_discards=0,
            in_errors=748131763181460,
            out_octets=11970108210903360,
            out_ucast=2992509872856660,
            out_mcast=0,
            out_bcast=0,
            out_discards=0,
            out_errors=0,
            out_qlen=0,
            oper_status_name="down",
            total_octets=18239111194162080,
        ),
        Interface(
            index="1",
            descr="Slot 1 FC-Switch B Port 5",
            alias="Slot 1 FC-Switch B Port 5",
            type="6",
            speed=0,
            oper_status="2",
            in_octets=6000859585097280,
            in_ucast=3199011900400260,
            in_mcast=0,
            in_bcast=0,
            in_discards=0,
            in_errors=714588068607510,
            out_octets=11433477817196880,
            out_ucast=2858352274430040,
            out_mcast=0,
            out_bcast=0,
            out_discards=0,
            out_errors=0,
            out_qlen=0,
            oper_status_name="down",
            total_octets=17434337402294160,
        ),
    ]

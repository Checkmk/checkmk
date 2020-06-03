#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# .1.3.6.1.2.1.1.1.0 Linux gateway1 2.6.18-92cp #1 SMP Tue Dec 4 21:44:22 IST 2012 i686
# .1.3.6.1.4.1.2620.1.1.25.3.0 19190

from cmk.base.plugins.agent_based.agent_based_api.v0 import register, SNMPTree
from cmk.base.plugins.agent_based.utils import checkpoint


def parse_checkpoint_vsx(string_table):
    parsed = {}
    status_table, counter_table = string_table

    vsid_info = [s + c for (s, c) in zip(status_table, counter_table)]

    for vs_id, vs_name, vs_type, vs_ip, vs_policy, vs_policy_type, \
        vs_sic_status, vs_ha_status, conn_num, conn_table_size, packets, \
        packets_dropped, packets_accepted, packets_rejected, bytes_accepted, \
        bytes_dropped, bytes_rejected, logged in vsid_info:

        item = "%s %s" % (vs_name, vs_id)
        parsed.setdefault(
            item, {
                "vs_name": vs_name,
                "vs_type": vs_type,
                "vs_sic_status": vs_sic_status,
                "vs_ha_status": vs_ha_status,
                "vs_ip": vs_ip,
                "vs_policy": vs_policy,
                "vs_policy_type": vs_policy_type,
            })

        inst = parsed.setdefault(item, {})
        for key, value in [
            ("conn_num", conn_num),
            ("conn_table_size", conn_table_size),
            ("packets", packets),
            ("packets_dropped", packets_dropped),
            ("packets_accepted", packets_accepted),
            ("packets_rejected", packets_rejected),
            ("bytes_accepted", bytes_accepted),
            ("bytes_dropped", bytes_dropped),
            ("bytes_rejected", bytes_rejected),
            ("logged", logged),
        ]:
            try:
                inst[key] = int(value)
            except ValueError:
                pass

    return parsed


register.snmp_section(
    name="checkpoint_vsx",
    parse_function=parse_checkpoint_vsx,
    detect=checkpoint.DETECT,
    trees=[  # SNMPTree(base=".1.3.6.1.4.1.2620.1.1.25", oids=['3'])
        SNMPTree(
            base='.1.3.6.1.4.1.2620.1.16.22.1.1',  # CHECKPOINT-MIB:vsxStatusTable:vsxStatusEntry
            oids=[
                '1',  # vsxStatusVSId
                '3',  # vsxStatusVsName
                '4',  # vsxStatusVsType
                '5',  # vsxStatusMainIP
                '6',  # vsxStatusPolicyName
                '7',  # vsxStatusVsPolicyType
                '8',  # vsxStatusSicTrustState
                '9',  # vsxStatusHAState
            ]),
        SNMPTree(
            base='.1.3.6.1.4.1.2620.1.16.23.1.1',  # CHECKPOINT-MIB:vsxCountersTable:vsxCountersEntry
            oids=[
                '2',  # vsxCountersConnNum
                '4',  # vsxCountersConnTableLimit
                '5',  # vsxCountersPackets
                '6',  # vsxCountersDroppedTotal
                '7',  # vsxCountersAcceptedTotal
                '8',  # vsxCountersRejectedTotal
                '9',  # vsxCountersBytesAcceptedTotal
                '10',  # vsxCountersBytesDroppedTotal
                '11',  # vsxCountersBytesRejectedTotal
                '12',  # vsxCountersLoggedTotal
            ]),
    ],
)

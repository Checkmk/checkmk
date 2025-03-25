#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections import defaultdict

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPTree, StringTable
from cmk.plugins.lib.cisco_ucs import DETECT, Fault, FaultSeverity

type Section = dict[str, list[Fault]]  # FIXME


def parse_cisco_ucs_fault(string_table: StringTable) -> Section:
    faults = defaultdict(list)
    for fault_object_id, fault_ack, fault_code, fault_description, fault_severity in string_table:
        faults[fault_object_id].append(
            Fault(
                acknowledge=(int(fault_ack) == 1),
                code=fault_code,
                description=fault_description,
                severity=FaultSeverity(fault_severity),
            )
        )

    return faults


snmp_section_cisco_ucs_fault = SimpleSNMPSection(
    name="cisco_ucs_fault",
    parse_function=parse_cisco_ucs_fault,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.1.1.1",
        oids=[
            "5",  # .1.3.6.1.4.1.9.9.719.1.1.1.1.5 cucsFaultAffectedObjectDn
            "6",  # .1.3.6.1.4.1.9.9.719.1.1.1.1.6 cucsFaultAck
            "9",  # .1.3.6.1.4.1.9.9.719.1.1.1.1.9 cucsFaultCode
            "11",  # .1.3.6.1.4.1.9.9.719.1.1.1.1.11 cucsFaultDescription
            "20",  # .1.3.6.1.4.1.9.9.719.1.1.1.1.20 cucsFaultSeverity
        ],
    ),
    detect=DETECT,
)

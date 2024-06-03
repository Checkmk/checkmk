#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Some (or all?) Eaton USVs yield MIBs that are labeled "Merlin Gerin".
# This module provides sections that read out the corresponding OIDs.


from collections.abc import Sequence

from cmk.agent_based.v2 import SimpleSNMPSection, SNMPSection, SNMPTree, startswith, StringTable
from cmk.plugins.lib.ups import Battery, optional_int, optional_yes_or_no

DETECT_UPS_EATON_MG = startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.705")


def parse_battery_capacity_eaton_mg(string_table: StringTable) -> Battery | None:
    return (
        Battery(
            seconds_left=optional_int(string_table[0][0]),
            percent_charged=optional_int(string_table[0][1]),
        )
        if string_table
        else None
    )


def parse_on_battery_eaton_mg(string_table: StringTable) -> Battery | None:
    return (
        Battery(
            on_battery=optional_yes_or_no(string_table[0][0]),
        )
        if string_table
        else None
    )


def parse_battery_warnings_eaton_mg(string_table: Sequence[StringTable]) -> Battery | None:
    if not any(string_table):
        return None

    return Battery(
        fault=optional_yes_or_no(string_table[0][0][0]),
        replace=optional_yes_or_no(string_table[0][0][1]),
        low=optional_yes_or_no(string_table[0][0][2]),
        not_charging=optional_yes_or_no(string_table[0][0][3]),
        low_condition=optional_yes_or_no(string_table[0][0][4]),
        on_bypass=optional_yes_or_no(string_table[1][0][0]),
        backup=optional_yes_or_no(string_table[1][0][1]),
        overload=optional_yes_or_no(string_table[1][0][2]),
    )


snmp_section_ups_battery_capacity_eaton_mg = SimpleSNMPSection(
    name="ups_battery_capacity_eaton_mg",
    parsed_section_name="ups_battery_capacity",
    parse_function=parse_battery_capacity_eaton_mg,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.705.1.5",
        oids=[
            "1.0",  # Remaining battery backup time  [sec], int
            "2.0",  # Battery charge level           [%], int
        ],
    ),
    detect=DETECT_UPS_EATON_MG,
    supersedes=["ups_battery_capacity"],
)

# Note: This value ("on_battery") comes from a vendor-specific ("Merlin Gerin")
# table and differs from the generic "time_on_battery" signal
snmp_section_ups_on_battery_eaton_mg = SimpleSNMPSection(
    name="ups_on_battery_eaton_mg",
    parsed_section_name="ups_on_battery",
    parse_function=parse_on_battery_eaton_mg,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.705.1.7",
        oids=[
            "3.0",  # UPS is on battery              yes: 1, no: 2
        ],
    ),
    detect=DETECT_UPS_EATON_MG,
)

snmp_section_ups_battery_warnings_eaton_mg = SNMPSection(
    name="ups_battery_warnings_eaton_mg",
    parsed_section_name="ups_battery_warnings",
    parse_function=parse_battery_warnings_eaton_mg,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.705.1.5",
            oids=[
                "9.0",  # Battery fault indicator        yes: 1, no: 2
                "11.0",  # Battery to be replaced        yes: 1, no: 2
                "14.0",  # Low battery                   yes: 1, no: 2
                "15.0",  # Battery not charging          yes: 1, no: 2
                "16.0",  # Battery at low condition      yes: 1, no: 2
            ],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.705.1.7",
            oids=[
                "4.0",  # UPS is on bypass               yes: 1, no: 2
                "7.0",  # UPS is in battery backup time  yes: 1, no: 2
                "10.0",  # Overload                      yes: 1, no: 2
            ],
        ),
    ],
    detect=DETECT_UPS_EATON_MG,
)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from contextlib import suppress
from typing import NamedTuple, Optional

from .agent_based_api.v1 import all_of, Attributes, exists, register, SNMPTree
from .agent_based_api.v1.type_defs import InventoryResult, StringTable


class Section(NamedTuple):
    serial: str
    expresscode: str
    bios_date: Optional[float]
    bios_version: str
    bios_vendor: str
    raid_name: str
    raid_version: str


def parse_dell_hw_info(string_table: StringTable) -> Optional[Section]:
    for line in string_table:
        return Section(
            serial=line[0],
            expresscode=line[1],
            bios_date=_format_date(line[2]),
            bios_version=line[3],
            bios_vendor=line[4],
            raid_name=line[5],
            raid_version=line[6],
        )
    return None


def _format_date(raw_date: str) -> Optional[float]:
    if fmt := _get_date_format(raw_date):
        return time.mktime(time.strptime(raw_date, fmt))
    return None


def _get_date_format(date: str) -> Optional[str]:
    # Beware: Dell's actual definition of the format supposed
    # to be here is yyyymmddHHMMSS.uuuuuu+ooo. This has *never*
    # been observed in the wild. More accurate appears to be
    # mm/dd/yyyy or 0mm/dd/yyyy or mm/0dd/yyyy. The 0 represents a
    # random 0 thrown in for good measure :/
    with suppress(IndexError):
        if date[2] == "/" and date[5] == "/":  # mm/dd/yyyy
            return "%m/%d/%Y"
        if date[3] == "/" and date[6] == "/":  # 0mm/dd/yyyy
            return "0%m/%d/%Y"
        if date[2] == "/" and date[6] == "/":  # mm/0dd/yyyy
            return "%m/0%d/%Y"
        if "/" not in date[:8]:  # In case of Dell devices following the MIB
            return "%Y%m%d"

    return None


register.snmp_section(
    name="dell_hw_info",
    parse_function=parse_dell_hw_info,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.674.10892.5",
        oids=[
            "1.3.2.0",  # IDRAC-MIB::systemServiceTag
            "1.3.3.0",  # IDRAC-MIB::systemExpressServiceCode
            "4.300.50.1.7.1.1",  # IDRAC-MIB::systemBIOSReleaseDateName
            "4.300.50.1.8.1.1",  # IDRAC-MIB::systemBIOSVersionName
            "4.300.50.1.11.1.1",  # IDRAC-MIB::systemBIOSManufacturerName
            "5.1.20.130.1.1.2.1",  # IDRAC-MIB::controllerName
            "5.1.20.130.1.1.8.1",  # IDRAC-MIB::controllerFWVersion
        ],
    ),
    detect=all_of(
        exists(".1.3.6.1.4.1.674.*"),  # shared with dell_compellent_ checks (performance!)
        exists(".1.3.6.1.4.1.674.10892.5.1.1.1.0"),
    ),
)


def inventory_dell_hw_info(section: Section) -> InventoryResult:

    yield Attributes(
        path=["hardware", "system"],
        inventory_attributes={
            "serial": section.serial,
            "expresscode": section.expresscode,
        },
    )

    yield Attributes(
        path=["software", "bios"],
        inventory_attributes={
            "version": section.bios_version,
            "vendor": section.bios_vendor,
            **({} if section.bios_date is None else {"date": section.bios_date}),
        },
    )

    yield Attributes(
        path=["hardware", "storage", "controller"],
        inventory_attributes={
            "version": section.raid_version,
            "name": section.raid_name,
        },
    )


register.inventory_plugin(
    name="dell_hw_info",
    inventory_function=inventory_dell_hw_info,
)

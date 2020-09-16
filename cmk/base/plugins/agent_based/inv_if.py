#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import time
from typing import List, Optional, Union

from .agent_based_api.v1.type_defs import InventoryResult, Parameters
from .agent_based_api.v1 import Attributes, register, TableRow
from .utils import interfaces


# TODO unify with other if inventory plugins
def inventory_if(
    params: Parameters,
    section_inv_if: Optional[List],
    section_snmp_uptime: Optional[int],
) -> InventoryResult:
    if section_inv_if is None or section_snmp_uptime is None:
        return

    def round_to_day(ts):
        broken = time.localtime(ts)
        return time.mktime((broken.tm_year, broken.tm_mon, broken.tm_mday, 0, 0, 0, broken.tm_wday,
                            broken.tm_yday, broken.tm_isdst))

    now = time.time()

    usage_port_types = params.get(
        "usage_port_types",
        ['6', '32', '62', '117', '127', '128', '129', '180', '181', '182', '205', '229'])
    unused_duration = params.get("unused_duration", 30 * 86400)

    total_ethernet_ports = 0
    available_ethernet_ports = 0

    for (if_index, if_descr, if_alias, if_type, if_speed, if_high_speed, if_oper_status,
         if_admin_status, if_phys_address, if_last_change) in section_inv_if:

        if if_type in ("231", "232"):
            continue  # Useless entries for "TenGigabitEthernet2/1/21--Uncontrolled"

        if not if_last_change or not if_speed:
            continue  # Ignore useless half-empty tables (e.g. Viprinet-Router)

        # if_last_change can be of type Timeticks (100th of seconds) or
        # a human readable time stamp (yurks)
        try:
            last_change = float(if_last_change) / 100.0
        except Exception:
            # Example: 0:0:01:09.96
            parts = if_last_change.split(":")
            days = int(parts[0])
            hours = int(parts[1])
            minutes = int(parts[2])
            seconds = float(parts[3])
            last_change = seconds + 60 * minutes + 3600 * hours + 86400 * days

        if if_high_speed:
            speed = int(if_high_speed) * 1000 * 1000
        else:
            speed = int(if_speed)

        if last_change > 0:
            state_age = section_snmp_uptime - last_change

            # Assume counter rollover in case uptime is less than last_change and
            # add 497 days (counter maximum).
            # This way no negative chenge times are shown anymore. The state change is shown
            # wrong in case it's really 497 days ago when state changed but there's no way to
            # get the count of rollovers since change (or since uptime) and it's better the
            # wrong negative state change is not shown anymore...
            if state_age < 0:
                state_age = 42949672 - last_change + section_snmp_uptime

        else:
            # Assume point of time of boot as last state change.
            state_age = section_snmp_uptime

        last_change_timestamp = round_to_day(now - state_age)

        # in case ifIndex is missing
        try:
            if_index_nr: Union[str, int] = int(if_index)
        except ValueError:
            if_index_nr = ""

        interface_row = {
            "speed": speed,
            "phys_address": interfaces.render_mac_address(if_phys_address),
            "oper_status": int(if_oper_status),
            "admin_status": int(if_admin_status),  # 1(up) or 2(down)
            "port_type": int(if_type),
        }

        if if_type in usage_port_types:
            total_ethernet_ports += 1
            if_available = if_oper_status == '2' and state_age > unused_duration
            if if_available:
                available_ethernet_ports += 1
            interface_row["available"] = if_available

        yield TableRow(path=["networking", "interfaces"],
                       key_columns={"index": if_index_nr},
                       inventory_columns=interface_row,
                       status_columns={
                           "description": if_descr,
                           "alias": if_alias,
                           "last_change": int(last_change_timestamp),
                       })

    yield Attributes(
        path=["networking"],
        inventory_attributes={
            "available_ethernet_ports": str(available_ethernet_ports),
            "total_ethernet_ports": str(total_ethernet_ports),
            "total_interfaces": str(len(section_inv_if)),
        },
    )


register.inventory_plugin(
    name='inv_if',
    inventory_function=inventory_if,
    inventory_default_parameters={},
    inventory_ruleset_name="inv_if",
    sections=["inv_if", "snmp_uptime"],
)

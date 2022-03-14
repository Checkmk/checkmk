#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from dataclasses import dataclass
from typing import Container, Iterable, Optional, TypedDict, Union

from ..agent_based_api.v1 import Attributes, TableRow
from ..agent_based_api.v1.type_defs import InventoryResult


@dataclass
class Interface:
    index: str
    descr: str
    alias: str
    type: str
    speed: int
    oper_status: int
    phys_address: str
    admin_status: Optional[int] = None
    last_change: Optional[float] = None


class InventoryParams(TypedDict, total=False):
    unused_duration: int
    usage_port_types: Container[str]


def _round_to_day(ts: float) -> float:
    broken = time.localtime(ts)
    return time.mktime(
        (
            broken.tm_year,
            broken.tm_mon,
            broken.tm_mday,
            0,
            0,
            0,
            broken.tm_wday,
            broken.tm_yday,
            broken.tm_isdst,
        )
    )


def _state_age(uptime_sec: float, last_change: float) -> float:
    if last_change <= 0:
        return uptime_sec
    # Assume counter rollover in case uptime is less than last_change and
    # add 497 days (counter maximum).
    # This way no negative change times are shown anymore. The state change is shown
    # wrong in case it's really 497 days ago when state changed but there's no way to
    # get the count of rollovers since change (or since uptime) and it's better the
    # wrong negative state change is not shown anymore...
    if (state_age := uptime_sec - last_change) < 0:
        return 42949672 - last_change + uptime_sec
    return state_age


def inventorize_interfaces(
    params: InventoryParams,
    interfaces: Iterable[Interface],
    n_total: int,
    uptime_sec: Optional[float] = None,
) -> InventoryResult:

    now = time.time()

    usage_port_types = params.get(
        "usage_port_types",
        ["6", "32", "62", "117", "127", "128", "129", "180", "181", "182", "205", "229"],
    )
    unused_duration = params.get("unused_duration", 30 * 86400)

    total_ethernet_ports = 0
    available_ethernet_ports = 0

    for interface in interfaces:
        state_age = (
            _state_age(uptime_sec, interface.last_change)
            if uptime_sec is not None and interface.last_change is not None
            else None
        )
        last_change_timestamp = _round_to_day(now - state_age) if state_age is not None else None
        try:
            if_index_nr: Union[str, int] = int(interface.index)
        except ValueError:
            if_index_nr = ""

        if_available = None
        if interface.type in usage_port_types:
            total_ethernet_ports += 1
            if if_available := (
                interface.oper_status == 2 and (state_age is None or state_age > unused_duration)
            ):
                available_ethernet_ports += 1

        yield TableRow(
            path=["networking", "interfaces"],
            key_columns={
                "index": if_index_nr,
                "description": interface.descr,
                "alias": interface.alias,
            },
            inventory_columns={
                "speed": interface.speed,
                "phys_address": interface.phys_address,
                "oper_status": interface.oper_status,
                "port_type": int(interface.type),
                **(
                    {"admin_status": interface.admin_status}
                    if interface.admin_status is not None
                    else {}
                ),
                **({"available": if_available} if if_available is not None else {}),
            },
            status_columns={
                "last_change": int(last_change_timestamp),
            }
            if last_change_timestamp is not None
            else {},
        )

    yield Attributes(
        path=["networking"],
        inventory_attributes={
            "available_ethernet_ports": available_ethernet_ports,
            "total_ethernet_ports": total_ethernet_ports,
            "total_interfaces": n_total,
        },
    )

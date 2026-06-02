#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from re import Pattern
from typing import NamedTuple, TypedDict


class GlobalIdent(TypedDict):
    site_id: str
    program_id: str
    instance_id: str


class HostOrder(NamedTuple):
    """What to do for a host"""

    folder_path: str
    delete_hosts: bool
    host_attributes: dict[str, object]
    host_filters: list[Pattern[str]]
    connector_name: str


def find_order(host: str, orders: Sequence[HostOrder]) -> HostOrder | None:
    for order in orders:
        if not order.host_filters or any(f.match(host) for f in order.host_filters):
            return order
    return None


# Plugin-apis stays str-only; downstream specialises ``HostT`` to e.g.
# ``cmk.ccc.hostaddress.HostName`` to preserve strong typing without
# making plugin-apis depend on cmk-ccc.
class ChangeDirective[HostT: str](NamedTuple):
    """Hint how to apply changes to the site"""

    ident: GlobalIdent
    site_id: str
    hosts: Sequence[HostT]
    is_delete_allowed: bool
    all_host_orders: Sequence[HostOrder]
    # Per-host attributes that override (are merged on top of) the attributes of the matched
    # ``HostOrder``. Used by connectors that derive attributes from each host's own data, e.g.
    # the metric backend connector storing the resolved host name template attributes.
    host_attributes_overrides: Mapping[HostT, Mapping[str, object]] = {}

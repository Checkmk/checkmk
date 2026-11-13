#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.livestatus_client import LocalConnection
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Hosts
from cmk.product_usage.schema import InventoryData


def collect() -> InventoryData:
    # mk_inventory_last is 0 for hosts without HW/SW inventory data
    query = Query([Hosts.name]).filter(Hosts.mk_inventory_last > 0)
    return InventoryData(hosts_with_inventory=len(LocalConnection().query(query)))

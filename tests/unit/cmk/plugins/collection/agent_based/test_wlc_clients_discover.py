#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Service
from cmk.plugins.collection.agent_based.wlc_clients import discover_wlc_clients
from cmk.plugins.lib.wlc_clients import ClientsTotal, WlcClientsSection


def test_discover_wlc_clients_skips_empty_ssid() -> None:
    section = WlcClientsSection[ClientsTotal](
        total_clients=5,
        clients_per_ssid={"": ClientsTotal(total=5)},
    )

    services = list(discover_wlc_clients(section))

    assert services == [Service(item="Summary")]

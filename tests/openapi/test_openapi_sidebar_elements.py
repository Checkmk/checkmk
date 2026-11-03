#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.sidebar._snapin import all_snapins
from tests.testlib.unit.rest_api_client import ClientRegistry


def test_list_test_openapi_sidebar_element(clients: ClientRegistry) -> None:
    all_sidebar_elements = clients.SidebarElement.get_all().json["value"]
    snapins = all_snapins()

    assert len(all_sidebar_elements) == len(snapins)
    for key, snapin in snapins.items():
        assert key in [d["id"] for d in all_sidebar_elements]
        assert snapin.title() in [d["title"] for d in all_sidebar_elements]

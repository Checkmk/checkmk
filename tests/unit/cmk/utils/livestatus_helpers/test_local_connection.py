#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import livestatus

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection


def test_local_table_assoc(patch_omd_site: None, mock_livestatus: MockLiveStatusConnection) -> None:
    live = mock_livestatus
    live.set_sites(["NO_SITE"])
    live.add_table(
        "hosts",
        [
            {
                "name": "example.com",
                "alias": "example.com alias",
                "address": "server.example.com",
                "custom_variables": {
                    "FILENAME": "/wato/hosts.mk",
                    "ADDRESS_FAMILY": "4",
                    "ADDRESS_4": "127.0.0.1",
                    "ADDRESS_6": "",
                    "TAGS": "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
                },
                "contacts": [],
                "contact_groups": ["all"],
            }
        ],
        site="NO_SITE",
    )
    live.expect_query(
        [
            "GET hosts",
            "Columns: name alias address custom_variables contacts contact_groups",
            "ColumnHeaders: on",
        ]
    )
    with live(expect_status_query=False):
        livestatus.LocalConnection().query_table_assoc(
            "GET hosts\nColumns: name alias address custom_variables contacts contact_groups"
        )

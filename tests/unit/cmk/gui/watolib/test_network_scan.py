#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

from cmk.utils.user import UserId

from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.network_scan import execute_network_scan_job


def test_scan_run_as_a_missing_user_is_recorded_as_failed(with_admin_login: UserId) -> None:
    folder_tree().root_folder().create_subfolder(
        "netscan",
        "NetScan",
        HostAttributes(
            {
                "network_scan": {
                    "exclude_ranges": [],
                    "ip_ranges": [("ip_range", ("10.3.1.1", "10.3.1.100"))],
                    "run_as": UserId("deleted_user"),
                    "scan_interval": 300,
                    "set_ipaddress": True,
                    "time_allowed": [((0, 0), (24, 0))],
                },
            }
        ),
    )

    execute_network_scan_job()

    result = folder_tree().folder("netscan").attributes["network_scan_result"]
    assert result["state"] is False
    assert "deleted_user" in result["output"]

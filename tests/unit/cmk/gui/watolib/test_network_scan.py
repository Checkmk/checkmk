#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.logged_in import LoggedInSuperUser
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import FolderTree, make_folder_tree
from cmk.gui.watolib.network_scan import execute_network_scan_job
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.livestatus_client import SiteConfigurations


def test_scan_run_as_a_missing_user_is_recorded_as_failed(
    config: Config, tree: FolderTree, with_admin: tuple[UserId, str]
) -> None:
    tree.root_folder().create_subfolder(
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
        pprint_value=False,
        pending_changes=PendingChanges(
            activation_sites=SiteConfigurations({}),
            local_site=SiteId("NO_SITE"),
            acting_user=None,
            store=NoopPendingChangesStore(),
            hooks=(),
        ),
        acting_user=LoggedInSuperUser(),
    )

    execute_network_scan_job(config)

    result = make_folder_tree(config).folder("netscan").attributes["network_scan_result"]
    assert result["state"] is False
    assert "deleted_user" in result["output"]

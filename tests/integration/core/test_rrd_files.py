#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from datetime import datetime

import pytest

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site


@pytest.mark.skip_if_edition("raw")
def test_rrd_files_creation(site: Site) -> None:
    """Test that RRD files are created for a hosts.

    Steps:

    1. Create a host with a specific configuration and activate changes.
    2. Check if the RRD file for PING is created.
    3. Verify the last update timestamp of the RRD file.
    """
    # Save the current timestamp before creating the host
    timestamp_before = datetime.now().timestamp()

    # Create a simple host
    site.openapi.hosts.create(
        hostname="test_host",
        attributes={
            "tag_address_family": "ip-v4-only",
            "ipaddress": "127.0.0.1",
            "tag_agent": "no-agent",
        },
    )

    # Activate the changes and wait for PING service to be executed
    site.activate_changes_and_wait_for_core_reload(allow_foreign_changes=True)
    site.wait_until_service_has_been_checked("test_host", "PING")

    # Check that the rrd file for PING is created
    file_path = "var/check_mk/rrd/test_host/PING.rrd"
    wait_until(
        lambda: site.file_exists(file_path),
        timeout=10,
        condition_name="RRD file for PING service creation",
    )

    # Get the information of the RRD file
    rrd_info = site.check_output(["rrdtool", "info", str(site.path(file_path))])

    # Check that the last_update timestamp is greater than or equal to the timestamp before host creation
    last_update_search_result = re.search(r"last_update = (?P<last_update_timestamp>\d+)", rrd_info)
    assert last_update_search_result is not None, "last_update not found in RRD info"

    last_update_timestamp = int(last_update_search_result.group("last_update_timestamp"))
    assert last_update_timestamp >= timestamp_before, (
        f"last_update of rrd file info ({last_update_timestamp}) is previous"
        f" than timestamp before host creation ({timestamp_before})"
    )

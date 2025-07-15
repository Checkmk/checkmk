#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from tests.testlib.unit.rest_api_client import ClientRegistry
from tests.unit.cmk.web_test_app import SetConfig


@pytest.mark.usefixtures("suppress_remote_automation_calls")
def test_openapi_wato_disabled_blocks_query(
    clients: ClientRegistry,
    mock_livestatus: MockLiveStatusConnection,
    set_config: SetConfig,
) -> None:
    live: MockLiveStatusConnection = mock_livestatus

    # add a host, so we can query it
    clients.HostConfig.create("neute", folder="/")

    live.expect_query(
        [
            "GET services",
            "Columns: host_name description",
        ]
    )

    # calls to setup endpoints work correctly
    clients.HostConfig.get("neute")

    # disable wato
    with set_config(wato_enabled=False):
        # calls to setup endpoints are forbidden
        clients.HostConfig.get("neute", expect_ok=False).assert_status_code(403)
        with live:
            # calls to monitoring endpoints should be allowed
            clients.Service.get_all()

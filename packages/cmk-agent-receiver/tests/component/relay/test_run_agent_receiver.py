#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi.testclient import TestClient

from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_health_check(test_client: TestClient, site: SiteMock) -> None:
    """Verify that the agent receiver application is running and responds to health check requests.

    Test steps:
    1. Send request to openapi.json endpoint
    2. Verify successful response
    3. Confirm agent receiver is running
    """
    response = test_client.get(f"/{site.site_name}/agent-receiver/openapi.json")
    assert response.status_code == 200

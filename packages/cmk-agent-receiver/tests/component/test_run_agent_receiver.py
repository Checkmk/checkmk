#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.main import main_app


@pytest.fixture(scope="session")
def agent_receiver_test_client() -> TestClient:
    app = main_app()
    client = TestClient(app)
    return client


@pytest.mark.skip(
    reason="This test cannot be run until agent_receiver_test_client is able to start the agent receiver process"
)
def test_health_check(agent_receiver_test_client: TestClient) -> None:
    response = agent_receiver_test_client.get("/my_component_test_site/agent-receiver")
    assert response.status_code == 200

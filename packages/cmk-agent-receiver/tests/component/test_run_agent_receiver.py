#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pathlib

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.main import main_app


@pytest.fixture()
def agent_receiver_test_client(tmp_path: pathlib.Path) -> TestClient:
    # setting up some checkmk stuff required by the agent receiver
    base_dir = tmp_path / "my_component_test_site"
    os.environ["OMD_ROOT"] = str(base_dir)
    os.environ["OMD_SITE"] = "my_component_test_site"
    log_dir = base_dir / "var" / "log" / "agent-receiver"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "agent-receiver.log").touch()

    # start the app
    app = main_app()
    client = TestClient(app)
    return client


def test_health_check(agent_receiver_test_client: TestClient) -> None:
    response = agent_receiver_test_client.get("/my_component_test_site/agent-receiver/openapi.json")
    assert response.status_code == 200

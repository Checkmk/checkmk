#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi.testclient import TestClient


def test_health_check(site_name: str, agent_receiver_test_client: TestClient) -> None:
    response = agent_receiver_test_client.get(f"/{site_name}/agent-receiver/openapi.json")
    assert response.status_code == 200

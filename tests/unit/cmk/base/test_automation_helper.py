#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi.testclient import TestClient

from cmk.base import automation_helper


def get_test_client() -> TestClient:
    """Helper for fetching fastapi test client."""
    app = automation_helper.get_application()
    return TestClient(app)


def test_health_check() -> None:
    client = get_test_client()

    value = client.get("/health").status_code
    expected = 200

    assert value == expected

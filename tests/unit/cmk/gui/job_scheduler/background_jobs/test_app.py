#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi.testclient import TestClient

from cmk.gui.job_scheduler._background_jobs._app import get_application, HealthResponse


def _get_test_client(loaded_at: int) -> TestClient:
    return TestClient(get_application(loaded_at=loaded_at))


def test_health_check() -> None:
    with _get_test_client(loaded_at=(loaded_at := 1337)) as client:
        resp = client.get("/health")

    assert resp.status_code == 200
    assert HealthResponse.model_validate(resp.json()).loaded_at == loaded_at

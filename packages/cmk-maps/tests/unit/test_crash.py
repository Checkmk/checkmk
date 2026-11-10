#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Crash reports: unhandled exceptions must land in the Checkmk crash store."""

import base64
import json
from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import cmk.ccc.version_info as cmk_version_info
from cmk.maps.backend import main
from cmk.maps.backend.core.crash import crash_report, save_crash_report
from cmk.maps.backend.core.ratelimit import CRASH_REPORT_KEY, RateLimiter
from cmk.maps.backend.schemas.connection import ConnectionConfig


@pytest.fixture(name="version_infos")
def fixture_version_infos(monkeypatch: pytest.MonkeyPatch) -> None:
    """The real helper reads the site's version symlink, which a tmp_path
    OMD root doesn't have — pin the environment-independent variant."""
    monkeypatch.setattr(
        cmk_version_info,
        "get_general_version_infos",
        lambda _omd_root: cmk_version_info.general_version_infos(
            edition=lambda: "cee", core=lambda: "cmc"
        ),
    )


def test_create_crash_report_persists_to_the_store(tmp_path: Path, version_infos: None) -> None:  # noqa: ARG001
    try:
        raise ValueError("boom")
    except ValueError:
        crash_id = save_crash_report(crash_report(tmp_path))

    crash_dir = tmp_path / "var" / "check_mk" / "crashes" / "maps" / crash_id
    assert (crash_dir / "crash.info").exists()


def test_a_crash_report_holds_no_connection_secret(tmp_path: Path, version_infos: None) -> None:  # noqa: ARG001
    connection = ConnectionConfig(
        id="c1", host="h", automation_user="automation", automation_secret="s3cr3t"
    )
    try:
        raise ValueError(connection.id)
    except ValueError:
        crash_id = save_crash_report(crash_report(tmp_path))

    crash_info = json.loads(
        (tmp_path / "var" / "check_mk" / "crashes" / "maps" / crash_id / "crash.info").read_text()
    )
    local_vars = base64.b64decode(crash_info["local_vars"]).decode()
    assert "automation" in local_vars
    assert "s3cr3t" not in local_vars


@pytest.fixture(name="crash_store")
def fixture_crash_store(tmp_path: Path, version_infos: None) -> Path:  # noqa: ARG001
    return tmp_path / "var" / "check_mk" / "crashes" / "maps"


def _crashing(omd_root: Path, limiter: RateLimiter | None = None) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(
        Exception,
        main.crash_handler(omd_root, limiter or RateLimiter(max_calls=30, window_seconds=60)),
    )

    @app.get("/crash")
    async def _boom() -> None:
        raise RuntimeError("boom")

    return TestClient(app, raise_server_exceptions=False)


def test_unhandled_request_exception_returns_500_with_crash_id(
    tmp_path: Path, crash_store: Path
) -> None:
    response = _crashing(tmp_path).get("/crash")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json()["detail"] == "Internal server error"
    crash_info = json.loads((crash_store / response.json()["crash_id"] / "crash.info").read_text())
    assert (crash_info["exc_type"], crash_info["exc_value"]) == ("RuntimeError", "boom")


@pytest.mark.usefixtures("crash_store")
def test_a_crash_is_answered_with_the_security_headers(tmp_path: Path) -> None:
    response = _crashing(tmp_path).get("/crash")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")


def test_crashes_past_the_limit_are_only_logged(tmp_path: Path, crash_store: Path) -> None:
    spent = RateLimiter(max_calls=1, window_seconds=60)
    spent.record(CRASH_REPORT_KEY)

    response = _crashing(tmp_path, spent).get("/crash")

    assert response.json()["crash_id"] == "n/a"
    assert not crash_store.exists()

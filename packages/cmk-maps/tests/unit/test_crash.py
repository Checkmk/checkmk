#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Crash reports: unhandled exceptions must land in the Checkmk crash store."""

from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import cmk.ccc.version_info as cmk_version_info
from cmk.maps.backend import main
from cmk.maps.backend.core.crash import create_crash_report


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
        crash_id = create_crash_report(tmp_path)

    crash_dir = tmp_path / "var" / "check_mk" / "crashes" / "maps" / crash_id
    assert (crash_dir / "crash.info").exists()


def test_unhandled_request_exception_returns_500_with_crash_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "create_crash_report", lambda _omd_root: "deadbeef-crash-id")

    @main.app.get("/test-unhandled-crash")
    async def _boom() -> None:
        raise RuntimeError("boom")

    client = TestClient(main.app, raise_server_exceptions=False)
    response = client.get("/test-unhandled-crash")

    assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert response.json() == {
        "detail": "Internal server error",
        "crash_id": "deadbeef-crash-id",
    }


def test_a_crash_is_answered_with_the_security_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "create_crash_report", lambda _omd_root: "deadbeef-crash-id")

    @main.app.get("/test-crash-headers")
    async def _boom() -> None:
        raise RuntimeError("boom")

    response = TestClient(main.app, raise_server_exceptions=False).get("/test-crash-headers")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["content-security-policy"].startswith("default-src 'none'")

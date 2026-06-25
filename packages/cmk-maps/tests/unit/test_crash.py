#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Crash reports: unhandled exceptions must land in the Checkmk crash store."""

import base64
import json
from pathlib import Path
from typing import NoReturn

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


def test_stream_token_is_not_persisted_in_crash_local_vars(
    tmp_path: Path,
    version_infos: None,  # noqa: ARG001
) -> None:
    # The SSE stream token is a replayable credential (valid until its short TTL).
    # A crash raised while it is in scope must not persist it into the crash
    # report's captured local variables: cmk.crash redacts locals whose name
    # matches a sensitive keyword, and the daemon names the token local ``token``.
    # Pin that here so renaming the local (or storing the raw token on a non-
    # sensitively-named object) can't silently start leaking it onto disk — the
    # crash store is part of ``omd backup`` and readable via the crash reports UI.
    secret_token = "maps-stream-DO-NOT-LEAK.deadbeefsig"

    def _sse_handler_frame(token: str) -> NoReturn:  # noqa: ARG001
        raise RuntimeError("boom while the stream token is in scope")

    try:
        _sse_handler_frame(secret_token)
    except RuntimeError:
        crash_id = create_crash_report(tmp_path)

    crash_info = json.loads(
        (tmp_path / "var" / "check_mk" / "crashes" / "maps" / crash_id / "crash.info").read_text()
    )
    local_vars = base64.b64decode(crash_info["local_vars"]).decode()
    assert secret_token not in local_vars
    assert "redacted" in local_vars


def test_unhandled_request_exception_returns_500_with_crash_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "create_crash_report", lambda _omd_root: "deadbeef-crash-id")

    @main.app.get("/test-unhandled-crash")
    async def _boom() -> None:
        raise RuntimeError("boom")

    client = TestClient(main.app, raise_server_exceptions=False)
    response = client.get("/test-unhandled-crash")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error",
        "crash_id": "deadbeef-crash-id",
    }

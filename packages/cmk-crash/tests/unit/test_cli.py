#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for cmk.crash_reporting.cli.

Network calls are intercepted with `responses`; no real OMD site is needed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import responses

from cmk.ccc.site import omd_site
from cmk.crash_reporting import cli

_CRASH_URL = "https://crash.checkmk.com"


def _write_global_mk(path: Path, **settings: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(f"{key} = {value!r}" for key, value in settings.items()))


@pytest.fixture(autouse=True)
def _fake_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))
    monkeypatch.setenv("OMD_SITE", "mysite")
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes"])
    omd_site.cache_clear()


def _global_mk_path(tmp_path: Path) -> Path:
    return tmp_path / "etc/check_mk/multisite.d/wato/global.mk"


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param(None, id="no-settings-file"),
        pytest.param({"automatic_crash_report_upload": None}, id="explicitly-disabled"),
        pytest.param({"automatic_crash_report_upload": ""}, id="empty-address"),
        pytest.param({"automatic_crash_report_upload": True}, id="non-string-value"),
    ],
)
def test_gate_blocks_upload_is_silent_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, settings: dict[str, object] | None
) -> None:
    if settings is not None:
        _write_global_mk(_global_mk_path(tmp_path), **settings)
    called = False

    def _fake_run_batch(**_kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(cli, "run_batch", _fake_run_batch)
    assert cli.main() == 0
    assert not called


def test_toggle_on_with_email_calls_run_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )
    captured: dict[str, object] = {}

    def _fake_run_batch(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(cli, "run_batch", _fake_run_batch)
    assert cli.main() == 0
    assert captured["mail"] == "admin@example.com"
    assert captured["name"] == "community mysite"
    assert captured["crash_report_url"] == _CRASH_URL
    assert captured["dry_run"] is False


def test_crash_report_url_override_is_honored(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
        crash_report_url="https://crash.example.com",
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli, "run_batch", lambda **kwargs: captured.update(kwargs))
    cli.main()
    assert captured["crash_report_url"] == "https://crash.example.com"


def test_dry_run_flag_passed_through(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )
    captured: dict[str, object] = {}
    monkeypatch.setattr(cli, "run_batch", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes", "--dry-run"])
    cli.main()
    assert captured["dry_run"] is True


@responses.activate
def test_end_to_end_uploads_via_real_run_batch(tmp_path: Path) -> None:
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )
    crash_dir = tmp_path / "var/check_mk/crashes/check/11111111-1111-1111-1111-111111111111"
    crash_dir.mkdir(parents=True)
    (crash_dir / "crash.info").write_bytes(b'{"id": "11111111-1111-1111-1111-111111111111"}')
    responses.add(responses.POST, _CRASH_URL, body=b"OK abc123", status=200)

    assert cli.main() == 0
    assert len(responses.calls) == 1
    assert (crash_dir / ".uploaded").exists()

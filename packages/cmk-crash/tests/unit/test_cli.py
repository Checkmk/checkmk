#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for cmk.crash_reporting.cli.

Network calls are intercepted with `responses`; no real OMD site is needed.
"""

from collections.abc import Iterator
from logging import getLogger
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
def _fake_site(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("OMD_ROOT", str(tmp_path))
    monkeypatch.setenv("OMD_SITE", "mysite")
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes"])
    (tmp_path / "var/log").mkdir(parents=True)  # part of the site skeleton
    omd_site.cache_clear()
    root = getLogger()
    installed_before = root.handlers[:]
    yield
    # setup_logging() installs on the process-global root logger, so its handler outlives
    # the test. Drop only what this test added - pytest keeps caplog and --log-file
    # handlers on root too, and closing those silences every later test.
    for handler in root.handlers:
        if handler not in installed_before:
            handler.close()
    root.handlers[:] = installed_before


def _global_mk_path(tmp_path: Path) -> Path:
    return tmp_path / "etc/check_mk/multisite.d/wato/global.mk"


def _next_run_path(tmp_path: Path) -> Path:
    return tmp_path / "var/check_mk/crash_upload_next_run"


def _arm_upload_slot(tmp_path: Path) -> None:
    """Put the schedule past due, so a --cron run uploads instead of arming its slot."""
    _next_run_path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    _next_run_path(tmp_path).write_text("0")


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


def test_manual_run_logs_to_stderr_and_keeps_no_schedule(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )

    assert cli.main() == 0

    assert "Crash upload summary" in capsys.readouterr().err
    assert not _next_run_path(tmp_path).exists()


def test_cron_run_logs_to_file_instead_of_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )
    _arm_upload_slot(tmp_path)
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes", "--cron"])

    assert cli.main() == 0

    assert capsys.readouterr().err == ""
    assert "Crash upload summary" in (tmp_path / "var/log/crash-upload.log").read_text()


def test_cron_run_while_disabled_does_nothing_observable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Arming while disabled would delay the first upload by up to a day once the admin
    opts in, so the slot must stay untouched until past the enabled check."""
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes", "--cron"])

    assert cli.main() == 0

    assert not (tmp_path / "var/log/crash-upload.log").exists()
    assert not _next_run_path(tmp_path).exists()


def test_cron_first_run_arms_its_slot_instead_of_uploading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes", "--cron"])
    uploads: list[object] = []
    monkeypatch.setattr(cli, "run_batch", lambda **kwargs: uploads.append(kwargs))

    assert cli.main() == 0

    assert not uploads
    assert _next_run_path(tmp_path).exists()


def test_cron_run_before_the_next_due_point_does_not_upload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pins the claim happening before the upload: claiming afterwards would let a tick
    overlapping a still-running batch upload a second time."""
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )
    _arm_upload_slot(tmp_path)
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes", "--cron"])
    assert cli.main() == 0  # uploads, and schedules a day on
    uploads: list[object] = []
    monkeypatch.setattr(cli, "run_batch", lambda **kwargs: uploads.append(kwargs))

    assert cli.main() == 0

    assert not uploads


def test_dry_run_under_cron_is_rejected() -> None:
    with pytest.raises(SystemExit):
        cli.parse_arguments(["--cron", "--dry-run"])


def test_cron_run_logs_an_upload_failure_to_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cron mails stderr only when CONFIG_ADMIN_MAIL is set, and it is empty by default."""
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )
    _arm_upload_slot(tmp_path)
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes", "--cron"])

    def _explode(**_kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "run_batch", _explode)

    assert cli.main() == 1

    logged = (tmp_path / "var/log/crash-upload.log").read_text()
    assert "RuntimeError: boom" in logged


def test_cron_run_logs_a_schedule_failure_to_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Claiming the slot touches the filesystem under a lock, so it can fail on its own -
    and its traceback must reach the log file rather than the discarded stderr."""
    _write_global_mk(
        _global_mk_path(tmp_path),
        automatic_crash_report_upload="admin@example.com",
    )
    monkeypatch.setattr("sys.argv", ["cmk-upload-crashes", "--cron"])

    def _explode(*_args: object) -> bool:
        raise PermissionError("var/check_mk not writable")

    monkeypatch.setattr(cli, "claim_due_run", _explode)

    assert cli.main() == 1

    assert "PermissionError" in (tmp_path / "var/log/crash-upload.log").read_text()


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

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import runpy
import shlex
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

import pytest

from cmk.testlib.notification_plugins import exit_code

_SPOOL_DIR: Final = Path("/var/spool/sms/outgoing")

_CONTEXT: Final = {
    "CONTACTNAME": "admin",
    "CONTACTPAGER": "+49 151 1234567",
    "HOSTNAME": "web01",
    "WHAT": "SERVICE",
    "NOTIFICATIONTYPE": "PROBLEM",
    "SERVICESTATE": "CRITICAL",
    "SERVICEDESC": "CPU load",
    "SERVICEOUTPUT": "it's " + "x" * 200,
}


def _run_sms_script() -> None:
    runpy.run_module("notifications.sms", run_name="__main__")


def _install_sendsms(bin_dir: Path, returncode: int) -> Path:
    record = bin_dir / "record"
    script = bin_dir / "sendsms"
    script.write_text(
        f"#!/bin/sh\nprintf '%s\\n' \"$@\" > {shlex.quote(str(record))}\nexit {returncode}\n"
    )
    script.chmod(0o755)
    return record


@pytest.fixture(name="bin_dir")
def fixture_bin_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("PATH", str(tmp_path))
    return tmp_path


def test_sms_is_handed_to_sendsms(
    bin_dir: Path, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    record = _install_sendsms(bin_dir, returncode=0)
    notify_context(_CONTEXT)

    _run_sms_script()

    recipient, _message = record.read_text().splitlines()
    assert recipient == "+491511234567"


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="message is shell-quoted although sendsms is called without a shell",
)
def test_sms_text_reaches_sendsms_verbatim(
    bin_dir: Path, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    record = _install_sendsms(bin_dir, returncode=0)
    notify_context(_CONTEXT)

    _run_sms_script()

    _recipient, message = record.read_text().splitlines()
    assert message == ("web01 CR CPU load " + _CONTEXT["SERVICEOUTPUT"])[:160]


def test_failing_sendsms_is_a_temporary_error(
    bin_dir: Path, notify_context: Callable[[Mapping[str, str]], None]
) -> None:
    _install_sendsms(bin_dir, returncode=1)
    notify_context(_CONTEXT)

    assert exit_code(_run_sms_script) == 1


@pytest.mark.parametrize(
    "pager, error",
    [
        pytest.param(" ", "Error: Pager Number of admin not set", id="missing"),
        pytest.param("+49;reboot", "Error: Pager Number of admin is not a valid", id="invalid"),
    ],
)
def test_unusable_pager_number_is_a_fatal_error(
    pager: str,
    error: str,
    bin_dir: Path,
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    _install_sendsms(bin_dir, returncode=0)
    notify_context({**_CONTEXT, "CONTACTPAGER": pager})

    assert exit_code(_run_sms_script) == 2
    assert error in capsys.readouterr().err


@pytest.mark.skipif(_SPOOL_DIR.exists(), reason="SMS tools spool directory exists")
@pytest.mark.usefixtures("bin_dir")
def test_missing_sms_tools_is_a_fatal_error(
    notify_context: Callable[[Mapping[str, str]], None],
    capsys: pytest.CaptureFixture[str],
) -> None:
    notify_context(_CONTEXT)

    assert exit_code(_run_sms_script) == 2
    assert "SMS Tools binaries (sendsms or smssend) not found" in capsys.readouterr().err

#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
from pathlib import Path

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.events.notify import ensure_utf8, NotificationHostConfig, read_notify_host_file


@pytest.fixture(name="fake_locale")
def fixture_fake_locale(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Directory for a fake `locale` command, which ensure_utf8 finds via PATH"""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", str(bin_dir))
    # ensure_utf8 changes LANG of the whole process, this restores it afterwards
    monkeypatch.setenv("LANG", os.environ.get("LANG", "C"))
    return bin_dir


_NO_UTF8_LOCALE = [
    pytest.param(["C", "POSIX"], 0, id="no UTF-8 locale"),
    pytest.param([], 1, id="locale command fails"),
]


def _install_locale(bin_dir: Path, *, locales: list[str], exit_code: int = 0) -> None:
    output = "".join(f"{locale}\\n" for locale in locales)
    script = bin_dir / "locale"
    script.write_text(f"#!/bin/sh\nprintf '{output}'\nexit {exit_code}\n")
    script.chmod(0o755)


def _lang_of_child_processes() -> str:
    return subprocess.run(
        ["/bin/sh", "-c", 'printf %s "$LANG"'], capture_output=True, text=True, check=True
    ).stdout


@pytest.mark.parametrize(
    "logger",
    [
        pytest.param(None, id="without logger"),
        pytest.param(logging.getLogger("test"), id="with logger"),
    ],
)
def test_utf8_locale_is_used_for_child_processes(
    fake_locale: Path, logger: logging.Logger | None
) -> None:
    _install_locale(fake_locale, locales=["C", "POSIX", "en_US.utf8"])

    ensure_utf8(logger)

    assert _lang_of_child_processes() == "en_US.utf8"


@pytest.mark.parametrize("locales, exit_code", _NO_UTF8_LOCALE)
def test_missing_utf8_locale_is_an_error_without_logger(
    fake_locale: Path, locales: list[str], exit_code: int
) -> None:
    _install_locale(fake_locale, locales=locales, exit_code=exit_code)

    with pytest.raises(MKGeneralException, match="No UTF-8 encoding found"):
        ensure_utf8()


@pytest.mark.parametrize("locales, exit_code", _NO_UTF8_LOCALE)
def test_missing_utf8_locale_is_logged_with_logger(
    fake_locale: Path, locales: list[str], exit_code: int, caplog: pytest.LogCaptureFixture
) -> None:
    _install_locale(fake_locale, locales=locales, exit_code=exit_code)

    with caplog.at_level(logging.INFO, logger="test"):
        ensure_utf8(logging.getLogger("test"))

    assert "No UTF-8 encoding found" in caplog.text


def test_unknown_host_has_empty_notification_config(tmp_path: Path) -> None:
    assert read_notify_host_file(HostName("unknown"), tmp_path) == NotificationHostConfig(
        host_labels={}, service_labels={}, tags={}
    )

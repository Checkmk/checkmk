#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import signal
from collections.abc import Iterator

import pytest

from cmk.gui.job_scheduler.main import run_with_crash_reporting

_LOGGER = logging.getLogger("test")


class _CrashReports:
    def __init__(self) -> None:
        self.reported: list[Exception] = []

    def __call__(self, exc: Exception) -> str:
        self.reported.append(exc)
        return "crash-id"


@pytest.fixture
def restore_sigterm_handler() -> Iterator[None]:
    # run_with_crash_reporting installs its own SIGTERM handler
    original = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGTERM, original)


def _terminate_while_building_model() -> None:
    # pydantic-core wraps a SystemExit raised while it builds a model serializer in a
    # SchemaError. This mimics the wrapping without depending on pydantic internals.
    try:
        signal.raise_signal(signal.SIGTERM)
    except SystemExit as exc:
        raise RuntimeError(f"Error building serializer: SystemExit: {exc.code}") from None


@pytest.mark.usefixtures("restore_sigterm_handler")
def test_sigterm_surfacing_wrapped_exits_cleanly_without_crash_report() -> None:
    crash_reports = _CrashReports()

    exit_code = run_with_crash_reporting(_terminate_while_building_model, crash_reports, _LOGGER)

    assert exit_code == 0
    assert not crash_reports.reported


@pytest.mark.usefixtures("restore_sigterm_handler")
def test_sigterm_exits_with_code_0() -> None:
    crash_reports = _CrashReports()

    with pytest.raises(SystemExit) as exc_info:
        run_with_crash_reporting(
            lambda: signal.raise_signal(signal.SIGTERM), crash_reports, _LOGGER
        )

    assert exc_info.value.code == 0
    assert not crash_reports.reported


@pytest.mark.usefixtures("restore_sigterm_handler")
def test_unexpected_exception_creates_crash_report() -> None:
    crash_reports = _CrashReports()
    error = RuntimeError("boom")

    def run() -> None:
        raise error

    exit_code = run_with_crash_reporting(run, crash_reports, _LOGGER)

    assert exit_code == 1
    assert crash_reports.reported == [error]

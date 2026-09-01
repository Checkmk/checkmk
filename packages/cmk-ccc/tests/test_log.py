#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import logging
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.ccc.log import CMKFormatter


def _record() -> logging.LogRecord:
    record = logging.LogRecord(
        name="cmk.web",
        level=logging.INFO,
        pathname="path.py",
        lineno=1,
        msg="the message",
        args=None,
        exc_info=None,
    )
    record.process = 12345
    record.processName = "cmk-worker"
    record.threadName = "worker-2"
    return record


# Summer in Europe/Berlin (+02:00); the 500us margin absorbs float64 epoch rounding.
_FROZEN = datetime.datetime(2026, 6, 26, 14, 32, 45, 123500, tzinfo=ZoneInfo("Europe/Berlin"))


@pytest.mark.parametrize(
    ["formatter_kwargs", "expected"],
    [
        pytest.param(
            {},
            "2026-06-26 14:32:45.123+02:00 [cmk.web] [INFO] the message",
            id="logger name only",
        ),
        pytest.param(
            {"with_process": True},
            "2026-06-26 14:32:45.123+02:00 [cmk.web cmk-worker(12345)] [INFO] the message",
            id="process as name(pid)",
        ),
        pytest.param(
            {"with_thread": True},
            "2026-06-26 14:32:45.123+02:00 [cmk.web worker-2] [INFO] the message",
            id="thread as its name alone",
        ),
        pytest.param(
            {"with_process": True, "with_thread": True},
            "2026-06-26 14:32:45.123+02:00 [cmk.web cmk-worker(12345) worker-2] [INFO] the message",
            id="process before thread",
        ),
    ],
)
@time_machine.travel(_FROZEN)
def test_cmk_formatter_renders_the_requested_fields(
    formatter_kwargs: dict[str, bool], expected: str
) -> None:
    assert CMKFormatter(**formatter_kwargs).format(_record()) == expected


@pytest.mark.parametrize(
    ["formatter_kwargs", "expected"],
    [
        pytest.param(
            {"with_process": True},
            "2026-06-26 14:32:45,123 [20] [cmk.web 12345] the message",
            id="numeric level before the logger, bare pid, no timezone",
        ),
        pytest.param(
            {"with_process": True, "with_thread": True},
            "2026-06-26 14:32:45,123 [20] [cmk.web 12345 worker-2] the message",
            id="thread name appended plainly",
        ),
    ],
)
@time_machine.travel(_FROZEN)
def test_cmk_formatter_legacy_matches_historical_format(
    formatter_kwargs: dict[str, bool], expected: str
) -> None:
    assert CMKFormatter(legacy=True, **formatter_kwargs).format(_record()) == expected


@time_machine.travel(_FROZEN)
def test_cmk_formatter_leaves_exception_rendering_to_the_base_formatter() -> None:
    try:
        raise ValueError("boom")
    except ValueError as exc:
        record = _record()
        record.exc_info = (type(exc), exc, exc.__traceback__)
    line, _, traceback = CMKFormatter(with_process=True).format(record).partition("\n")
    assert line == "2026-06-26 14:32:45.123+02:00 [cmk.web cmk-worker(12345)] [INFO] the message"
    assert traceback.startswith("Traceback (most recent call last):")
    assert traceback.endswith("ValueError: boom")

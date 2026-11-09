#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import logging
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.ccc.log import CMKFormatter, log_to_watched_file, VERBOSE, verbosity_to_log_level


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


@time_machine.travel(_FROZEN)
def test_cmk_formatter_message_only_renders_bare_message() -> None:
    assert CMKFormatter(message_only=True).format(_record()) == "the message"


@time_machine.travel(_FROZEN)
def test_cmk_formatter_message_only_takes_precedence() -> None:
    assert (
        CMKFormatter(message_only=True, with_process=True, with_thread=True, legacy=True).format(
            _record()
        )
        == "the message"
    )


def test_the_verbose_level_has_a_name() -> None:
    assert logging.getLevelName(VERBOSE) == "VERBOSE"


def test_without_verbosity_the_log_level_is_info() -> None:
    assert verbosity_to_log_level(0) == logging.INFO


def test_one_verbosity_is_the_verbose_level() -> None:
    assert verbosity_to_log_level(1) == VERBOSE


def test_two_verbosities_are_debug() -> None:
    assert verbosity_to_log_level(2) == logging.DEBUG


def test_more_verbosity_than_we_know_stays_debug() -> None:
    assert verbosity_to_log_level(23) == logging.DEBUG


def test_watched_file_logging_writes_to_the_given_file(tmp_path: Path) -> None:
    logger = logging.getLogger("test_watched_file_logging_writes_to_the_given_file")
    path = tmp_path / "cmk.log"

    log_to_watched_file(logger, path)
    logger.error("a message")

    assert "a message" in path.read_text()


def test_watched_file_logging_replaces_the_handlers_it_finds(tmp_path: Path) -> None:
    logger = logging.getLogger("test_watched_file_logging_replaces_the_handlers_it_finds")
    logger.addHandler(logging.NullHandler())

    log_to_watched_file(logger, tmp_path / "cmk.log")

    assert len(logger.handlers) == 1

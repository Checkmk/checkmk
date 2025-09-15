#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Final

import pytest
from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
)

from cmk.base.automation_helper._cache import Cache
from cmk.base.automation_helper._watcher import _AutomationWatcherHandler
from tests.testlib.common.utils import wait_until

_WATCHED_MK_PATTERN: Final = "*.mk"
_WATCHED_TXT_FILE: Final = "foo.txt"
_WATCHED_DIRECTORY_PATTERN: Final = "some_dir*"
_WATCHED_DIRECTORY = "some_dir"
_MK_FILE: Final = "foo.mk"


@pytest.fixture(name="file_watcher_handler")
def get_file_watcher_handler(cache: Cache) -> _AutomationWatcherHandler:
    return _AutomationWatcherHandler(
        cache=cache, patterns=[_WATCHED_MK_PATTERN, "*.txt"], ignore_directories=True
    )


@pytest.fixture(name="directory_watcher_handler")
def get_directory_watcher_handler(cache: Cache) -> _AutomationWatcherHandler:
    return _AutomationWatcherHandler(
        cache=cache, patterns=[_WATCHED_DIRECTORY_PATTERN], ignore_directories=False
    )


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(
            FileMovedEvent(src_path="", dest_path=_MK_FILE),
            f"Source: n/a, destination: {_MK_FILE}, type: moved",
            id="file moved umwatched to watched directory",
        ),
        pytest.param(
            FileMovedEvent(src_path=_MK_FILE, dest_path=""),
            "Source: foo.mk, destination: n/a, type: moved",
            id="file moved from watched to unwatched directory",
        ),
        pytest.param(
            FileMovedEvent(src_path=_MK_FILE, dest_path="bar.mk"),
            f"Source: {_MK_FILE}, destination: bar.mk, type: moved",
            id="file moved within watched directory",
        ),
        pytest.param(
            FileCreatedEvent(src_path=_MK_FILE),
            f"Source: {_MK_FILE}, destination: n/a, type: created",
            id="mk-file created",
        ),
        pytest.param(
            FileCreatedEvent(src_path=_WATCHED_TXT_FILE),
            f"Source: {_WATCHED_TXT_FILE}, destination: n/a, type: created",
            id="txt-file created",
        ),
        pytest.param(
            FileModifiedEvent(src_path=_MK_FILE),
            f"Source: {_MK_FILE}, destination: n/a, type: modified",
            id="file modified",
        ),
        pytest.param(
            FileDeletedEvent(src_path=_MK_FILE),
            f"Source: {_MK_FILE}, destination: n/a, type: deleted",
            id="file deleted",
        ),
    ],
)
def test_automation_watcher_logging_pattern_match(
    caplog: pytest.LogCaptureFixture,
    file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
    output: str,
) -> None:
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)

    assert output in caplog.text


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(FileMovedEvent(src_path="", dest_path="foo.bar"), id="no match overwritten"),
        pytest.param(FileCreatedEvent(src_path="foo.bar"), id="no match created"),
        pytest.param(FileModifiedEvent(src_path="foo.bar"), id="no match modified"),
        pytest.param(FileDeletedEvent(src_path="foo.bar"), id="no match deleted"),
    ],
)
def test_automation_watcher_logging_no_match(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)
    assert cache.get_last_detected_change() == last_change_reference
    assert not caplog.text


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(
            DirMovedEvent(src_path="", dest_path=_WATCHED_DIRECTORY),
            f"Source: n/a, destination: {_WATCHED_DIRECTORY}, type: moved",
            id="dir moved from unwatched to watched directory",
        ),
        pytest.param(
            DirMovedEvent(src_path=_WATCHED_DIRECTORY, dest_path=""),
            f"Source: {_WATCHED_DIRECTORY}, destination: n/a, type: moved",
            id="dir moved from watched to unwatched directory",
        ),
        pytest.param(
            DirMovedEvent(src_path=_WATCHED_DIRECTORY, dest_path=f"{_WATCHED_DIRECTORY}2"),
            f"Source: {_WATCHED_DIRECTORY}, destination: {_WATCHED_DIRECTORY}2, type: moved",
            id="watched dir moved to watched dir",
        ),
        pytest.param(
            DirCreatedEvent(src_path=_WATCHED_DIRECTORY),
            f"Source: {_WATCHED_DIRECTORY}, destination: n/a, type: created",
            id="dir created",
        ),
        pytest.param(
            DirModifiedEvent(src_path=_WATCHED_DIRECTORY),
            f"Source: {_WATCHED_DIRECTORY}, destination: n/a, type: modified",
            id="dir modified",
        ),
        pytest.param(
            DirDeletedEvent(src_path=_WATCHED_DIRECTORY),
            f"Source: {_WATCHED_DIRECTORY}, destination: n/a, type: deleted",
            id="dir deleted",
        ),
    ],
)
def test_automation_watcher_logging_directory_match(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    directory_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
    output: str,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO):
        directory_watcher_handler.dispatch(event)
    assert cache.get_last_detected_change() > last_change_reference
    assert output in caplog.text


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(
            DirMovedEvent(src_path="", dest_path=_WATCHED_DIRECTORY),
            id="no match dir overwritten",
        ),
        pytest.param(DirCreatedEvent(src_path=_WATCHED_DIRECTORY), id="no match dir created"),
        pytest.param(DirModifiedEvent(src_path=_WATCHED_DIRECTORY), id="no match dir modified"),
        pytest.param(DirDeletedEvent(src_path=_WATCHED_DIRECTORY), id="no match dir deleted"),
    ],
)
def test_automation_watcher_logging_directories_ignored(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)
    assert cache.get_last_detected_change() == last_change_reference
    assert not caplog.text


def _wait_for_last_change_timestamp_to_increment(
    cache: Cache,
    reference_timestamp: float,
) -> None:
    wait_until(
        lambda: cache.get_last_detected_change() > reference_timestamp,
        timeout=0.5,
        interval=0.05,
    )

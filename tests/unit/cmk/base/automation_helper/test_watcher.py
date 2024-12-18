#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import shutil
import time
from collections.abc import Generator
from pathlib import Path
from typing import ContextManager, Final

import pytest
from fakeredis import FakeRedis
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
from cmk.base.automation_helper._config import Schedule
from cmk.base.automation_helper._watcher import (
    _AutomationWatcherHandler,
    run,
)

_WATCHED_MK_PATTERN: Final = "*.mk"
_WATCHED_TXT_FILE: Final = "foo.txt"
_WATCHED_DIRECTORY: Final = "some_dir"
_MK_FILE: Final = "foo.mk"


@pytest.fixture(name="cache")
def get_cache() -> Generator[Cache]:
    yield Cache.setup(client=FakeRedis())


@pytest.fixture(name="mk_file_watcher_handler")
def get_mk_file_watcher_handler(cache: Cache) -> _AutomationWatcherHandler:
    return _AutomationWatcherHandler(
        cache=cache, patterns=[_WATCHED_MK_PATTERN], ignore_directories=True
    )


@pytest.fixture(name="directory_watcher_handler")
def get_directory_watcher_handler(cache: Cache) -> _AutomationWatcherHandler:
    return _AutomationWatcherHandler(
        cache=cache, patterns=[_WATCHED_DIRECTORY], ignore_directories=False
    )


@pytest.fixture(name="target_mk_file")
def get_mk_target_file(tmp_path: Path) -> Path:
    return tmp_path / _MK_FILE


@pytest.fixture(name="observer")
def get_observer(cache: Cache, tmp_path: Path) -> ContextManager:
    return run(
        [
            Schedule(
                path=tmp_path,
                ignore_directories=True,
                recursive=True,
                patterns=[_WATCHED_MK_PATTERN],
            ),
            Schedule(
                path=tmp_path,
                ignore_directories=True,
                recursive=True,
                patterns=[_WATCHED_TXT_FILE],
            ),
        ],
        cache,
    )


def wait_for_observer_log_output(
    log: pytest.LogCaptureFixture,
    output_to_wait_for: str,
    interval: float = 0.001,
    tries: int = 100,
) -> None:
    while tries:
        if output_to_wait_for in log.text:
            return
        tries -= 1
        time.sleep(interval)
    raise AssertionError(f"Expected output '{output_to_wait_for}' not found in log output")


@pytest.mark.xfail(reason="Cannot reproduce the 'moved' event with shutil")
def test_observer_handles_moved_mk_file(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, observer: ContextManager, target_mk_file: Path
) -> None:
    target_mk_file.write_bytes(b"hello")
    tmp_file = tmp_path / f"{_MK_FILE}.tmp"
    tmp_file.write_bytes(b"goodbye")

    with caplog.at_level(logging.INFO), observer:
        shutil.move(tmp_file, target_mk_file)
        wait_for_observer_log_output(caplog, "foo.mk (overwritten)")


def test_observer_handles_created_mk_file(
    caplog: pytest.LogCaptureFixture, observer: ContextManager, target_mk_file: Path
) -> None:
    with caplog.at_level(logging.INFO), observer:
        target_mk_file.touch()
        wait_for_observer_log_output(caplog, "foo.mk (created)")


def test_observer_handles_modified_mk_file(
    caplog: pytest.LogCaptureFixture, observer: ContextManager, target_mk_file: Path
) -> None:
    target_mk_file.touch()

    with caplog.at_level(logging.INFO), observer:
        target_mk_file.write_bytes(b"hello")
        wait_for_observer_log_output(caplog, "foo.mk (modified)")


def test_observer_handles_deleted_mk_file(
    caplog: pytest.LogCaptureFixture, observer: ContextManager, target_mk_file: Path
) -> None:
    target_mk_file.touch()

    with caplog.at_level(logging.INFO), observer:
        target_mk_file.unlink()
        wait_for_observer_log_output(caplog, "foo.mk (deleted)")


def test_observer_also_handles_txt_files(
    caplog: pytest.LogCaptureFixture, observer: ContextManager, tmp_path: Path
) -> None:
    with caplog.at_level(logging.INFO), observer:
        (tmp_path / _WATCHED_TXT_FILE).touch()
        wait_for_observer_log_output(caplog, "foo.txt (created)")


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(
            FileMovedEvent(src_path="", dest_path=_MK_FILE),
            "foo.mk (overwritten)",
            id="file overwritten",
        ),
        pytest.param(FileCreatedEvent(src_path=_MK_FILE), "foo.mk (created)", id="file created"),
        pytest.param(FileModifiedEvent(src_path=_MK_FILE), "foo.mk (modified)", id="file modified"),
        pytest.param(FileDeletedEvent(src_path=_MK_FILE), "foo.mk (deleted)", id="file deleted"),
    ],
)
def test_automation_watcher_logging_pattern_match(
    caplog: pytest.LogCaptureFixture,
    mk_file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
    output: str,
) -> None:
    with caplog.at_level(logging.INFO):
        mk_file_watcher_handler.dispatch(event)

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
    mk_file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    with caplog.at_level(logging.INFO):
        mk_file_watcher_handler.dispatch(event)

    assert not caplog.text


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(
            DirMovedEvent(src_path="", dest_path=_WATCHED_DIRECTORY),
            f"{_WATCHED_DIRECTORY} (overwritten)",
            id="dir overwritten",
        ),
        pytest.param(
            DirCreatedEvent(src_path=_WATCHED_DIRECTORY),
            f"{_WATCHED_DIRECTORY} (created)",
            id="dir created",
        ),
        pytest.param(
            DirModifiedEvent(src_path=_WATCHED_DIRECTORY),
            f"{_WATCHED_DIRECTORY} (modified)",
            id="dir modified",
        ),
        pytest.param(
            DirDeletedEvent(src_path=_WATCHED_DIRECTORY),
            f"{_WATCHED_DIRECTORY} (deleted)",
            id="dir deleted",
        ),
    ],
)
def test_automation_watcher_logging_directory_match(
    caplog: pytest.LogCaptureFixture,
    directory_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
    output: str,
) -> None:
    with caplog.at_level(logging.INFO):
        directory_watcher_handler.dispatch(event)

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
    mk_file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    with caplog.at_level(logging.INFO):
        mk_file_watcher_handler.dispatch(event)

    assert not caplog.text

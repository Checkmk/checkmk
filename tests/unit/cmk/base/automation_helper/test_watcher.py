#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from contextlib import AbstractContextManager as ContextManager
from pathlib import Path
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

from tests.testlib.common.utils import wait_until

from cmk.base.automation_helper._cache import Cache
from cmk.base.automation_helper._config import Schedule, WatcherConfig
from cmk.base.automation_helper._watcher import (
    _AutomationWatcherHandler,
    run,
)

_WATCHED_MK_PATTERN: Final = "*.mk"
_WATCHED_TXT_FILE: Final = "foo.txt"
_WATCHED_DIRECTORY_PATTERN: Final = "some_dir*"
_WATCHED_DIRECTORY = "some_dir"
_MK_FILE: Final = "foo.mk"


@pytest.fixture(name="mk_file_watcher_handler")
def get_mk_file_watcher_handler(cache: Cache) -> _AutomationWatcherHandler:
    return _AutomationWatcherHandler(
        cache=cache, patterns=[_WATCHED_MK_PATTERN], ignore_directories=True
    )


@pytest.fixture(name="directory_watcher_handler")
def get_directory_watcher_handler(cache: Cache) -> _AutomationWatcherHandler:
    return _AutomationWatcherHandler(
        cache=cache, patterns=[_WATCHED_DIRECTORY_PATTERN], ignore_directories=False
    )


@pytest.fixture(name="target_directory")
def get_targed_directory(tmp_path: Path) -> Path:
    (tmp_path / "watched").mkdir()
    return tmp_path / "watched"


@pytest.fixture(name="target_mk_file")
def get_mk_target_file(target_directory: Path) -> Path:
    return target_directory / _MK_FILE


@pytest.fixture(name="observer")
def get_observer(cache: Cache, target_directory: Path) -> ContextManager:
    return run(
        WatcherConfig(
            schedules=[
                Schedule(
                    path=target_directory,
                    ignore_directories=True,
                    recursive=True,
                    patterns=[_WATCHED_MK_PATTERN],
                ),
                Schedule(
                    path=target_directory,
                    ignore_directories=True,
                    recursive=True,
                    patterns=[_WATCHED_TXT_FILE],
                ),
            ],
        ),
        cache,
    )


def test_observer_handles_move_from_unwatched_to_watched_directory(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    observer: ContextManager,
    tmp_path: Path,
    target_mk_file: Path,
) -> None:
    tmp_file = tmp_path / "file.mk"
    tmp_file.touch()
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO), observer:
        tmp_file.rename(target_mk_file)
        _wait_for_last_change_timestamp_to_increment(cache, last_change_reference)
    assert f"Source: n/a, destination: {target_mk_file}, type: moved" in caplog.text


def test_observer_handles_move_from_watched_to_unwatched_directory(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    observer: ContextManager,
    tmp_path: Path,
    target_mk_file: Path,
) -> None:
    target_mk_file.touch()
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO), observer:
        target_mk_file.rename(tmp_path / "file.mk")
        _wait_for_last_change_timestamp_to_increment(cache, last_change_reference)
    assert f"Source: {target_mk_file}, destination: n/a, type: moved" in caplog.text


def test_observer_handles_move_within_watched_directory(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    observer: ContextManager,
    target_mk_file: Path,
) -> None:
    tmp_file = target_mk_file.with_suffix(".tmp")
    tmp_file.touch()
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO), observer:
        tmp_file.rename(target_mk_file)
        _wait_for_last_change_timestamp_to_increment(cache, last_change_reference)
    assert f"Source: {tmp_file}, destination: {target_mk_file}, type: moved" in caplog.text


def test_observer_handles_created_mk_file(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    observer: ContextManager,
    target_mk_file: Path,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO), observer:
        target_mk_file.touch()
        _wait_for_last_change_timestamp_to_increment(cache, last_change_reference)
    assert f"Source: {target_mk_file}, destination: n/a, type: created" in caplog.text


def test_observer_handles_modified_mk_file(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    observer: ContextManager,
    target_mk_file: Path,
) -> None:
    target_mk_file.touch()
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO), observer:
        target_mk_file.write_bytes(b"hello")
        _wait_for_last_change_timestamp_to_increment(cache, last_change_reference)
    assert f"Source: {target_mk_file}, destination: n/a, type: modified" in caplog.text


def test_observer_handles_deleted_mk_file(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    observer: ContextManager,
    target_mk_file: Path,
) -> None:
    target_mk_file.touch()
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO), observer:
        target_mk_file.unlink()
        _wait_for_last_change_timestamp_to_increment(cache, last_change_reference)
    assert f"Source: {target_mk_file}, destination: n/a, type: deleted" in caplog.text


def test_observer_also_handles_txt_files(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    observer: ContextManager,
    target_directory: Path,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO), observer:
        (target_directory / _WATCHED_TXT_FILE).touch()
        _wait_for_last_change_timestamp_to_increment(cache, last_change_reference)
    assert (
        f"Source: {target_directory / _WATCHED_TXT_FILE}, destination: n/a, type: created"
        in caplog.text
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
            id="file created",
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
    cache: Cache,
    mk_file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO):
        mk_file_watcher_handler.dispatch(event)
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
    mk_file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO):
        mk_file_watcher_handler.dispatch(event)
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

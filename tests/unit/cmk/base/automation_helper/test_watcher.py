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
    AutomationWatcherHandler,
    start_automation_watcher_observer,
)

MK_PATTERN: Final = "*.mk"
MK_FILE: Final = "foo.mk"
TXT_FILE: Final = "foo.txt"
DIRECTORY: Final = "local"


@pytest.fixture(name="cache")
def get_cache() -> Generator[Cache]:
    cache = Cache.setup(client=FakeRedis())
    yield cache


@pytest.fixture(scope="function", name="file_watcher_handler")
def get_file_watcher_handler(cache: Cache) -> AutomationWatcherHandler:
    return AutomationWatcherHandler(cache=cache, patterns=[MK_PATTERN], ignore_directories=True)


@pytest.fixture(scope="function", name="directory_watcher_handler")
def get_directory_watcher_handler(cache: Cache) -> AutomationWatcherHandler:
    return AutomationWatcherHandler(cache=cache, patterns=[DIRECTORY], ignore_directories=False)


@pytest.fixture(scope="function", name="target_directory")
def get_target_directory(tmp_path: Path) -> Path:
    target_directory = tmp_path / DIRECTORY
    target_directory.mkdir(parents=True)
    return target_directory


@pytest.fixture(scope="function", name="target_file")
def get_target_file(target_directory: Path) -> Path:
    return target_directory / MK_FILE


@pytest.fixture(scope="function", name="observer")
def get_observer(cache: Cache, target_directory: Path) -> ContextManager:
    schedules: list[Schedule] = [
        Schedule(
            path=target_directory,
            ignore_directories=True,
            recursive=True,
            patterns=[MK_PATTERN],
        ),
        Schedule(
            path=target_directory,
            ignore_directories=True,
            recursive=True,
            patterns=[TXT_FILE],
        ),
    ]
    return start_automation_watcher_observer(schedules, cache)


def wait_for_observer_log_output(
    log: pytest.LogCaptureFixture, interval: float = 0.001, tries: int = 100
) -> str:
    output = ""
    while tries and not (output := log.text):
        tries -= 1
        time.sleep(interval)
    return output


@pytest.mark.xfail(reason="Cannot reproduce the 'moved' event with shutil")
def test_observer_handles_moved_mk_file(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, observer: ContextManager, target_file: Path
) -> None:
    target_file.write_bytes(b"hello")
    tmp_file = tmp_path / f"{MK_FILE}.tmp"
    tmp_file.write_bytes(b"goodbye")

    with caplog.at_level(logging.INFO):
        with observer:
            shutil.move(tmp_file, target_file)
            log_output = wait_for_observer_log_output(caplog)

    assert "foo.mk (overwritten)" in log_output


def test_observer_handles_created_mk_file(
    caplog: pytest.LogCaptureFixture, observer: ContextManager, target_file: Path
) -> None:
    with caplog.at_level(logging.INFO):
        with observer:
            target_file.touch()
            log_output = wait_for_observer_log_output(caplog)

    assert "foo.mk (created)" in log_output


def test_observer_handles_modified_mk_file(
    caplog: pytest.LogCaptureFixture, observer: ContextManager, target_file: Path
) -> None:
    target_file.touch()

    with caplog.at_level(logging.INFO):
        with observer:
            target_file.write_bytes(b"hello")
            log_output = wait_for_observer_log_output(caplog)

    assert "foo.mk (modified)" in log_output


def test_observer_handles_deleted_mk_file(
    caplog: pytest.LogCaptureFixture, observer: ContextManager, target_file: Path
) -> None:
    target_file.touch()

    with caplog.at_level(logging.INFO):
        with observer:
            target_file.unlink()
            log_output = wait_for_observer_log_output(caplog)

    assert "foo.mk (deleted)" in log_output


def test_observer_also_handles_txt_files(
    caplog: pytest.LogCaptureFixture, observer: ContextManager, target_directory: Path
) -> None:
    with caplog.at_level(logging.INFO):
        with observer:
            (target_directory / TXT_FILE).touch()
            log_output = wait_for_observer_log_output(caplog)

    assert "foo.txt (created)" in log_output


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(
            FileMovedEvent(src_path="", dest_path=MK_FILE),
            "foo.mk (overwritten)",
            id="file overwritten",
        ),
        pytest.param(FileCreatedEvent(src_path=MK_FILE), "foo.mk (created)", id="file created"),
        pytest.param(FileModifiedEvent(src_path=MK_FILE), "foo.mk (modified)", id="file modified"),
        pytest.param(FileDeletedEvent(src_path=MK_FILE), "foo.mk (deleted)", id="file deleted"),
    ],
)
def test_automation_watcher_logging_pattern_match(
    caplog: pytest.LogCaptureFixture,
    file_watcher_handler: AutomationWatcherHandler,
    event: FileSystemEvent,
    output: str,
) -> None:
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)

    assert output in caplog.text


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(FileMovedEvent(src_path="", dest_path=TXT_FILE), id="no match overwritten"),
        pytest.param(FileCreatedEvent(src_path=TXT_FILE), id="no match created"),
        pytest.param(FileModifiedEvent(src_path=TXT_FILE), id="no match modified"),
        pytest.param(FileDeletedEvent(src_path=TXT_FILE), id="no match deleted"),
    ],
)
def test_automation_watcher_logging_no_match(
    caplog: pytest.LogCaptureFixture,
    file_watcher_handler: AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)

    assert not caplog.text


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(
            DirMovedEvent(src_path="", dest_path=DIRECTORY),
            "local (overwritten)",
            id="dir overwritten",
        ),
        pytest.param(DirCreatedEvent(src_path=DIRECTORY), "local (created)", id="dir created"),
        pytest.param(DirModifiedEvent(src_path=DIRECTORY), "local (modified)", id="dir modified"),
        pytest.param(DirDeletedEvent(src_path=DIRECTORY), "local (deleted)", id="dir deleted"),
    ],
)
def test_automation_watcher_logging_directory_match(
    caplog: pytest.LogCaptureFixture,
    directory_watcher_handler: AutomationWatcherHandler,
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
            DirMovedEvent(src_path="", dest_path=DIRECTORY),
            id="no match dir overwritten",
        ),
        pytest.param(DirCreatedEvent(src_path=DIRECTORY), id="no match dir created"),
        pytest.param(DirModifiedEvent(src_path=DIRECTORY), id="no match dir modified"),
        pytest.param(DirDeletedEvent(src_path=DIRECTORY), id="no match dir deleted"),
    ],
)
def test_automation_watcher_logging_directories_ignored(
    caplog: pytest.LogCaptureFixture,
    file_watcher_handler: AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)

    assert not caplog.text

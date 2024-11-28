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
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileSystemEvent,
)

from cmk.base.automation_helper._watcher import AutomationWatcherHandler

MK_PATTERN: Final = "*.mk"
MK_FILE: Final = "foo.mk"
TXT_FILE: Final = "foo.txt"
DIRECTORY: Final = "local"


@pytest.fixture(scope="function", name="file_watcher_handler")
def get_file_watcher_handler() -> AutomationWatcherHandler:
    return AutomationWatcherHandler(patterns=[MK_PATTERN], ignore_directories=True)


@pytest.fixture(scope="function", name="directory_watcher_handler")
def get_directory_watcher_handler() -> AutomationWatcherHandler:
    return AutomationWatcherHandler(patterns=[DIRECTORY], ignore_directories=False)


@pytest.mark.parametrize(
    "event, output",
    [
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

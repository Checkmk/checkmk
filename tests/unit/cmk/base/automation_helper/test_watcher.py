#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Final

import pytest
from watchdog.events import FileCreatedEvent, FileDeletedEvent, FileModifiedEvent, FileSystemEvent

from cmk.base.automation_helper._watcher import AutomationWatcherHandler

MK_PATTERN: Final = "*.mk"
MK_FILE: Final = "foo.mk"
TXT_FILE: Final = "foo.txt"


@pytest.fixture(scope="function", name="watcher_handler")
def get_watcher_handler() -> AutomationWatcherHandler:
    return AutomationWatcherHandler(patterns=[MK_PATTERN])


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(FileCreatedEvent(src_path=MK_FILE), "foo.mk (created)", id="match created"),
        pytest.param(FileModifiedEvent(src_path=MK_FILE), "foo.mk (modified)", id="match modified"),
        pytest.param(FileDeletedEvent(src_path=MK_FILE), "foo.mk (deleted)", id="match deleted"),
    ],
)
def test_automation_watcher_logging_pattern_match(
    caplog: pytest.LogCaptureFixture,
    watcher_handler: AutomationWatcherHandler,
    event: FileSystemEvent,
    output: str,
) -> None:
    with caplog.at_level(logging.INFO):
        watcher_handler.dispatch(event)

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
    watcher_handler: AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    with caplog.at_level(logging.INFO):
        watcher_handler.dispatch(event)

    assert not caplog.text

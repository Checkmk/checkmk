#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
from collections.abc import Generator, Sequence
from pathlib import Path

import pydantic
from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

from ._log import watcher_logger


class AutomationWatcherHandler(PatternMatchingEventHandler):
    def __init__(self, *, patterns: Sequence[str] | None, ignore_directories: bool) -> None:
        patterns_ = list(patterns) if patterns else None
        super().__init__(patterns=patterns_, ignore_directories=ignore_directories)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._log_handled_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._log_handled_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._log_handled_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._log_handled_event(event)

    @classmethod
    def _log_handled_event(cls, event: FileSystemEvent) -> None:
        match event.event_type:
            case "moved":
                watcher_logger.info("%s (overwritten)", event.dest_path)
            case _:
                watcher_logger.info("%s (%s)", event.src_path, event.event_type)


class Schedule(pydantic.BaseModel, frozen=True):
    ignore_directories: bool
    recursive: bool
    relative_path: str = ""
    patterns: Sequence[str] | None = None


@contextlib.contextmanager
def start_automation_watcher_observer(root: Path, schedules: Sequence[Schedule]) -> Generator[None]:
    observer = Observer()

    for schedule in schedules:
        handler = AutomationWatcherHandler(
            patterns=schedule.patterns,
            ignore_directories=schedule.ignore_directories,
        )
        observer.schedule(
            handler,
            path=str(root / schedule.relative_path),
            recursive=schedule.recursive,
        )

    try:
        observer.start()
        yield
    except Exception as err:
        watcher_logger.exception(err)
    finally:
        observer.stop()
        observer.join()

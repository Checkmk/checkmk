#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler

from ._log import watcher_logger


class AutomationWatcherHandler(PatternMatchingEventHandler):
    def __init__(self, *, patterns: list[str] | None, ignore_directories: bool) -> None:
        super().__init__(patterns=patterns, ignore_directories=ignore_directories)

    def on_created(self, event: FileSystemEvent) -> None:
        self._log_handled_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._log_handled_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._log_handled_event(event)

    @classmethod
    def _log_handled_event(cls, event: FileSystemEvent) -> None:
        watcher_logger.info("%s (%s)", event.src_path, event.event_type)

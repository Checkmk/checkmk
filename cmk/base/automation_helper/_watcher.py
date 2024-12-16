#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import time
from collections.abc import Generator, Sequence
from pathlib import Path
from threading import Thread
from typing import Final

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

from ._cache import Cache
from ._config import Schedule
from ._log import LOGGER

WATCHER_SLEEP_INTERVAL: Final = 1


class AutomationWatcherHandler(PatternMatchingEventHandler):
    def __init__(
        self,
        *,
        cache: Cache,
        patterns: Sequence[str] | None,
        ignore_directories: bool,
    ) -> None:
        self._cache = cache
        patterns_ = list(patterns) if patterns else None
        super().__init__(patterns=patterns_, ignore_directories=ignore_directories)

    def on_moved(self, event: FileSystemEvent) -> None:
        self._cache.store_last_detected_change(time.time())
        self._log_handled_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._cache.store_last_detected_change(time.time())
        self._log_handled_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._cache.store_last_detected_change(time.time())
        self._log_handled_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._cache.store_last_detected_change(time.time())
        self._log_handled_event(event)

    @classmethod
    def _log_handled_event(cls, event: FileSystemEvent) -> None:
        match event.event_type:
            case "moved":
                LOGGER.info("[watcher] %s (overwritten)", event.dest_path)
            case _:
                LOGGER.info("[watcher] %s (%s)", event.src_path, event.event_type)


@contextlib.contextmanager
def start_automation_watcher_observer(
    schedules: Sequence[Schedule], cache: Cache
) -> Generator[None]:
    observer = Observer()

    for schedule in schedules:
        handler = AutomationWatcherHandler(
            cache=cache,
            patterns=schedule.patterns,
            ignore_directories=schedule.ignore_directories,
        )
        observer.schedule(
            handler,
            path=str(schedule.path),
            recursive=schedule.recursive,
        )

    try:
        observer.start()
        yield
    except Exception as err:
        LOGGER.exception(err)
    finally:
        observer.stop()
        observer.join()


def run_watcher(schedules: Sequence[Schedule], cache: Cache) -> None:
    with start_automation_watcher_observer(schedules, cache):
        while True:
            time.sleep(WATCHER_SLEEP_INTERVAL)


class Watcher(Thread):
    def __init__(self, schedules: Sequence[Schedule], cache: Cache) -> None:
        LOGGER.info("[watcher] initializing thread...")
        kwargs = {"schedules": schedules, "cache": cache}
        super().__init__(target=run_watcher, name="watcher", kwargs=kwargs, daemon=True)

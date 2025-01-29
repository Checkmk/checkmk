#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import time
from collections.abc import Generator, Sequence

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

from ._cache import Cache, CacheError
from ._config import WatcherConfig
from ._log import LOGGER


@contextlib.contextmanager
def run(config: WatcherConfig, cache: Cache) -> Generator[None]:
    LOGGER.info("[watcher] Initializing")
    observer = Observer()
    for schedule in config.schedules:
        handler = _AutomationWatcherHandler(
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
        LOGGER.info("[watcher] Operational")
        yield
    except Exception as err:
        LOGGER.error("[watcher] Error while starting observer", exc_info=err)
    finally:
        LOGGER.info("[watcher] Shutting down")
        observer.stop()
        observer.join()
        LOGGER.info("[watcher] Shutdown complete")


class _AutomationWatcherHandler(PatternMatchingEventHandler):
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
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    def on_modified(self, event: FileSystemEvent) -> None:
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        self._store_last_detected_change(time.time())
        self._log_handled_event(event)

    def _store_last_detected_change(self, time: float) -> None:
        try:
            self._cache.store_last_detected_change(time)
        except CacheError as err:
            LOGGER.error("[watcher] Cache failure", exc_info=err)

    @classmethod
    def _log_handled_event(cls, event: FileSystemEvent) -> None:
        match event.event_type:
            case "moved":
                LOGGER.info("[watcher] %s (overwritten)", event.dest_path)
            case _:
                LOGGER.info("[watcher] %s (%s)", event.src_path, event.event_type)

#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import time
from collections.abc import Generator, Sequence

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers.inotify import InotifyObserver
from watchdog.observers.inotify_buffer import InotifyBuffer

from ._cache import Cache, CacheError
from ._config import WatcherConfig
from ._log import LOGGER

# When a file or folder is moved, two events are created: IN_MOVED_FROM and IN_MOVED_TO.
# watchdog tries to combine these two events into a single move event. In case it received
# IN_MOVED_FROM but not yet in IN_MOVED_TO, it waits up `InotifyBuffer.delay` seconds for
# IN_MOVED_TO, thereby delaying the reporting of other events. This might be an actual problem
# for us if an automation call is triggered right after files relevant to this call were modified.
# In such scenarios, the reload notification from the watcher might arrive too late if watchdog
# adds some delay. As a result, the automation call uses an outdated configuration.
# See also https://man7.org/linux/man-pages/man7/inotify.7.html, "Dealing with rename() events"
InotifyBuffer.delay = 0.0


@contextlib.contextmanager
def run(config: WatcherConfig, cache: Cache) -> Generator[None]:
    LOGGER.info("[watcher] Initializing")
    observer = InotifyObserver(generate_full_events=True)
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
        LOGGER.info(
            f"[watcher] Source: {_decode_if_necessary(event.src_path) or "n/a"}, "
            f"destination: {_decode_if_necessary(event.dest_path)or "n/a"}, "
            f"type: {event.event_type}"
        )


def _decode_if_necessary(v: str | bytes, encoding: str = "utf-8") -> str:
    return v if isinstance(v, str) else v.decode(encoding)

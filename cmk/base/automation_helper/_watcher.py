#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import dataclasses
import time
from collections.abc import Generator, Sequence
from pathlib import Path
from threading import Thread
from typing import Final, Self

from watchdog.events import FileSystemEvent, PatternMatchingEventHandler
from watchdog.observers import Observer

from ._cache import Cache
from ._log import logger

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
                logger.info("%s (overwritten)", event.dest_path)
            case _:
                logger.info("%s (%s)", event.src_path, event.event_type)


@dataclasses.dataclass(frozen=True)
class Schedule:
    ignore_directories: bool
    recursive: bool
    relative_path: str = ""
    patterns: Sequence[str] | None = None


@dataclasses.dataclass(frozen=True)
class WatcherConfig:
    root: Path
    schedules: Sequence[Schedule]

    @classmethod
    def load(cls, root: Path) -> Self:
        return cls(root=root, schedules=_SCHEDULES)


@contextlib.contextmanager
def start_automation_watcher_observer(
    root: Path, schedules: Sequence[Schedule], cache: Cache
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
            path=str(root / schedule.relative_path),
            recursive=schedule.recursive,
        )

    try:
        observer.start()
        yield
    except Exception as err:
        logger.exception(err)
    finally:
        observer.stop()
        observer.join()


def run_watcher(root: Path, schedules: Sequence[Schedule], cache: Cache) -> None:
    with start_automation_watcher_observer(root, schedules, cache):
        while True:
            time.sleep(WATCHER_SLEEP_INTERVAL)


class Watcher(Thread):
    def __init__(self, cfg: WatcherConfig, cache: Cache) -> None:
        logger.info("Initializing watcher thread...")
        kwargs = {"root": cfg.root, "schedules": cfg.schedules, "cache": cache}
        super().__init__(target=run_watcher, name="watcher", kwargs=kwargs, daemon=True)


_SCHEDULES = (
    Schedule(
        ignore_directories=True,
        recursive=False,
        relative_path="etc/check_mk",
        patterns=["main.mk", "local.mk", "final.mk", "experimental.mk"],
    ),
    Schedule(
        ignore_directories=True,
        recursive=True,
        relative_path="etc/check_mk/conf.d",
        patterns=["*.mk"],
    ),
)

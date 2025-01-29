#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event

from ._cache import Cache, CacheError
from ._config import ReloaderConfig
from ._log import LOGGER


@contextmanager
def run(
    config: ReloaderConfig,
    cache: Cache,
    reload_callback: Callable[[], None],
    shutdown_flag: Event,
) -> Generator[None]:
    LOGGER.info("[reloader] Initializing")
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(_run, config, cache, reload_callback, shutdown_flag)
        try:
            LOGGER.info("[reloader] Operational")
            yield
        finally:
            LOGGER.info("[reloader] Shutting down")
            shutdown_flag.set()
    LOGGER.info("[reloader] Shutdown complete")


def _run(
    config: ReloaderConfig,
    cache: Cache,
    reload_callback: Callable[[], None],
    shutdown_flag: Event,
) -> None:
    last_change = _retrieve_last_change(cache)
    while not shutdown_flag.wait(timeout=config.poll_interval):
        if (cached_last_change := _retrieve_last_change(cache)) == last_change:
            continue

        last_change = cached_last_change
        LOGGER.info(
            "[reloader] Change detected %.2f seconds ago",
            time.time() - last_change,
        )

        current_cooldown = config.cooldown_interval
        while not shutdown_flag.wait(timeout=current_cooldown):
            cached_last_change = _retrieve_last_change(cache)
            if cached_last_change == last_change:
                LOGGER.info("[reloader] Triggering reload")
                reload_callback()
                break

            else:
                current_cooldown = min(
                    # be rebust against cache resets, just in case
                    abs(cached_last_change - last_change),
                    config.cooldown_interval,
                )
                last_change = cached_last_change
                LOGGER.info(
                    "[reloader] Change detected %.2f seconds ago",
                    time.time() - last_change,
                )


def _retrieve_last_change(cache: Cache) -> float:
    try:
        return cache.get_last_detected_change()
    except CacheError as err:
        LOGGER.error("[reloader] Cache failure", exc_info=err)
        return 0

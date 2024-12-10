#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import signal
import time
from threading import Thread
from typing import Final

from ._cache import Cache
from ._log import logger

RELOADER_SLEEP_INTERVAL: Final = 5


def log_reload_info(last_change_at: float) -> None:
    when = round(time.time() - last_change_at, 2)
    logger.info(f"[reloader] change detected {when}s ago reloading now...")


def reload_application() -> None:
    os.kill(os.getpid(), signal.SIGHUP)


def run_reloader(cache: Cache) -> None:
    last_change = cache.last_detected_change

    while True:
        time.sleep(RELOADER_SLEEP_INTERVAL)

        if (cached_last_change := cache.last_detected_change) != last_change:
            log_reload_info(cached_last_change)
            reload_application()
            last_change = cached_last_change


class Reloader(Thread):
    def __init__(self, cache: Cache) -> None:
        logger.info("[reloader] initializing thread...")
        super().__init__(target=run_reloader, name="reloader", kwargs={"cache": cache}, daemon=True)

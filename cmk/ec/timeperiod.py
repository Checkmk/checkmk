#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping
from logging import Logger

from cmk.utils.timeperiod import TimeperiodName

from .core_queries import query_timeperiods_in


# TODO: Replace this with cmk.utils.timeperiod
class TimePeriods:
    """Time Periods are used in rule conditions."""

    def __init__(self, logger: Logger) -> None:
        self._logger = logger
        self._active: Mapping[TimeperiodName, bool] = {}
        self._cache_timestamp: int | None = None

    def _update(self) -> None:
        try:
            timestamp = int(time.time())
            # update at most once a minute
            if self._cache_timestamp is None or self._cache_timestamp + 60 <= timestamp:
                self._active = query_timeperiods_in()
                self._cache_timestamp = timestamp
        except Exception:
            self._logger.exception("Cannot update time period information.")
            raise

    def active(self, name: TimeperiodName) -> bool:
        self._update()
        if (is_active := self._active.get(name)) is None:
            self._logger.warning("unknown time period '%s', assuming it is active", name)
            is_active = True
        return is_active

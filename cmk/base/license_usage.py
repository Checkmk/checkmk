#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import random
import time
from pathlib import Path
from datetime import datetime, timedelta

import livestatus

import cmk.utils.paths
import cmk.utils.version as cmk_version
import cmk.utils.store as store
from cmk.utils.license_usage import (
    LicenseUsageSample,
    LicenseUsageHistoryDump,
    rot47,
)

logger = logging.getLogger("cmk.base.license_usage")

license_usage_dir = Path(cmk.utils.paths.var_dir, "license_usage")
next_run_filepath = license_usage_dir.joinpath("next_run")
history_filepath = license_usage_dir.joinpath("history.json")

_last_update_try_ts = 0.0


def try_history_update() -> None:
    logger.debug("Try license usage history update.")

    license_usage_dir.mkdir(parents=True, exist_ok=True)

    with store.locked(next_run_filepath), store.locked(history_filepath):
        now = datetime.now()
        next_run_ts = int(rot47(store.load_text_from_file(next_run_filepath, default="_")))

        if not _may_update(now.timestamp(), next_run_ts):
            return

        history_dump = _create_or_update_history_dump()
        store.save_bytes_to_file(history_filepath, history_dump.serialize())
        store.save_text_to_file(next_run_filepath, rot47(str(_create_next_run_ts(now))))
        logger.debug("Successfully updated history.")


def _may_update(now_ts: float, next_run_ts: int) -> bool:
    global _last_update_try_ts

    if (now_ts - _last_update_try_ts) < 600:
        logger.debug("Last try is not 10 minutes ago. Abort.")
        _last_update_try_ts = now_ts
        return False

    if now_ts < next_run_ts:
        logger.debug("Next run time has not been reached yet. Abort.")
        return False

    return True


def _create_next_run_ts(now: datetime) -> int:
    """The next run time is randomly set to the next day between 8 am and 4 pm."""
    eight_am_tdy = datetime(now.year, now.month, now.day, 8, 0, 0)
    start = eight_am_tdy + timedelta(days=1)
    end = start + timedelta(hours=8)
    return random.randrange(int(start.timestamp()), int(end.timestamp()), 600)


def _create_or_update_history_dump() -> LicenseUsageHistoryDump:
    """Update the license usage history

    If the history does not exist yet (or the history file is broken)
    we create a new one and add a new sample to it.

    The history has a max. length of 400 (days)."""
    history_dump = _load_history_dump()
    history_dump.add_sample(_create_sample())
    return history_dump


def _load_history_dump() -> LicenseUsageHistoryDump:
    raw_history_dump = store.load_bytes_from_file(
        history_filepath,
        default=b'{}',
    )
    return LicenseUsageHistoryDump.deserialize(raw_history_dump)


def _create_sample() -> LicenseUsageSample:
    query = "GET status\nColumns: num_hosts num_services\n"
    try:
        num_hosts, num_services = livestatus.LocalConnection().query(query)[0]
    except (livestatus.MKLivestatusSocketError, livestatus.MKLivestatusNotFoundError) as e:
        logger.debug("Livestatus error: %s", e)
        num_hosts, num_services = 0, 0

    general_infos = cmk_version.get_general_version_infos()
    return LicenseUsageSample(
        version=cmk_version.omd_version(),
        edition=general_infos['edition'],
        platform=general_infos['os'],
        is_cma=cmk_version.is_cma(),
        num_hosts=num_hosts,
        num_services=num_services,
        sample_time=int(time.time()),
        timezone=time.localtime().tm_zone,
    )

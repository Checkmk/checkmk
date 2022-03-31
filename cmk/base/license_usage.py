#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import random
import time
from datetime import datetime, timedelta
from typing import NamedTuple, Optional, Tuple

import livestatus

import cmk.utils.store as store
import cmk.utils.version as cmk_version
from cmk.utils.license_usage import (
    get_history_dump_filepath,
    LicenseUsageHistoryDump,
    load_extensions,
    load_history_dump,
    rot47,
    save_history_dump,
)
from cmk.utils.license_usage.export import LicenseUsageSample
from cmk.utils.paths import license_usage_dir

import cmk.base.crash_reporting as crash_reporting

logger = logging.getLogger("cmk.base.license_usage")

_last_update_try_ts = 0.0

_LICENSE_LABEL_NAME = "cmk/licensing"
_LICENSE_LABEL_EXCLUDE = "excluded"


def try_history_update() -> None:
    # 'try_history_update' is executed by every Check_MK service, thus we MUST be sure that there
    # is no error. Nevertheless if an error occurs it must not be raised because every Check_MK
    # service would crash, no host with Check_MK service  is checked anymore and might cause a
    # notification.
    try:
        _try_history_update()
    except Exception as e:
        crash = crash_reporting.CMKBaseCrashReport.from_exception()
        logger.error(
            "Error during license usage history update (Crash ID: %s): %s", crash.ident_to_text(), e
        )
        crash_reporting.CrashReportStore().save(crash)


def _try_history_update() -> None:
    logger.debug("Try license usage history update.")

    license_usage_dir.mkdir(parents=True, exist_ok=True)
    history_dump_filepath = get_history_dump_filepath()
    next_run_filepath = license_usage_dir / "next_run"

    with store.locked(next_run_filepath), store.locked(history_dump_filepath):
        now = datetime.now()
        next_run_ts = int(rot47(store.load_text_from_file(next_run_filepath, default="_")))

        if not _may_update(now.timestamp(), next_run_ts):
            return

        history_dump = _create_or_update_history_dump()
        save_history_dump(history_dump)

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
    history_dump = load_history_dump()
    if sample := _create_sample():
        history_dump.history.add_sample(sample)
    return history_dump


def _create_sample() -> Optional[LicenseUsageSample]:
    hosts_counter = _get_hosts_counter()
    services_counter = _get_services_counter()

    if (
        hosts_counter.included == 0
        and hosts_counter.excluded == 0
        and services_counter.included == 0
        and services_counter.excluded == 0
    ):
        return None

    general_infos = cmk_version.get_general_version_infos()
    extensions = load_extensions()
    return LicenseUsageSample(
        version=cmk_version.omd_version(),
        edition=general_infos["edition"],
        platform=general_infos["os"],
        is_cma=cmk_version.is_cma(),
        num_hosts=hosts_counter.included,
        num_hosts_excluded=hosts_counter.excluded,
        num_services=services_counter.included,
        num_services_excluded=services_counter.excluded,
        sample_time=int(time.time()),
        timezone=time.localtime().tm_zone,
        extension_ntop=extensions.ntop,
    )


class EntityCounter(NamedTuple):
    included: int
    excluded: int


def _get_hosts_counter() -> EntityCounter:
    included_num_hosts, excluded_num_hosts = _get_stats_from_livestatus(
        (
            "GET hosts\n"
            "Stats: host_labels != '{label_name}' '{label_value}'\n"
            "Stats: host_labels = '{label_name}' '{label_value}'\n"
        ).format(
            label_name=_LICENSE_LABEL_NAME,
            label_value=_LICENSE_LABEL_EXCLUDE,
        )
    )

    return EntityCounter(
        included=included_num_hosts,
        excluded=excluded_num_hosts,
    )


def _get_services_counter() -> EntityCounter:
    included_num_services, excluded_num_services = _get_stats_from_livestatus(
        (
            "GET services\n"
            "Stats: host_labels != '{label_name}' '{label_value}'\n"
            "Stats: service_labels != '{label_name}' '{label_value}'\n"
            "StatsAnd: 2\n"
            "Stats: host_labels = '{label_name}' '{label_value}'\n"
            "Stats: service_labels = '{label_name}' '{label_value}'\n"
            "StatsOr: 2\n"
        ).format(
            label_name=_LICENSE_LABEL_NAME,
            label_value=_LICENSE_LABEL_EXCLUDE,
        )
    )

    return EntityCounter(
        included=included_num_services,
        excluded=excluded_num_services,
    )


def _get_stats_from_livestatus(query: str) -> Tuple[int, int]:
    try:
        stats = livestatus.LocalConnection().query(query)[0]
        return int(stats[0]), int(stats[1])
    except (livestatus.MKLivestatusSocketError, livestatus.MKLivestatusNotFoundError) as e:
        logger.debug("Livestatus error: %s", e)
        return (0, 0)

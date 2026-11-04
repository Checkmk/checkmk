#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import random
from datetime import datetime, timedelta
from pathlib import Path

from cmk.ccc import store
from cmk.product_usage.exceptions import InvalidTimestampError

# The cron job (etc/cron.d/cmk_collect_transmit_product_usage_analytics) runs this often
CRON_PERIOD = timedelta(minutes=30)
# The first run must start within 24 hours, so it is planned at least one cron period earlier
FIRST_RUN_WINDOW = timedelta(hours=24) - CRON_PERIOD
STANDARD_INTERVAL = timedelta(days=30)
CLOUD_TRIAL_INTERVAL = timedelta(days=7)


def should_run_collection_on_schedule(var_dir: Path, dt: datetime) -> bool:
    next_run_fp = next_run_file_path(var_dir)
    next_ts = get_next_run_ts(next_run_fp)

    if not next_ts or next_ts > dt:
        return False

    return True


def next_run_file_path(var_dir: Path) -> Path:
    return var_dir / "product_usage" / "next_run"


def get_next_run_ts(file_path: Path) -> datetime | None:
    try:
        with file_path.open("r", encoding="utf-8") as fp:
            return datetime.fromtimestamp(int(fp.read()))
    except (FileNotFoundError, ValueError):
        return None


def create_next_random_ts(dt: datetime) -> int:
    # Creates and returns a random timestamp within FIRST_RUN_WINDOW from the given datetime
    try:
        end = dt + FIRST_RUN_WINDOW
        return random.randrange(int(dt.timestamp()), int(end.timestamp()), 60)
    except (OverflowError, OSError, ValueError, TypeError) as exc:
        raise InvalidTimestampError from exc


def create_next_ts(dt: datetime, *, interval: timedelta) -> int:
    # Returns a timestamp one interval after the given datetime
    try:
        return int((dt + interval).timestamp())
    except OverflowError as exc:
        raise InvalidTimestampError from exc


def store_next_run_ts(file_path: Path, timestamp: int) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    store.save_text_to_file(file_path, str(timestamp))


def next_run_interval(*, cloud_trial: bool) -> timedelta:
    return CLOUD_TRIAL_INTERVAL if cloud_trial else STANDARD_INTERVAL

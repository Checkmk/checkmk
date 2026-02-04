#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta

from cmk.product_usage.schedule import (
    create_next_random_ts,
    get_next_run_ts,
    next_run_file_path,
    should_run_collection_on_schedule,
    store_next_run_ts,
)
from cmk.utils.paths import var_dir


def test_create_next_random_ts() -> None:
    now = datetime.now()
    min_ts = now + timedelta(days=1)
    max_ts = now + timedelta(days=30)

    new_ts = create_next_random_ts(now)

    assert int(min_ts.timestamp()) <= new_ts < int(max_ts.timestamp())


def test_get_and_store_next_product_usage_run_ts() -> None:
    ts_file_path = next_run_file_path(var_dir)
    now = datetime.now().replace(microsecond=0)

    assert get_next_run_ts(ts_file_path) is None

    store_next_run_ts(ts_file_path, int(now.timestamp()))

    assert get_next_run_ts(ts_file_path) == now


def test_should_run_product_usage_on_schedule() -> None:
    now = datetime.now()
    ts_file_path = next_run_file_path(var_dir)

    assert should_run_collection_on_schedule(var_dir, now) is False

    store_next_run_ts(ts_file_path, 1)

    assert should_run_collection_on_schedule(var_dir, now) is True

    future_ts = int((now + timedelta(days=1)).timestamp())
    store_next_run_ts(ts_file_path, future_ts)

    assert should_run_collection_on_schedule(var_dir, now) is False


def test_get_next_product_usage_run_ts() -> None:
    ts_file_path = next_run_file_path(var_dir)
    assert get_next_run_ts(ts_file_path) is None

    ts_file_path.parent.mkdir(parents=True, exist_ok=True)
    ts_file_path.write_text("not_a_timestamp")

    assert get_next_run_ts(ts_file_path) is None

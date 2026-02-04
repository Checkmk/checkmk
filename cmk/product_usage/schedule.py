#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import random
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from cmk.product_usage.exceptions import InvalidTimestampError


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
    # Creates and returns a timestamp between 1 and 30 days from the given datetime
    try:
        start = dt + timedelta(days=1)
        end = dt + timedelta(days=30)
        return random.randrange(int(start.timestamp()), int(end.timestamp()), 60)
    except (OverflowError, OSError, ValueError, TypeError) as exc:
        raise InvalidTimestampError from exc


def create_next_ts(dt: datetime) -> int:
    # Returns a timestamp 30 days after the given datetime
    try:
        return int((dt + timedelta(days=30)).timestamp())
    except OverflowError as exc:
        raise InvalidTimestampError from exc


def store_next_run_ts(file_path: Path, timestamp: int) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write(str(timestamp))
        shutil.move(f.name, file_path)

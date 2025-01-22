#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path


def get_free_space(omd_root: Path) -> int:
    statvfs_result = os.statvfs(omd_root)
    return statvfs_result.f_bavail * statvfs_result.f_frsize


def fmt_bytes(v: float) -> str:
    for prefix in ("B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"):
        if abs(v) < 1024:
            return f"{v:.2f} {prefix}"
        v /= 1024
    return f"{v:.2f} YiB"

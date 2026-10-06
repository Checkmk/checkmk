#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from pathlib import Path


def omd_root() -> Path:
    return Path(os.environ.get("OMD_ROOT", ""))


def db_path(feature: str) -> Path:
    return omd_root() / "var" / "check_mk" / feature / "db.sqlite3"

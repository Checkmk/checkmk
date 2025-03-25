#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

_RELATIVE_PAYLOAD_DIR = "tmp/check_mk/piggyback"
_RELATIVE_SOURCE_STATUS_DIR = "tmp/check_mk/piggyback_sources"


def payload_dir(omd_root: Path) -> Path:
    return omd_root / _RELATIVE_PAYLOAD_DIR


def source_status_dir(omd_root: Path) -> Path:
    return omd_root / _RELATIVE_SOURCE_STATUS_DIR

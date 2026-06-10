#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class ExitSpec(TypedDict, total=False):
    connection: int
    timeout: int
    exception: int
    wrong_version: int
    missing_sections: int
    specific_missing_sections: list[tuple[str, int]]
    restricted_address_mismatch: int
    legacy_pull_mode: int

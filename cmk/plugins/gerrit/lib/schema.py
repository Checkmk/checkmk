#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import TypedDict


class VersionInfo(TypedDict):
    current: str
    latest: LatestVersion


class LatestVersion(TypedDict):
    major: str | None
    minor: str | None
    patch: str | None

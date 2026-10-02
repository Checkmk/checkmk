#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from datetime import datetime

# Veeam's TimeSpan format: "[-][d.]hh:mm:ss[.fffffff]"
_DOTNET_TIMESPAN = re.compile(
    r"^(?:(?P<days>\d+)\.)?(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+)(?:\.\d+)?$"
)


def parse_dotnet_timespan_seconds(duration: str) -> float | None:
    if (match := _DOTNET_TIMESPAN.match(duration)) is None:
        return None
    days = int(match["days"] or 0)
    hours, minutes, seconds = int(match["hours"]), int(match["minutes"]), int(match["seconds"])
    return float(((days * 24 + hours) * 60 + minutes) * 60 + seconds)


def parse_iso8601_epoch(value: str) -> float | None:
    """Parses an ISO 8601 timestamp with an explicit UTC offset, e.g.
    "2024-02-04T21:40:34.473+03:00" (the format the VBR REST API uses)."""
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def sanitize_name(name: str) -> str:
    return name.replace("'", "_").replace(" ", "_")

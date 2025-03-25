#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
The "render" namespace adds functions to render values in a human-readable way.

All the render functions take a single numerical value as an argument, and return
a string.
"""

from cmk.agent_based.v1.render import (
    bytes,  # noqa: A004
    date,
    datetime,
    disksize,
    filesize,
    frequency,
    iobandwidth,
    networkbandwidth,
    nicspeed,
    percent,
    timespan,
)


def time_offset(seconds: float) -> str:
    """Render a time offset (positive or negative) given in seconds

    Like :func:`timespan`, but allows negative values.

    Example:
        >>> time_offset(-0.0001)
        '-100 microseconds'

    Please carefully consider if this really is what you want.
    Here are the main two reasons why it might not be:

    Firstly, a negative time span might indicate that actually
    something else is wrong. A negative uptime or a negative
    amount of remaining battery time is nothing that a monitored
    device should ever report.

    Secondly, even if a negative time is a reasonable thing to observe,
    you might want to render it differently, taking care of the sign
    for yourself. Consider the slightly weird

        >>> f"Time until certificate expires: {time_offset(-183600)}"
        'Time until certificate expires: -2 days 3 hours'

    compared to the more straightforward

        >>> f"Time since certificate expired: {timespan(183600)}"
        'Time since certificate expired: 2 days 3 hours'

    """
    return f"-{timespan(-seconds)}" if seconds < 0 else timespan(seconds)


__all__ = [
    "bytes",
    "date",
    "datetime",
    "disksize",
    "filesize",
    "frequency",
    "iobandwidth",
    "networkbandwidth",
    "nicspeed",
    "percent",
    "timespan",
    "time_offset",
]

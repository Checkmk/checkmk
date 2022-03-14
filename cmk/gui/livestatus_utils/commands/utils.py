#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import datetime as dt


def to_timestamp(datetime: dt.datetime) -> int:
    """Convert a datetime object (timezone aware) to a unix-timestamp.

    Args:
        datetime:
            A timezone aware datetime object.

    Examples:

        >>> import pytz
        >>> from dateutil import tz

        >>> to_timestamp(dt.datetime(2020, 1, 1))
        Traceback (most recent call last):
        ...
        RuntimeError: Only timezone aware dates are allowed.

        >>> to_timestamp(dt.datetime(2020, 1, 1, tzinfo=tz.tzutc()))
        1577836800

        >>> to_timestamp(dt.datetime(2020, 1, 1, tzinfo=pytz.timezone("UTC")))
        1577836800

        >>> to_timestamp(dt.datetime(2020, 1, 1, tzinfo=pytz.timezone("GMT")))
        1577836800

        >>> to_timestamp(dt.datetime(2020, 1, 1, tzinfo=pytz.timezone("MET")))
        1577833200

        >>> to_timestamp(dt.datetime(2020, 1, 1, tzinfo=pytz.timezone("Asia/Tokyo")))
        1577803260

        >>> to_timestamp(dt.datetime(2020, 1, 1, tzinfo=tz.tzoffset(None, 3600)))
        1577833200

        >>> to_timestamp(dt.datetime(2020, 1, 1, tzinfo=tz.tzoffset(None, -3600)))
        1577840400

    Returns:
        The unix timestamp of the date.
    """

    if not datetime.tzinfo:
        raise RuntimeError("Only timezone aware dates are allowed.")

    return int(datetime.timestamp())

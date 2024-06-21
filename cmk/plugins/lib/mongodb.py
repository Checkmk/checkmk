#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dateutil import parser as dateutil_parser


def parse_date(date: float | str) -> float:
    """
    Parse $date fields in JSON output of mk_mongodb

    The format of the $date field depends on the pymongo version. Newer versions use the "Relaxed
    Mode" by default, while older versions use the "Legacy Mode", see
    https://pymongo.readthedocs.io/en/stable/api/bson/json_util.html#bson.json_util.dumps.

    * In legacy mode, "The value represents milliseconds relative to the epoch."
    * In relaxed mode, it is an ISO-8601 date string
    see
    https://www.mongodb.com/docs/manual/reference/mongodb-extended-json/#mongodb-bsontype-Date.

    >>> parse_date(123400)
    123.4
    >>> parse_date('2022-08-01T01:30:07.827Z')
    1659317407.827
    """
    return dateutil_parser.isoparse(date).timestamp() if isinstance(date, str) else date / 1000.0

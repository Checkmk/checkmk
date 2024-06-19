#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

from cmk.agent_based.v2 import StringTable

GraylogSection = dict


def deserialize_and_merge_json(string_table: StringTable) -> GraylogSection:
    """
    >>> deserialize_and_merge_json([['{"a": 1, "b": 2}'], ['{"b": 3, "c": 4}']])
    {'a': 1, 'b': 3, 'c': 4}
    """
    parsed = {}

    for line in string_table:
        parsed.update(json.loads(line[0]))

    return parsed

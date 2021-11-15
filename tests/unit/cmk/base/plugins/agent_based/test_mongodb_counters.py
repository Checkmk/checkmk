#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.mongodb_counters import parse_mongodb_counters

_SECTION = {
    "opcounters": {
        "command": 71299015,
        "delete": 524385,
        "getmore": 2805620,
        "insert": 24361,
        "query": 6027449,
        "update": 1476490,
    },
    "opcountersRepl": {
        "command": 0,
        "delete": 0,
        "getmore": 0,
        "insert": 0,
        "query": 0,
        "update": 0,
    },
}


@pytest.mark.parametrize(
    "string_table",
    [
        pytest.param(
            [
                ["opcounters", "getmore", "2805620"],
                ["opcounters", "insert", "24361"],
                ["opcounters", "update", "1476490"],
                ["opcounters", "command", "71299015"],
                ["opcounters", "query", "6027449"],
                ["opcounters", "delete", "524385"],
                ["opcountersRepl", "getmore", "0"],
                ["opcountersRepl", "insert", "0"],
                ["opcountersRepl", "update", "0"],
                ["opcountersRepl", "command", "0"],
                ["opcountersRepl", "query", "0"],
                ["opcountersRepl", "delete", "0"],
            ],
            id="standard case",
        ),
        pytest.param(
            [
                ["opcounters", "getmore", "2805620"],
                ["opcounters", "insert", "24361"],
                [
                    "opcounters",
                    "deprecated",
                    "{u'getmore':",
                    "0L,",
                    "u'insert':",
                    "0L,",
                    "u'killcursors':",
                    "0L,",
                    "u'update':",
                    "0L,",
                    "u'query':",
                    "1L,",
                    "u'total':",
                    "1L,",
                    "u'delete':",
                    "0L}",
                ],
                ["opcounters", "update", "1476490"],
                ["opcounters", "command", "71299015"],
                ["opcounters", "query", "6027449"],
                ["opcounters", "delete", "524385"],
                ["opcountersRepl", "getmore", "0"],
                ["opcountersRepl", "insert", "0"],
                ["opcountersRepl", "update", "0"],
                ["opcountersRepl", "command", "0"],
                ["opcountersRepl", "query", "0"],
                ["opcountersRepl", "delete", "0"],
            ],
            id="with counter 'deprecated'",
        ),
    ],
)
def test_parse_mongodb_counters(
    string_table: StringTable,
) -> None:
    assert parse_mongodb_counters(string_table) == _SECTION

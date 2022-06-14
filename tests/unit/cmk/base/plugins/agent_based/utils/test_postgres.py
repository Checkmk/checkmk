#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.plugins.agent_based.utils import postgres


def test_parse_function_for_stats_section() -> None:
    assert postgres.parse_dbs(
        [
            ["[databases_start]"],
            ["postgres"],
            ["adwebconnect"],
            ["[databases_end]"],
            ["datname", "sname", "tname", "vtime", "atime"],
            ["postgres", "pg_catalog", "pg_statistic", "-1", "-1"],
            ["adwebconnect", "public", "serveraktion", "1488881726", "1488881726"],
            ["adwebconnect", "pg_catalog", "pg_statistic", "1488882719", "-1"],
            ["adwebconnect", "public", "auftrag", "1489001316", "1489001316"],
            ["adwebconnect", "public", "anrede", "-1", "-1"],
            ["adwebconnect", "public", "auftrag_mediadaten", "-1", ""],
        ]
    ) == {
        "adwebconnect": [
            {
                "atime": "1488881726",
                "sname": "public",
                "tname": "serveraktion",
                "vtime": "1488881726",
            },
            {"atime": "-1", "sname": "pg_catalog", "tname": "pg_statistic", "vtime": "1488882719"},
            {"atime": "1489001316", "sname": "public", "tname": "auftrag", "vtime": "1489001316"},
            {"atime": "-1", "sname": "public", "tname": "anrede", "vtime": "-1"},
            {"atime": "", "sname": "public", "tname": "auftrag_mediadaten", "vtime": "-1"},
        ],
        "postgres": [
            {"atime": "-1", "sname": "pg_catalog", "tname": "pg_statistic", "vtime": "-1"},
        ],
    }

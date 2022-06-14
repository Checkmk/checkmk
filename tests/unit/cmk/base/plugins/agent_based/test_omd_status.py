#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.omd_status import (
    check_omd_status,
    cluster_check_omd_status,
    parse_omd_status,
)


@pytest.mark.parametrize(
    "string_table,expected_parsed_data",
    [
        (
            [
                ["[heute]"],
                ["cmc", "0"],
                ["apache", "0"],
                ["OVERALL", "0"],
                ["[stable]"],
                ["cmc", "0"],
                ["apache", "0"],
                ["OVERALL", "0"],
            ],
            {
                "heute": {"stopped": [], "existing": ["cmc", "apache"], "overall": "running"},
                "stable": {"stopped": [], "existing": ["cmc", "apache"], "overall": "running"},
            },
        ),
        ([], {}),
    ],
)
def test_parse_omd_status(string_table, expected_parsed_data) -> None:
    assert parse_omd_status(string_table) == expected_parsed_data


@pytest.mark.parametrize(
    "item,section_omd_status,section_omd_info,result",
    [
        (
            "stable",
            {
                "heute": {
                    "stopped": [],
                    "existing": ["mknotifyd", "rrdcached", "cmc", "apache", "dcd", "crontab"],
                    "overall": "running",
                },
                "stable": {
                    "stopped": [],
                    "existing": ["mknotifyd", "rrdcached", "cmc", "apache", "dcd", "crontab"],
                    "overall": "running",
                },
            },
            {
                "versions": {
                    "1.6.0-2020.04.27.cee": {
                        "version": "1.6.0-2020.04.27.cee",
                        "number": "1.6.0-2020.04.27",
                        "edition": "cee",
                        "demo": "0",
                    },
                },
                "sites": {
                    "heute": {"site": "heute", "used_version": "2020.07.29.cee", "autostart": "1"},
                    "stable": {
                        "site": "stable",
                        "used_version": "1.6.0-2020.07.22.cee",
                        "autostart": "0",
                    },
                },
            },
            [Result(state=state.OK, summary="running")],
        ),
    ],
)
def test_check_omd_status(item, section_omd_status, section_omd_info, result) -> None:
    assert list(check_omd_status(item, section_omd_status, section_omd_info)) == result


@pytest.mark.parametrize(
    "item,section_omd_status,section_omd_info,result",
    [
        (
            "stable",
            {
                "monitoring": {
                    "heute": {
                        "stopped": [],
                        "existing": ["mknotifyd", "rrdcached", "cmc", "apache", "dcd", "crontab"],
                        "overall": "running",
                    },
                    "stable": {
                        "stopped": [],
                        "existing": ["mknotifyd", "rrdcached", "cmc", "apache", "dcd", "crontab"],
                        "overall": "running",
                    },
                }
            },
            {"monitoring": {}},
            [Result(state=state.OK, summary="running")],
        ),
        (
            "site2",
            {
                "hostname1": {},
                "hostname2": {
                    "site1": {
                        "stopped": [],
                        "existing": [
                            "mkeventd",
                            "liveproxyd",
                            "mknotifyd",
                            "rrdcached",
                            "cmc",
                            "apache",
                            "dcd",
                            "crontab",
                        ],
                        "overall": "running",
                    },
                    "site2": {
                        "stopped": [],
                        "existing": [
                            "mkeventd",
                            "liveproxyd",
                            "mknotifyd",
                            "rrdcached",
                            "cmc",
                            "apache",
                            "dcd",
                            "crontab",
                        ],
                        "overall": "running",
                    },
                },
            },
            {"hostname1": None, "hostname2": None},
            [Result(state=state.OK, summary="running")],
        ),
    ],
)
def test_cluster_check_omd_status(item, section_omd_status, section_omd_info, result) -> None:
    assert list(cluster_check_omd_status(item, section_omd_status, section_omd_info)) == result

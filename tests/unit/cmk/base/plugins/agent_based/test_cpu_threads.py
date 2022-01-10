#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict

import pytest

from cmk.base.api.agent_based.checking_classes import Metric, Result, State
from cmk.base.plugins.agent_based.agent_based_api.v1 import Service
from cmk.base.plugins.agent_based.cpu import parse_cpu
from cmk.base.plugins.agent_based.cpu_threads import check_cpu_threads, discover_cpu_threads
from cmk.base.plugins.agent_based.utils.cpu import Load, Section, Threads


def test_cpu_threads():
    section = Section(
        load=Load(0.1, 0.1, 0.1),
        num_cpus=4,
        threads=Threads(count=1234),
    )
    params: Dict[str, Any] = {}
    result = set(check_cpu_threads(params, section))
    assert result == {
        Metric("threads", 1234.0),
        Result(state=State.OK, summary="1234"),
    }


def test_cpu_threads_max_threads():
    section = Section(
        load=Load(0.1, 0.1, 0.1),
        num_cpus=4,
        threads=Threads(count=1234, max=2468),
    )
    params: Dict[str, Any] = {}
    result = set(check_cpu_threads(params, section))
    assert result == {
        Metric("thread_usage", 50.0),
        Metric("threads", 1234.0),
        Result(state=State.OK, summary="1234"),
        Result(state=State.OK, summary="Usage: 50.00%"),
    }


@pytest.mark.parametrize(
    "info, check_result",
    [
        (
            [["0.88", "0.83", "0.87", "2/2148", "21050", "8"]],
            {
                Metric("threads", 2148.0, levels=(2000.0, 4000.0)),
                Result(state=State.WARN, summary="2148 (warn/crit at 2000/4000)"),
            },
        ),
        (
            [["0.88", "0.83", "0.87", "2/1748", "21050", "8"], ["124069"]],
            {
                Metric("threads", 1748.0, levels=(2000.0, 4000.0)),
                Result(state=State.OK, summary="1748"),
                Metric("thread_usage", 1.408893438328672),
                Result(state=State.OK, summary="Usage: 1.41%"),
            },
        ),
    ],
)
def test_cpu_threads_regression(info, check_result):
    section = parse_cpu(info)
    assert section is not None
    params = {"levels": (2000, 4000)}
    assert list(discover_cpu_threads(section)) == [Service()]
    assert set(check_cpu_threads(params, section)) == check_result

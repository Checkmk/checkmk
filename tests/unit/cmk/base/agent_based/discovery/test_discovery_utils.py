#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.base.agent_based.discovery.utils import QualifiedDiscovery, TimeLimitFilter


def test_time_limit_filter_iterates():

    with TimeLimitFilter(limit=42, grace=0) as limiter:
        test_list = list(limiter(range(3)))
    assert test_list == [0, 1, 2]


def test_time_limit_filter_stops():
    def test_generator():
        time.sleep(10)
        yield

    # sorry for for wasting one second of your time
    with TimeLimitFilter(limit=1, grace=0) as limiter:
        assert not list(limiter(test_generator()))


def test_qualified_discovery():

    result = QualifiedDiscovery(
        preexisting=(1, 2),
        current=(2, 3),
        key=lambda x: x,
    )

    assert result.vanished == [1]
    assert result.old == [2]
    assert result.new == [3]
    assert result.present == [2, 3]


def test_qualified_discovery_keeps_old():

    # e.g.: same service, different parameters
    result = QualifiedDiscovery(
        preexisting=["this is old"],
        current=["this is new"],
        key=lambda x: x[:6],
    )

    assert not result.vanished
    assert result.old == ["this is old"]
    assert not result.new
    assert result.present == ["this is old"]

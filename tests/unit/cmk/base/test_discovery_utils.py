#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.base.discovery.utils import TimeLimitFilter


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

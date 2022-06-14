#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.observer import FetcherMemoryObserver


def test_fetcher_memory_observer() -> None:
    observer = FetcherMemoryObserver(170)

    # Phase 1. Wait for steady and ignore any problems
    try:
        observer._allowed_growth = 1  # simulate memory overload
        assert observer.memory_usage() == 0
        for _ in range(observer._steady_cycle_num):
            observer.check_resources("13;heute;checking;60")
    except SystemExit:
        pytest.fail("Should not exit at the phase")

    assert observer._context() == '[cycle 5, command "13;heute;checking;60"]'
    assert observer.memory_usage() != 0

    # Phase 2. Steady achieved.
    try:
        observer._allowed_growth = 500  # no more overload
        observer.check_resources(None)  # execute
    except SystemExit:
        pytest.fail("Should not exit at the phase")

    observer._allowed_growth = 1  # simulate memory overload
    with pytest.raises(SystemExit) as exit_expected:
        observer.check_resources(None)  # execute
    assert exit_expected.type == SystemExit
    assert exit_expected.value.code == 14

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.observer import FetcherMemoryObserver


def _achieve_steady_state(observer: FetcherMemoryObserver) -> None:
    """Wait for steady and ignore any problems"""
    try:
        for _ in range(5):  # '5 checks ti achieve steady state' is a business rule
            observer.check_resources("13;heute;checking;60")
    except SystemExit:
        pytest.fail("Should not exit at the phase")


def test_fetcher_memory_observer_before_steady() -> None:
    observer = FetcherMemoryObserver(100)
    observer.check_resources(None)
    # use real RAM
    very_big_object = []
    for _ in range(10000):
        very_big_object.append(10000 * "aaa")
    # expected NO reaction on overflow BEFORE steady achieved
    try:
        observer.check_resources(None)
    except SystemExit:
        pytest.fail("Should not exit at the phase")


def test_fetcher_memory_observer_steady_setup() -> None:
    observer = FetcherMemoryObserver(100)
    assert observer.memory_usage() == 0
    _achieve_steady_state(observer)
    assert observer._context() == '[cycle 5, command "13;heute;checking;60"]'
    assert observer.memory_usage() != 0


def test_fetcher_memory_overflow() -> None:
    observer = FetcherMemoryObserver(100)
    _achieve_steady_state(observer)
    # use real RAM
    very_big_object = []
    for _ in range(10000):
        very_big_object.append(10000 * "aaa")
    # expected EXIT on overflow AFTER steady achieved
    with pytest.raises(SystemExit) as exit_expected:
        observer.check_resources(None, False)
    assert exit_expected.type == SystemExit
    assert exit_expected.value.code == 14


def test_fetcher_memory_observer_no_overflow() -> None:
    observer = FetcherMemoryObserver(1000)
    _achieve_steady_state(observer)
    very_big_object = []
    for _ in range(10000):
        very_big_object.append(10000 * "aaa")
    # no reaction for very big numbers(as checker)
    try:
        observer.check_resources(None, False)
    except SystemExit:
        pytest.fail("Should not exit at the phase")


def test_fetcher_memory_observer_hard_limit() -> None:
    ram_size = 10000
    observer = FetcherMemoryObserver(200, lambda: ram_size)
    _achieve_steady_state(observer)

    ram_size = observer.memory_usage() * 4 + 1000  # simulate hard limit break
    with pytest.raises(SystemExit) as exit_expected:
        observer.check_resources(None, False)
    assert exit_expected.type == SystemExit
    assert exit_expected.value.code == 14

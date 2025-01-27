#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.utils.observer import FetcherMemoryObserver, vm_size

LOG_MESSAGE = "13;heute;checking;60"
ONE_KiB = 2**10  # 1024
STEADY_CYCLE = 5


def _change_state(
    observer: FetcherMemoryObserver, log: str | None = None, steady: bool = False
) -> None:
    """Change state of 'observer' by one cycle, unless 'steady' is mentioned."""
    num_cycles = STEADY_CYCLE if steady else 1
    try:
        for _ in range(num_cycles):  # '5 checks to achieve steady state' is a business rule
            observer.check_resources(log, verbose=False)
    except SystemExit as excp:
        pytest.fail(f"Should not exit at the phase\n{excp}")


def test_fetcher_memory_observer_before_steady() -> None:
    memory_used = ONE_KiB
    observer = FetcherMemoryObserver(100, lambda: memory_used)
    initial_memory_usage = observer.memory_usage()
    _change_state(observer)
    # exceed 'hard_limit' of memory usage.
    memory_used += ONE_KiB
    # expected NO reaction on overflow BEFORE steady achieved
    _change_state(observer)
    assert initial_memory_usage == observer.memory_usage() == 0, (
        "Memory usage is updated ONLY at steady state!"
    )
    assert observer._num_check_cycles == 2


def test_fetcher_memory_observer_steady_setup() -> None:
    memory_usage = ONE_KiB
    observer = FetcherMemoryObserver(100, lambda: memory_usage)
    _change_state(observer, steady=True, log=LOG_MESSAGE)
    assert observer._context() == f'[cycle {STEADY_CYCLE}, command "{LOG_MESSAGE}"]'
    assert observer.memory_usage() == memory_usage


def test_fetcher_memory_observer_overflow() -> None:
    memory_used = ONE_KiB
    observer = FetcherMemoryObserver(100, lambda: memory_used)
    _change_state(observer, steady=True, log=LOG_MESSAGE)
    steady_state_memory_usage = observer.memory_usage()
    # exceed 'hard_limit' of memory usage.
    overflow = 1
    memory_used += overflow
    # expected EXIT on overflow AFTER steady achieved
    with pytest.raises(SystemExit) as exit_expected:
        observer.check_resources(None, False)
    assert observer._num_check_cycles == STEADY_CYCLE + 1
    assert observer.memory_usage() == steady_state_memory_usage, (
        "Memory usage is updated ONLY at steady state!"
    )
    assert exit_expected.value.code == 14


@pytest.mark.parametrize("delta", [0, 10], ids=["at_limit", "below_limit"])
def test_fetcher_memory_observer_no_overflow(delta: int) -> None:
    memory_used = ONE_KiB
    factor = 2
    # 'allowed_growth' calculates 'hard_limit' as a factor of current memory usage.
    observer = FetcherMemoryObserver(factor * 100, lambda: memory_used)
    _change_state(observer, steady=True, log=LOG_MESSAGE)
    steady_state_memory_usage = observer.memory_usage()
    # define 'hard_limit' of memory usage.
    memory_used = (memory_used * factor) - delta
    # expected NO reaction
    _change_state(observer)
    assert observer.memory_usage() == steady_state_memory_usage, (
        "Memory usage is updated ONLY at steady state!"
    )


def test_fetcher_memory_obeserver_vm_size():
    mibs_to_bytes = 2**20
    memory_assigned = mibs_to_bytes * 50  # 50 MiBs
    initial_measure = vm_size()
    _ = bytearray(memory_assigned)  # use memory in RAM
    final_measure = vm_size()
    threshold = 5 * ONE_KiB
    _assertion = (final_measure - initial_measure) - memory_assigned  # observed - expected
    assert 0 < _assertion <= threshold


@pytest.mark.parametrize("growth_factor", [0.2, 2], ids=["fractional", "integral"])
def test_fetcher_memory_observer_hard_limit(growth_factor: float) -> None:
    ram_size = ONE_KiB
    expected_limit = int(ram_size * growth_factor)
    observer = FetcherMemoryObserver(int(growth_factor * 100), lambda: ram_size)
    assert observer.hard_limit() == 0, "Updates itself ONLY at steady state!"
    _change_state(observer, steady=True, log=LOG_MESSAGE)
    assert observer.hard_limit() == expected_limit

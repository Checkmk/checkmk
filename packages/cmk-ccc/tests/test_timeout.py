#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import signal
from collections.abc import Iterator

import pytest

from cmk.ccc.timeout import MKTimeout, Timeout


@pytest.fixture(name="restored_sigalrm")
def fixture_restored_sigalrm() -> Iterator[None]:
    """Restore the handling of SIGALRM afterwards: Timeout leaves it ignored"""
    previous = signal.getsignal(signal.SIGALRM)
    yield
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous)


@pytest.mark.usefixtures("restored_sigalrm")
def test_timeout_arms_the_alarm_for_its_seconds() -> None:
    with Timeout(3600, message="too slow"):
        remaining, _interval = signal.getitimer(signal.ITIMER_REAL)

    # Only a process stopped for half an hour would see less.
    assert 1800 < remaining <= 3600


@pytest.mark.usefixtures("restored_sigalrm")
def test_alarm_raises_the_message_of_the_timeout() -> None:
    with pytest.raises(MKTimeout, match="^too slow$"), Timeout(3600, message="too slow"):
        signal.raise_signal(signal.SIGALRM)


@pytest.mark.usefixtures("restored_sigalrm")
def test_timeout_is_signaled_after_an_alarm() -> None:
    timeout = Timeout(3600, message="too slow")

    with pytest.raises(MKTimeout), timeout:
        signal.raise_signal(signal.SIGALRM)

    assert timeout.signaled


@pytest.mark.usefixtures("restored_sigalrm")
def test_timeout_is_not_signaled_without_an_alarm() -> None:
    timeout = Timeout(3600, message="too slow")

    with timeout:
        pass

    assert not timeout.signaled


@pytest.mark.usefixtures("restored_sigalrm")
def test_reentered_timeout_forgets_an_earlier_alarm() -> None:
    timeout = Timeout(3600, message="too slow")
    with pytest.raises(MKTimeout), timeout:
        signal.raise_signal(signal.SIGALRM)

    with timeout:
        pass

    assert not timeout.signaled


@pytest.mark.usefixtures("restored_sigalrm")
def test_leaving_the_timeout_disarms_the_alarm() -> None:
    with Timeout(3600, message="too slow"):
        pass

    assert signal.getitimer(signal.ITIMER_REAL)[0] == 0


@pytest.mark.usefixtures("restored_sigalrm")
def test_leaving_the_timeout_ignores_a_late_alarm() -> None:
    with Timeout(3600, message="too slow"):
        pass

    assert signal.getsignal(signal.SIGALRM) == signal.SIG_IGN

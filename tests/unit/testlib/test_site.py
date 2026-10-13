#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for :meth:`tests.testlib.system.site.Site.stop`.

A site that does not reach the stopped state fails in fixture teardown, where it is read as
a flake of whichever test ran last. What a caller needs from ``stop()`` is therefore to wait
for a site which is merely slow to shut down, and to report a site which is genuinely stuck
as a timeout naming what is still running - not as a bare exception.
"""

import subprocess
import time
from collections.abc import Sequence
from typing import override

import pytest

from tests.testlib.system import site as site_module
from tests.testlib.system.site import Site

# 'omd status' exit codes
_RUNNING = 0
_STOPPED = 1
_PARTIALLY_RUNNING = 2


class _OmdStub:
    """Stand-in for `Site.omd`.

    The site is running until "stop" is called. From then on each "status" call answers the
    next entry of `states_after_stop`; the last entry repeats.
    """

    def __init__(self, states_after_stop: Sequence[int], bare_status: str = "") -> None:
        self._states_after_stop = list(states_after_stop)
        self._bare_status = bare_status
        self._stop_called = False
        self.status_polls_after_stop = 0

    def __call__(
        self, mode: str, *args: str, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if mode == "stop":
            self._stop_called = True
            return self._completed(0)
        if mode != "status":
            return self._completed(0)
        state = self._next_state()
        return self._completed(state, self._bare_status if "--bare" in args else f"OVERALL {state}")

    def _next_state(self) -> int:
        if not self._stop_called:
            return _RUNNING
        self.status_polls_after_stop += 1
        return (
            self._states_after_stop.pop(0)
            if len(self._states_after_stop) > 1
            else self._states_after_stop[0]
        )

    def _completed(self, returncode: int, stdout: str = "") -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["omd"], returncode=returncode, stdout=stdout, stderr=""
        )

    @override
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(polls={self.status_polls_after_stop})"


class _FakeClock:
    """Stand-in for `time.time` and `time.sleep`: sleeping advances the clock instantly."""

    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(name="site_without_processes")
def fixture_site_without_processes(monkeypatch: pytest.MonkeyPatch) -> Site:
    """A Site which talks to no real site: process lookups answer 'nothing running'."""
    monkeypatch.setattr(site_module, "check_output", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(site_module, "get_processes_by_cmdline", lambda _pattern: [])
    # the polling itself is what is under test here, its pace is not
    clock = _FakeClock()
    monkeypatch.setattr(time, "time", clock.time)
    monkeypatch.setattr(time, "sleep", clock.sleep)
    site = object.__new__(Site)
    site.id = "unit_test_site"
    return site


def test_stop_keeps_waiting_for_a_site_which_is_slow_to_shut_down(
    site_without_processes: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    # a site which is still partially running for a while after "omd stop" returned
    omd = _OmdStub([_PARTIALLY_RUNNING] * 15 + [_STOPPED])
    monkeypatch.setattr(site_without_processes, "omd", omd)

    site_without_processes.stop()

    assert omd.status_polls_after_stop == 16


def test_stop_reports_a_timeout_naming_the_service_which_keeps_running(
    site_without_processes: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        site_without_processes,
        "omd",
        _OmdStub([_PARTIALLY_RUNNING], bare_status="apache 1\ndcd 0\nOVERALL 2"),
    )

    with pytest.raises(TimeoutError) as excinfo:
        site_without_processes.stop()

    note = "\n".join(excinfo.value.__notes__)
    assert "Still running: dcd\n" in note, note

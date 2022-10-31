#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path
from typing import Generator

import pytest

from cmk.base.auto_queue import AutodiscoveryQueue, TimeLimitFilter


def test_time_limit_filter_iterates() -> None:

    with TimeLimitFilter(limit=42, grace=0) as limiter:
        test_list = list(limiter(iter(range(3))))
    assert test_list == [0, 1, 2]


def test_time_limit_filter_stops() -> None:
    def test_generator() -> Generator:
        time.sleep(10)
        yield

    # sorry for for wasting one second of your time
    with TimeLimitFilter(limit=1, grace=0) as limiter:
        assert not list(limiter(test_generator()))


@pytest.fixture(name="autodiscovery_queue")
def _mocked_queue(tmpdir):
    adq = AutodiscoveryQueue()
    mockdir = Path(tmpdir)
    (mockdir / "most").touch()
    (mockdir / "lost").touch()
    adq._dir = mockdir
    yield adq


class TestAutodiscoveryQueue:
    def test_len(self, autodiscovery_queue) -> None:  # type:ignore[no-untyped-def]
        assert len(AutodiscoveryQueue()) == 0
        assert len(autodiscovery_queue) == 2

    def test_bool(self, autodiscovery_queue) -> None:  # type:ignore[no-untyped-def]
        assert not AutodiscoveryQueue()
        assert autodiscovery_queue

    def test_oldest_empty(self) -> None:
        assert AutodiscoveryQueue().oldest() is None

    def test_oldest_populated(self, autodiscovery_queue) -> None:  # type:ignore[no-untyped-def]
        assert isinstance(autodiscovery_queue.oldest(), float)

    def test_queued_empty(  # type:ignore[no-untyped-def]
        self, autodiscovery_queue, monkeypatch
    ) -> None:
        autodiscovery_queue = AutodiscoveryQueue()
        assert not list(autodiscovery_queue.queued_hosts())

    def test_queued_populated(  # type:ignore[no-untyped-def]
        self, autodiscovery_queue, monkeypatch
    ) -> None:
        assert set(autodiscovery_queue.queued_hosts()) == {"most", "lost"}

    def test_add(self, autodiscovery_queue, monkeypatch) -> None:  # type:ignore[no-untyped-def]
        autodiscovery_queue = AutodiscoveryQueue()
        autodiscovery_queue.add("most")
        assert list(autodiscovery_queue.queued_hosts()) == ["most"]

    def test_remove(self, autodiscovery_queue, monkeypatch) -> None:  # type:ignore[no-untyped-def]
        autodiscovery_queue.remove("lost")
        assert list(autodiscovery_queue.queued_hosts()) == ["most"]

    def test_cleanup(self, autodiscovery_queue) -> None:  # type:ignore[no-untyped-def]
        autodiscovery_queue.cleanup(valid_hosts={"lost", "rost"}, logger=lambda x: None)
        assert list(autodiscovery_queue.queued_hosts()) == ["lost"]

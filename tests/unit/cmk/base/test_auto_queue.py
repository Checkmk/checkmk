#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Generator, Iterator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

import cmk.base.auto_queue
from cmk.base.auto_queue import AutoQueue, TimeLimitFilter


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


@pytest.fixture(name="auto_queue")
def _mocked_queue(tmpdir: Path) -> Iterator[AutoQueue]:
    adq = AutoQueue(tmpdir / "dir1")
    mockdir = Path(tmpdir)
    (mockdir / "most").touch()
    (mockdir / "lost").touch()
    adq._dir = mockdir
    yield adq


class TestAutoQueue:
    def test_len(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        assert len(AutoQueue(tmpdir / "dir2")) == 0
        assert len(auto_queue) == 2

    def test_bool(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        assert not AutoQueue(tmpdir / "dir2")
        assert auto_queue

    def test_oldest_empty(self, tmpdir: Path) -> None:
        assert AutoQueue(tmpdir).oldest() is None

    def test_oldest_populated(self, auto_queue: AutoQueue) -> None:
        assert isinstance(auto_queue.oldest(), float)

    def test_queued_empty(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        auto_queue = AutoQueue(tmpdir / "dir2")
        assert not list(auto_queue.queued_hosts())

    def test_queued_populated(self, auto_queue: AutoQueue) -> None:
        assert set(auto_queue.queued_hosts()) == {"most", "lost"}

    def test_add(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        auto_queue = AutoQueue(tmpdir / "dir2")
        auto_queue.add("most")
        assert list(auto_queue.queued_hosts()) == ["most"]

    def test_add_existing(self, tmpdir: Path, auto_queue: AutoQueue, mocker: MockerFixture) -> None:
        auto_queue = AutoQueue(tmpdir / "dir2")
        auto_queue.add("most")

        mock_touch = mocker.patch.object(cmk.base.auto_queue.Path, "touch")
        auto_queue.add("most")

        mock_touch.assert_not_called()

    def test_remove(self, auto_queue: AutoQueue) -> None:
        auto_queue.remove("lost")
        assert list(auto_queue.queued_hosts()) == ["most"]

    def test_cleanup(self, auto_queue: AutoQueue) -> None:
        auto_queue.cleanup(valid_hosts={"lost", "rost"}, logger=lambda x: None)
        assert list(auto_queue.queued_hosts()) == ["lost"]

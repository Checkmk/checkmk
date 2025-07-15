#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.ccc.hostaddress import HostName

from cmk.utils.auto_queue import AutoQueue


@pytest.fixture(name="auto_queue")
def auto_queue_fixture(tmpdir: Path) -> Iterator[AutoQueue]:
    adq = AutoQueue(tmpdir)
    (adq.path / HostName("most")).touch()
    (adq.path / HostName("lost")).touch()
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
        assert not auto_queue

    def test_queued_populated(self, auto_queue: AutoQueue) -> None:
        assert set(auto_queue) == {HostName("most"), HostName("lost")}

    def test_add(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        auto_queue = AutoQueue(tmpdir / "dir2")
        auto_queue.add(HostName("most"))
        assert list(auto_queue) == [HostName("most")]

    def test_add_existing(self, tmpdir: Path, auto_queue: AutoQueue, mocker: MockerFixture) -> None:
        auto_queue = AutoQueue(tmpdir / "dir2")
        auto_queue.add(HostName("most"))

        mock_touch = mocker.patch.object(Path, "touch")
        auto_queue.add(HostName("most"))

        mock_touch.assert_not_called()

#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.checkengine.auto_queue import AutoQueue


@pytest.fixture(name="auto_queue")
def auto_queue_fixture(tmpdir: Path) -> Iterator[AutoQueue]:
    adq = AutoQueue(Path(tmpdir))
    adq.add(HostName("most"))
    adq.add(HostName("lost"))
    yield adq


class TestAutoQueue:
    def test_len(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        assert len(AutoQueue(Path(tmpdir) / "dir2")) == 0
        assert len(auto_queue) == 2

    def test_bool(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        assert not AutoQueue(Path(tmpdir) / "dir2")
        assert auto_queue

    def test_oldest_empty(self, tmpdir: Path) -> None:
        assert AutoQueue(Path(tmpdir)).oldest() is None

    def test_oldest_populated(self, auto_queue: AutoQueue) -> None:
        assert isinstance(auto_queue.oldest(), float)

    def test_queued_empty(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        auto_queue = AutoQueue(Path(tmpdir) / "dir2")
        assert not auto_queue

    def test_queued_populated(self, auto_queue: AutoQueue) -> None:
        assert set(auto_queue) == {HostName("most"), HostName("lost")}

    def test_add(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        auto_queue = AutoQueue(Path(tmpdir) / "dir2")
        auto_queue.add(HostName("most"))
        assert list(auto_queue) == [HostName("most")]

    def test_add_existing(self, tmpdir: Path, auto_queue: AutoQueue) -> None:
        host_name = HostName("most")
        auto_queue = AutoQueue(Path(tmpdir) / "dir2")
        auto_queue.add(HostName("most"))

        host_file = auto_queue._host_path(host_name)  # noqa: SLF001
        old_host_file_mtime = host_file.stat().st_mtime

        auto_queue.add(HostName("most"))

        assert old_host_file_mtime == host_file.stat().st_mtime

    def test_remove(self, tmpdir: Path) -> None:
        auto_queue = AutoQueue(Path(tmpdir) / "dir2")
        auto_queue.add(HostName("most"))
        auto_queue.remove(HostName("most"))
        assert len(auto_queue) == 0

    def test_remove_missing(self, tmpdir: Path) -> None:
        auto_queue = AutoQueue(Path(tmpdir) / "dir2")
        auto_queue.remove(HostName("most"))
        assert len(auto_queue) == 0

#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.base.agent_based.discovery as discovery


@pytest.fixture(name="autodiscovery_queue")
def _mocked_queue(tmpdir):
    adq = discovery.AutodiscoveryQueue()
    mockdir = Path(tmpdir)
    (mockdir / "most").touch()
    (mockdir / "lost").touch()
    adq._dir = mockdir
    yield adq


class TestAutodiscoveryQueue:
    def test_len(self, autodiscovery_queue) -> None:  # type:ignore[no-untyped-def]
        assert len(discovery.AutodiscoveryQueue()) == 0
        assert len(autodiscovery_queue) == 2

    def test_bool(self, autodiscovery_queue) -> None:  # type:ignore[no-untyped-def]
        assert not discovery.AutodiscoveryQueue()
        assert autodiscovery_queue

    def test_oldest_empty(self) -> None:
        assert discovery.AutodiscoveryQueue().oldest() is None

    def test_oldest_populated(self, autodiscovery_queue) -> None:  # type:ignore[no-untyped-def]
        assert isinstance(autodiscovery_queue.oldest(), float)

    def test_queued_empty(  # type:ignore[no-untyped-def]
        self, autodiscovery_queue, monkeypatch
    ) -> None:
        autodiscovery_queue = discovery.AutodiscoveryQueue()
        assert not list(autodiscovery_queue.queued_hosts())

    def test_queued_populated(  # type:ignore[no-untyped-def]
        self, autodiscovery_queue, monkeypatch
    ) -> None:
        assert set(autodiscovery_queue.queued_hosts()) == {"most", "lost"}

    def test_add(self, autodiscovery_queue, monkeypatch) -> None:  # type:ignore[no-untyped-def]
        autodiscovery_queue = discovery.AutodiscoveryQueue()
        autodiscovery_queue.add("most")
        assert list(autodiscovery_queue.queued_hosts()) == ["most"]

    def test_remove(self, autodiscovery_queue, monkeypatch) -> None:  # type:ignore[no-untyped-def]
        autodiscovery_queue.remove("lost")
        assert list(autodiscovery_queue.queued_hosts()) == ["most"]

    def test_cleanup(self, autodiscovery_queue) -> None:  # type:ignore[no-untyped-def]
        autodiscovery_queue.cleanup(valid_hosts={"lost", "rost"}, logger=lambda x: None)
        assert list(autodiscovery_queue.queued_hosts()) == ["lost"]

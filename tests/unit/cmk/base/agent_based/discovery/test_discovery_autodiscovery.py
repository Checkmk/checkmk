#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

import cmk.base.agent_based.discovery as discovery


@pytest.fixture(name="autodiscovery_queue")
def _mocked_queue(tmpdir):
    adq = discovery._AutodiscoveryQueue()
    mockdir = Path(tmpdir)
    (mockdir / "most").touch()
    (mockdir / "lost").touch()
    adq._dir = mockdir
    yield adq


class TestAutodiscoveryQueue:
    def test_oldest_empty(self):
        assert discovery._AutodiscoveryQueue().oldest() is None

    def test_oldest_populated(self, autodiscovery_queue):
        assert isinstance(autodiscovery_queue.oldest(), float)

    def test_queued_empty(self, autodiscovery_queue, monkeypatch):
        autodiscovery_queue = discovery._AutodiscoveryQueue()
        assert not list(autodiscovery_queue.queued_hosts())

    def test_queued_populated(self, autodiscovery_queue, monkeypatch):
        assert set(autodiscovery_queue.queued_hosts()) == {"most", "lost"}

    def test_add(self, autodiscovery_queue, monkeypatch):
        autodiscovery_queue = discovery._AutodiscoveryQueue()
        autodiscovery_queue.add("most")
        assert list(autodiscovery_queue.queued_hosts()) == ["most"]

    def test_remove(self, autodiscovery_queue, monkeypatch):
        autodiscovery_queue.remove("lost")
        assert list(autodiscovery_queue.queued_hosts()) == ["most"]

    def test_cleanup(self, autodiscovery_queue):
        autodiscovery_queue.cleanup(valid_hosts={"lost", "rost"}, logger=lambda x: None)
        assert list(autodiscovery_queue.queued_hosts()) == ["lost"]

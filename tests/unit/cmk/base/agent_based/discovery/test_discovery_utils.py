#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Generator

import pytest

from cmk.base.agent_based.discovery.utils import DiscoveryMode, QualifiedDiscovery, TimeLimitFilter


class TestDiscoveryMode:
    @staticmethod
    def test_modes_wato() -> None:
        # these are special, in the sense that they might be contained in
        # users configs, so they must be created from 0-3.
        assert DiscoveryMode(0) is DiscoveryMode.NEW
        assert DiscoveryMode(1) is DiscoveryMode.REMOVE
        assert DiscoveryMode(2) is DiscoveryMode.FIXALL
        assert DiscoveryMode(3) is DiscoveryMode.REFRESH

    @staticmethod
    def test_modes_invalid() -> None:
        invalid = len(DiscoveryMode)
        assert DiscoveryMode(invalid) is DiscoveryMode.FALLBACK
        with pytest.raises(KeyError):
            _ = DiscoveryMode.from_str("UNKNOWN")

    @staticmethod
    def test_modes_automation() -> None:
        # these strings are used by (remote) automation calls, and must not be changed!
        assert DiscoveryMode.from_str("new") is DiscoveryMode.NEW
        assert DiscoveryMode.from_str("remove") is DiscoveryMode.REMOVE
        assert DiscoveryMode.from_str("fixall") is DiscoveryMode.FIXALL
        assert DiscoveryMode.from_str("refresh") is DiscoveryMode.REFRESH
        assert DiscoveryMode.from_str("only-host-labels") == DiscoveryMode.ONLY_HOST_LABELS


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


def test_qualified_discovery() -> None:

    result = QualifiedDiscovery(
        preexisting=(1, 2),
        current=(2, 3),
        key=lambda x: x,
    )

    assert result.vanished == [1]
    assert result.old == [2]
    assert result.new == [3]
    assert result.present == [2, 3]

    assert list(result.chain_with_qualifier()) == [
        ("vanished", 1),
        ("old", 2),
        ("new", 3),
    ]


def test_qualified_discovery_keeps_old() -> None:

    # e.g.: same service, different parameters
    result = QualifiedDiscovery(
        preexisting=["this is old"],
        current=["this is new"],
        key=lambda x: x[:6],
    )

    assert not result.vanished
    assert result.old == ["this is old"]
    assert not result.new
    assert result.present == ["this is old"]


def test_qualified_discovery_replaced() -> None:
    result = QualifiedDiscovery(
        preexisting=(
            [
                {"key": "a", "value": "1"},
                {"key": "b", "value": "1"},
            ]
        ),
        current=(
            [
                {"key": "a", "value": "1"},
                {"key": "b", "value": "2"},
            ]
        ),
        key=lambda item: item["key"] + ":" + item["value"],
    )

    assert result.vanished == [{"key": "b", "value": "1"}]
    assert result.old == [{"key": "a", "value": "1"}]
    assert result.new == [{"key": "b", "value": "2"}]
    assert result.present == [{"key": "a", "value": "1"}, {"key": "b", "value": "2"}]

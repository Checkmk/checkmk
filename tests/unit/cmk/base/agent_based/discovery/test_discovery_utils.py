#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

import pytest

from cmk.utils.labels import HostLabel

from cmk.checkers.discovery import DiscoveryMode, QualifiedDiscovery


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


@dataclass(frozen=True)
class _Discoverable:
    name: str
    value: str = ""

    def id(self) -> str:
        return self.name


def test_qualified_discovery() -> None:
    result = QualifiedDiscovery(
        preexisting=(_Discoverable("one"), _Discoverable("two")),
        current=(_Discoverable("two"), _Discoverable("three")),
    )

    assert result.vanished == [_Discoverable("one")]
    assert result.old == [_Discoverable("two")]
    assert result.new == [_Discoverable("three")]
    assert result.present == [_Discoverable("two"), _Discoverable("three")]

    assert list(result.chain_with_qualifier()) == [
        ("vanished", _Discoverable("one")),
        ("old", _Discoverable("two")),
        ("new", _Discoverable("three")),
    ]


def test_qualified_discovery_keeps_old() -> None:
    # This behaviour is debatable; but this is the way it is, so test it.
    # e.g.: same service, changed parameters
    result = QualifiedDiscovery(
        preexisting=[_Discoverable("name", "old value")],
        current=[_Discoverable("name", "new value")],
    )

    assert not result.vanished
    assert result.old == [_Discoverable("name", "old value")]
    assert not result.new
    assert result.present == [_Discoverable("name", "old value")]


def test_qualified_discovery_replaced() -> None:
    # Note: this does not keep the old value, but the new one.
    result = QualifiedDiscovery(
        preexisting=[HostLabel("a", "1"), HostLabel("b", "1")],
        current=[HostLabel("a", "1"), HostLabel("b", "2")],
    )

    assert result.vanished == [HostLabel("b", "1")]
    assert result.old == [HostLabel("a", "1")]
    assert result.new == [HostLabel("b", "2")]
    assert result.present == [HostLabel("a", "1"), HostLabel("b", "2")]

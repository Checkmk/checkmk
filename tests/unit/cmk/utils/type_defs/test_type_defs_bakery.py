#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import (
    BakeryTarget,
    BakeryTargetFolder,
    BakeryTargetHost,
    BakeryTargetVanilla,
    get_bakery_target,
    HostName,
)


class TestBakeryTargetVanilla:
    def test_serialize(self) -> None:
        assert isinstance(BakeryTargetVanilla().serialize(), str)

    def test_deserialize_ok(self) -> None:
        assert BakeryTargetVanilla() == BakeryTargetVanilla.deserialize(
            BakeryTargetVanilla().serialize()
        )

    def test_deserialize_fails(self) -> None:
        with pytest.raises(ValueError):
            BakeryTargetVanilla.deserialize("sktbh")

        with pytest.raises(ValueError):
            BakeryTargetVanilla.deserialize(BakeryTargetHost(HostName("host")).serialize())

        with pytest.raises(ValueError):
            BakeryTargetVanilla.deserialize(BakeryTargetFolder("folder").serialize())

    def test_hashable(self) -> None:
        assert BakeryTargetVanilla() in {BakeryTargetVanilla()}

    def test_equals(self) -> None:
        assert BakeryTargetVanilla() == BakeryTargetVanilla()
        assert BakeryTargetVanilla() != 21  # type: ignore[comparison-overlap]


class TestBakeryTargetFolder:
    def test_serialize(self) -> None:
        assert isinstance(BakeryTargetFolder("foo/bar").serialize(), str)

    def test_deserialize_ok(self) -> None:
        btf = BakeryTargetFolder("foo/bar")
        assert btf == BakeryTargetFolder.deserialize(btf.serialize())

    def test_deserialize_fails(self) -> None:
        with pytest.raises(ValueError):
            BakeryTargetFolder.deserialize("sktbh")

        with pytest.raises(ValueError):
            BakeryTargetFolder.deserialize(BakeryTargetHost(HostName("host")).serialize())

        with pytest.raises(ValueError):
            BakeryTargetFolder.deserialize(BakeryTargetVanilla().serialize())

    def test_hashable(self) -> None:
        assert BakeryTargetFolder("foo/bar") in {BakeryTargetFolder("foo/bar")}

    def test_equals(self) -> None:
        assert BakeryTargetFolder("foo/bar") == BakeryTargetFolder("foo/bar")
        assert BakeryTargetFolder("foo/bar") != BakeryTargetFolder("bar/foos")
        assert BakeryTargetFolder("knulf") != "knulf"  # type: ignore[comparison-overlap]


class TestBakeryTargetHost:
    def test_serialize(self) -> None:
        assert isinstance(BakeryTargetHost(HostName("foobar")).serialize(), str)

    def test_deserialize_ok(self) -> None:
        bth = BakeryTargetHost(HostName("foobar"))
        assert bth == BakeryTargetHost.deserialize(bth.serialize())

    # These should all fail, because these are no valid host names :-(
    def test_deserialize_fails(self) -> None:
        # with pytest.raises(ValueError):
        BakeryTargetHost.deserialize("no limits on what can be a host name :-(")

        # with pytest.raises(ValueError):
        BakeryTargetHost.deserialize(BakeryTargetFolder("foobar").serialize())

        # with pytest.raises(ValueError):
        BakeryTargetHost.deserialize(BakeryTargetVanilla().serialize())

    def test_hashable(self) -> None:
        assert BakeryTargetHost(HostName("foobar")) in {BakeryTargetHost(HostName("foobar"))}

    def test_equals(self) -> None:
        assert BakeryTargetHost(HostName("foobar")) == BakeryTargetHost(HostName("foobar"))
        assert BakeryTargetHost(HostName("foobar")) != BakeryTargetHost(HostName("barfoos"))
        assert BakeryTargetHost(HostName("knulf")) != "knulf"  # type: ignore[comparison-overlap]


@pytest.mark.parametrize(
    "target",
    [
        # regular
        BakeryTargetHost(HostName("my_host")),
        BakeryTargetVanilla(),
        BakeryTargetFolder("foo/bar"),
        # weird cases
        BakeryTargetHost(HostName("foo/bar")),
        BakeryTargetFolder("_VANILLA"),
    ],
)
def test_get_bakery_target(target: BakeryTarget) -> None:
    assert get_bakery_target(target.serialize()) == target

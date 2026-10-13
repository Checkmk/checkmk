#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.plugins.traceroute.active_check.check_traceroute import main, Route


class _MockRoutertracer:
    def __init__(self, routers: set[str], n_hops: int) -> None:
        self.routers: Final = routers
        self.n_hops: Final = n_hops

    def __call__(
        self,
        *_args: object,
        **_kwargs: object,
    ) -> Route:
        return Route(
            self.routers,
            self.n_hops,
            "a -> b -> c\n",
        )


def test_main_empty(capsys: pytest.CaptureFixture[str]) -> None:
    assert not main(
        ["some-target"],
        _MockRoutertracer(set(), 0),
    )
    out, err = capsys.readouterr()
    assert (
        out
        == """0 hops, missing routers: none, bad routers: none
a -> b -> c
 | hops=0
"""
    )
    assert not err


def test_main_ipv4(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "some-target",
                "--routers_missing_warn",
                "194.45.196.23",
                "--routers_found_warn",
                "my-router",
                "--routers_found_crit",
            ],
            _MockRoutertracer(
                {
                    "fritz.box",
                    "192.168.178.1",
                    "fra1.mx204.ae6.de-cix.as48314.net",
                    "194.45.196.22",
                    "fra1.cc.as48314.net",
                    "80.81.196.134",
                },
                2,
            ),
        )
        == 1
    )
    out, err = capsys.readouterr()
    assert (
        out
        == """2 hops, missing routers: 194.45.196.23(!), bad routers: none
a -> b -> c
 | hops=2
"""
    )
    assert not err


def test_main_ipv6(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "some-target",
                "--routers_missing_warn",
                "--routers_missing_crit",
                "my-router",
                "--routers_found_warn",
                "my-router",
                "--routers_found_crit",
                "fra1.cc.as48314.net",
            ],
            _MockRoutertracer(
                {
                    "fritz.box",
                    "2001:a61:433:bc01:9a9b:cbff:fe06:2f84",
                    "fra1.mx204.ae6.de-cix.as48314.net",
                    "2001:4860::c:4002:365d",
                    "fra1.cc.as48314.net",
                    "2001:4860:0:1::10d9",
                },
                4,
            ),
        )
        == 2
    )
    out, err = capsys.readouterr()
    assert (
        out
        == """4 hops, missing routers: my-router(!!), bad routers: fra1.cc.as48314.net(!!)
a -> b -> c
 | hops=4
"""
    )
    assert not err
